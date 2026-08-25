from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
import importlib
import inspect
import re
import sys
import tomllib
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import govengine  # noqa: E402


MATRIX_PATH = ROOT / 'docs' / 'API_STABILITY_MATRIX.md'
MATRIX_STATUSES = (
    'v1-candidate',
    'adapter',
    'experimental',
    'fixture',
    'remove',
    'internal-exposed',
)
TOP_LEVEL_CLASSIFICATIONS = MATRIX_STATUSES[:-1]
IGNORED_CONSUMER_PARTS = frozenset({'.git', '.mypy_cache', '.pytest_cache', '.ruff_cache', '.tox', '.venv', 'build', 'dist', 'venv'})
VALIDATION_MODES = frozenset({'local', 'cross-repo'})
DIRECT_CONSUMER_PROJECTS = frozenset({'rexecop', 'tecrax'})


@dataclass(frozen=True)
class ApiMatrixRecord:
    classification: str
    source: str
    exports: tuple[str, ...]
    migration_note: str


@dataclass(frozen=True)
class ConsumerImport:
    import_path: str
    classification: str
    owner: str
    source_file: str
    line: int


def matrix_records(path: Path = MATRIX_PATH) -> tuple[ApiMatrixRecord, ...]:
    records: list[ApiMatrixRecord] = []
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line.startswith('| '):
            continue
        cells = [cell.strip() for cell in line.strip().strip('|').split('|')]
        if len(cells) < 4 or cells[0] not in MATRIX_STATUSES:
            continue
        records.append(
            ApiMatrixRecord(
                classification=cells[0],
                source=cells[1],
                exports=tuple(re.findall(r'`([A-Za-z_][A-Za-z0-9_]*)`', cells[2])),
                migration_note=cells[3],
            )
        )
    return tuple(records)


def matrix_inventory(path: Path = MATRIX_PATH) -> dict[str, set[str]]:
    inventory: dict[str, set[str]] = {status: set() for status in MATRIX_STATUSES}
    for record in matrix_records(path):
        inventory[record.classification].update(record.exports)
    return inventory


def module_owned_exposed_callables(module: ModuleType = govengine) -> set[str]:
    return {
        name
        for name, value in vars(module).items()
        if not name.startswith('_')
        and name not in module.__all__
        and (inspect.isfunction(value) or inspect.isclass(value))
        and str(getattr(value, '__module__', '')).startswith('govengine')
    }


def consumer_top_level_imports(root: Path) -> set[str]:
    return {
        record.import_path.removeprefix('govengine.')
        for record in consumer_import_map(root)
        if record.owner == 'govengine' and record.import_path != 'govengine'
    }


def consumer_import_map(root: Path, *, matrix_path: Path = MATRIX_PATH) -> tuple[ConsumerImport, ...]:
    symbol_records: dict[str, ApiMatrixRecord] = {}
    module_symbol_records: dict[tuple[str, str], ApiMatrixRecord] = {}
    for record in matrix_records(matrix_path):
        module = record.source.split()[0]
        for name in record.exports:
            symbol_records[name] = record
            module_symbol_records[(module, name)] = record

    imports: list[ConsumerImport] = []
    for path in sorted(root.rglob('*.py')):
        if any(part in IGNORED_CONSUMER_PARTS for part in path.parts):
            continue
        try:
            tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        except (OSError, UnicodeDecodeError, SyntaxError) as exc:
            raise AssertionError(f'consumer_import_scan_failed:{path}:{exc}') from exc
        source_file = str(path.relative_to(root))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == 'govengine' or alias.name.startswith('govengine.'):
                        imports.append(
                            ConsumerImport(
                                import_path=alias.name,
                                classification='package' if alias.name == 'govengine' else 'deep-only',
                                owner=alias.name,
                                source_file=source_file,
                                line=node.lineno,
                            )
                        )
            if not isinstance(node, ast.ImportFrom) or not node.module:
                continue
            if node.module != 'govengine' and not node.module.startswith('govengine.'):
                continue
            for alias in node.names:
                import_path = f'{node.module}.{alias.name}'
                if node.module == 'govengine':
                    record = symbol_records.get(alias.name)
                else:
                    record = module_symbol_records.get((node.module, alias.name)) or symbol_records.get(alias.name)
                imports.append(
                    ConsumerImport(
                        import_path=import_path,
                        classification=record.classification if record else 'deep-only',
                        owner=node.module,
                        source_file=source_file,
                        line=node.lineno,
                    )
                )
    return tuple(sorted(set(imports), key=lambda item: (item.import_path, item.source_file, item.line)))


def _consumer_project(root: Path) -> str:
    path = root / 'pyproject.toml'
    if not path.is_file():
        raise AssertionError(f'api_consumer_pyproject_missing:{root}')
    project = tomllib.loads(path.read_text(encoding='utf-8')).get('project')
    if not isinstance(project, dict):
        raise AssertionError(f'api_consumer_project_missing:{root}')
    name = project.get('name')
    if not isinstance(name, str) or not name:
        raise AssertionError(f'api_consumer_project_identity_invalid:{root}')
    return name.lower().replace('_', '-')


def _validate_consumer_roots(
    *,
    mode: str,
    consumer_roots: tuple[Path, ...],
) -> tuple[Path, ...]:
    if mode not in VALIDATION_MODES:
        raise AssertionError(f'api_validation_mode_invalid:{mode}')
    if mode == 'local':
        if consumer_roots:
            raise AssertionError('api_local_mode_rejects_consumer_roots')
        return ()

    by_project: dict[str, Path] = {}
    for root in consumer_roots:
        project = _consumer_project(root)
        if project in by_project:
            raise AssertionError(f'api_consumer_project_duplicate:{project}')
        by_project[project] = root
    if set(by_project) != set(DIRECT_CONSUMER_PROJECTS):
        raise AssertionError(
            'api_cross_repo_consumer_inventory_mismatch:'
            f'expected={sorted(DIRECT_CONSUMER_PROJECTS)}:'
            f'actual={sorted(by_project)}'
        )
    return tuple(by_project[project] for project in sorted(by_project))


def validate_api_stability(
    *,
    mode: str = 'local',
    matrix_path: Path = MATRIX_PATH,
    consumer_roots: tuple[Path, ...] = (),
) -> dict[str, int | str]:
    checked_consumer_roots = _validate_consumer_roots(
        mode=mode,
        consumer_roots=consumer_roots,
    )
    records = matrix_records(matrix_path)
    seen_exports: dict[str, str] = {}
    for record in records:
        if not record.source.startswith('govengine.') or not record.exports or not record.migration_note:
            raise AssertionError(f'incomplete_api_classification:{record.source}')
        for name in record.exports:
            previous = seen_exports.get(name)
            if previous:
                raise AssertionError(f'duplicate_api_classification:{name}:{previous}:{record.classification}')
            seen_exports[name] = record.classification

    inventory = matrix_inventory(matrix_path)
    classified_top_level = set().union(*(inventory[status] for status in TOP_LEVEL_CLASSIFICATIONS))
    if classified_top_level != set(govengine.__all__):
        missing = sorted(set(govengine.__all__) - classified_top_level)
        extra = sorted(classified_top_level - set(govengine.__all__))
        raise AssertionError(f'api_stability_matrix_drift:missing={missing}:extra={extra}')

    exposed = module_owned_exposed_callables()
    if exposed != inventory['internal-exposed']:
        missing = sorted(exposed - inventory['internal-exposed'])
        extra = sorted(inventory['internal-exposed'] - exposed)
        raise AssertionError(
            f'api_internal_exposed_inventory_drift:missing={missing}:extra={extra}'
        )

    facade = importlib.import_module('govengine.v1')
    facade_exports = set(getattr(facade, '__all__', ()))
    if facade_exports != inventory['v1-candidate']:
        missing = sorted(inventory['v1-candidate'] - facade_exports)
        extra = sorted(facade_exports - inventory['v1-candidate'])
        raise AssertionError(f'v1_facade_matrix_drift:missing={missing}:extra={extra}')
    if not facade_exports or len(facade_exports) > 40:
        raise AssertionError(f'invalid_v1_facade_size:{len(facade_exports)}')
    allowed_v1_modules = (
        'govengine.api',
        'govengine.approvals',
        'govengine.governance',
        'govengine.governance_decision',
        'govengine.governance_trace',
        'govengine.policy',
    )
    for name in facade_exports:
        value = getattr(facade, name)
        source_module = str(getattr(value, '__module__', ''))
        if source_module and not source_module.startswith(allowed_v1_modules):
            raise AssertionError(f'v1_facade_forbidden_owner:{name}:{source_module}')

    matrix_text = matrix_path.read_text(encoding='utf-8')
    for status in MATRIX_STATUSES:
        expected = f'- {status} exports: {len(inventory[status])}'
        if expected not in matrix_text:
            raise AssertionError(f'api_stability_summary_drift:{expected}')

    allowed_imports = classified_top_level | inventory['internal-exposed']
    consumer_import_count = 0
    for root in checked_consumer_roots:
        imports = consumer_top_level_imports(root)
        consumer_import_count += len(imports)
        unsupported = sorted(imports - allowed_imports)
        if unsupported:
            raise AssertionError(
                f'undocumented_consumer_top_level_imports:{root}:{unsupported}'
            )

    return {
        'mode': mode,
        **{status: len(inventory[status]) for status in MATRIX_STATUSES},
        'top_level': len(govengine.__all__),
        'consumer_imports': consumer_import_count,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--local', action='store_true')
    mode.add_argument('--cross-repo', action='store_true')
    parser.add_argument(
        '--consumer-root',
        action='append',
        default=[],
        type=Path,
        help='RExecOp or Tecrax source root; cross-repo mode requires both.',
    )
    args = parser.parse_args(argv)
    selected_mode = 'cross-repo' if args.cross_repo else 'local'
    report = validate_api_stability(
        mode=selected_mode,
        consumer_roots=tuple(args.consumer_root),
    )
    print(
        f'api_stability_ok:{report["mode"]}:'
        f"top_level={report['top_level']}:"
        f"v1_candidate={report['v1-candidate']}:adapter={report['adapter']}:"
        f"experimental={report['experimental']}:fixture={report['fixture']}:remove={report['remove']}:"
        f"internal_exposed={report['internal-exposed']}:"
        f"consumer_imports={report['consumer_imports']}"
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
