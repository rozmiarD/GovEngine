from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from scripts.validate_rc_window import RECORD_PATH, validate_rc_window


def test_rc_window_matches_frozen_contract_inputs() -> None:
    record = validate_rc_window()

    assert record['version'] == '1.0.0rc1'
    assert record['status'] == 'active'
    assert record['published_at'] == '2026-07-20T17:39:58.058090Z'
    assert record['observation_ends_at'] == '2026-07-27T17:39:58.058090Z'
    assert record['minimum_observation_days'] == 7
    assert record['facade_exports'] == 40
    assert record['v1_records'] == 15


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
