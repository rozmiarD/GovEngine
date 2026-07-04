from __future__ import annotations

import json
from pathlib import Path

from govengine import explain_supervisor_action


def _digest(char: str) -> str:
    return 'sha256:' + char * 64


def _request(**overrides):
    payload = {
        'request_id': 'watchdog-request-1',
        'action': 'block_autostart',
        'reason': 'stale_active_operation',
        'watchdog_record_ref': _digest('a'),
        'observation': 'stuck_operation',
        'affected_kind': 'operation',
        'operation_id': 'op-1',
        'age_seconds': 3601,
        'max_age_seconds': 3600,
    }
    payload.update(overrides)
    return payload


def test_explain_supervisor_action_for_block_autostart(tmp_path: Path) -> None:
    request_path = tmp_path / 'request.json'
    request_path.write_text(json.dumps(_request()), encoding='utf-8')

    explanation = explain_supervisor_action(json.loads(request_path.read_text())).as_dict()

    assert explanation['schema_version'] == 'v0.1'
    assert explanation['status'] == 'explained'
    assert explanation['recovery_class'] == 'block_autostart'
    assert explanation['reason_code'] == 'supervisor_action_allowed'
    assert explanation['evaluation_path'] == 'allowed'
    assert explanation['gates_checked'][0]['gate'] == 'stale_age'
    assert explanation['request_digest'].startswith('sha256:')
    assert explanation['admission_digest'].startswith('sha256:')
    assert 'Does not execute recovery' in explanation['non_claims'][0]


def test_explain_supervisor_action_for_dead_letter_budget_denial() -> None:
    explanation = explain_supervisor_action(
        _request(
            action='move_to_dead_letter',
            reason='retry_budget_exhausted',
            observation='inbox_item',
            affected_kind='inbox_item',
            operation_id='',
            inbox_item_name='job-1.json',
            attempt_count=4,
            max_attempts=3,
            age_seconds=0,
            max_age_seconds=0,
        )
    ).as_dict()

    assert explanation['status'] == 'blocked'
    assert explanation['recovery_class'] == 'dead_letter'
    assert explanation['reason_code'] == 'supervisor_action_retry_budget_exceeded'
    assert explanation['evaluation_path'] == 'retry_budget'
    assert 'rexecop dead-letter list' in explanation['safe_next_actions']


def test_explain_supervisor_action_for_manual_recovery_signoff() -> None:
    explanation = explain_supervisor_action(
        _request(
            action='renew_lease',
            reason='operator_recovery',
            observation='expired_lease',
            operation_id='',
            age_seconds=0,
            max_age_seconds=0,
        )
    ).as_dict()

    assert explanation['status'] == 'blocked'
    assert explanation['recovery_class'] == 'stale_lease'
    assert explanation['reason_code'] == 'supervisor_action_requires_human_signoff'
    assert 'rexecop watchdog manual-record' in explanation['safe_next_actions'][-1]


def test_explain_supervisor_action_for_signed_manual_record() -> None:
    explanation = explain_supervisor_action(
        _request(
            action='mark_stale',
            reason='operator_break_glass',
            observation='manual_recovery',
            human_signoff=True,
            actor_ref='operator:local-admin',
            scope='operation:op-1',
        )
    ).as_dict()

    assert explanation['status'] == 'explained'
    assert explanation['recovery_class'] == 'manual_record'
    assert explanation['evaluation_path'] == 'signed_manual_recovery'
    assert explanation['gates_checked'][0]['gate'] == 'human_signoff'