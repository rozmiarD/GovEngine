from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_v1_freeze import validate_v1_freeze  # noqa: E402


RECORD_PATH = ROOT / 'docs' / 'rc-window' / '1.0.0rc1.json'
FULL_SHA = re.compile(r'^[0-9a-f]{40}$')
DIGEST = re.compile(r'^[0-9a-f]{64}$')
HASHED_FILES = {
    'v1_manifest_sha256': ROOT / 'govengine' / 'v1_compatibility_manifest.json',
    'conformance_manifest_sha256': (
        ROOT / 'govengine' / 'conformance' / 'v1' / 'manifest.json'
    ),
    'reason_registry_source_sha256': ROOT / 'govengine' / 'policy' / 'reasons.py',
}


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AssertionError(f'rc_window_duplicate_key:{key}')
        result[key] = value
    return result


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _aware_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def validate_rc_window(path: Path = RECORD_PATH) -> Mapping[str, Any]:
    record = json.loads(
        path.read_text(encoding='utf-8'),
        object_pairs_hook=_strict_object,
        parse_constant=lambda value: (_ for _ in ()).throw(
            AssertionError(f'rc_window_non_finite:{value}')
        ),
    )
    if not isinstance(record, Mapping):
        raise AssertionError('rc_window_not_mapping')
    required = {
        'schema_version',
        'status',
        'version',
        'started_at',
        'baseline_commit',
        *HASHED_FILES,
        'facade_exports',
        'v1_records',
        'rule',
        'notes',
    }
    if set(record) != required:
        raise AssertionError('rc_window_fields_drift')
    if record['schema_version'] != 'govengine.rc_window.v1':
        raise AssertionError('rc_window_schema_mismatch')
    if record['status'] != 'active' or record['version'] != '1.0.0rc1':
        raise AssertionError('rc_window_not_active_candidate')
    if not _aware_timestamp(record['started_at']):
        raise AssertionError('rc_window_started_at_invalid')
    if not isinstance(record['baseline_commit'], str) or not FULL_SHA.fullmatch(
        record['baseline_commit']
    ):
        raise AssertionError('rc_window_baseline_commit_invalid')
    if (
        record['rule']
        != 'schema_facade_corpus_or_reason_registry_change_requires_new_rc'
    ):
        raise AssertionError('rc_window_rule_drift')
    if not isinstance(record['notes'], str) or not record['notes'].strip():
        raise AssertionError('rc_window_notes_missing')

    freeze = validate_v1_freeze()
    if record['facade_exports'] != freeze['facade_exports']:
        raise AssertionError('rc_window_facade_export_drift')
    if record['v1_records'] != freeze['v1_records']:
        raise AssertionError('rc_window_v1_record_drift')
    for field, artifact in HASHED_FILES.items():
        expected = record[field]
        if not isinstance(expected, str) or not DIGEST.fullmatch(expected):
            raise AssertionError(f'rc_window_digest_invalid:{field}')
        if _sha256(artifact) != expected:
            raise AssertionError(f'rc_window_contract_drift:{field}')
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--record', type=Path, default=RECORD_PATH)
    args = parser.parse_args(argv)
    record = validate_rc_window(args.record)
    print(
        'rc_window_ok:'
        f"version={record['version']}:status={record['status']}:"
        f"baseline={record['baseline_commit']}"
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
