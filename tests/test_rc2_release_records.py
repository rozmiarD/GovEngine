from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.validate_rc2_release_records import ROOT, validate_rc2_release_records


SOURCE = 'a' * 40


def _write_records(
    tmp_path: Path,
    wheel: Path,
    sdist: Path,
    *,
    confidential_report_sha256: str = 'b' * 64,
    reviewer: str = 'reviewer@example.invalid',
    open_p0: object = 0,
    open_p1: object = 0,
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
        'schema_version': 'govengine.rc2_window.v1', 'status': 'prepared', 'source_commit': SOURCE,
        'frozen_inputs': {'pyproject_sha256': hashlib.sha256((ROOT / 'pyproject.toml').read_bytes()).hexdigest(), 'v1_compatibility_manifest_sha256': hashlib.sha256((ROOT / 'govengine/v1_compatibility_manifest.json').read_bytes()).hexdigest(), 'v1_conformance_manifest_sha256': hashlib.sha256((ROOT / 'govengine/conformance/v1/manifest.json').read_bytes()).hexdigest(), 'policy_reason_registry_sha256': hashlib.sha256((ROOT / 'govengine/policy/reasons.py').read_bytes()).hexdigest()},
        'security_review': {'path': 'docs/security-review/rc2-external-review.json', 'sha256': hashlib.sha256(review.read_bytes()).hexdigest()},
    }), encoding='utf-8')
    return review, window


def test_accepts_bound_review_and_prepared_window(tmp_path: Path) -> None:
    wheel, sdist = tmp_path / 'a.whl', tmp_path / 'a.tar.gz'
    wheel.write_bytes(b'wheel')
    sdist.write_bytes(b'sdist')
    review, window = _write_records(tmp_path, wheel, sdist)
    validate_rc2_release_records(review=review, window=window, source_commit=SOURCE, wheel=wheel, sdist=sdist)


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
