from __future__ import annotations

import json
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from scripts.validate_rc_window import RECORD_PATH, validate_rc_window
import scripts.validate_rc_window as validator


def test_rc_window_matches_frozen_contract_inputs() -> None:
    record = validate_rc_window()

    assert record['version'] == '1.0.0rc1'
    assert record['status'] == 'active'
    assert record['published_at'] == '2026-07-20T17:39:58.058090Z'
    assert record['observation_ends_at'] == '2026-07-27T17:39:58.058090Z'
    assert record['minimum_observation_days'] == 7
    assert record['facade_exports'] == 40
    assert record['v1_records'] == 15


def test_main_reports_v1_baseline_commit(capsys: pytest.CaptureFixture[str]) -> None:
    record = json.loads(RECORD_PATH.read_text(encoding='utf-8'))

    assert validator.main([]) == 0

    assert capsys.readouterr().out == (
        'rc_window_ok:version=1.0.0rc1:status=active:'
        f"baseline={record['baseline_commit']}\n"
    )


def test_rc_window_rejects_contract_digest_drift(tmp_path: Path) -> None:
    record = json.loads(RECORD_PATH.read_text(encoding='utf-8'))
    record['v1_manifest_sha256'] = '0' * 64
    path = tmp_path / 'rc-window.json'
    path.write_text(json.dumps(record), encoding='utf-8')

    with pytest.raises(
        AssertionError,
        match='rc_window_contract_drift:v1_manifest_sha256',
    ):
        validate_rc_window(path)


@pytest.mark.parametrize(
    ('field', 'invalid_value', 'reason'),
    (
        ('facade_exports', False, 'rc_window_facade_export_invalid'),
        ('facade_exports', 40.0, 'rc_window_facade_export_invalid'),
        ('facade_exports', '40', 'rc_window_facade_export_invalid'),
        ('facade_exports', None, 'rc_window_facade_export_invalid'),
        ('v1_records', False, 'rc_window_v1_record_invalid'),
        ('v1_records', 15.0, 'rc_window_v1_record_invalid'),
        ('v1_records', '15', 'rc_window_v1_record_invalid'),
        ('v1_records', None, 'rc_window_v1_record_invalid'),
    ),
)
def test_rc_window_rejects_non_integer_freeze_counts(
    tmp_path: Path, field: str, invalid_value: object, reason: str
) -> None:
    record = json.loads(RECORD_PATH.read_text(encoding='utf-8'))
    record[field] = invalid_value
    path = tmp_path / 'rc-window.json'
    path.write_text(json.dumps(record), encoding='utf-8')

    with pytest.raises(AssertionError, match=reason):
        validate_rc_window(path)


def test_active_window_is_publication_evidence() -> None:
    checked = validate_rc_window(require_published=True)

    assert checked['status'] == 'active'


def test_prepared_window_is_not_publication_evidence(tmp_path: Path) -> None:
    record = json.loads(RECORD_PATH.read_text(encoding='utf-8'))
    record.update(
        {
            'status': 'prepared',
            'published_at': None,
            'observation_ends_at': None,
            'public_evidence_ref': '',
        }
    )
    path = tmp_path / 'rc-window.json'
    path.write_text(json.dumps(record), encoding='utf-8')

    with pytest.raises(
        AssertionError,
        match='published_rc_evidence_required',
    ):
        validate_rc_window(path, require_published=True)


def test_active_window_starts_at_publication(tmp_path: Path) -> None:
    record = json.loads(RECORD_PATH.read_text(encoding='utf-8'))
    published_at = datetime(2026, 7, 20, 12, tzinfo=timezone.utc)
    record.update(
        {
            'status': 'active',
            'published_at': published_at.isoformat(),
            'observation_ends_at': (
                published_at + timedelta(days=7)
            ).isoformat(),
            'public_evidence_ref': (
                'https://pypi.org/project/govengine/1.0.0rc1/'
            ),
        }
    )
    path = tmp_path / 'rc-window.json'
    path.write_text(json.dumps(record), encoding='utf-8')

    checked = validate_rc_window(
        path,
        require_published=True,
        now=published_at,
    )

    assert checked['status'] == 'active'


def test_active_window_rejects_future_publication(tmp_path: Path) -> None:
    record = json.loads(RECORD_PATH.read_text(encoding='utf-8'))
    published_at = datetime(2026, 7, 20, 12, tzinfo=timezone.utc)
    record.update(
        {
            'status': 'active',
            'published_at': published_at.isoformat(),
            'observation_ends_at': (
                published_at + timedelta(days=7)
            ).isoformat(),
            'public_evidence_ref': (
                'https://pypi.org/project/govengine/1.0.0rc1/'
            ),
        }
    )
    path = tmp_path / 'rc-window.json'
    path.write_text(json.dumps(record), encoding='utf-8')

    with pytest.raises(
        AssertionError,
        match='rc_window_published_in_future',
    ):
        validate_rc_window(
            path,
            require_published=True,
            now=published_at - timedelta(seconds=1),
        )


def test_completed_window_requires_elapsed_observation_period(
    tmp_path: Path,
) -> None:
    record = json.loads(RECORD_PATH.read_text(encoding='utf-8'))
    published_at = datetime(2026, 7, 20, 12, tzinfo=timezone.utc)
    observation_ends_at = published_at + timedelta(days=7)
    record.update(
        {
            'status': 'completed',
            'published_at': published_at.isoformat(),
            'observation_ends_at': observation_ends_at.isoformat(),
            'completed_at': observation_ends_at.isoformat(),
            'public_evidence_ref': (
                'https://pypi.org/project/govengine/1.0.0rc1/'
            ),
        }
    )
    path = tmp_path / 'rc-window.json'
    path.write_text(json.dumps(record), encoding='utf-8')

    with pytest.raises(
        AssertionError,
        match='rc_window_observation_period_not_elapsed',
    ):
        validate_rc_window(
            path,
            require_completed=True,
            now=observation_ends_at - timedelta(seconds=1),
        )

    checked = validate_rc_window(
        path,
        require_completed=True,
        now=observation_ends_at,
    )
    assert checked['status'] == 'completed'


def _write_v2_prepared_window(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    facade_exports: object = 40,
    v1_records: object = 15,
) -> Path:
    root = tmp_path
    for relative in (
        'pyproject.toml', 'govengine/v1_compatibility_manifest.json',
        'govengine/conformance/v1/manifest.json', 'govengine/policy/reasons.py',
    ):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((Path.cwd() / relative).read_bytes())
    review_path = root / 'docs/security-review/rc2-external-review.json'
    review_path.parent.mkdir(parents=True)
    source_commit = 'a' * 40
    review_path.write_text(json.dumps({'source_commit': source_commit}), encoding='utf-8')
    frozen = {
        'pyproject_sha256': hashlib.sha256((root / 'pyproject.toml').read_bytes()).hexdigest(),
        'v1_compatibility_manifest_sha256': hashlib.sha256((root / 'govengine/v1_compatibility_manifest.json').read_bytes()).hexdigest(),
        'v1_conformance_manifest_sha256': hashlib.sha256((root / 'govengine/conformance/v1/manifest.json').read_bytes()).hexdigest(),
        'policy_reason_registry_sha256': hashlib.sha256((root / 'govengine/policy/reasons.py').read_bytes()).hexdigest(),
    }
    record = {'schema_version': 'govengine.rc_window.v2', 'status': 'prepared', 'version': '1.0.0rc2', 'source_commit': source_commit, 'prepared_at': '2026-01-01T00:00:00Z', 'published_at': None, 'observation_ends_at': None, 'completed_at': None, 'minimum_observation_days': 7, 'public_evidence_ref': '', 'frozen_inputs': frozen, 'security_review': {'path': 'docs/security-review/rc2-external-review.json', 'sha256': hashlib.sha256(review_path.read_bytes()).hexdigest()}, 'facade_exports': facade_exports, 'v1_records': v1_records, 'rule': 'schema_facade_corpus_or_reason_registry_change_requires_new_rc', 'notes': 'Prepared review-bound candidate.'}
    window = root / 'docs/rc-window/1.0.0rc2.json'
    window.parent.mkdir(parents=True)
    window.write_text(json.dumps(record), encoding='utf-8')
    monkeypatch.setattr(validator, 'ROOT', root)
    return window


def test_v2_prepared_window_binds_current_frozen_inputs_and_review(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = _write_v2_prepared_window(tmp_path, monkeypatch)
    assert validate_rc_window(window, expected_version='1.0.0rc2')['status'] == 'prepared'


def test_main_reports_v2_source_commit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    window = _write_v2_prepared_window(tmp_path, monkeypatch)

    assert validator.main([
        '--record', str(window), '--expected-version', '1.0.0rc2',
    ]) == 0

    assert capsys.readouterr().out == (
        'rc_window_ok:version=1.0.0rc2:status=prepared:'
        f"source={'a' * 40}\n"
    )


@pytest.mark.parametrize(
    ('field', 'invalid_value', 'reason'),
    (
        ('facade_exports', False, 'rc_window_v2_facade_export_invalid'),
        ('facade_exports', 40.0, 'rc_window_v2_facade_export_invalid'),
        ('facade_exports', '40', 'rc_window_v2_facade_export_invalid'),
        ('facade_exports', None, 'rc_window_v2_facade_export_invalid'),
        ('v1_records', False, 'rc_window_v2_v1_record_invalid'),
        ('v1_records', 15.0, 'rc_window_v2_v1_record_invalid'),
        ('v1_records', '15', 'rc_window_v2_v1_record_invalid'),
        ('v1_records', None, 'rc_window_v2_v1_record_invalid'),
    ),
)
def test_v2_prepared_window_rejects_non_integer_freeze_counts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    invalid_value: object,
    reason: str,
) -> None:
    window = _write_v2_prepared_window(
        tmp_path,
        monkeypatch,
        **{field: invalid_value},
    )

    with pytest.raises(AssertionError, match=reason):
        validate_rc_window(window, expected_version='1.0.0rc2')
