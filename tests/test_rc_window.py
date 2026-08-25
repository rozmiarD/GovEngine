from __future__ import annotations

import json
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from scripts.validate_rc_window import RECORD_PATH, validate_rc_window
import scripts.validate_rc_window as validator


def test_rc_window_matches_frozen_contract_inputs() -> None:
    record = validate_rc_window(history_mode=True)

    assert record['version'] == '1.0.0rc1'
    assert record['status'] == 'elapsed_unclosed'
    assert record['record_status'] == 'active'
    assert record['published_at'] == '2026-07-20T17:39:58.058090Z'
    assert record['observation_ends_at'] == '2026-07-27T17:39:58.058090Z'
    assert record['minimum_observation_days'] == 7
    assert record['facade_exports'] == 40
    assert record['v1_records'] == 15


def test_main_reports_v1_baseline_commit(capsys: pytest.CaptureFixture[str]) -> None:
    record = json.loads(RECORD_PATH.read_text(encoding='utf-8'))

    assert validator.main(['--history-mode']) == 0

    assert capsys.readouterr().out == (
        'rc_window_ok:version=1.0.0rc1:status=elapsed_unclosed:record_status=active:'
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
    checked = validate_rc_window(
        require_published=True,
        now=datetime(2026, 7, 21, tzinfo=timezone.utc),
    )

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
    closure_path, _ = _write_closure_record(
        path,
        completed_at=observation_ends_at,
    )

    with pytest.raises(
        AssertionError,
        match='rc_window_observation_period_not_elapsed',
    ):
        validate_rc_window(
            path,
            require_completed=True,
            closure_path=closure_path,
            now=observation_ends_at - timedelta(seconds=1),
        )

    checked = validate_rc_window(
        path,
        require_completed=True,
        closure_path=closure_path,
        now=observation_ends_at,
    )
    assert checked['status'] == 'completed'


def _write_closure_record(
    record_path: Path,
    *,
    completed_at: datetime,
) -> tuple[Path, dict[str, object]]:
    record = json.loads(record_path.read_text(encoding='utf-8'))
    evidence_path = record_path.parent / 'closure-evidence.json'
    evidence_path.write_text('{"open_p0":0,"open_p1":0}\n', encoding='utf-8')
    closure: dict[str, object] = {
        'schema_version': 'govengine.rc_window_closure.v1',
        'status': 'completed',
        'version': record['version'],
        'supersedes_record_sha256': hashlib.sha256(record_path.read_bytes()).hexdigest(),
        'published_at': record['published_at'],
        'observation_ends_at': record['observation_ends_at'],
        'completed_at': completed_at.isoformat(),
        'closure_evidence': {
            'path': evidence_path.name,
            'sha256': hashlib.sha256(evidence_path.read_bytes()).hexdigest(),
        },
    }
    closure_path = record_path.parent / 'closure.json'
    closure_path.write_text(json.dumps(closure), encoding='utf-8')
    return closure_path, closure


def test_active_window_derives_elapsed_unclosed_at_and_after_expiry(
    tmp_path: Path,
) -> None:
    record = json.loads(RECORD_PATH.read_text(encoding='utf-8'))
    published_at = datetime(2026, 7, 20, 12, tzinfo=timezone.utc)
    ends_at = published_at + timedelta(days=7)
    record.update({
        'status': 'active',
        'published_at': published_at.isoformat(),
        'observation_ends_at': ends_at.isoformat(),
        'completed_at': None,
        'public_evidence_ref': 'https://pypi.org/project/govengine/1.0.0rc1/',
    })
    path = tmp_path / 'rc-window.json'
    path.write_text(json.dumps(record), encoding='utf-8')
    closure_path, _ = _write_closure_record(path, completed_at=ends_at)

    assert validate_rc_window(path, now=ends_at - timedelta(seconds=1))['status'] == 'active'
    with pytest.raises(AssertionError, match='rc_window_elapsed_unclosed'):
        validate_rc_window(path, now=ends_at)
    with pytest.raises(AssertionError, match='rc_window_elapsed_unclosed'):
        validate_rc_window(path, now=ends_at + timedelta(seconds=1))
    historical = validate_rc_window(path, now=ends_at, history_mode=True)
    assert historical['status'] == 'elapsed_unclosed'
    assert historical['record_status'] == 'active'
    completed = validate_rc_window(
        path,
        require_completed=True,
        closure_path=closure_path,
        now=ends_at,
    )
    assert completed['status'] == 'completed'
    assert completed['record_status'] == 'active'


def test_completed_window_requires_forward_closure_record(tmp_path: Path) -> None:
    record = json.loads(RECORD_PATH.read_text(encoding='utf-8'))
    published_at = datetime(2026, 7, 20, 12, tzinfo=timezone.utc)
    ends_at = published_at + timedelta(days=7)
    record.update({
        'status': 'completed',
        'published_at': published_at.isoformat(),
        'observation_ends_at': ends_at.isoformat(),
        'completed_at': ends_at.isoformat(),
        'public_evidence_ref': 'https://pypi.org/project/govengine/1.0.0rc1/',
    })
    path = tmp_path / 'rc-window.json'
    path.write_text(json.dumps(record), encoding='utf-8')

    with pytest.raises(AssertionError, match='rc_window_closure_record_required'):
        validate_rc_window(path, now=ends_at)


@pytest.mark.parametrize(
    ('evidence_path', 'reason'),
    (
        ('https://example.invalid/rc1-closure.json', 'rc_window_closure_evidence_path_invalid'),
        ('missing-evidence.json', 'rc_window_closure_evidence_missing'),
    ),
)
def test_closure_rejects_url_or_nonexistent_evidence(
    tmp_path: Path,
    evidence_path: str,
    reason: str,
) -> None:
    record = json.loads(RECORD_PATH.read_text(encoding='utf-8'))
    path = tmp_path / 'rc-window.json'
    path.write_text(json.dumps(record), encoding='utf-8')
    ends_at = datetime.fromisoformat(record['observation_ends_at'].replace('Z', '+00:00'))
    closure_path, closure = _write_closure_record(path, completed_at=ends_at)
    assert isinstance(closure['closure_evidence'], dict)
    closure['closure_evidence']['path'] = evidence_path
    closure_path.write_text(json.dumps(closure), encoding='utf-8')

    with pytest.raises(AssertionError, match=reason):
        validate_rc_window(path, closure_path=closure_path, now=ends_at)


def test_closure_rejects_future_completion(tmp_path: Path) -> None:
    record = json.loads(RECORD_PATH.read_text(encoding='utf-8'))
    path = tmp_path / 'rc-window.json'
    path.write_text(json.dumps(record), encoding='utf-8')
    ends_at = datetime.fromisoformat(record['observation_ends_at'].replace('Z', '+00:00'))
    closure_path, _ = _write_closure_record(
        path,
        completed_at=ends_at + timedelta(seconds=1),
    )

    with pytest.raises(AssertionError, match='rc_window_closure_completed_in_future'):
        validate_rc_window(path, closure_path=closure_path, now=ends_at)


def test_closure_binds_original_record_and_evidence_digests(tmp_path: Path) -> None:
    record = json.loads(RECORD_PATH.read_text(encoding='utf-8'))
    path = tmp_path / 'rc-window.json'
    path.write_text(json.dumps(record), encoding='utf-8')
    ends_at = datetime.fromisoformat(record['observation_ends_at'].replace('Z', '+00:00'))
    closure_path, closure = _write_closure_record(path, completed_at=ends_at)

    closure['supersedes_record_sha256'] = '0' * 64
    closure_path.write_text(json.dumps(closure), encoding='utf-8')
    with pytest.raises(AssertionError, match='rc_window_closure_record_binding_invalid'):
        validate_rc_window(path, closure_path=closure_path, now=ends_at)

    closure['supersedes_record_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    assert isinstance(closure['closure_evidence'], dict)
    closure['closure_evidence']['sha256'] = '0' * 64
    closure_path.write_text(json.dumps(closure), encoding='utf-8')
    with pytest.raises(AssertionError, match='rc_window_closure_evidence_digest_mismatch'):
        validate_rc_window(path, closure_path=closure_path, now=ends_at)


def test_main_reports_forward_closure_digest(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / 'rc-window.json'
    path.write_bytes(RECORD_PATH.read_bytes())
    record = json.loads(path.read_text(encoding='utf-8'))
    ends_at = datetime.fromisoformat(record['observation_ends_at'].replace('Z', '+00:00'))
    closure_path, _ = _write_closure_record(path, completed_at=ends_at)

    assert validator.main([
        '--record', str(path),
        '--require-completed',
        '--closure-record', str(closure_path),
    ]) == 0

    assert capsys.readouterr().out.endswith(
        f':closure={hashlib.sha256(closure_path.read_bytes()).hexdigest()}\n'
    )


def test_v1_record_inventory_rejects_closure_field(tmp_path: Path) -> None:
    record = json.loads(RECORD_PATH.read_text(encoding='utf-8'))
    record['closure_evidence_ref'] = 'https://example.invalid/rc1-closure.json'
    path = tmp_path / 'rc-window.json'
    path.write_text(json.dumps(record), encoding='utf-8')

    with pytest.raises(AssertionError, match='rc_window_fields_drift'):
        validate_rc_window(path, now=datetime(2026, 7, 21, tzinfo=timezone.utc))


def test_frozen_rc_records_remain_byte_identical() -> None:
    assert hashlib.sha256((Path.cwd() / 'docs/rc-window/1.0.0rc1.json').read_bytes()).hexdigest() == (
        '7b7880fd035ed879584199e3156f34795369d217070f29fea081b085c3293851'
    )
    assert hashlib.sha256((Path.cwd() / 'docs/rc-window/1.0.0rc2.json').read_bytes()).hexdigest() == (
        'db26ba6ad1c5b0bdd3bdeddf420567ca5b8f74febdc9ec7036c467b7adead4e0'
    )


def test_rc3_source_a_is_exact_pending_review_without_artifact_claims() -> None:
    record = validate_rc_window(
        Path.cwd() / 'docs/rc-window/1.0.0rc3.json',
        expected_version='1.0.0rc3',
    )

    assert record['status'] == 'pending_review'
    assert record['source_commit'] is None
    assert record['prepared_at'] is None
    assert record['published_at'] is None
    assert record['public_evidence_ref'] == ''
    review = json.loads(
        (Path.cwd() / 'docs/security-review/rc3-external-review.json').read_text(
            encoding='utf-8'
        )
    )
    assert review['verdict'] == 'pending_external_reviewer'
    assert review['artifacts']['wheel_sha256'] == ''
    assert review['artifacts']['normalized_sdist_sha256'] == ''


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


def test_v2_record_inventory_rejects_closure_field(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    window = _write_v2_prepared_window(tmp_path, monkeypatch)
    record = json.loads(window.read_text(encoding='utf-8'))
    record['closure_evidence_ref'] = 'https://example.invalid/rc2-closure.json'
    window.write_text(json.dumps(record), encoding='utf-8')

    with pytest.raises(AssertionError, match='rc_window_v2_fields_drift'):
        validate_rc_window(window, expected_version='1.0.0rc2')


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
