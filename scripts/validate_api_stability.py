from __future__ import annotations

import argparse
import ast
import inspect
import re
import sys
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import govengine  # noqa: E402


MATRIX_PATH = ROOT / 'docs' / 'API_STABILITY_MATRIX.md'
MATRIX_STATUSES = (
    'stable',
    'alpha',
    'fixture',
    'deprecated',
    'internal-exposed',
)


def matrix_inventory(path: Path = MATRIX_PATH) -> dict[str, set[str]]:
    inventory = {status: set() for status in MATRIX_STATUSES}
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line.startswith('| '):
            continue
        cells = [cell.strip() for cell in line.strip().strip('|').split('|')]
        if len(cells) < 3 or cells[0] not in inventory:
            continue
        inventory[cells[0]].update(
            re.findall(r'`([A-Za-z_][A-Za-z0-9_]*)`', cells[2])
        )
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
    imports: set[str] = set()
    for path in sorted(root.rglob('*.py')):
        try:
            tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        except (OSError, UnicodeDecodeError, SyntaxError) as exc:
            raise AssertionError(f'consumer_import_scan_failed:{path}:{exc}') from exc
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == 'govengine':
                imports.update(alias.name for alias in node.names)
    return imports


def validate_api_stability(
    *,
    matrix_path: Path = MATRIX_PATH,
    consumer_roots: tuple[Path, ...] = (),
) -> dict[str, int]:
    inventory = matrix_inventory(matrix_path)
    classified_top_level = set().union(
        inventory['stable'],
        inventory['alpha'],
        inventory['fixture'],
        inventory['deprecated'],
    )
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

    matrix_text = matrix_path.read_text(encoding='utf-8')
    for status in MATRIX_STATUSES:
        expected = f'- {status} exports: {len(inventory[status])}'
        if expected not in matrix_text:
            raise AssertionError(f'api_stability_summary_drift:{expected}')

    allowed_imports = classified_top_level | inventory['internal-exposed']
    consumer_import_count = 0
    for root in consumer_roots:
        imports = consumer_top_level_imports(root)
        consumer_import_count += len(imports)
        unsupported = sorted(imports - allowed_imports)
        if unsupported:
            raise AssertionError(
                f'undocumented_consumer_top_level_imports:{root}:{unsupported}'
            )

    return {
        **{status: len(inventory[status]) for status in MATRIX_STATUSES},
        'top_level': len(govengine.__all__),
        'consumer_imports': consumer_import_count,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--consumer-root',
        action='append',
        default=[],
        type=Path,
        help='Optional consumer source root to scan for from-govengine imports.',
    )
    args = parser.parse_args(argv)
    report = validate_api_stability(consumer_roots=tuple(args.consumer_root))
    print(
        'api_stability_ok:'
        f"top_level={report['top_level']}:"
        f"alpha={report['alpha']}:fixture={report['fixture']}:"
        f"internal_exposed={report['internal-exposed']}:"
        f"consumer_imports={report['consumer_imports']}"
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
