from __future__ import annotations

from dataclasses import replace

import pytest

from govengine import (
    AUTOMATION_TRANSITION_REQUEST_SCHEMA_VERSION,
    SUPPORTED_AUTOMATION_CHAIN_SCHEMA_REF,
    AutomationTransitionRequest,
    GovApiError,
    admit_automation_transition,
    automation_transition_admission_digest,
    automation_transition_request_digest,
    validate_automation_transition_admission,
    validate_automation_transition_request,
)


def _digest(char: str) -> str:
    return 'sha256:' + char * 64


def _request(**overrides):
    payload = {
        'request_id': 'automation-request-1',
        'chain_id': 'chain-1',
        'parent_operation_id': 'op-parent',
        'parent_operation_ref': _digest('a'),
        'parent_intent': 'collect_basic_host_inventory',
        'parent_status': 'completed',
        'child_operation_id': 'op-child',
        'child_intent': 'summarize_inventory',
        'child_intent_class': 'readonly_followup',
        'transition_reason': 'parent_completed_with_followup',
        'automation_chain_ref': _digest('b'),
        'automation_chain_schema_ref': SUPPORTED_AUTOMATION_CHAIN_SCHEMA_REF,
        'source': 'reaction',
        'depth': 1,
        'max_depth': 3,
        'child_sequence': 1,
        'max_children': 2,
        'allowed_child_intent_classes': ['readonly_followup', 'evidence_review'],
    }
    payload.update(overrides)
    return payload


def test_automation_transition_admission_allows_bounded_child_plan() -> None:
    request = AutomationTransitionRequest.from_mapping(_request())
    admission = admit_automation_transition(request)

    assert request.schema_version == AUTOMATION_TRANSITION_REQUEST_SCHEMA_VERSION
    assert admission.allowed is True
    assert admission.outcome == 'allowed'
    assert admission.reason_code == 'automation_transition_allowed'
    assert admission.signal['automation_chain_schema_ref'] == SUPPORTED_AUTOMATION_CHAIN_SCHEMA_REF
    assert admission.metadata['governance_flow'] == 'planning_admission_adapter.v1'
    assert admission.metadata['execution_authority'] is False
    assert 'authorization' not in admission.as_dict()
    assert automation_transition_request_digest(request).startswith('sha256:')
    assert automation_transition_admission_digest(admission).startswith('sha256:')
    assert validate_automation_transition_request(request.as_dict()) == request
    assert validate_automation_transition_admission(admission, request=request) == admission


def test_automation_transition_denies_llm_authority() -> None:
    request = AutomationTransitionRequest.from_mapping(
        _request(source='llm_proposal', llm_proposed=True, llm_authority=True)
    )

    admission = admit_automation_transition(request)

    assert admission.allowed is False
    assert admission.outcome == 'denied'
    assert admission.reason_code == 'automation_transition_llm_authority_denied'
    assert admission.blockers == ('llm_authority_denied',)
    assert admission.metadata['execution_authority'] is False


@pytest.mark.parametrize(
    ('field', 'value', 'reason_code'),
    [
        ('parent_operation_ref', 'sha256:' + 'A' * 64, 'invalid_automation_parent_operation_ref'),
        ('depth', '1', 'invalid_automation_transition_depth'),
        ('max_depth', True, 'invalid_automation_transition_depth'),
        ('child_sequence', '1', 'invalid_automation_transition_child_limits'),
        ('llm_proposed', 'false', 'invalid_automation_llm_proposed'),
        ('allowed_child_intent_classes', ['readonly_followup', 1], 'invalid_automation_allowed_child_intent_classes'),
    ],
)
def test_automation_transition_rejects_coercions_with_typed_errors(
    field: str, value: object, reason_code: str
) -> None:
    with pytest.raises(GovApiError, match=reason_code):
        AutomationTransitionRequest.from_mapping(_request(**{field: value}))


def test_automation_transition_defers_llm_proposal_without_approval() -> None:
    request = AutomationTransitionRequest.from_mapping(
        _request(source='llm_proposal', llm_proposed=True)
    )

    admission = admit_automation_transition(request)

    assert admission.allowed is False
    assert admission.outcome == 'deferred'
    assert admission.reason_code == 'automation_transition_requires_approval'
    assert admission.blockers == ('approval_required',)


def test_automation_transition_allows_llm_proposal_with_approval_ref() -> None:
    request = AutomationTransitionRequest.from_mapping(
        _request(source='llm_proposal', llm_proposed=True, approval_ref='operator-approval:123')
    )

    admission = admit_automation_transition(request)

    assert admission.allowed is True
    assert admission.reason_code == 'automation_transition_allowed'


def test_automation_transition_denies_depth_budget_child_budget_and_intent_class() -> None:
    depth = admit_automation_transition(AutomationTransitionRequest.from_mapping(_request(depth=4)))
    child_budget = admit_automation_transition(
        AutomationTransitionRequest.from_mapping(_request(child_sequence=3))
    )
    intent_class = admit_automation_transition(
        AutomationTransitionRequest.from_mapping(_request(child_intent_class='mutating_change'))
    )

    assert depth.reason_code == 'automation_transition_depth_exceeded'
    assert depth.blockers == ('depth_exceeded',)
    assert child_budget.reason_code == 'automation_transition_child_budget_exceeded'
    assert child_budget.blockers == ('child_budget_exceeded',)
    assert intent_class.reason_code == 'automation_transition_child_intent_class_denied'
    assert intent_class.blockers == ('child_intent_class_denied',)


def test_automation_transition_denies_unknown_automation_chain_schema() -> None:
    request = AutomationTransitionRequest.from_mapping(
        _request(automation_chain_schema_ref='schemas/automation_chain.v9.0.schema.json')
    )

    admission = admit_automation_transition(request)

    assert admission.allowed is False
    assert admission.reason_code == 'automation_transition_unsupported_chain_schema'
    assert admission.blockers == ('unsupported_automation_chain_schema',)


def test_automation_transition_rejects_raw_metadata() -> None:
    with pytest.raises(GovApiError, match='forbidden_automation_transition_metadata:raw_output'):
        validate_automation_transition_request(_request(metadata={'nested': {'raw_output': 'secret'}}))


def test_automation_transition_admission_detects_drift() -> None:
    request = AutomationTransitionRequest.from_mapping(_request())
    admission = admit_automation_transition(request)
    drifted = replace(admission, reason_code='different')

    with pytest.raises(GovApiError, match='automation_transition_admission_drift'):
        validate_automation_transition_admission(drifted, request=request)

def test_automation_transition_admission_is_bound_to_exact_chain_request() -> None:
    admitted_request = AutomationTransitionRequest.from_mapping(_request())
    admission = admit_automation_transition(admitted_request)
    different_chain_request = AutomationTransitionRequest.from_mapping(
        _request(automation_chain_ref=_digest('c'))
    )

    assert automation_transition_request_digest(
        admitted_request
    ) != automation_transition_request_digest(different_chain_request)
    with pytest.raises(GovApiError, match='automation_transition_admission_drift'):
        validate_automation_transition_admission(admission, request=different_chain_request)
