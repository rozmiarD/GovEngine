from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from govengine.api import GovApiError
from govengine.approvals import (
    ApprovalAttestation,
    ApprovalRevocationPort,
    ApprovalTrustPolicy,
    approval_attestation_digest,
)
from govengine.capabilities import (
    CapabilityInventoryBinding,
    OperationCapabilityRequirements,
    capability_inventory_binding_digest,
    operation_capability_requirements_digest,
)
from govengine.governance import (
    GovernanceRequest,
    execution_facts_digest,
    governance_request_digest,
    governance_subject_digest,
    requested_scope_digest,
)
from govengine.governance_decision import (
    ApprovalSignatureVerificationPort,
    GovernanceDecision,
    PolicyActivationPort,
    _governance_decision_body_digest,
    evaluate_governance,
    governance_decision_digest,
)
from govengine.policy import CompiledPolicyPack, PolicyCompiler, policy_pack_digest
from govengine.policy.activation import PolicyActivationBinding
from govengine.scope_policy import ScopePolicyBinding, scope_policy_binding_digest
from govengine.typed_execution_governance import (
    project_typed_execution_governance,
    runtime_capability_descriptor_digest,
    typed_execution_governance_request_digest,
)
from govengine.typed_execution_governed_admission import (
    TYPED_EXECUTION_GOVERNED_ADMISSION_SCHEMA_VERSION,
    TypedExecutionGovernedAdmission,
    _admission_body_digest,
    evaluate_typed_execution_governed_admission,
    validate_typed_execution_governed_admission,
)


NOW = datetime(2026, 7, 15, 12, 5, tzinfo=timezone.utc)


class _PolicyActivation(PolicyActivationPort):
    def __init__(self, request: dict[str, Any]) -> None:
        self.request = request

    def current_binding(self, policy_id: str) -> PolicyActivationBinding:
        compiled = PolicyCompiler().compile(self.request['policy_pack'])
        assert compiled.policy_pack is not None
        pack = compiled.policy_pack
        return PolicyActivationBinding.from_mapping(
            {
                'schema_version': 'v1',
                'binding_id': 'policy-activation:production-mutation',
                'policy_id': policy_id,
                'policy_version': pack.version,
                'policy_pack_digest': self.request['policy_pack_digest'],
                'policy_epoch': self.request['policy_epoch'],
                'issuer_ref': pack.issuer_ref,
                'trust_ref': 'policy-trust:production',
                'status': 'active',
                'not_before': '2026-07-15T12:00:00Z',
                'expires_at': '2026-07-15T13:00:00Z',
            }
        )


class _Revocations(ApprovalRevocationPort):
    def __init__(self, *, revoked: bool = False) -> None:
        self.revoked = revoked

    def is_revoked(
        self,
        approval_id: str,
        *,
        approval_digest: str,
        revocation_ref: str,
    ) -> bool:
        return self.revoked


class _SignatureVerifier(ApprovalSignatureVerificationPort):
    def __init__(self, *, valid: bool = True) -> None:
        self.valid = valid

    def verify_approval_signature(
        self,
        attestation: ApprovalAttestation,
        *,
        approval_digest: str,
        trust_policy_id: str,
    ) -> bool:
        return bool(
            self.valid
            and attestation.approval_id
            and approval_digest
            and trust_policy_id
        )


def _trust_policy() -> ApprovalTrustPolicy:
    return ApprovalTrustPolicy(
        policy_id='production-approvers',
        trusted_roles=('infrastructure-admin',),
        trusted_domains=('organization:example',),
        trusted_approver_refs=('operator:alice',),
        require_signature_ref=True,
    )


def _digest(seed: str) -> str:
    return f'sha256:{seed * 64}'[:71]


def _typed_request(
    *,
    approval_evidence_ref: str = '',
    required_capabilities: tuple[str, ...] = ('connector.fixture.static',),
    **overrides: Any,
) -> dict[str, Any]:
    capability = {
        'schema_version': 'v0.1',
        'backend_class': 'static_fixture',
        'identity_class': 'none',
        'egress_class': 'no_network',
        'read_only_backend': False,
        'live_backend_posture': 'fixture_only',
        'network_boundary': {
            'egress': 'no_network',
            'host_declared': False,
        },
        'secret_ref_requirements': [],
        'declared_capability_descriptors': ['connector.fixture.static'],
        'certification_tier': 'core',
        'mode': 'apply',
    }
    evidence: dict[str, Any] = {'receipt_required': True}
    if approval_evidence_ref:
        evidence['approval_evidence_ref'] = approval_evidence_ref
    request = {
        'schema_version': 'v0.1',
        'request_id': 'typed-exec:op-123:step-4',
        'operation_id': 'op-123',
        'step_id': 'step-4',
        'operation_mode': 'apply',
        'step_execution_spec_digest': _digest('1'),
        'capability_descriptor_digest': runtime_capability_descriptor_digest(
            capability
        ),
        'payload_schema': 'rexecop.static_fixture_execution_spec.v0.1',
        'payload_digest': _digest('2'),
        'backend_class': 'static_fixture',
        'connector': 'fixture_source',
        'action': 'mutate_fixture_state',
        'read_only': False,
        'side_effect_class': 'mutation',
        'capability_descriptor': capability,
        'evidence_requirements': evidence,
        'allowed_network_egress': ['no_network'],
        'required_capability_descriptors': list(required_capabilities),
    }
    request.update(overrides)
    return request


def _compiled_policy(
    *,
    effect: str = 'approval_required',
) -> CompiledPolicyPack:
    result = PolicyCompiler().compile(
        {
            'policy_id': 'production-mutation',
            'version': '1',
            'schema_version': 'v1',
            'issuer_ref': 'organization:example',
            'policy_epoch': 42,
            'validity': {
                'not_before': '2026-07-15T12:00:00Z',
                'expires_at': '2026-07-15T13:00:00Z',
            },
            'supersedes': [],
            'rules': [
                {
                    'rule_id': 'govern-mutation',
                    'effect': effect,
                    'conditions': [
                        {
                            'path': 'action.mode',
                            'operator': 'eq',
                            'value': 'mutation',
                        }
                    ],
                    'reason_code': (
                        'mutation_requires_approval'
                        if effect == 'approval_required'
                        else 'mutation_denied'
                    ),
                    'obligations': [
                        {'obligation_id': 'receipt', 'kind': 'receipt'}
                    ],
                    'constraints': [
                        {
                            'constraint_id': 'bounded-output',
                            'kind': 'output_limit',
                            'value': 4096,
                        }
                    ],
                }
            ],
        }
    )
    assert result.ok
    assert result.policy_pack is not None
    return result.policy_pack


def _governance_request(
    typed_request: dict[str, Any],
    *,
    actual_operation_mode: str,
    with_approval: bool = True,
    policy_effect: str = 'approval_required',
    approval_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    policy_pack = _compiled_policy(effect=policy_effect)
    pack_digest = policy_pack_digest(policy_pack)
    execution_facts = {
        'schema_version': 'v0.1',
        'request_id': 'gov-tx-123',
        'subject_ref': 'governance:op-123:step-4:attempt-2',
        'principal': {'kind': 'operator'},
        'action': {'mode': 'mutation'},
        'resource': {'criticality': 'low'},
        'context': {'environment': 'production'},
        'evidence_refs': [],
        'metadata': {
            'actual_operation_mode': actual_operation_mode,
            'typed_execution_governance_request_digest': (
                typed_execution_governance_request_digest(typed_request)
            ),
        },
    }
    requested_scope = {
        'target_namespace': 'service.inventory',
        'environment': 'production',
        'requested_destination': {
            'scheme': 'https',
            'effective_port': 443,
            'address_class': 'public',
            'origin_binding_digest': _digest('4'),
        },
    }
    scope_policy = ScopePolicyBinding.from_mapping(
        {
            'schema_version': 'v1',
            'binding_id': 'scope-policy-1',
            'policy_pack_digest': pack_digest,
            'policy_epoch': 42,
            'source_ref': 'policy-pack:production-mutation@1',
            'attestation_ref': 'catalog-attestation:scope-42',
            'allowed_target_namespaces': ['service.inventory'],
            'network_allowed': True,
            'allowed_schemes': ['https'],
            'allowed_ports': [443],
            'allowed_address_classes': ['public'],
            'redirect_policy': 'same_origin',
            'private_networks_allowed': False,
        }
    )
    requirements = OperationCapabilityRequirements.from_mapping(
        {
            'schema_version': 'v1',
            'requirements_id': 'requirements-1',
            'operation_id': 'op-123',
            'step_id': 'step-4',
            'execution_spec_digest': typed_request[
                'step_execution_spec_digest'
            ],
            'required_backend_class': 'static_fixture',
            'side_effect_class': 'mutation',
            'required_capabilities': [
                'connector.fixture.static',
                'receipt.terminal',
            ],
        }
    )
    inventory = CapabilityInventoryBinding.from_mapping(
        {
            'schema_version': 'v1',
            'inventory_id': 'runtime-inventory-42',
            'runtime_instance_id': 'rexecop-1',
            'runtime_version': '0.3.0rc2',
            'inventory_epoch': 42,
            'source_ref': 'runtime-registry:rexecop-1',
            'attestation_ref': 'runtime-inventory-attestation:42',
            'backend_classes': ['static_fixture'],
            'side_effect_classes': ['mutation'],
            'capabilities': [
                'connector.fixture.static',
                'receipt.terminal',
            ],
        }
    )
    request: dict[str, Any] = {
        'schema_version': 'v1',
        'transaction_id': 'gov-tx-123',
        'operation_id': 'op-123',
        'step_id': 'step-4',
        'attempt_id': 'attempt-2',
        'policy_pack': policy_pack.as_dict(),
        'policy_pack_digest': pack_digest,
        'policy_epoch': 42,
        'execution_facts': execution_facts,
        'execution_facts_digest': execution_facts_digest(execution_facts),
        'execution_spec_digest': typed_request['step_execution_spec_digest'],
        'payload_digest': typed_request['payload_digest'],
        'requested_scope': requested_scope,
        'requested_scope_digest': requested_scope_digest(requested_scope),
        'scope_policy_binding': scope_policy.as_dict(),
        'scope_policy_binding_digest': scope_policy_binding_digest(scope_policy),
        'capability_requirements': requirements.as_dict(),
        'capability_requirements_digest': (
            operation_capability_requirements_digest(requirements)
        ),
        'capability_inventory': inventory.as_dict(),
        'capability_inventory_digest': capability_inventory_binding_digest(
            inventory
        ),
        'side_effect_class': 'mutation',
        'runtime_instance_id': 'rexecop-1',
        'lease_id': 'lease-55',
        'lease_epoch': 9,
        'fencing_token_digest': _digest('3'),
    }
    if with_approval:
        subject = GovernanceRequest.from_mapping(request)
        approval = {
            'schema_version': 'v1',
            'approval_id': 'approval-123',
            'subject_digest': governance_subject_digest(subject),
            'operation_id': request['operation_id'],
            'step_id': request['step_id'],
            'attempt_id': request['attempt_id'],
            'execution_spec_digest': request['execution_spec_digest'],
            'execution_facts_digest': request['execution_facts_digest'],
            'target_scope_digest': request['requested_scope_digest'],
            'policy_pack_digest': pack_digest,
            'policy_epoch': 42,
            'approved_side_effect_class': 'mutation',
            'approver_ref': 'operator:alice',
            'approver_role': 'infrastructure-admin',
            'trust_domain': 'organization:example',
            'issued_at': '2026-07-15T12:00:00Z',
            'not_before': '2026-07-15T12:00:00Z',
            'expires_at': '2026-07-15T12:15:00Z',
            'revocation_ref': 'approval-revocations:v1',
            'signature_ref': 'sigstore:bundle-123',
        }
        approval.update(approval_overrides or {})
        attestation = ApprovalAttestation.from_mapping(approval)
        request['approval_attestation'] = attestation.as_dict()
        request['approval_attestation_digest'] = approval_attestation_digest(
            attestation
        )
    return request


def _evaluate(
    typed_request: dict[str, Any],
    governance_request: dict[str, Any],
    *,
    actual_operation_mode: str,
    admitted_at: datetime = NOW,
    revoked: bool = False,
    valid_signature: bool = True,
) -> tuple[TypedExecutionGovernedAdmission, GovernanceDecision]:
    return evaluate_typed_execution_governed_admission(
        typed_request,
        governance_request,
        actual_operation_mode=actual_operation_mode,
        policy_activation_port=_PolicyActivation(governance_request),
        evaluated_at=NOW,
        admitted_at=admitted_at,
        approval_trust_policy=_trust_policy(),
        approval_revocation_port=_Revocations(revoked=revoked),
        approval_signature_verifier=_SignatureVerifier(valid=valid_signature),
        authorization_nonce='nonce-123',
        authorization_expires_at=NOW + timedelta(seconds=30),
    )


@pytest.mark.parametrize('actual_operation_mode', ['apply', 'recovery'])
def test_governed_admission_allows_exact_approval_attested_mode(
    actual_operation_mode: str,
) -> None:
    typed_request = _typed_request()
    governance_request = _governance_request(
        typed_request,
        actual_operation_mode=actual_operation_mode,
    )

    admission, decision = _evaluate(
        typed_request,
        governance_request,
        actual_operation_mode=actual_operation_mode,
    )

    assert admission.status == 'passed'
    assert (
        admission.schema_version
        == TYPED_EXECUTION_GOVERNED_ADMISSION_SCHEMA_VERSION
    )
    assert admission.allowed is True
    assert admission.actual_operation_mode == actual_operation_mode
    assert admission.typed_execution_operation_mode == 'apply'
    assert admission.discounted_typed_execution_blockers == (
        'mutation_requires_approval_evidence',
    )
    assert decision.allowed is True
    assert admission.governance_decision_digest == decision.decision_digest
    assert admission.approval_attestation_digest == (
        decision.approval_attestation_digest
    )
    assert (
        TypedExecutionGovernedAdmission.from_mapping(admission.as_dict())
        == admission
    )
    assert (
        validate_typed_execution_governed_admission(
            admission.as_dict(),
            typed_execution_request=typed_request,
            governance_request=governance_request,
            governance_decision=decision,
            validated_at=NOW,
        )
        == admission
    )


@pytest.mark.parametrize(
    ('approval_evidence_ref', 'expected_discounted'),
    [
        ('', 'mutation_requires_approval_evidence'),
        (_digest('a'), 'mutation_requires_approval_attestation'),
    ],
)
def test_opaque_ref_or_missing_attestation_never_becomes_authority(
    approval_evidence_ref: str,
    expected_discounted: str,
) -> None:
    typed_request = _typed_request(
        approval_evidence_ref=approval_evidence_ref
    )
    governance_request = _governance_request(
        typed_request,
        actual_operation_mode='apply',
        with_approval=False,
    )

    admission, decision = _evaluate(
        typed_request,
        governance_request,
        actual_operation_mode='apply',
    )

    assert admission.status == 'blocked'
    assert admission.allowed is False
    assert admission.discounted_typed_execution_blockers == (
        expected_discounted,
    )
    assert admission.blockers[0] == 'governance_decision_not_allowed'
    assert 'approval_attestation_required' in admission.blockers
    assert decision.allowed is False
    assert decision.authorization is None


@pytest.mark.parametrize(
    ('approval_overrides', 'reason_code'),
    [
        (
            {
                'not_before': '2026-07-15T12:06:00Z',
                'expires_at': '2026-07-15T12:15:00Z',
            },
            'approval_not_yet_valid',
        ),
        (
            {'expires_at': '2026-07-15T12:05:00Z'},
            'approval_expired',
        ),
        (
            {'approver_role': 'observer'},
            'approval_role_not_trusted',
        ),
        (
            {'trust_domain': 'organization:other'},
            'approval_trust_domain_not_trusted',
        ),
        (
            {'approver_ref': 'operator:mallory'},
            'approval_approver_not_trusted',
        ),
    ],
)
def test_invalid_approval_authority_fails_closed(
    approval_overrides: dict[str, Any],
    reason_code: str,
) -> None:
    typed_request = _typed_request()
    governance_request = _governance_request(
        typed_request,
        actual_operation_mode='apply',
        approval_overrides=approval_overrides,
    )

    with pytest.raises(GovApiError, match=reason_code):
        _evaluate(
            typed_request,
            governance_request,
            actual_operation_mode='apply',
        )


@pytest.mark.parametrize(
    ('revoked', 'valid_signature', 'reason_code'),
    [
        (True, True, 'approval_revoked'),
        (False, False, 'approval_signature_verification_failed'),
    ],
)
def test_revoked_or_signature_invalid_approval_fails_closed(
    revoked: bool,
    valid_signature: bool,
    reason_code: str,
) -> None:
    typed_request = _typed_request()
    governance_request = _governance_request(
        typed_request,
        actual_operation_mode='apply',
    )

    with pytest.raises(GovApiError, match=reason_code):
        _evaluate(
            typed_request,
            governance_request,
            actual_operation_mode='apply',
            revoked=revoked,
            valid_signature=valid_signature,
        )


def test_typed_precheck_cannot_discount_any_other_blocker() -> None:
    typed_request = _typed_request(required_capabilities=())
    governance_request = _governance_request(
        typed_request,
        actual_operation_mode='apply',
    )

    with pytest.raises(
        GovApiError,
        match='typed_execution_governed_precheck_blocked',
    ) as exc_info:
        _evaluate(
            typed_request,
            governance_request,
            actual_operation_mode='apply',
        )

    assert exc_info.value.context['blockers'] == [
        'operation_capability_requirements_missing'
    ]


def test_non_allowed_and_expired_decisions_are_blocked() -> None:
    typed_request = _typed_request()
    denied_request = _governance_request(
        typed_request,
        actual_operation_mode='apply',
        policy_effect='deny',
    )
    denied, denied_decision = _evaluate(
        typed_request,
        denied_request,
        actual_operation_mode='apply',
    )
    assert denied.status == 'blocked'
    assert denied.blockers[0] == 'governance_decision_not_allowed'
    assert denied_decision.allowed is False

    allowed_request = _governance_request(
        typed_request,
        actual_operation_mode='apply',
    )
    expired, expired_decision = _evaluate(
        typed_request,
        allowed_request,
        actual_operation_mode='apply',
        admitted_at=NOW + timedelta(seconds=30),
    )
    assert expired.status == 'blocked'
    assert expired.blockers == ('governance_decision_expired',)
    assert expired_decision.allowed is True


@pytest.mark.parametrize(
    ('field_name', 'replacement_value', 'reason_code'),
    [
        (
            'actual_operation_mode',
            'recovery',
            'typed_execution_governed_actual_operation_mode_mismatch',
        ),
        (
            'request_id',
            'typed-exec:other',
            'typed_execution_governed_request_id_mismatch',
        ),
        (
            'transaction_id',
            'gov-tx-other',
            'typed_execution_governed_transaction_id_mismatch',
        ),
        (
            'decision_id',
            'gov-decision:other',
            'typed_execution_governed_decision_id_mismatch',
        ),
        (
            'operation_id',
            'op-other',
            'typed_execution_governed_operation_id_mismatch',
        ),
        (
            'step_id',
            'step-other',
            'typed_execution_governed_step_id_mismatch',
        ),
        (
            'attempt_id',
            'attempt-other',
            'typed_execution_governed_attempt_id_mismatch',
        ),
        (
            'runtime_instance_id',
            'rexecop-other',
            'typed_execution_governed_runtime_instance_id_mismatch',
        ),
        (
            'lease_id',
            'lease-other',
            'typed_execution_governed_lease_id_mismatch',
        ),
        (
            'lease_epoch',
            10,
            'typed_execution_governed_lease_epoch_mismatch',
        ),
        (
            'fencing_token_digest',
            _digest('a'),
            'typed_execution_governed_fencing_token_digest_mismatch',
        ),
        (
            'typed_execution_request_digest',
            _digest('b'),
            'typed_execution_governed_request_digest_mismatch',
        ),
        (
            'typed_execution_governance_projection_digest',
            _digest('c'),
            'typed_execution_governed_projection_digest_mismatch',
        ),
        (
            'typed_execution_capability_compatibility_digest',
            _digest('d'),
            'typed_execution_governed_compatibility_digest_mismatch',
        ),
        (
            'typed_execution_bundle_digest',
            _digest('e'),
            'typed_execution_governed_bundle_digest_mismatch',
        ),
        (
            'governance_request_digest',
            _digest('f'),
            'typed_execution_governed_governance_request_digest_mismatch',
        ),
        (
            'governance_decision_digest',
            _digest('a'),
            'typed_execution_governed_decision_digest_mismatch',
        ),
        (
            'approval_attestation_digest',
            _digest('b'),
            'typed_execution_governed_approval_attestation_digest_mismatch',
        ),
        (
            'execution_spec_digest',
            _digest('c'),
            'typed_execution_governed_execution_spec_digest_mismatch',
        ),
        (
            'execution_facts_digest',
            _digest('d'),
            'typed_execution_governed_execution_facts_digest_mismatch',
        ),
        (
            'payload_digest',
            _digest('e'),
            'typed_execution_governed_payload_digest_mismatch',
        ),
        (
            'requested_scope_digest',
            _digest('f'),
            'typed_execution_governed_requested_scope_digest_mismatch',
        ),
        (
            'capability_inventory_digest',
            _digest('a'),
            'typed_execution_governed_capability_inventory_digest_mismatch',
        ),
        (
            'inventory_epoch',
            43,
            'typed_execution_governed_inventory_epoch_mismatch',
        ),
        (
            'policy_pack_digest',
            _digest('b'),
            'typed_execution_governed_policy_pack_digest_mismatch',
        ),
        (
            'policy_epoch',
            43,
            'typed_execution_governed_policy_epoch_mismatch',
        ),
    ],
)
def test_every_projected_binding_drift_is_rejected(
    field_name: str,
    replacement_value: str | int,
    reason_code: str,
) -> None:
    typed_request = _typed_request()
    governance_request = _governance_request(
        typed_request,
        actual_operation_mode='apply',
    )
    admission, decision = _evaluate(
        typed_request,
        governance_request,
        actual_operation_mode='apply',
    )
    drifted = replace(
        admission,
        **{field_name: replacement_value, 'admission_digest': ''},
    )
    drifted = replace(
        drifted,
        admission_digest=_admission_body_digest(drifted),
    )

    with pytest.raises(GovApiError, match=reason_code):
        validate_typed_execution_governed_admission(
            drifted,
            typed_execution_request=typed_request,
            governance_request=governance_request,
            governance_decision=decision,
            validated_at=NOW,
        )


@pytest.mark.parametrize(
    'decision_approval_digest',
    ['', _digest('f')],
)
def test_decision_approval_digest_must_match_recomputed_request_attestation(
    decision_approval_digest: str,
) -> None:
    typed_request = _typed_request()
    governance_request = _governance_request(
        typed_request,
        actual_operation_mode='apply',
    )
    admission, decision = _evaluate(
        typed_request,
        governance_request,
        actual_operation_mode='apply',
    )
    drifted_decision = replace(
        decision,
        approval_attestation_digest=decision_approval_digest,
        decision_digest='',
    )
    drifted_decision = replace(
        drifted_decision,
        decision_digest=_governance_decision_body_digest(drifted_decision),
    )
    drifted_admission = replace(
        admission,
        governance_decision_digest=drifted_decision.decision_digest,
        admission_digest='',
    )
    drifted_admission = replace(
        drifted_admission,
        admission_digest=_admission_body_digest(drifted_admission),
    )

    with pytest.raises(
        GovApiError,
        match=(
            'typed_execution_governed_decision_'
            'approval_attestation_digest_mismatch'
        ),
    ):
        validate_typed_execution_governed_admission(
            drifted_admission,
            typed_execution_request=typed_request,
            governance_request=governance_request,
            governance_decision=drifted_decision,
            validated_at=NOW,
        )


def test_delayed_validation_before_decision_expiry_passes() -> None:
    typed_request = _typed_request()
    governance_request = _governance_request(
        typed_request,
        actual_operation_mode='apply',
    )
    admission, decision = _evaluate(
        typed_request,
        governance_request,
        actual_operation_mode='apply',
    )

    assert validate_typed_execution_governed_admission(
        admission,
        typed_execution_request=typed_request,
        governance_request=governance_request,
        governance_decision=decision,
        validated_at=NOW + timedelta(seconds=29),
    ) == admission


@pytest.mark.parametrize(
    ('admitted_at', 'reason_code'),
    [
        (
            NOW + timedelta(seconds=1),
            'typed_execution_governed_admitted_at_in_future',
        ),
        (
            NOW - timedelta(seconds=1),
            'typed_execution_governed_admission_precedes_authorization',
        ),
    ],
)
def test_invalid_admission_time_binding_fails_closed(
    admitted_at: datetime,
    reason_code: str,
) -> None:
    typed_request = _typed_request()
    governance_request = _governance_request(
        typed_request,
        actual_operation_mode='apply',
    )
    admission, decision = _evaluate(
        typed_request,
        governance_request,
        actual_operation_mode='apply',
    )
    drifted = replace(
        admission,
        admitted_at=admitted_at.isoformat(),
        admission_digest='',
    )
    drifted = replace(
        drifted,
        admission_digest=_admission_body_digest(drifted),
    )

    with pytest.raises(GovApiError, match=reason_code):
        validate_typed_execution_governed_admission(
            drifted,
            typed_execution_request=typed_request,
            governance_request=governance_request,
            governance_decision=decision,
            validated_at=NOW,
        )


def test_current_time_expired_decision_fails_closed() -> None:
    typed_request = _typed_request()
    governance_request = _governance_request(
        typed_request,
        actual_operation_mode='apply',
    )
    admission, decision = _evaluate(
        typed_request,
        governance_request,
        actual_operation_mode='apply',
    )

    with pytest.raises(
        GovApiError,
        match='typed_execution_governed_decision_expired',
    ):
        validate_typed_execution_governed_admission(
            admission,
            typed_execution_request=typed_request,
            governance_request=governance_request,
            governance_decision=decision,
            validated_at=NOW + timedelta(seconds=30),
        )


def test_facts_must_bind_actual_mode_and_full_typed_request_digest() -> None:
    typed_request = _typed_request()
    governance_request = _governance_request(
        typed_request,
        actual_operation_mode='recovery',
    )

    with pytest.raises(
        GovApiError,
        match='typed_execution_governed_actual_operation_mode_mismatch',
    ):
        _evaluate(
            typed_request,
            governance_request,
            actual_operation_mode='apply',
        )

    other_typed_request = _typed_request(action='different_action')
    with pytest.raises(
        GovApiError,
        match='typed_execution_governed_facts_request_digest_mismatch',
    ):
        _evaluate(
            other_typed_request,
            governance_request,
            actual_operation_mode='recovery',
        )

    drifted_capability = dict(typed_request['capability_descriptor'])
    drifted_capability['mode'] = 'dry_run'
    drifted_typed_request = _typed_request(
        capability_descriptor=drifted_capability,
        capability_descriptor_digest=runtime_capability_descriptor_digest(
            drifted_capability
        ),
    )
    drifted_governance_request = _governance_request(
        drifted_typed_request,
        actual_operation_mode='apply',
    )
    with pytest.raises(
        GovApiError,
        match='typed_execution_governed_capability_apply_alias_required',
    ):
        _evaluate(
            drifted_typed_request,
            drifted_governance_request,
            actual_operation_mode='apply',
        )


def test_unknown_composite_version_and_digest_tamper_fail_closed() -> None:
    typed_request = _typed_request()
    governance_request = _governance_request(
        typed_request,
        actual_operation_mode='apply',
    )
    admission, _decision = _evaluate(
        typed_request,
        governance_request,
        actual_operation_mode='apply',
    )
    unknown = admission.as_dict()
    unknown['schema_version'] = 'v9.0'
    with pytest.raises(
        GovApiError,
        match='unsupported_typed_execution_governed_admission_version',
    ):
        TypedExecutionGovernedAdmission.from_mapping(unknown)

    tampered = admission.as_dict()
    tampered['operation_id'] = 'op-other'
    with pytest.raises(
        GovApiError,
        match='typed_execution_governed_admission_digest_mismatch',
    ):
        TypedExecutionGovernedAdmission.from_mapping(tampered)


def test_frozen_v0_1_and_v1_digest_fixtures_remain_exact() -> None:
    read_capability = {
        'schema_version': 'v0.1',
        'backend_class': 'static_fixture',
        'identity_class': 'none',
        'egress_class': 'no_network',
        'read_only_backend': False,
        'live_backend_posture': 'fixture_only',
        'network_boundary': {'egress': 'no_network', 'host_declared': False},
        'secret_ref_requirements': [],
        'declared_capability_descriptors': ['connector.fixture.static'],
        'certification_tier': 'core',
        'mode': 'dry_run',
    }
    frozen_typed = {
        'schema_version': 'v0.1',
        'request_id': 'typed-exec-1',
        'operation_id': 'operation-1',
        'step_id': 'inspect_state',
        'operation_mode': 'dry_run',
        'step_execution_spec_digest': _digest('a'),
        'capability_descriptor_digest': runtime_capability_descriptor_digest(
            read_capability
        ),
        'payload_schema': 'rexecop.static_fixture_execution_spec.v0.1',
        'payload_digest': _digest('c'),
        'backend_class': 'static_fixture',
        'connector': 'fixture_source',
        'action': 'read_fixture_state',
        'read_only': True,
        'side_effect_class': 'read_only',
        'capability_descriptor': read_capability,
        'evidence_requirements': {
            'receipt_required': True,
            'output_digest_required': False,
        },
        'allowed_network_egress': ['no_network'],
        'required_capability_descriptors': ['connector.fixture.static'],
    }
    assert typed_execution_governance_request_digest(frozen_typed) == (
        'sha256:11dc005f86b246b9dac21293e1b3a21a4934dddb04faf28d'
        '7635a007440cfb76'
    )
    assert project_typed_execution_governance(frozen_typed).projection_digest == (
        'sha256:39b165f9d7fe11dd251ab50abc327a4cd291d4ab4f55e85a'
        '89cd27fc4520241e'
    )

    baseline = _baseline_frozen_governance_request()
    assert governance_request_digest(baseline) == (
        'sha256:37729d0aa80b656be7cb7ad57347347eb2cfe0944363c73b2'
        '36fb73125f34459'
    )
    assert approval_attestation_digest(
        baseline['approval_attestation']
    ) == (
        'sha256:a639999c788c0ff40ee768f9cdb0362e53a32f57bb30f3d60'
        '881d0aa37e69e9a'
    )
    decision = evaluate_governance(
        baseline,
        policy_activation_port=_PolicyActivation(baseline),
        evaluated_at=NOW,
        approval_trust_policy=_trust_policy(),
        approval_revocation_port=_Revocations(),
        approval_signature_verifier=_SignatureVerifier(),
        authorization_nonce='nonce-123',
        authorization_expires_at=NOW + timedelta(seconds=30),
    )
    assert governance_decision_digest(decision) == (
        'sha256:cbcf8e9fa0b9cc3bb7b047098bf16811ad6cc7a6e6dd0f92'
        'e12bcc71b7eb1959'
    )


def _baseline_frozen_governance_request() -> dict[str, Any]:
    policy_pack = _compiled_policy()
    pack_digest = policy_pack_digest(policy_pack)
    execution_facts = {
        'schema_version': 'v0.1',
        'request_id': 'gov-tx-123',
        'subject_ref': 'governance:op-123:step-4:attempt-2',
        'principal': {'kind': 'operator'},
        'action': {'mode': 'mutation'},
        'resource': {'criticality': 'low'},
        'context': {'environment': 'production'},
        'evidence_refs': [],
        'metadata': {},
    }
    requested_scope = {
        'target_namespace': 'service.inventory',
        'environment': 'production',
        'requested_destination': {
            'scheme': 'https',
            'effective_port': 443,
            'address_class': 'public',
            'origin_binding_digest': _digest('4'),
        },
    }
    scope_policy = ScopePolicyBinding.from_mapping(
        {
            'schema_version': 'v1',
            'binding_id': 'scope-policy-1',
            'policy_pack_digest': pack_digest,
            'policy_epoch': 42,
            'source_ref': 'policy-pack:production-mutation@1',
            'attestation_ref': 'catalog-attestation:scope-42',
            'allowed_target_namespaces': ['service.inventory'],
            'network_allowed': True,
            'allowed_schemes': ['https'],
            'allowed_ports': [443],
            'allowed_address_classes': ['public'],
            'redirect_policy': 'same_origin',
            'private_networks_allowed': False,
        }
    )
    requirements = OperationCapabilityRequirements.from_mapping(
        {
            'schema_version': 'v1',
            'requirements_id': 'requirements-1',
            'operation_id': 'op-123',
            'step_id': 'step-4',
            'execution_spec_digest': _digest('1'),
            'required_backend_class': 'http_api',
            'side_effect_class': 'mutation',
            'required_capabilities': [
                'connector.inventory.update',
                'network.tls.required',
                'receipt.terminal',
            ],
        }
    )
    inventory = CapabilityInventoryBinding.from_mapping(
        {
            'schema_version': 'v1',
            'inventory_id': 'runtime-inventory-42',
            'runtime_instance_id': 'rexecop-1',
            'runtime_version': '0.3.0rc2',
            'inventory_epoch': 42,
            'source_ref': 'runtime-registry:rexecop-1',
            'attestation_ref': 'runtime-inventory-attestation:42',
            'backend_classes': ['http_api'],
            'side_effect_classes': ['mutation'],
            'capabilities': [
                'connector.inventory.update',
                'network.tls.required',
                'receipt.terminal',
            ],
        }
    )
    request: dict[str, Any] = {
        'schema_version': 'v1',
        'transaction_id': 'gov-tx-123',
        'operation_id': 'op-123',
        'step_id': 'step-4',
        'attempt_id': 'attempt-2',
        'policy_pack': policy_pack.as_dict(),
        'policy_pack_digest': pack_digest,
        'policy_epoch': 42,
        'execution_facts': execution_facts,
        'execution_facts_digest': execution_facts_digest(execution_facts),
        'execution_spec_digest': _digest('1'),
        'payload_digest': _digest('2'),
        'requested_scope': requested_scope,
        'requested_scope_digest': requested_scope_digest(requested_scope),
        'scope_policy_binding': scope_policy.as_dict(),
        'scope_policy_binding_digest': scope_policy_binding_digest(scope_policy),
        'capability_requirements': requirements.as_dict(),
        'capability_requirements_digest': (
            operation_capability_requirements_digest(requirements)
        ),
        'capability_inventory': inventory.as_dict(),
        'capability_inventory_digest': capability_inventory_binding_digest(
            inventory
        ),
        'side_effect_class': 'mutation',
        'runtime_instance_id': 'rexecop-1',
        'lease_id': 'lease-55',
        'lease_epoch': 9,
        'fencing_token_digest': _digest('3'),
    }
    subject = GovernanceRequest.from_mapping(request)
    approval = ApprovalAttestation.from_mapping(
        {
            'schema_version': 'v1',
            'approval_id': 'approval-123',
            'subject_digest': governance_subject_digest(subject),
            'operation_id': 'op-123',
            'step_id': 'step-4',
            'attempt_id': 'attempt-2',
            'execution_spec_digest': request['execution_spec_digest'],
            'execution_facts_digest': request['execution_facts_digest'],
            'target_scope_digest': request['requested_scope_digest'],
            'policy_pack_digest': pack_digest,
            'policy_epoch': 42,
            'approved_side_effect_class': 'mutation',
            'approver_ref': 'operator:alice',
            'approver_role': 'infrastructure-admin',
            'trust_domain': 'organization:example',
            'issued_at': '2026-07-15T12:00:00Z',
            'not_before': '2026-07-15T12:00:00Z',
            'expires_at': '2026-07-15T12:15:00Z',
            'revocation_ref': 'approval-revocations:v1',
            'signature_ref': 'sigstore:bundle-123',
        }
    )
    request['approval_attestation'] = approval.as_dict()
    request['approval_attestation_digest'] = approval_attestation_digest(
        approval
    )
    return request
