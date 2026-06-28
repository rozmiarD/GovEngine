from __future__ import annotations

from dataclasses import replace

import pytest

from govengine import (
    GovApiError,
    SUPERVISOR_ACTION_REQUEST_SCHEMA_VERSION,
    SupervisorActionRequest,
    admit_supervisor_action,
    supervisor_action_admission_digest,
    supervisor_action_request_digest,
    validate_supervisor_action_admission,
    validate_supervisor_action_request,
)


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
        'age_seconds': 120,
        'max_age_seconds': 300,
    }
    payload.update(overrides)
    return payload


def test_supervisor_action_admission_allows_block_autostart() -> None:
    request = SupervisorActionRequest.from_mapping(_request())
    admission = admit_supervisor_action(request)

    assert request.schema_version == SUPERVISOR_ACTION_REQUEST_SCHEMA_VERSION
    assert admission.allowed is True
    assert admission.outcome == 'allowed'
    assert admission.reason_code == 'supervisor_action_allowed'
    assert admission.signal['operation_id'] == 'op-1'
    assert supervisor_action_request_digest(request).startswith('sha256:')
    assert supervisor_action_admission_digest(admission).startswith('sha256:')
    assert validate_supervisor_action_request(request.as_dict()) == request
    assert validate_supervisor_action_admission(admission, request=request) == admission


def test_supervisor_record_health_is_record_only() -> None:
    request = SupervisorActionRequest.from_mapping(
        _request(
            action='record_health',
            reason='worker_heartbeat',
            observation='worker_heartbeat',
            affected_kind='worker',
            operation_id='',
            age_seconds=0,
            max_age_seconds=0,
        )
    )

    admission = admit_supervisor_action(request)

    assert admission.allowed is True
    assert admission.outcome == 'record_only'
    assert admission.reason_code == 'supervisor_action_record_only'


def test_supervisor_action_denies_retry_budget_exceeded() -> None:
    request = SupervisorActionRequest.from_mapping(
        _request(
            action='move_to_dead_letter',
            reason='retry_budget_exhausted',
            observation='inbox_item',
            affected_kind='inbox_item',
            operation_id='',
            inbox_item_name='job-1.json',
            attempt_count=4,
            max_attempts=3,
        )
    )

    admission = admit_supervisor_action(request)

    assert admission.allowed is False
    assert admission.outcome == 'denied'
    assert admission.reason_code == 'supervisor_action_retry_budget_exceeded'
    assert admission.blockers == ('retry_budget_exceeded',)


def test_supervisor_action_requires_human_signoff_for_recovery_actions() -> None:
    request = SupervisorActionRequest.from_mapping(
        _request(
            action='renew_lease',
            reason='operator_recovery',
            observation='expired_lease',
        )
    )

    admission = admit_supervisor_action(request)

    assert admission.allowed is False
    assert admission.outcome == 'deferred'
    assert admission.reason_code == 'supervisor_action_requires_human_signoff'
    assert admission.blockers == ('human_signoff_required',)


def test_supervisor_action_rejects_raw_metadata() -> None:
    with pytest.raises(GovApiError, match='forbidden_supervisor_action_metadata:raw_event'):
        validate_supervisor_action_request(_request(metadata={'raw_event': {'subject': 'host-1'}}))


def test_supervisor_action_admission_detects_drift() -> None:
    request = SupervisorActionRequest.from_mapping(_request())
    admission = admit_supervisor_action(request)
    drifted = replace(admission, reason_code='different')

    with pytest.raises(GovApiError, match='supervisor_action_admission_drift'):
        validate_supervisor_action_admission(drifted, request=request)
