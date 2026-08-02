from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.validate_rc2_release_records import ROOT, validate_rc2_release_records


SOURCE = 'a' * 40
SEEDED_REVIEW = ROOT / 'docs/security-review/rc2-external-review.json'
RC2_WINDOW = ROOT / 'docs/rc-window/1.0.0rc2.json'
PENDING_REVIEW = {
    'schema_version': 'govengine.rc2_external_security_review.v1',
    'source_commit': '',
    'artifacts': {
        'runner': 'github-hosted-runner',
        'wheel_sha256': '',
        'normalized_sdist_sha256': '',
    },
    'confidential_report_sha256': '',
    'reviewer': '',
    'reviewed_at': None,
    'verdict': 'pending_external_reviewer',
    'open_p0': None,
    'open_p1': None,
}


def _assert_live_review_posture(review_path: Path, window_path: Path) -> str:
    review = json.loads(review_path.read_text(encoding='utf-8'))
    assert isinstance(review, dict)
    if window_path.exists():
        assert review.get('verdict') == 'approved'
        return 'record_child_b'
    assert review == PENDING_REVIEW
    return 'source_a'


def _write_records(
    tmp_path: Path,
    wheel: Path,
    sdist: Path,
    *,
    confidential_report_sha256: str = 'b' * 64,
    reviewer: str = 'reviewer@example.invalid',
    open_p0: object = 0,
    open_p1: object = 0,
    facade_exports: object = 40,
    v1_records: object = 15,
) -> tuple[Path, Path]:
    review = tmp_path / 'review.json'
    review.write_text(json.dumps({
        'schema_version': 'govengine.rc2_external_security_review.v1', 'source_commit': SOURCE,
        'artifacts': {'runner': 'github-hosted-runner', 'wheel_sha256': hashlib.sha256(wheel.read_bytes()).hexdigest(), 'normalized_sdist_sha256': hashlib.sha256(sdist.read_bytes()).hexdigest()},
        'confidential_report_sha256': confidential_report_sha256, 'reviewer': reviewer,
        'reviewed_at': '2026-01-01T00:00:00Z', 'verdict': 'approved', 'open_p0': open_p0, 'open_p1': open_p1,
    }), encoding='utf-8')
    window = tmp_path / 'window.json'
    window.write_text(json.dumps({
        'schema_version': 'govengine.rc_window.v2', 'status': 'prepared', 'version': '1.0.0rc2', 'source_commit': SOURCE,
        'prepared_at': '2026-01-01T00:00:00Z', 'published_at': None, 'observation_ends_at': None, 'completed_at': None,
        'minimum_observation_days': 7, 'public_evidence_ref': '',
        'frozen_inputs': {'pyproject_sha256': hashlib.sha256((ROOT / 'pyproject.toml').read_bytes()).hexdigest(), 'v1_compatibility_manifest_sha256': hashlib.sha256((ROOT / 'govengine/v1_compatibility_manifest.json').read_bytes()).hexdigest(), 'v1_conformance_manifest_sha256': hashlib.sha256((ROOT / 'govengine/conformance/v1/manifest.json').read_bytes()).hexdigest(), 'policy_reason_registry_sha256': hashlib.sha256((ROOT / 'govengine/policy/reasons.py').read_bytes()).hexdigest()},
        'security_review': {'path': 'docs/security-review/rc2-external-review.json', 'sha256': hashlib.sha256(review.read_bytes()).hexdigest()},
        'facade_exports': facade_exports, 'v1_records': v1_records,
        'rule': 'schema_facade_corpus_or_reason_registry_change_requires_new_rc', 'notes': 'Synthetic fixture.',
    }), encoding='utf-8')
    return review, window


def test_accepts_bound_review_and_prepared_window(tmp_path: Path) -> None:
    wheel, sdist = tmp_path / 'a.whl', tmp_path / 'a.tar.gz'
    wheel.write_bytes(b'wheel')
    sdist.write_bytes(b'sdist')
    review, window = _write_records(tmp_path, wheel, sdist)
    validate_rc2_release_records(review=review, window=window, source_commit=SOURCE, wheel=wheel, sdist=sdist)


def test_live_review_matches_repository_posture_and_pending_fails_authentic_validation(
    tmp_path: Path,
) -> None:
    posture = _assert_live_review_posture(SEEDED_REVIEW, RC2_WINDOW)
    if posture == 'record_child_b':
        return

    wheel, sdist = tmp_path / 'a.whl', tmp_path / 'a.tar.gz'
    wheel.write_bytes(b'wheel')
    sdist.write_bytes(b'sdist')
    _, window = _write_records(tmp_path, wheel, sdist)
    with pytest.raises(ValueError, match='rc2_security_review_identity_invalid'):
        validate_rc2_release_records(
            review=SEEDED_REVIEW,
            window=window,
            source_commit=SOURCE,
            wheel=wheel,
            sdist=sdist,
        )


def test_live_review_posture_helper_accepts_source_a_and_record_child_b(
    tmp_path: Path,
) -> None:
    source_a = tmp_path / 'source-a'
    source_a.mkdir()
    pending_review = source_a / 'review.json'
    pending_review.write_text(json.dumps(PENDING_REVIEW), encoding='utf-8')
    assert _assert_live_review_posture(pending_review, source_a / 'window.json') == 'source_a'

    record_child = tmp_path / 'record-child-b'
    record_child.mkdir()
    wheel, sdist = record_child / 'a.whl', record_child / 'a.tar.gz'
    wheel.write_bytes(b'wheel')
    sdist.write_bytes(b'sdist')
    approved_review, window = _write_records(record_child, wheel, sdist)
    assert _assert_live_review_posture(approved_review, window) == 'record_child_b'


def test_rejects_window_field_duplication(tmp_path: Path) -> None:
    wheel, sdist = tmp_path / 'a.whl', tmp_path / 'a.tar.gz'
    wheel.write_bytes(b'wheel')
    sdist.write_bytes(b'sdist')
    review, window = _write_records(tmp_path, wheel, sdist)
    value = json.loads(window.read_text())
    value['reviewer'] = 'duplicated'
    window.write_text(json.dumps(value), encoding='utf-8')
    with pytest.raises(ValueError, match='rc2_window_fields_invalid'):
        validate_rc2_release_records(review=review, window=window, source_commit=SOURCE, wheel=wheel, sdist=sdist)


def test_rejects_reason_registry_hash_drift(tmp_path: Path) -> None:
    wheel, sdist = tmp_path / 'a.whl', tmp_path / 'a.tar.gz'
    wheel.write_bytes(b'wheel')
    sdist.write_bytes(b'sdist')
    review, window = _write_records(tmp_path, wheel, sdist)
    value = json.loads(window.read_text())
    value['frozen_inputs']['policy_reason_registry_sha256'] = '0' * 64
    window.write_text(json.dumps(value), encoding='utf-8')
    with pytest.raises(ValueError, match='rc2_window_frozen_input_hash_mismatch'):
        validate_rc2_release_records(review=review, window=window, source_commit=SOURCE, wheel=wheel, sdist=sdist)


@pytest.mark.parametrize(
    ('field', 'invalid_value'),
    (
        ('facade_exports', False),
        ('facade_exports', 40.0),
        ('facade_exports', '40'),
        ('facade_exports', None),
        ('v1_records', False),
        ('v1_records', 15.0),
        ('v1_records', '15'),
        ('v1_records', None),
    ),
)
def test_rejects_non_integer_v2_freeze_counts(
    tmp_path: Path, field: str, invalid_value: object
) -> None:
    wheel, sdist = tmp_path / 'a.whl', tmp_path / 'a.tar.gz'
    wheel.write_bytes(b'wheel')
    sdist.write_bytes(b'sdist')
    review, window = _write_records(tmp_path, wheel, sdist, **{field: invalid_value})

    with pytest.raises(ValueError, match='rc2_window_prepared_lifecycle_invalid'):
        validate_rc2_release_records(
            review=review, window=window, source_commit=SOURCE, wheel=wheel, sdist=sdist
        )


@pytest.mark.parametrize(
    ('report_hash', 'reviewer', 'expected'),
    (
        ('0' * 64, 'reviewer@example.invalid', 'synthetic_report_rejected'),
        ('b' * 64, 'synthetic-record-only-gate', 'synthetic_reviewer_rejected'),
    ),
)
def test_strict_mode_rejects_exact_synthetic_evidence(
    tmp_path: Path, report_hash: str, reviewer: str, expected: str
) -> None:
    wheel, sdist = tmp_path / 'a.whl', tmp_path / 'a.tar.gz'
    wheel.write_bytes(b'wheel')
    sdist.write_bytes(b'sdist')
    review, window = _write_records(
        tmp_path,
        wheel,
        sdist,
        confidential_report_sha256=report_hash,
        reviewer=reviewer,
    )
    with pytest.raises(ValueError, match=expected):
        validate_rc2_release_records(
            review=review, window=window, source_commit=SOURCE, wheel=wheel, sdist=sdist
        )


def test_synthetic_mode_accepts_exact_synthetic_fixture(tmp_path: Path) -> None:
    wheel, sdist = tmp_path / 'a.whl', tmp_path / 'a.tar.gz'
    wheel.write_bytes(b'wheel')
    sdist.write_bytes(b'sdist')
    review, window = _write_records(
        tmp_path,
        wheel,
        sdist,
        confidential_report_sha256='0' * 64,
        reviewer='synthetic-record-only-gate',
    )
    validate_rc2_release_records(
        review=review,
        window=window,
        source_commit=SOURCE,
        wheel=wheel,
        sdist=sdist,
        allow_synthetic=True,
    )


@pytest.mark.parametrize('field', ('open_p0', 'open_p1'))
@pytest.mark.parametrize(
    'invalid_value',
    (False, True, 0.0, 1.0, '0', None, [], {}, -1, 1),
)
def test_rejects_non_exact_integer_zero_review_counters(
    tmp_path: Path, field: str, invalid_value: object
) -> None:
    wheel, sdist = tmp_path / 'a.whl', tmp_path / 'a.tar.gz'
    wheel.write_bytes(b'wheel')
    sdist.write_bytes(b'sdist')
    counters = {field: invalid_value}
    review, window = _write_records(tmp_path, wheel, sdist, **counters)
    with pytest.raises(ValueError, match='rc2_security_review_open_counter_invalid'):
        validate_rc2_release_records(
            review=review, window=window, source_commit=SOURCE, wheel=wheel, sdist=sdist
        )
