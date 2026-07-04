from __future__ import annotations

import json
import subprocess
from pathlib import Path

from govengine.cli_errors import CLI_ERROR_SCHEMA

ROOT = Path(__file__).resolve().parents[1]


def test_supervisor_cli_explain_success(tmp_path: Path) -> None:
    request_path = tmp_path / 'request.json'
    request_path.write_text(
        json.dumps(
            {
                'request_id': 'watchdog-request-1',
                'action': 'block_autostart',
                'reason': 'stale_active_operation',
                'watchdog_record_ref': 'sha256:' + 'a' * 64,
                'observation': 'stuck_operation',
                'affected_kind': 'operation',
                'operation_id': 'op-1',
                'age_seconds': 3601,
                'max_age_seconds': 3600,
            }
        ),
        encoding='utf-8',
    )

    proc = subprocess.run(
        ['govengine-supervisor', 'explain', str(request_path), '--json'],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    payload = json.loads(proc.stdout)

    assert proc.returncode == 0
    assert payload['status'] == 'explained'
    assert payload['reason_code'] == 'supervisor_action_allowed'


def test_supervisor_cli_explain_blocked_exits_two(tmp_path: Path) -> None:
    request_path = tmp_path / 'request.json'
    request_path.write_text(
        json.dumps(
            {
                'request_id': 'watchdog-request-2',
                'action': 'move_to_dead_letter',
                'reason': 'retry_budget_exhausted',
                'watchdog_record_ref': 'sha256:' + 'b' * 64,
                'observation': 'inbox_item',
                'affected_kind': 'inbox_item',
                'operation_id': '',
                'inbox_item_name': 'job-1.json',
                'attempt_count': 4,
                'max_attempts': 3,
                'age_seconds': 0,
                'max_age_seconds': 0,
            }
        ),
        encoding='utf-8',
    )

    proc = subprocess.run(
        ['govengine-supervisor', 'explain', str(request_path), '--json'],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    payload = json.loads(proc.stdout)

    assert proc.returncode == 2
    assert payload['status'] == 'blocked'
    assert payload['reason_code'] == 'supervisor_action_retry_budget_exceeded'


def test_supervisor_cli_invalid_request_emits_json_error_envelope(tmp_path: Path) -> None:
    request_path = tmp_path / 'request.json'
    request_path.write_text('not-json', encoding='utf-8')

    proc = subprocess.run(
        ['govengine-supervisor', 'explain', str(request_path), '--json'],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    payload = json.loads(proc.stdout)

    assert proc.returncode == 2
    assert payload['schema'] == CLI_ERROR_SCHEMA
    assert payload['status'] == 'error'
    assert payload['reason_code'] == 'supervisor_request_json_invalid'
    assert payload['command'] == 'govengine-supervisor explain'