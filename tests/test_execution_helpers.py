from __future__ import annotations

import pytest

from govengine.execution.approved_spec import approved_execution_steps, validate_approved_execution_spec
from govengine.execution.runner import approved_spec_dry_run_result
from govengine.execution.ticket_gate import validate_execution_ticket_gate


def _approved_spec() -> dict:
    return {
        'spec_version': '2026-03-18.approved.v1',
        'action_type': 'single_probe',
        'capability': 'http_probe',
        'resolved_tool': 'curl',
        'execution_mode': 'normalized',
        'compiler': {'semantic_loss_policy': {'loss_class': 'none', 'policy_response': 'proceed'}},
        'approval': {'decision': 'approve', 'reason': 'ok'},
        'execution_truth': {
            'artifact_type': 'approved_execution_spec',
            'execution_plan': [{'tool': 'curl', 'args': ['https://example.com']}],
        },
    }


def test_approved_spec_and_dry_run_result() -> None:
    approved = _approved_spec()
    assert validate_approved_execution_spec(approved) == approved['execution_truth']
    assert approved_execution_steps(approved) == [{'tool': 'curl', 'args': ['https://example.com']}]
    result = approved_spec_dry_run_result(approved_execution_spec=approved, planned_commands=[['curl', 'https://example.com']])
    assert result['status'] == 'dry-run'
    assert result['execution_source'] == 'approved_execution_spec'
    assert result['execution_ticket_gate'] == {'status': 'not_required'}


def test_execution_ticket_gate_requires_ticket_when_called() -> None:
    approved = _approved_spec()
    with pytest.raises(ValueError, match='missing_execution_ticket'):
        validate_execution_ticket_gate(approved, execution_ticket=None, execution_contract=None, raw_steps=approved_execution_steps(approved))
