from __future__ import annotations

import copy

import pytest

from govengine.api import GovApiError
from govengine.policy.compiler import PolicyCompiler
from govengine.policy.enforcement import policy_pack_digest
from govengine.policy.explain import explain_policy_evaluation
from govengine.policy.migration import migrate_policy_pack_v0_1_to_v1
from govengine.policy.reasons import (
    POLICY_REASON_CODE_REGISTRY_SCHEMA_VERSION,
    policy_reason_code_registry,
)
from govengine.policy.runtime import PolicyEngine
from govengine.signing import govengine_record_digest


def _legacy_pack() -> dict[str, object]:
    return {
        'policy_id': 'legacy-read-policy',
        'version': '0.1.0',
        'rules': [
            {
                'rule_id': 'read-low-risk',
                'effect': 'allow',
                'priority': 20,
                'conditions': {
                    'resource.criticality': 'low',
                    'action.mode': 'read',
                },
                'reason_code': 'read_allowed',
                'risk_class': 'low',
                'risk_score': 0.1,
            }
        ],
    }


def _request() -> dict[str, object]:
    return {
        'request_id': 'request-read',
        'subject_ref': 'artifact://policy/request-read',
        'action': {'mode': 'read'},
        'resource': {'criticality': 'low'},
    }


def _migrated_pack() -> dict[str, object]:
    return migrate_policy_pack_v0_1_to_v1(
        _legacy_pack(),
        issuer_ref='organization:example',
        policy_epoch=9,
        not_before='2026-07-16T00:00:00Z',
        expires_at='2026-08-16T00:00:00Z',
        supersedes=('legacy-read-policy@0.0.9',),
    )


def test_policy_v1_trace_is_digest_bound_and_golden() -> None:
    result = PolicyCompiler().compile(_migrated_pack())
    assert result.ok
    assert result.policy_pack is not None

    explanation = explain_policy_evaluation(_request(), result.policy_pack)
    payload = explanation.as_dict()
    body = copy.deepcopy(payload)
    trace_digest = body.pop('trace_digest')

    assert payload['schema_version'] == 'v1'
    assert payload['decision'] == 'allow'
    assert payload['reason_code'] == 'read_allowed'
    assert payload['policy_pack_digest'] == policy_pack_digest(result.policy_pack)
    assert payload['policy_issuer_ref'] == 'organization:example'
    assert payload['policy_epoch'] == 9
    assert payload['reason_registry_version'] == POLICY_REASON_CODE_REGISTRY_SCHEMA_VERSION
    assert trace_digest == govengine_record_digest(
        body,
        record_type='govengine.policy.PolicyEvaluationExplanation',
        schema_version='v1',
    )
    assert {
        'policy_pack_digest': payload['policy_pack_digest'],
        'trace_digest': trace_digest,
        'matched_rule': payload['matched_rule'],
        'rule_evaluations': payload['rule_evaluations'],
    } == {
        'policy_pack_digest': (
            'sha256:c868c34cafb9dbbb41c4480d5f9a2e1e'
            '7bbef5694b3de8c2b0355c1db1e46aaa'
        ),
        'trace_digest': (
            'sha256:fe3ef5ebbd7a2eabf30383f60377bc0b'
            '21c90ae9b76fdf4a30fc9505e86356f5'
        ),
        'matched_rule': {
            'rule_id': 'read-low-risk',
            'effect': 'allow',
            'priority': 20,
            'reason_code': 'read_allowed',
            'matched': True,
            'conditions': [
                {
                    'matched': True,
                    'redacted': True,
                    'path': 'action.mode',
                    'operator': 'eq',
                },
                {
                    'matched': True,
                    'redacted': True,
                    'path': 'resource.criticality',
                    'operator': 'eq',
                },
            ],
        },
        'rule_evaluations': [
            {
                'rule_id': 'read-low-risk',
                'effect': 'allow',
                'priority': 20,
                'reason_code': 'read_allowed',
                'matched': True,
                'conditions': [
                    {
                        'matched': True,
                        'redacted': True,
                        'path': 'action.mode',
                        'operator': 'eq',
                    },
                    {
                        'matched': True,
                        'redacted': True,
                        'path': 'resource.criticality',
                        'operator': 'eq',
                    },
                ],
            }
        ],
    }


def test_policy_v0_1_migration_preserves_decision_without_inventing_trust() -> None:
    legacy_result = PolicyCompiler().compile(_legacy_pack())
    migrated = _migrated_pack()
    migrated_result = PolicyCompiler().compile(migrated)
    assert legacy_result.policy_pack is not None
    assert migrated_result.policy_pack is not None

    legacy_verdict = PolicyEngine().evaluate(_request(), legacy_result.policy_pack)
    migrated_verdict = PolicyEngine().evaluate(_request(), migrated_result.policy_pack)

    assert migrated['schema_version'] == 'v1'
    assert migrated['issuer_ref'] == 'organization:example'
    assert migrated['policy_epoch'] == 9
    assert migrated['rules'][0]['conditions'] == [
        {'path': 'action.mode', 'operator': 'eq', 'value': 'read'},
        {'path': 'resource.criticality', 'operator': 'eq', 'value': 'low'},
    ]
    assert (migrated_verdict.decision, migrated_verdict.reason_code) == (
        legacy_verdict.decision,
        legacy_verdict.reason_code,
    )


def test_policy_v0_1_migration_rejects_wrong_source_and_invalid_target_binding() -> None:
    v1 = _migrated_pack()
    with pytest.raises(GovApiError, match='policy_migration_source_schema_mismatch'):
        migrate_policy_pack_v0_1_to_v1(
            v1,
            issuer_ref='organization:example',
            policy_epoch=10,
            not_before='2026-07-16T00:00:00Z',
            expires_at='2026-08-16T00:00:00Z',
        )

    with pytest.raises(GovApiError) as exc_info:
        migrate_policy_pack_v0_1_to_v1(
            _legacy_pack(),
            issuer_ref='',
            policy_epoch=10,
            not_before='2026-07-16T00:00:00Z',
            expires_at='2026-08-16T00:00:00Z',
        )
    assert exc_info.value.reason_code == 'policy_migration_target_invalid'
    assert exc_info.value.context == {'target_reason_code': 'missing_policy_issuer_ref'}


def test_policy_reason_registry_separates_kernel_and_authored_codes() -> None:
    registry = policy_reason_code_registry()
    codes = [item['code'] for item in registry['kernel_codes']]

    assert registry['schema_version'] == 'v1'
    assert registry['authored_codes'] == {
        'owner': 'policy_pack_author',
        'pattern': r'^[a-z][a-z0-9_]{0,127}$',
        'max_length': 128,
    }
    assert len(codes) == len(set(codes))
    assert {
        'compiled',
        'no_matching_policy_rule',
        'policy_condition_operand_type_mismatch',
        'invalid_policy_reason_code',
    }.issubset(codes)


@pytest.mark.parametrize(
    ('field', 'value', 'reason_code'),
    [
        ('reason_code', 'not valid', 'invalid_policy_reason_code'),
        ('reason_code', 7, 'invalid_policy_reason_code'),
        ('risk_class', 'unknown', 'invalid_policy_risk_class'),
        ('risk_score', '0.5', 'invalid_policy_risk_score'),
        ('risk_score', float('nan'), 'json_boundary_non_finite_number'),
        ('risk_score', 1.1, 'invalid_policy_risk_score'),
    ],
)
def test_policy_rule_reason_and_risk_values_are_strict(
    field: str,
    value: object,
    reason_code: str,
) -> None:
    policy = _legacy_pack()
    policy['rules'][0][field] = value  # type: ignore[index]

    assert PolicyCompiler().compile(policy).reason_code == reason_code
