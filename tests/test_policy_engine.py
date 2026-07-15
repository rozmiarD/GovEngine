from __future__ import annotations

import pytest

from govengine import (
    PolicyCompiler,
    PolicyEngine,
    PolicyVerdict,
    policy_verdict_to_gov_policy_decision,
    validate_policy_request,
    validate_policy_verdict,
)
from govengine.api import GovApiError


def _compiled_pack():
    result = PolicyCompiler().compile({
        'policy_id': 'policy-pack-1',
        'version': '2026-06-20',
        'rules': [
            {
                'rule_id': 'allow-read-with-receipt',
                'effect': 'allow_with_obligations',
                'conditions': {'action.mode': 'read'},
                'reason_code': 'read_allowed_with_receipt',
                'obligations': [{'obligation_id': 'receipt-required', 'kind': 'receipt'}],
                'constraints': [{'constraint_id': 'bounded-output', 'kind': 'output_limit', 'value': 4096}],
            },
            {
                'rule_id': 'deny-unsafe',
                'effect': 'deny',
                'conditions': {'action.mode': 'unsafe'},
                'reason_code': 'unsafe_action_denied',
            },
        ],
    })
    assert result.ok
    assert result.policy_pack is not None
    return result.policy_pack


def test_policy_compiler_rejects_invalid_or_conflicting_packs() -> None:
    compiler = PolicyCompiler()

    missing = compiler.compile({'policy_id': 'bad', 'version': '1'})
    assert missing.status == 'rejected'
    assert missing.reason_code == 'policy_pack_without_rules'

    conflict = compiler.compile({
        'policy_id': 'conflict',
        'version': '1',
        'rules': [
            {'rule_id': 'allow-read', 'effect': 'allow', 'conditions': {'action.mode': 'read'}},
            {'rule_id': 'deny-read', 'effect': 'deny', 'conditions': {'action.mode': 'read'}},
        ],
    })
    assert conflict.status == 'rejected'
    assert conflict.reason_code == 'conflicting_policy_rules'


def test_policy_engine_allows_with_obligations_and_projects_to_admission_decision() -> None:
    verdict = PolicyEngine().evaluate(
        {
            'request_id': 'request-1',
            'subject_ref': 'artifact://task/1',
            'action': {'mode': 'read'},
            'resource': {'criticality': 'low'},
        },
        _compiled_pack(),
    )

    assert verdict.decision == 'allow_with_obligations'
    assert verdict.obligations[0].obligation_id == 'receipt-required'

    decision = policy_verdict_to_gov_policy_decision(verdict)
    assert decision.decision == 'allow'
    assert decision.subject_ref == 'artifact://task/1'
    assert 'obligation:receipt-required' in decision.controls
    assert 'constraint:bounded-output' in decision.controls


def test_policy_engine_requires_approval_for_critical_mutation_without_evidence() -> None:
    verdict = PolicyEngine().evaluate(
        {
            'request_id': 'request-2',
            'subject_ref': 'artifact://task/2',
            'action': {'mode': 'mutating'},
            'resource': {'criticality': 'critical'},
        },
        _compiled_pack(),
    )

    assert verdict.decision == 'approval_required'
    assert verdict.reason_code == 'critical_mutating_action_requires_approval'
    assert verdict.blockers == ('operator_approval_required',)


@pytest.mark.parametrize(
    'request_patch',
    [
        {'evidence_refs': ['not-an-approval']},
        {'evidence_refs': ['approval:opaque-reference']},
        {'context': {'approval': True}},
        {'context': {'evidence': {'operator_approval': True}}},
    ],
)
def test_policy_engine_does_not_treat_opaque_claims_as_approval(request_patch) -> None:
    request = {
        'request_id': 'request-opaque-approval',
        'subject_ref': 'artifact://task/opaque-approval',
        'action': {'mode': 'mutating'},
        'resource': {'criticality': 'critical'},
        **request_patch,
    }

    verdict = PolicyEngine().evaluate(request, _compiled_pack())

    assert verdict.decision == 'approval_required'
    assert verdict.reason_code == 'critical_mutating_action_requires_approval'


def test_policy_verdict_rejects_non_finite_risk_score() -> None:
    with pytest.raises(GovApiError, match='invalid_policy_risk_score'):
        validate_policy_verdict(PolicyVerdict(
            verdict_id='verdict-nan',
            request_id='request-nan',
            subject_ref='artifact://task/nan',
            decision='allow',
            risk_score=float('nan'),
        ))


def test_policy_boundary_rejects_unsupported_json_values_and_keys() -> None:
    with pytest.raises(GovApiError, match='json_boundary_unsupported_type'):
        validate_policy_request({
            'request_id': 'request-set',
            'subject_ref': 'artifact://task/set',
            'metadata': {'items': {'not', 'json'}},
        })

    with pytest.raises(GovApiError, match='json_boundary_non_string_key'):
        validate_policy_request({
            'request_id': 'request-key',
            'subject_ref': 'artifact://task/key',
            'action': {1: 'read'},
        })


def test_policy_engine_denies_unsafe_and_unmatched_requests() -> None:
    engine = PolicyEngine()

    unsafe = engine.evaluate(
        {
            'request_id': 'request-3',
            'subject_ref': 'artifact://task/3',
            'action': {'unsafe_execution_shape': True},
        },
        _compiled_pack(),
    )
    assert unsafe.decision == 'deny'
    assert unsafe.reason_code == 'unsafe_execution_shape'

    unmatched = engine.evaluate(
        {
            'request_id': 'request-4',
            'subject_ref': 'artifact://task/4',
            'action': {'mode': 'observe'},
        },
        _compiled_pack(),
    )
    assert unmatched.decision == 'deny'
    assert unmatched.reason_code == 'no_matching_policy_rule'


def test_policy_request_rejects_raw_runtime_ownership_claims() -> None:
    with pytest.raises(GovApiError, match='forbidden_policy_metadata:command'):
        validate_policy_request({
            'request_id': 'request-bad',
            'subject_ref': 'artifact://task/bad',
            'action': {'command': ['rm', '-rf', '/']},
        })
