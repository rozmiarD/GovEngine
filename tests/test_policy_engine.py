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
from govengine.policy.model import PolicyConstraint, PolicyObligation


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


def _policy_metadata_result(surface: str, metadata):
    if surface == 'pack':
        result = PolicyCompiler().compile({
            'policy_id': 'metadata-pack',
            'version': '1',
            'schema_version': 'v1',
            'issuer_ref': 'issuer://fixture/security',
            'policy_epoch': 1,
            'validity': {
                'not_before': '2026-01-01T00:00:00Z',
                'expires_at': '2027-01-01T00:00:00Z',
            },
            'supersedes': [],
            'rules': [
                {
                    'rule_id': 'allow-read',
                    'effect': 'allow',
                    'conditions': [
                        {'path': 'action.mode', 'operator': 'eq', 'value': 'read'},
                    ],
                },
            ],
            'metadata': metadata,
        })
        if not result.ok:
            assert result.policy_pack is None
            raise GovApiError(result.diagnostics[0])
        assert result.policy_pack is not None
        return result.policy_pack.as_dict()['metadata']
    if surface == 'request':
        return validate_policy_request({
            'request_id': 'metadata-request',
            'subject_ref': 'artifact://fixture/metadata',
            'metadata': metadata,
        }).as_dict()['metadata']
    if surface == 'obligation':
        return PolicyObligation.from_mapping({
            'obligation_id': 'metadata-obligation',
            'kind': 'receipt',
            'metadata': metadata,
        }).as_dict()['metadata']
    if surface == 'constraint':
        return PolicyConstraint.from_mapping({
            'constraint_id': 'metadata-constraint',
            'kind': 'output_limit',
            'value': 1024,
            'metadata': metadata,
        }).as_dict()['metadata']
    if surface == 'verdict':
        return PolicyVerdict.from_mapping({
            'verdict_id': 'metadata-verdict',
            'request_id': 'metadata-request',
            'subject_ref': 'artifact://fixture/metadata',
            'decision': 'allow',
            'metadata': metadata,
        }).as_dict()['metadata']
    raise AssertionError(f'unknown test surface: {surface}')


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


@pytest.mark.parametrize('surface', ('pack', 'request', 'obligation', 'constraint', 'verdict'))
@pytest.mark.parametrize(
    ('metadata', 'forbidden_key'),
    [
        ({'password': 'fixture-value'}, 'password'),
        ({'ToKeN': 'fixture-value'}, 'token'),
        ({' secret': 'fixture-value'}, 'secret'),
        ({'api_key ': 'fixture-value'}, 'api_key'),
        ({'nested': {' Credential ': 'fixture-value'}}, 'credential'),
        ({'nested': [{'command': 'fixture-value'}]}, 'command'),
        ({'nested': ({' shell ': 'fixture-value'},)}, 'shell'),
        ({'outer': [[{' Token ': 'fixture-value'}]]}, 'token'),
    ],
    ids=(
        'exact',
        'case',
        'leading-whitespace',
        'trailing-whitespace',
        'nested-mapping',
        'mapping-inside-list',
        'mapping-inside-tuple',
        'mapping-inside-nested-sequences',
    ),
)
def test_policy_metadata_surfaces_reject_normalized_forbidden_keys(
    surface,
    metadata,
    forbidden_key,
) -> None:
    with pytest.raises(GovApiError) as exc_info:
        _policy_metadata_result(surface, metadata)

    assert exc_info.value.reason_code == 'forbidden_policy_metadata'
    assert exc_info.value.context['detail'] == forbidden_key


@pytest.mark.parametrize('surface', ('pack', 'request', 'obligation', 'constraint', 'verdict'))
def test_policy_metadata_surfaces_preserve_safe_bounded_metadata(surface) -> None:
    metadata = {
        'labels': ['fixture', {'owner_ref': 'artifact://fixture/owner'}],
        'tuple_values': ('alpha', {'note': 'deterministic'}),
    }
    expected = {
        'labels': ['fixture', {'owner_ref': 'artifact://fixture/owner'}],
        'tuple_values': ['alpha', {'note': 'deterministic'}],
    }

    assert _policy_metadata_result(surface, metadata) == expected
    assert _policy_metadata_result(surface, metadata) == expected


@pytest.mark.parametrize(
    ('metadata', 'reason_code'),
    [
        ({'items': {'not', 'json'}}, 'json_boundary_unsupported_type'),
        ({1: 'not-a-string-key'}, 'json_boundary_non_string_key'),
    ],
)
def test_policy_pack_metadata_preserves_bounded_json_rejection(metadata, reason_code) -> None:
    result = PolicyCompiler().compile({
        'policy_id': 'bounded-metadata-pack',
        'version': '1',
        'rules': [
            {
                'rule_id': 'allow-read',
                'effect': 'allow',
                'conditions': {'action.mode': 'read'},
            },
        ],
        'metadata': metadata,
    })

    assert result.status == 'rejected'
    assert result.reason_code == reason_code
    assert result.policy_pack is None


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
