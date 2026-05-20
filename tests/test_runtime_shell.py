from __future__ import annotations

import pytest

from govengine import (
    GovControlAction,
    GovQueueSnapshot,
    GovRuntimeSnapshot,
    GovSchedulerTick,
    control_action_from_host_action,
    queue_snapshot_from_lanes,
    validate_control_action,
    validate_queue_snapshot,
    validate_runtime_snapshot,
    validate_scheduler_tick,
)
from govengine.api import GovApiError


def test_control_action_models_host_lifecycle_without_command_authority() -> None:
    action = control_action_from_host_action(
        action='stop',
        run_id='run-1',
        profile='ravenclaw-security',
        metadata={'source': 'logdash_control'},
    )

    payload = action.as_dict()

    assert isinstance(action, GovControlAction)
    assert payload['action'] == 'stop'
    assert payload['requested_state'] == 'stopped'
    assert payload['metadata'] == {'source': 'logdash_control'}
    assert validate_control_action(payload).requested_state == 'stopped'


def test_direct_control_action_constructor_fills_default_requested_state() -> None:
    action = GovControlAction(action_id='a-1', run_id='run-1', action='cancel')

    assert action.requested_state == 'cancelled'
    assert validate_control_action(action.as_dict()).requested_state == 'cancelled'


def test_control_action_rejects_raw_intent_and_commands() -> None:
    with pytest.raises(GovApiError, match='forbidden_runtime_metadata:raw_intent'):
        validate_control_action({
            'action_id': 'a-1',
            'run_id': 'run-1',
            'action': 'start',
            'metadata': {'raw_intent': 'scan everything'},
        })

    with pytest.raises(GovApiError, match='forbidden_runtime_metadata:command'):
        validate_control_action({
            'action_id': 'a-2',
            'run_id': 'run-1',
            'action': 'start',
            'metadata': {'command': 'curl https://example.com'},
        })


def test_queue_snapshot_is_redaction_bounded_and_host_owned() -> None:
    snapshot = queue_snapshot_from_lanes(
        snapshot_id='q-1',
        run_id='run-1',
        profile='ravenclaw-security',
        lanes={
            'followup': [{'task_family': 'recon', 'target_redacted': True}],
            'precision': [],
        },
        telemetry={'precheck_skip_count': 1},
        metadata={'source': 'ravenclaw_projection'},
    )

    payload = snapshot.as_dict()

    assert isinstance(snapshot, GovQueueSnapshot)
    assert payload['lanes'][0]['name'] == 'followup'
    assert payload['lanes'][0]['count'] == 1
    assert payload['telemetry']['precheck_skip_count'] == 1
    assert validate_queue_snapshot(payload).run_id == 'run-1'


def test_queue_snapshot_rejects_hidden_commands() -> None:
    with pytest.raises(GovApiError, match='forbidden_runtime_metadata:command'):
        queue_snapshot_from_lanes(
            snapshot_id='q-1',
            run_id='run-1',
            lanes={'followup': [{'command': ['curl', 'https://example.com']}]},
        )


def test_runtime_snapshot_combines_state_control_and_queue_without_storage_claim() -> None:
    queue = queue_snapshot_from_lanes(
        snapshot_id='q-1',
        run_id='run-1',
        lanes={'followup': [{'task_family': 'recon'}]},
    )
    action = control_action_from_host_action(action='pause', run_id='run-1')
    snapshot = validate_runtime_snapshot({
        'snapshot_id': 'rt-1',
        'run_id': 'run-1',
        'state': 'paused',
        'control_actions': [action.as_dict()],
        'queue_snapshot': queue.as_dict(),
        'non_claims': ['host_owns_runtime_storage'],
    })

    payload = snapshot.as_dict()

    assert isinstance(snapshot, GovRuntimeSnapshot)
    assert payload['state'] == 'paused'
    assert payload['control_actions'][0]['action'] == 'pause'
    assert payload['queue_snapshot']['run_id'] == 'run-1'
    assert 'host_owns_runtime_storage' in payload['non_claims']


def test_runtime_snapshot_rejects_cross_run_queue_and_action_drift() -> None:
    with pytest.raises(GovApiError, match='queue_snapshot_run_mismatch'):
        validate_runtime_snapshot({
            'snapshot_id': 'rt-1',
            'run_id': 'run-1',
            'state': 'running',
            'queue_snapshot': {'snapshot_id': 'q-1', 'run_id': 'other', 'lanes': []},
        })

    with pytest.raises(GovApiError, match='control_action_run_mismatch'):
        validate_runtime_snapshot({
            'snapshot_id': 'rt-1',
            'run_id': 'run-1',
            'state': 'running',
            'control_actions': [{'action_id': 'a-1', 'run_id': 'other', 'action': 'pause'}],
        })


def test_scheduler_tick_is_metadata_only() -> None:
    tick = validate_scheduler_tick({
        'tick_id': 'tick-1',
        'run_id': 'run-1',
        'due_action_refs': ['run-1:pause'],
        'heartbeat_status': 'healthy',
        'metadata': {'source': 'host_clock'},
    })

    assert isinstance(tick, GovSchedulerTick)
    assert tick.as_dict()['due_action_refs'] == ['run-1:pause']

    with pytest.raises(GovApiError, match='forbidden_runtime_metadata:schedule'):
        validate_scheduler_tick({
            'tick_id': 'tick-2',
            'run_id': 'run-1',
            'metadata': {'schedule': '* * * * *'},
        })
