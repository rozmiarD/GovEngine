from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.validate_rc_window import RECORD_PATH, validate_rc_window


def test_rc_window_matches_frozen_contract_inputs() -> None:
    record = validate_rc_window()

    assert record['version'] == '1.0.0rc1'
    assert record['status'] == 'active'
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
