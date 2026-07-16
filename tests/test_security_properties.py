from __future__ import annotations

import copy
from dataclasses import replace
from typing import Any

from hypothesis import given, settings, strategies as st
import pytest

from govengine._governance_validation import require_sha256_digest
from govengine._json_boundary import JsonBoundaryLimits, bounded_json_copy
from govengine.api import GovApiError
from govengine.approvals import (
    ApprovalAttestation,
    approval_attestation_digest,
)
from govengine.conformance import iter_conformance_cases
from govengine.governance import GovernanceRequest
from govengine.governance_decision import GovernanceDecision
from govengine.policy import CompiledPolicyPack, PolicyCompiler, PolicyEngine
from govengine.receipt_conformance import (
    RuntimeReceiptBinding,
    evaluate_receipt_conformance,
    runtime_receipt_binding_digest,
)


JSON_SCALARS = (
    st.none()
    | st.booleans()
    | st.integers(min_value=-1_000_000, max_value=1_000_000)
    | st.floats(
        min_value=-1_000_000,
        max_value=1_000_000,
        allow_nan=False,
        allow_infinity=False,
    )
    | st.text(max_size=64)
)
JSON_VALUES = st.recursive(
    JSON_SCALARS,
    lambda children: st.lists(children, max_size=8)
    | st.dictionaries(st.text(max_size=24), children, max_size=8),
    max_leaves=64,
)


def _case(case_id: str) -> dict[str, Any]:
    return dict(
        next(case for case in iter_conformance_cases() if case['case_id'] == case_id)
    )


def _typed_numeric_pack(operator: str, expected: int) -> CompiledPolicyPack:
    result = PolicyCompiler().compile(
        {
            'schema_version': 'v1',
            'policy_id': 'property-numeric',
            'version': '1',
            'issuer_ref': 'organization:property',
            'policy_epoch': 1,
            'validity': {
                'not_before': '2026-07-01T00:00:00Z',
                'expires_at': '2026-08-01T00:00:00Z',
            },
            'supersedes': [],
            'rules': [
                {
                    'rule_id': 'numeric',
                    'effect': 'allow',
                    'conditions': [
                        {
                            'path': 'resource.value',
                            'operator': operator,
                            'value': expected,
                        }
                    ],
                    'reason_code': 'numeric_condition_matched',
                }
            ],
        }
    )
    assert result.policy_pack is not None
    return result.policy_pack


@settings(max_examples=75, deadline=None)
@given(JSON_VALUES)
def test_bounded_json_copy_is_deterministic_and_idempotent(value: Any) -> None:
    first = bounded_json_copy(value)

    assert bounded_json_copy(first) == first


@settings(max_examples=40, deadline=None)
@given(limit=st.integers(min_value=1, max_value=12))
def test_bounded_json_depth_limit_fails_closed(limit: int) -> None:
    value: Any = 'leaf'
    for _ in range(limit + 1):
        value = [value]

    with pytest.raises(GovApiError) as exc_info:
        bounded_json_copy(
            value,
            limits=JsonBoundaryLimits(
                max_depth=limit,
                max_nodes=100,
                max_collection_length=100,
                max_string_length=100,
            ),
        )
    assert exc_info.value.reason_code == 'json_boundary_max_depth'


@settings(max_examples=60, deadline=None)
@given(
    operator=st.sampled_from(('lt', 'lte', 'gt', 'gte')),
    actual=st.integers(min_value=-1000, max_value=1000),
    expected=st.integers(min_value=-1000, max_value=1000),
)
def test_typed_numeric_policy_operators_match_python_integer_order(
    operator: str,
    actual: int,
    expected: int,
) -> None:
    verdict = PolicyEngine().evaluate(
        {
            'request_id': 'property-numeric',
            'subject_ref': 'artifact://property/numeric',
            'resource': {'value': actual},
        },
        _typed_numeric_pack(operator, expected),
    )
    relation = {
        'lt': actual < expected,
        'lte': actual <= expected,
        'gt': actual > expected,
        'gte': actual >= expected,
    }[operator]

    assert (verdict.decision == 'allow') is relation


@settings(max_examples=40, deadline=None)
@given(mode=st.text(min_size=1, max_size=24).filter(lambda value: value != 'mutation'))
def test_execution_facts_digest_drift_always_fails_closed(mode: str) -> None:
    request = copy.deepcopy(
        _case('approval-expired')['input']['governance_request']
    )
    request['execution_facts']['action']['mode'] = mode

    with pytest.raises(GovApiError) as exc_info:
        GovernanceRequest.from_mapping(request)
    assert exc_info.value.reason_code == 'execution_facts_digest_mismatch'


@settings(max_examples=30, deadline=None)
@given(
    binding=st.sampled_from(
        (
            (
                'execution_spec_digest',
                'sha256:' + 'f' * 64,
                'approval_execution_spec_digest_mismatch',
            ),
            (
                'target_scope_digest',
                'sha256:' + 'e' * 64,
                'approval_target_scope_digest_mismatch',
            ),
            (
                'attempt_id',
                'attempt-property',
                'approval_attempt_id_mismatch',
            ),
        )
    )
)
def test_approval_binding_mutations_have_stable_reason_codes(
    binding: tuple[str, str, str],
) -> None:
    field, value, reason_code = binding
    request_payload = copy.deepcopy(
        _case('approval-expired')['input']['governance_request']
    )
    approval = dict(request_payload['approval_attestation'])
    approval[field] = value
    checked = ApprovalAttestation.from_mapping(approval)
    request_payload['approval_attestation'] = checked.as_dict()
    request_payload['approval_attestation_digest'] = approval_attestation_digest(
        checked
    )
    with pytest.raises(GovApiError) as exc_info:
        GovernanceRequest.from_mapping(request_payload)
    assert exc_info.value.reason_code == reason_code


@settings(max_examples=40, deadline=None)
@given(
    field=st.sampled_from(
        (
            'attempt_id',
            'runtime_instance_id',
            'lease_epoch',
            'fencing_token_digest',
            'capability_inventory_digest',
        )
    )
)
def test_authorization_mutation_invalidates_governance_decision_digest(
    field: str,
) -> None:
    payload = copy.deepcopy(
        _case('receipt-conformant')['input']['governance_decision']
    )
    current = payload['authorization'][field]
    if isinstance(current, int):
        payload['authorization'][field] = current + 1
    elif str(current).startswith('sha256:'):
        payload['authorization'][field] = 'sha256:' + 'f' * 64
    else:
        payload['authorization'][field] = f'{current}-drift'

    with pytest.raises(GovApiError) as exc_info:
        GovernanceDecision.from_mapping(payload)
    assert exc_info.value.reason_code == 'governance_decision_digest_mismatch'


@settings(max_examples=60, deadline=None)
@given(output_bytes=st.integers(min_value=0, max_value=8192))
def test_receipt_output_limit_property(output_bytes: int) -> None:
    case = _case('receipt-conformant')
    decision = GovernanceDecision.from_mapping(
        case['input']['governance_decision']
    )
    receipt = RuntimeReceiptBinding.from_mapping(
        case['input']['runtime_receipt_binding']
    )
    changed = replace(receipt, output_bytes=output_bytes, receipt_digest='')
    changed = replace(
        changed,
        receipt_digest=runtime_receipt_binding_digest(changed),
    )
    result = evaluate_receipt_conformance(
        decision,
        changed,
        expected_runtime_permit_digest=case['input'][
            'expected_runtime_permit_digest'
        ],
    )

    assert result.conformant is (output_bytes <= 4096)
    assert (
        'receipt_output_limit_exceeded' in result.failures
    ) is (output_bytes > 4096)


@settings(max_examples=50, deadline=None)
@given(
    forbidden=st.sampled_from(
        ('password', 'secret', 'token', 'credential', 'raw_output')
    ),
    depth=st.integers(min_value=0, max_value=8),
)
def test_forbidden_governance_keys_are_rejected_at_any_list_depth(
    forbidden: str,
    depth: int,
) -> None:
    request = copy.deepcopy(
        _case('approval-expired')['input']['governance_request']
    )
    nested: Any = {forbidden: 'redacted-fixture'}
    for _ in range(depth):
        nested = [nested]
    request['execution_facts'] = {'items': nested}

    with pytest.raises(GovApiError) as exc_info:
        GovernanceRequest.from_mapping(request)
    assert exc_info.value.reason_code == 'forbidden_governance_input'


@settings(max_examples=60, deadline=None)
@given(value=st.text(max_size=100).filter(lambda item: len(item) != 71))
def test_invalid_digest_shapes_fail_with_the_requested_reason(value: str) -> None:
    with pytest.raises(GovApiError) as exc_info:
        require_sha256_digest(value, 'property_digest_invalid')
    assert exc_info.value.reason_code == 'property_digest_invalid'
