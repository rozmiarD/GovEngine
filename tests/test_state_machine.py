from __future__ import annotations

import pytest

from govengine import GovRunState, StateTransition, apply_state_transition, validate_run_state, validate_state_transition
from govengine.api import GovApiError


def test_run_state_is_json_safe_summary() -> None:
    state = validate_run_state({
        'run_id': 'run-1',
        'state': 'admitted',
        'profile': 'ravenclaw',
        'event_refs': ['event-1'],
        'artifact_refs': ['contract-1'],
        'metadata': {'trace_ref': 'trace-1'},
    })

    assert isinstance(state, GovRunState)
    assert state.as_dict() == {
        'run_id': 'run-1',
        'state': 'admitted',
        'profile': 'ravenclaw',
        'event_refs': ['event-1'],
        'artifact_refs': ['contract-1'],
        'blockers': [],
        'metadata': {'trace_ref': 'trace-1'},
        'terminal': False,
        'blocked': False,
    }


def test_state_transition_requires_runner_gate_before_dry_run() -> None:
    with pytest.raises(GovApiError, match='missing_runner_gate_decision'):
        validate_state_transition({
            'run_id': 'run-1',
            'from_state': 'gated',
            'to_state': 'running_dry_run',
        })

    transition = validate_state_transition({
        'run_id': 'run-1',
        'from_state': 'gated',
        'to_state': 'running_dry_run',
        'required_decisions': ['runner_gate_decision'],
        'event_ref': 'event-2',
    })
    assert isinstance(transition, StateTransition)


def test_apply_state_transition_updates_state_without_storage_claim() -> None:
    state = GovRunState(run_id='run-1', state='gated', event_refs=('event-1',))
    transition = StateTransition(
        run_id='run-1',
        from_state='gated',
        to_state='running_dry_run',
        required_decisions=('runner_gate_decision',),
        event_ref='event-2',
    )

    updated = apply_state_transition(state, transition)

    assert updated.state == 'running_dry_run'
    assert updated.event_refs == ('event-1', 'event-2')
    assert updated.metadata == {}


def test_blocked_transition_preserves_reason_as_blocker() -> None:
    state = GovRunState(run_id='run-1', state='policy_checked')
    transition = StateTransition(
        run_id='run-1',
        from_state='policy_checked',
        to_state='blocked',
        reason_code='trust_missing',
    )

    updated = apply_state_transition(state, transition)

    assert updated.blocked is True
    assert updated.blockers == ('trust_missing',)


def test_state_transition_rejects_invalid_sequence_and_mismatch() -> None:
    with pytest.raises(GovApiError, match='invalid_state_transition:new->completed'):
        validate_state_transition({
            'run_id': 'run-1',
            'from_state': 'new',
            'to_state': 'completed',
        })

    with pytest.raises(GovApiError, match='state_transition_from_mismatch:admitted!=new'):
        apply_state_transition(
            GovRunState(run_id='run-1', state='admitted'),
            StateTransition(run_id='run-1', from_state='new', to_state='admitted'),
        )


def test_state_machine_rejects_runtime_and_sensitive_claims() -> None:
    with pytest.raises(GovApiError, match='raw_intent_not_state_transition'):
        validate_state_transition({
            'run_id': 'run-1',
            'from_state': 'new',
            'to_state': 'admitted',
            'raw_intent': 'run this target',
        })

    with pytest.raises(GovApiError, match='forbidden_state_metadata:credential'):
        validate_run_state({
            'run_id': 'run-1',
            'metadata': {'nested': {'credential': 'secret-value'}},
        })

    with pytest.raises(GovApiError, match='forbidden_state_metadata:scheduler'):
        validate_state_transition({
            'run_id': 'run-1',
            'from_state': 'new',
            'to_state': 'admitted',
            'metadata': {'scheduler': 'cron'},
        })


def test_state_metadata_scan_is_iterative_bounded_and_normalized() -> None:
    metadata: dict[str, object] = {}
    for _ in range(1_200):
        metadata = {'nested': metadata}

    with pytest.raises(GovApiError, match='json_boundary_max_depth'):
        validate_run_state({'run_id': 'run-1', 'metadata': metadata})

    with pytest.raises(GovApiError, match='forbidden_state_metadata:credential'):
        validate_run_state({
            'run_id': 'run-1',
            'metadata': {'nested': {' CREDENTIAL ': 'not-secret-material'}},
        })

    with pytest.raises(GovApiError, match='raw_intent_not_state_transition'):
        validate_state_transition({
            'run_id': 'run-1',
            'from_state': 'new',
            'to_state': 'admitted',
            ' RAW_INTENT ': 'run this target',
        })
