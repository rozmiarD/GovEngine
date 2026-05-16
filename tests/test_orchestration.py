from __future__ import annotations

import pytest

from govengine import OrchestrationStep, orchestrator_boundary_contract, validate_orchestration_step
from govengine.api import GovApiError


def test_orchestrator_boundary_keeps_runtime_authority_out_of_kernel() -> None:
    payload = orchestrator_boundary_contract().as_dict()

    assert 'between_step_control_decisions' in payload['kernel_controls']
    assert 'workflow_scheduling' in payload['runtime_owns']
    assert 'live_execution' in payload['forbidden_authority']
    assert any('does not own an agent loop' in claim for claim in payload['non_claims'])


def test_orchestration_step_is_json_safe_handoff_record() -> None:
    step = validate_orchestration_step({
        'step_id': 'gate-1',
        'stage': 'runner_gate',
        'profile': 'ravenclaw',
        'consumes': ['approved_execution_ticket'],
        'produces': ['runner_gate_decision'],
        'required_decisions': ['policy_decision', 'trust_decision'],
        'metadata': {'receipt_ref': 'receipt-1'},
    })

    assert isinstance(step, OrchestrationStep)
    assert step.stage == 'runner_gate'
    assert step.as_dict()['metadata'] == {'receipt_ref': 'receipt-1'}


def test_orchestration_step_rejects_raw_intent_shape() -> None:
    with pytest.raises(GovApiError, match='raw_intent_not_orchestration_step'):
        validate_orchestration_step({
            'step_id': 'bad',
            'stage': 'admission',
            'raw_intent': 'run this target',
        })


def test_orchestration_step_rejects_forbidden_runtime_authority() -> None:
    with pytest.raises(GovApiError, match='forbidden_orchestration_authority:live_execution'):
        validate_orchestration_step({
            'step_id': 'bad',
            'stage': 'runner_gate',
            'forbidden_authority': ['live_execution'],
        })


def test_orchestration_step_rejects_unknown_stage() -> None:
    with pytest.raises(GovApiError, match='unknown_orchestration_stage:background_job'):
        validate_orchestration_step({
            'step_id': 'bad',
            'stage': 'background_job',
        })
