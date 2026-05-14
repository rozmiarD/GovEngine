from __future__ import annotations

import json
from importlib import resources

import pytest

from govengine.execution.approved_spec import approved_execution_steps, validate_approved_execution_spec
from govengine.execution.runner import approved_spec_dry_run_result
from govengine.execution.ticket_gate import validate_execution_ticket_gate, validate_scoped_ticket_use_gate


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


def _scoped_ticket_fixture(name: str) -> dict:
    path = resources.files('sclite.examples').joinpath('scoped-ticket-v0.3', name)
    return json.loads(path.read_text())


def test_execution_ticket_gate_delegates_v03_semantics_to_sclite() -> None:
    approved = _approved_spec()
    ticket = _scoped_ticket_fixture('execution_ticket.json')
    contract = _scoped_ticket_fixture('execution_contract.json')

    result = validate_execution_ticket_gate(
        approved,
        execution_ticket=ticket,
        execution_contract=contract,
        raw_steps=[{'tool': 'http_probe', 'args': ['https://example.com/login']}],
    )

    assert result['status'] == 'passed'
    assert result['schema_version'] == 'v0.3'
    assert 'ticket_scope_matches_execution_contract' in result['sclite_checks']


def test_scoped_ticket_use_gate_delegates_receipt_evidence_bounds_to_sclite() -> None:
    result = validate_scoped_ticket_use_gate(
        execution_ticket=_scoped_ticket_fixture('execution_ticket.json'),
        execution_contract=_scoped_ticket_fixture('execution_contract.json'),
        execution_receipt=_scoped_ticket_fixture('execution_receipt.json'),
        evidence_contract=_scoped_ticket_fixture('evidence_contract.json'),
    )

    assert result['status'] == 'passed'
    assert result['ticket_id'] == 'scoped-ticket-demo-001'
    assert result['receipt_id'] == 'scoped-ticket-receipt-demo-001'
    assert result['source'] == 'sclite.verify_ticket_use'
    assert 'evidence_claims_bounded_by_receipt' in result['checks']


def test_scoped_ticket_use_gate_rejects_unbounded_execution_claims() -> None:
    evidence = _scoped_ticket_fixture('evidence_contract.json')
    evidence['claims'][0]['claim_type'] = 'completed_execution'
    evidence['claims'][0]['statement'] = 'The runtime completed actual execution.'

    with pytest.raises(ValueError, match='sclite_ticket_use_failed'):
        validate_scoped_ticket_use_gate(
            execution_ticket=_scoped_ticket_fixture('execution_ticket.json'),
            execution_contract=_scoped_ticket_fixture('execution_contract.json'),
            execution_receipt=_scoped_ticket_fixture('execution_receipt.json'),
            evidence_contract=evidence,
        )
