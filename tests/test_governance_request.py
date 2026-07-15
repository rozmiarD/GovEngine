from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from typing import Any, Mapping

import pytest

from govengine.api import GovApiError
from govengine.approvals import (
    ApprovalAttestation,
    ApprovalRevocationPort,
    ApprovalTrustPolicy,
    approval_attestation_digest,
    validate_approval_attestation,
)
from govengine.governance import (
    GovernanceRequest,
    execution_facts_digest,
    governance_request_digest,
    governance_subject_digest,
    requested_scope_digest,
    validate_governance_request,
)
from govengine.policy import PolicyCompiler, policy_pack_digest
from govengine.signing import govengine_record_digest


class _Revocations(ApprovalRevocationPort):
    def __init__(self, *, revoked: bool = False) -> None:
        self.revoked = revoked
        self.calls: list[tuple[str, str, str]] = []

    def is_revoked(
        self,
        approval_id: str,
        *,
        approval_digest: str,
        revocation_ref: str,
    ) -> bool:
        self.calls.append((approval_id, approval_digest, revocation_ref))
        return self.revoked


def _compiled_policy():
    result = PolicyCompiler().compile(
        {
            'policy_id': 'production-mutation',
            'version': '1',
            'rules': [
                {
                    'rule_id': 'require-approval',
                    'effect': 'approval_required',
                    'conditions': {'action.mode': 'mutation'},
                    'reason_code': 'mutation_requires_approval',
                }
            ],
        }
    )
    assert result.ok
    assert result.policy_pack is not None
    return result.policy_pack


def _base_request_mapping() -> dict[str, Any]:
    policy_pack = _compiled_policy()
    execution_facts = {
        'backend_class': 'http_api',
        'connector': 'connector.inventory',
        'action': 'update',
    }
    requested_scope = {
        'target': 'service:inventory',
        'environment': 'production',
    }
    return {
        'schema_version': 'v1',
        'transaction_id': 'gov-tx-123',
        'operation_id': 'op-123',
        'step_id': 'step-4',
        'attempt_id': 'attempt-2',
        'policy_pack': policy_pack.as_dict(),
        'policy_pack_digest': policy_pack_digest(policy_pack),
        'policy_epoch': 42,
        'execution_facts': execution_facts,
        'execution_facts_digest': execution_facts_digest(execution_facts),
        'execution_spec_digest': 'sha256:' + '1' * 64,
        'payload_digest': 'sha256:' + '2' * 64,
        'requested_scope': requested_scope,
        'requested_scope_digest': requested_scope_digest(requested_scope),
        'side_effect_class': 'mutation',
        'runtime_instance_id': 'rexecop-1',
        'lease_id': 'lease-55',
        'lease_epoch': 9,
        'fencing_token_digest': 'sha256:' + '3' * 64,
    }


def _request_mapping_with_approval(
    *,
    attestation_patch: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    request = _base_request_mapping()
    subject = GovernanceRequest.from_mapping(request)
    attestation: dict[str, Any] = {
        'schema_version': 'v1',
        'approval_id': 'approval-123',
        'subject_digest': governance_subject_digest(subject),
        'operation_id': request['operation_id'],
        'step_id': request['step_id'],
        'attempt_id': request['attempt_id'],
        'execution_spec_digest': request['execution_spec_digest'],
        'execution_facts_digest': request['execution_facts_digest'],
        'target_scope_digest': request['requested_scope_digest'],
        'policy_pack_digest': request['policy_pack_digest'],
        'policy_epoch': request['policy_epoch'],
        'approved_side_effect_class': request['side_effect_class'],
        'approver_ref': 'operator:alice',
        'approver_role': 'infrastructure-admin',
        'trust_domain': 'organization:example',
        'issued_at': '2026-07-15T12:00:00Z',
        'not_before': '2026-07-15T12:00:00Z',
        'expires_at': '2026-07-15T12:15:00Z',
        'revocation_ref': 'approval-revocations:v1',
        'signature_ref': 'sigstore:bundle-123',
    }
    if attestation_patch:
        attestation.update(attestation_patch)
    checked = ApprovalAttestation.from_mapping(attestation)
    request['approval_attestation'] = checked.as_dict()
    request['approval_attestation_digest'] = approval_attestation_digest(checked)
    return request


def _trust_policy() -> ApprovalTrustPolicy:
    return ApprovalTrustPolicy(
        policy_id='production-approvers',
        trusted_roles=('infrastructure-admin',),
        trusted_domains=('organization:example',),
        trusted_approver_refs=('operator:alice',),
        require_signature_ref=True,
    )


def test_governance_request_round_trip_recomputes_owned_digests() -> None:
    request = GovernanceRequest.from_mapping(_request_mapping_with_approval())

    assert validate_governance_request(request) == request
    assert GovernanceRequest.from_mapping(request.as_dict()) == request
    assert request.approval_attestation is not None
    assert governance_request_digest(request).startswith('sha256:')


@pytest.mark.parametrize(
    ('field', 'reason_code'),
    [
        ('policy_pack_digest', 'policy_pack_digest_mismatch'),
        ('execution_facts_digest', 'execution_facts_digest_mismatch'),
        ('requested_scope_digest', 'requested_scope_digest_mismatch'),
        ('approval_attestation_digest', 'approval_attestation_digest_mismatch'),
    ],
)
def test_governance_request_rejects_supplied_owned_digest_drift(
    field: str,
    reason_code: str,
) -> None:
    request = _request_mapping_with_approval()
    request[field] = 'sha256:' + 'f' * 64

    with pytest.raises(GovApiError, match=reason_code):
        GovernanceRequest.from_mapping(request)


@pytest.mark.parametrize(
    ('field', 'value', 'reason_code'),
    [
        ('operation_id', 'op-other', 'approval_operation_id_mismatch'),
        ('step_id', 'step-other', 'approval_step_id_mismatch'),
        ('attempt_id', 'attempt-other', 'approval_attempt_id_mismatch'),
        (
            'execution_spec_digest',
            'sha256:' + 'a' * 64,
            'approval_execution_spec_digest_mismatch',
        ),
        (
            'target_scope_digest',
            'sha256:' + 'b' * 64,
            'approval_target_scope_digest_mismatch',
        ),
        (
            'policy_pack_digest',
            'sha256:' + 'c' * 64,
            'approval_policy_pack_digest_mismatch',
        ),
        ('policy_epoch', 43, 'approval_policy_epoch_mismatch'),
        ('approved_side_effect_class', 'read_only', 'approval_side_effect_class_mismatch'),
    ],
)
def test_governance_request_rejects_approval_for_another_subject(
    field: str,
    value: Any,
    reason_code: str,
) -> None:
    request = _request_mapping_with_approval(attestation_patch={field: value})

    with pytest.raises(GovApiError, match=reason_code):
        GovernanceRequest.from_mapping(request)


def test_approval_validation_checks_trust_time_and_revocation() -> None:
    request = GovernanceRequest.from_mapping(_request_mapping_with_approval())
    revocations = _Revocations()

    attestation = validate_approval_attestation(
        request.approval_attestation,
        request=request,
        trust_policy=_trust_policy(),
        revocation_port=revocations,
        now=datetime(2026, 7, 15, 12, 5, tzinfo=timezone.utc),
    )

    assert attestation.approval_id == 'approval-123'
    assert revocations.calls == [
        (
            'approval-123',
            approval_attestation_digest(attestation),
            'approval-revocations:v1',
        )
    ]


@pytest.mark.parametrize(
    ('attestation_patch', 'reason_code'),
    [
        ({'approver_ref': 'operator:bob'}, 'approval_approver_not_trusted'),
        ({'approver_role': 'viewer'}, 'approval_role_not_trusted'),
        ({'trust_domain': 'organization:other'}, 'approval_trust_domain_not_trusted'),
        ({'signature_ref': ''}, 'approval_signature_ref_required'),
    ],
)
def test_approval_validation_rejects_untrusted_issuer(
    attestation_patch: Mapping[str, Any],
    reason_code: str,
) -> None:
    request = GovernanceRequest.from_mapping(
        _request_mapping_with_approval(attestation_patch=attestation_patch)
    )

    with pytest.raises(GovApiError, match=reason_code):
        validate_approval_attestation(
            request.approval_attestation,
            request=request,
            trust_policy=_trust_policy(),
            revocation_port=_Revocations(),
            now=datetime(2026, 7, 15, 12, 5, tzinfo=timezone.utc),
        )


@pytest.mark.parametrize(
    ('now', 'reason_code'),
    [
        (datetime(2026, 7, 15, 11, 59, tzinfo=timezone.utc), 'approval_not_yet_valid'),
        (datetime(2026, 7, 15, 12, 15, tzinfo=timezone.utc), 'approval_expired'),
    ],
)
def test_approval_validation_rejects_invalid_time_window(
    now: datetime,
    reason_code: str,
) -> None:
    request = GovernanceRequest.from_mapping(_request_mapping_with_approval())

    with pytest.raises(GovApiError, match=reason_code):
        validate_approval_attestation(
            request.approval_attestation,
            request=request,
            trust_policy=_trust_policy(),
            revocation_port=_Revocations(),
            now=now,
        )


def test_approval_validation_rejects_revoked_attestation() -> None:
    request = GovernanceRequest.from_mapping(_request_mapping_with_approval())

    with pytest.raises(GovApiError, match='approval_revoked'):
        validate_approval_attestation(
            request.approval_attestation,
            request=request,
            trust_policy=_trust_policy(),
            revocation_port=_Revocations(revoked=True),
            now=datetime(2026, 7, 15, 12, 5, tzinfo=timezone.utc),
        )


@pytest.mark.parametrize('field', ['execution_facts', 'requested_scope'])
def test_governance_request_rejects_nested_secret_material(field: str) -> None:
    request = _base_request_mapping()
    request[field] = {'items': [{'password': 'inline-secret'}]}
    digest_field = (
        'execution_facts_digest' if field == 'execution_facts' else 'requested_scope_digest'
    )
    record_type = (
        'govengine.governance.ExecutionFacts'
        if field == 'execution_facts'
        else 'govengine.governance.RequestedScope'
    )
    request[digest_field] = govengine_record_digest(
        request[field],
        record_type=record_type,
    )

    with pytest.raises(GovApiError, match='forbidden_governance_input:password'):
        GovernanceRequest.from_mapping(request)


def test_v1_facade_exposes_only_the_bounded_g2a_contract() -> None:
    from govengine import v1

    assert v1.ApprovalAttestation is ApprovalAttestation
    assert v1.ApprovalRevocationPort is ApprovalRevocationPort
    assert v1.ApprovalTrustPolicy is ApprovalTrustPolicy
    assert v1.GovernanceRequest is GovernanceRequest
    assert v1.validate_approval_attestation is validate_approval_attestation
    assert v1.validate_governance_request is validate_governance_request


@pytest.mark.parametrize(
    ('field', 'value', 'reason_code'),
    [
        ('operation_id', '', 'missing_governance_operation_id'),
        ('policy_epoch', -1, 'invalid_governance_policy_epoch'),
        (
            'fencing_token_digest',
            'sha256:not-a-digest',
            'invalid_governance_fencing_token_digest',
        ),
    ],
)
def test_direct_governance_request_instances_still_receive_full_validation(
    field: str,
    value: Any,
    reason_code: str,
) -> None:
    request = GovernanceRequest.from_mapping(_base_request_mapping())

    with pytest.raises(GovApiError, match=reason_code):
        validate_governance_request(replace(request, **{field: value}))


@pytest.mark.parametrize(
    ('field', 'value', 'reason_code'),
    [
        ('attempt_id', '', 'missing_approval_attempt_id'),
        ('policy_epoch', -1, 'invalid_approval_policy_epoch'),
        (
            'subject_digest',
            'sha256:not-a-digest',
            'invalid_approval_subject_digest',
        ),
    ],
)
def test_direct_approval_attestation_instances_still_receive_full_validation(
    field: str,
    value: Any,
    reason_code: str,
) -> None:
    request = GovernanceRequest.from_mapping(_request_mapping_with_approval())
    assert request.approval_attestation is not None

    with pytest.raises(GovApiError, match=reason_code):
        approval_attestation_digest(
            replace(request.approval_attestation, **{field: value})
        )
