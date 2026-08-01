from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
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
V2_REVIEW_PATH = 'docs/security-review/rc2-external-review.json'
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


def _timestamp(value: Any, reason: str) -> datetime:
    if not _aware_timestamp(value):
        raise AssertionError(reason)
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    return parsed.astimezone(timezone.utc)


def _validate_v2(
    record: Mapping[str, Any], *, expected_version: str, now: datetime
) -> Mapping[str, Any]:
    required = {
        'schema_version', 'status', 'version', 'source_commit', 'prepared_at',
        'published_at', 'observation_ends_at', 'completed_at',
        'minimum_observation_days', 'public_evidence_ref', 'frozen_inputs',
        'security_review', 'facade_exports', 'v1_records', 'rule', 'notes',
    }
    if set(record) != required:
        raise AssertionError('rc_window_v2_fields_drift')
    if record['schema_version'] != 'govengine.rc_window.v2':
        raise AssertionError('rc_window_v2_schema_mismatch')
    if record['version'] != expected_version or record['version'] != '1.0.0rc2':
        raise AssertionError('rc_window_v2_version_mismatch')
    if not isinstance(record['source_commit'], str) or not FULL_SHA.fullmatch(record['source_commit']):
        raise AssertionError('rc_window_v2_source_commit_invalid')
    status = record['status']
    if status not in {'prepared', 'active', 'completed'}:
        raise AssertionError('rc_window_v2_status_invalid')
    prepared_at = _timestamp(record['prepared_at'], 'rc_window_v2_prepared_at_invalid')
    minimum_days = record['minimum_observation_days']
    if type(minimum_days) is not int or minimum_days != 7:
        raise AssertionError('rc_window_v2_minimum_observation_days_invalid')
    if status == 'prepared':
        if any(record[field] is not None for field in ('published_at', 'observation_ends_at', 'completed_at')):
            raise AssertionError('rc_window_v2_prepared_has_public_timestamps')
        if record['public_evidence_ref'] != '':
            raise AssertionError('rc_window_v2_prepared_has_public_evidence')
    else:
        published_at = _timestamp(record['published_at'], 'rc_window_v2_published_at_invalid')
        ends_at = _timestamp(record['observation_ends_at'], 'rc_window_v2_observation_ends_at_invalid')
        if published_at < prepared_at or published_at > now or ends_at != published_at + timedelta(days=7):
            raise AssertionError('rc_window_v2_lifecycle_timing_invalid')
        if not isinstance(record['public_evidence_ref'], str) or not record['public_evidence_ref'].strip():
            raise AssertionError('rc_window_v2_public_evidence_missing')
        if status == 'active' and record['completed_at'] is not None:
            raise AssertionError('rc_window_v2_active_has_completed_at')
        if status == 'completed':
            completed_at = _timestamp(record['completed_at'], 'rc_window_v2_completed_at_invalid')
            if completed_at < ends_at or now < ends_at or completed_at > now:
                raise AssertionError('rc_window_v2_completed_timing_invalid')
    frozen = record['frozen_inputs']
    expected_frozen = {
        'pyproject_sha256': ROOT / 'pyproject.toml',
        'v1_compatibility_manifest_sha256': ROOT / 'govengine/v1_compatibility_manifest.json',
        'v1_conformance_manifest_sha256': ROOT / 'govengine/conformance/v1/manifest.json',
        'policy_reason_registry_sha256': ROOT / 'govengine/policy/reasons.py',
    }
    if not isinstance(frozen, Mapping) or set(frozen) != set(expected_frozen):
        raise AssertionError('rc_window_v2_frozen_inputs_invalid')
    for field, source in expected_frozen.items():
        if not isinstance(frozen[field], str) or not DIGEST.fullmatch(frozen[field]) or frozen[field] != _sha256(source):
            raise AssertionError(f'rc_window_v2_frozen_input_drift:{field}')
    review = record['security_review']
    if not isinstance(review, Mapping) or set(review) != {'path', 'sha256'} or review['path'] != V2_REVIEW_PATH or not isinstance(review['sha256'], str) or not DIGEST.fullmatch(review['sha256']):
        raise AssertionError('rc_window_v2_security_review_invalid')
    review_path = ROOT / str(review['path'])
    if not review_path.is_file() or review['sha256'] != _sha256(review_path):
        raise AssertionError('rc_window_v2_security_review_binding_invalid')
    review_data = json.loads(review_path.read_text(encoding='utf-8'))
    if review_data.get('source_commit') != record['source_commit']:
        raise AssertionError('rc_window_v2_review_source_mismatch')
    if type(record['facade_exports']) is not int or record['facade_exports'] != 40:
        raise AssertionError('rc_window_v2_facade_export_invalid')
    if type(record['v1_records']) is not int or record['v1_records'] != 15:
        raise AssertionError('rc_window_v2_v1_record_invalid')
    freeze = validate_v1_freeze()
    if record['facade_exports'] != freeze['facade_exports'] or record['v1_records'] != freeze['v1_records']:
        raise AssertionError('rc_window_v2_freeze_count_drift')
    if record['rule'] != 'schema_facade_corpus_or_reason_registry_change_requires_new_rc' or not isinstance(record['notes'], str) or not record['notes'].strip():
        raise AssertionError('rc_window_v2_rule_or_notes_invalid')
    return record


def validate_rc_window(
    path: Path = RECORD_PATH,
    *,
    require_published: bool = False,
    require_completed: bool = False,
    expected_version: str = '1.0.0rc1',
    now: datetime | None = None,
) -> Mapping[str, Any]:
    record = json.loads(
        path.read_text(encoding='utf-8'),
        object_pairs_hook=_strict_object,
        parse_constant=lambda value: (_ for _ in ()).throw(
            AssertionError(f'rc_window_non_finite:{value}')
        ),
    )
    if not isinstance(record, Mapping):
        raise AssertionError('rc_window_not_mapping')
    checked_now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if record.get('schema_version') == 'govengine.rc_window.v2':
        checked = _validate_v2(record, expected_version=expected_version, now=checked_now)
        if require_published and checked['status'] == 'prepared':
            raise AssertionError('published_rc_evidence_required')
        if require_completed and checked['status'] != 'completed':
            raise AssertionError('completed_rc_window_required')
        return checked
    required = {
        'schema_version',
        'status',
        'version',
        'prepared_at',
        'published_at',
        'observation_ends_at',
        'completed_at',
        'minimum_observation_days',
        'public_evidence_ref',
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
    status = record['status']
    if status not in {'prepared', 'active', 'completed'}:
        raise AssertionError('rc_window_status_invalid')
    if record['version'] != expected_version:
        raise AssertionError('rc_window_version_mismatch')
    prepared_at = _timestamp(
        record['prepared_at'],
        'rc_window_prepared_at_invalid',
    )
    minimum_days = record['minimum_observation_days']
    if (
        isinstance(minimum_days, bool)
        or not isinstance(minimum_days, int)
        or minimum_days != 7
    ):
        raise AssertionError('rc_window_minimum_observation_days_invalid')
    published_at_raw = record['published_at']
    observation_ends_at_raw = record['observation_ends_at']
    completed_at_raw = record['completed_at']
    evidence_ref = record['public_evidence_ref']
    checked_now = now or datetime.now(timezone.utc)
    if checked_now.tzinfo is None or checked_now.utcoffset() is None:
        raise AssertionError('rc_window_now_not_aware')
    checked_now = checked_now.astimezone(timezone.utc)
    if status == 'prepared':
        if any(
            value is not None
            for value in (
                published_at_raw,
                observation_ends_at_raw,
                completed_at_raw,
            )
        ):
            raise AssertionError('rc_window_prepared_has_public_timestamps')
        if evidence_ref != '':
            raise AssertionError('rc_window_prepared_has_public_evidence')
    else:
        published_at = _timestamp(
            published_at_raw,
            'rc_window_published_at_invalid',
        )
        observation_ends_at = _timestamp(
            observation_ends_at_raw,
            'rc_window_observation_ends_at_invalid',
        )
        if published_at < prepared_at:
            raise AssertionError('rc_window_published_before_prepared')
        if published_at > checked_now:
            raise AssertionError('rc_window_published_in_future')
        if observation_ends_at != published_at + timedelta(days=minimum_days):
            raise AssertionError('rc_window_observation_period_invalid')
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise AssertionError('rc_window_public_evidence_missing')
        if status == 'active':
            if completed_at_raw is not None:
                raise AssertionError('rc_window_active_has_completed_at')
        else:
            completed_at = _timestamp(
                completed_at_raw,
                'rc_window_completed_at_invalid',
            )
            if completed_at < observation_ends_at:
                raise AssertionError('rc_window_completed_too_early')
            if checked_now < observation_ends_at:
                raise AssertionError('rc_window_observation_period_not_elapsed')
            if completed_at > checked_now:
                raise AssertionError('rc_window_completed_in_future')
    if require_published and status == 'prepared':
        raise AssertionError('published_rc_evidence_required')
    if require_completed and status != 'completed':
        raise AssertionError('completed_rc_window_required')
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

    if type(record['facade_exports']) is not int or record['facade_exports'] != 40:
        raise AssertionError('rc_window_facade_export_invalid')
    if type(record['v1_records']) is not int or record['v1_records'] != 15:
        raise AssertionError('rc_window_v1_record_invalid')
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
    parser.add_argument('--expected-version', default='1.0.0rc1')
    parser.add_argument('--require-published', action='store_true')
    parser.add_argument('--require-completed', action='store_true')
    args = parser.parse_args(argv)
    record = validate_rc_window(
        args.record,
        require_published=args.require_published or args.require_completed,
        require_completed=args.require_completed,
        expected_version=args.expected_version,
    )
    print(
        'rc_window_ok:'
        f"version={record['version']}:status={record['status']}:"
        f"baseline={record['baseline_commit']}"
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
