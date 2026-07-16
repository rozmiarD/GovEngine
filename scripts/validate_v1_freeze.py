from __future__ import annotations

import argparse
import ast
import importlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import govengine.v1 as facade  # noqa: E402


MANIFEST_PATH = ROOT / 'govengine' / 'v1_compatibility_manifest.json'
MIGRATION_PATH = ROOT / 'docs' / 'MIGRATING_TO_1.md'
V1_SCHEMA_MODULES = (
    'govengine.approvals',
    'govengine.capabilities',
    'govengine.governance',
    'govengine.governance_decision',
    'govengine.policy.activation',
    'govengine.policy.compiler',
    'govengine.policy.explain',
    'govengine.policy.reasons',
    'govengine.receipt_conformance',
    'govengine.scope_policy',
)


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AssertionError(f'v1_manifest_duplicate_key:{key}')
        result[key] = value
    return result


def load_v1_manifest(path: Path = MANIFEST_PATH) -> Mapping[str, Any]:
    value = json.loads(
        path.read_text(encoding='utf-8'),
        object_pairs_hook=_strict_object,
        parse_constant=lambda value: (_ for _ in ()).throw(
            AssertionError(f'v1_manifest_non_finite_number:{value}')
        ),
    )
    if not isinstance(value, Mapping):
        raise AssertionError('v1_manifest_not_mapping')
    return value


def _constant_value(reference: str) -> Any:
    module_name, separator, name = reference.rpartition('.')
    if not separator:
        raise AssertionError(f'v1_manifest_invalid_constant_ref:{reference}')
    module = importlib.import_module(module_name)
    if not hasattr(module, name):
        raise AssertionError(f'v1_manifest_missing_constant:{reference}')
    return getattr(module, name)


def _local_v1_constants(module_name: str) -> set[str]:
    path = ROOT.joinpath(*module_name.split('.')).with_suffix('.py')
    if not path.exists():
        path = ROOT.joinpath(*module_name.split('.'), '__init__.py')
    tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    constants: set[str] = set()
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        value = node.value
        if not isinstance(value, ast.Constant) or value.value != 'v1':
            continue
        targets = node.targets if isinstance(node, ast.Assign) else (node.target,)
        for target in targets:
            if isinstance(target, ast.Name) and target.id.endswith('SCHEMA_VERSION'):
                constants.add(f'{module_name}.{target.id}')
    return constants


def validate_v1_freeze(path: Path = MANIFEST_PATH) -> dict[str, int]:
    manifest = load_v1_manifest(path)
    if manifest.get('manifest_version') != 'v1':
        raise AssertionError('v1_manifest_version_mismatch')
    if manifest.get('release_line') != '1.x-candidate':
        raise AssertionError('v1_manifest_release_line_mismatch')
    if manifest.get('freeze_status') != 'frozen_for_1.0':
        raise AssertionError('v1_manifest_not_frozen_for_1_0')
    exports = manifest.get('facade_exports')
    if not isinstance(exports, list) or any(not isinstance(item, str) for item in exports):
        raise AssertionError('v1_manifest_invalid_facade_exports')
    if tuple(exports) != tuple(facade.__all__):
        raise AssertionError('v1_manifest_facade_drift')
    if len(exports) != 40 or len(exports) != len(set(exports)):
        raise AssertionError(f'v1_manifest_invalid_facade_size:{len(exports)}')

    records = manifest.get('v1_records')
    if not isinstance(records, list) or not records:
        raise AssertionError('v1_manifest_missing_records')
    record_types: set[str] = set()
    constants: set[str] = set()
    for raw in records:
        if not isinstance(raw, Mapping):
            raise AssertionError('v1_manifest_invalid_record')
        record_type = raw.get('record_type')
        constant = raw.get('schema_constant')
        if (
            not isinstance(record_type, str)
            or not isinstance(constant, str)
            or raw.get('schema_version') != 'v1'
            or raw.get('owner') != 'govengine'
            or raw.get('surface') not in {'facade', 'module-scoped'}
        ):
            raise AssertionError(f'v1_manifest_incomplete_record:{record_type}')
        if record_type in record_types or constant in constants:
            raise AssertionError(f'v1_manifest_duplicate_record:{record_type}')
        if _constant_value(constant) != 'v1':
            raise AssertionError(f'v1_manifest_schema_drift:{constant}')
        record_types.add(record_type)
        constants.add(constant)

    discovered = set().union(*(_local_v1_constants(name) for name in V1_SCHEMA_MODULES))
    if constants != discovered:
        missing = sorted(discovered - constants)
        extra = sorted(constants - discovered)
        raise AssertionError(f'v1_manifest_inventory_drift:missing={missing}:extra={extra}')

    legacy = manifest.get('legacy_facade_records')
    if not isinstance(legacy, list):
        raise AssertionError('v1_manifest_invalid_legacy_records')
    for raw in legacy:
        if (
            not isinstance(raw, Mapping)
            or not isinstance(raw.get('record_type'), str)
            or not isinstance(raw.get('schema_constant'), str)
            or not isinstance(raw.get('schema_version'), str)
        ):
            raise AssertionError('v1_manifest_incomplete_legacy_record')
        if _constant_value(raw['schema_constant']) != raw['schema_version']:
            raise AssertionError(
                f"v1_manifest_legacy_schema_drift:{raw['schema_constant']}"
            )

    compatibility = manifest.get('compatibility_policy')
    required_policy = {
        'v1_field_or_semantic_break',
        'optional_addition',
        'unknown_fields',
        'legacy_v0_1',
        'experimental_modules',
    }
    if not isinstance(compatibility, Mapping) or set(compatibility) != required_policy:
        raise AssertionError('v1_manifest_compatibility_policy_drift')
    migration = MIGRATION_PATH.read_text(encoding='utf-8')
    for marker in (
        'govengine==0.16.11',
        'govengine==1.0.0rc1',
        'rexecop==0.3.0rc3',
        'sclite-core==2.0.0',
        'Admission is not approval.',
        'GovEngine does not issue RExecOp runtime permits',
        'SCLite remains the final lifecycle, evidence and review-bundle authority',
        'Rollback means returning to a separate environment',
    ):
        if marker not in migration:
            raise AssertionError(f'v1_migration_guide_missing:{marker}')
    return {
        'facade_exports': len(exports),
        'v1_records': len(records),
        'legacy_records': len(legacy),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, default=MANIFEST_PATH)
    args = parser.parse_args(argv)
    report = validate_v1_freeze(args.manifest)
    print(
        'v1_freeze_ok:'
        f"facade_exports={report['facade_exports']}:"
        f"v1_records={report['v1_records']}:"
        f"legacy_records={report['legacy_records']}"
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
