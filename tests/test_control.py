from __future__ import annotations

import pytest

from govengine import ControlDecision, GovRunState, apply_control_decision, validate_control_decision
from govengine.api import GovApiError


def test_control_decision_is_json_safe_between_step_record() -> None:
    decision = validate_control_decision({
        'decision_id': 'decision-1',
        'run_id': 'run-1',
        'action': 'advance_state',
        'from_state': 'gated',
        'to_state': 'running_dry_run',
        'profile': 'ravenclaw',
        'event_refs': ['event-1'],
        'required_decisions': ['runner_gate_decision'],
        'metadata': {'trace_ref': 'trace-1'},
    })

    assert isinstance(decision, ControlDecision)
    assert decision.as_dict() == {
        'decision_id': 'decision-1',
        'run_id': 'run-1',
        'action': 'advance_state',
        'reason_code': 'ok',
        'from_state': 'gated',
        'to_state': 'running_dry_run',
        'profile': 'ravenclaw',
        'event_refs': ['event-1'],
        'required_decisions': ['runner_gate_decision'],
        'metadata': {'trace_ref': 'trace-1'},
    }


def test_apply_control_decision_delegates_to_state_machine_without_storage_claim() -> None:
    state = GovRunState(run_id='run-1', state='gated')
    decision = validate_control_decision({
        'decision_id': 'decision-1',
        'run_id': 'run-1',
        'action': 'advance_state',
        'from_state': 'gated',
        'to_state': 'running_dry_run',
        'event_refs': ['event-2'],
        'required_decisions': ['runner_gate_decision'],
    })

    updated = apply_control_decision(state, decision)

    assert updated.state == 'running_dry_run'
    assert updated.event_refs == ('event-2',)
    assert updated.metadata == {}


def test_record_only_control_does_not_mutate_state() -> None:
    state = GovRunState(run_id='run-1', state='policy_checked')
    decision = validate_control_decision({
        'decision_id': 'decision-1',
        'run_id': 'run-1',
        'action': 'record_only',
        'event_refs': ['event-1'],
    })

    assert apply_control_decision(state, decision) is state


def test_block_control_preserves_reason_as_state_blocker() -> None:
    state = GovRunState(run_id='run-1', state='policy_checked')
    decision = validate_control_decision({
        'decision_id': 'decision-1',
        'run_id': 'run-1',
        'action': 'block',
        'from_state': 'policy_checked',
        'to_state': 'blocked',
        'reason_code': 'trust_missing',
    })

    updated = apply_control_decision(state, decision)

    assert updated.blocked is True
    assert updated.blockers == ('trust_missing',)


def test_control_decision_rejects_runtime_authority_and_raw_intent() -> None:
    with pytest.raises(GovApiError, match='raw_intent_not_control_decision'):
        validate_control_decision({
            'decision_id': 'bad',
            'run_id': 'run-1',
            'action': 'record_only',
            'raw_intent': 'run this target',
        })

    with pytest.raises(GovApiError, match='forbidden_control_metadata:command'):
        validate_control_decision({
            'decision_id': 'bad',
            'run_id': 'run-1',
            'action': 'record_only',
            'metadata': {'nested': {'command': ['curl', 'https://example.com']}},
        })

    with pytest.raises(GovApiError, match='forbidden_control_metadata:scheduler'):
        validate_control_decision({
            'decision_id': 'bad',
            'run_id': 'run-1',
            'action': 'record_only',
            'metadata': {'scheduler': 'cron'},
        })


def test_control_decision_rejects_invalid_state_claims() -> None:
    with pytest.raises(GovApiError, match='unknown_control_action:execute_now'):
        validate_control_decision({
            'decision_id': 'bad',
            'run_id': 'run-1',
            'action': 'execute_now',
        })

    with pytest.raises(GovApiError, match='control_decision_missing_state_transition'):
        validate_control_decision({
            'decision_id': 'bad',
            'run_id': 'run-1',
            'action': 'advance_state',
        })

    with pytest.raises(GovApiError, match='record_control_must_not_claim_state_transition'):
        validate_control_decision({
            'decision_id': 'bad',
            'run_id': 'run-1',
            'action': 'record_only',
            'from_state': 'new',
            'to_state': 'admitted',
        })

    with pytest.raises(GovApiError, match='pause_control_must_target_paused'):
        validate_control_decision({
            'decision_id': 'bad',
            'run_id': 'run-1',
            'action': 'pause',
            'from_state': 'gated',
            'to_state': 'blocked',
        })
