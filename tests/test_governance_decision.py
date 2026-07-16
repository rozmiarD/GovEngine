from __future__ import annotations

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
    governance_subject_digest,
    requested_scope_digest,
)
from govengine.governance_decision import (
    ApprovalSignatureVerificationPort,
    DecisionClaimPort,
    GovernanceDecision,
    PolicyActivationPort,
    evaluate_governance,
    governance_decision_digest,
)
from govengine.governance_decision_signing import (
    SIGNED_GOVERNANCE_DECISION_PURPOSE,
    require_trusted_governance_decision,
    sign_governance_decision,
)
from govengine.policy import PolicyCompiler, policy_pack_digest
from govengine.policy.activation import PolicyActivationBinding
from govengine.scope_policy import ScopePolicyBinding, scope_policy_binding_digest
from govengine.signing import (
    DemoDigestSigner,
    DemoDigestVerifier,
    SigningPolicy,
    TrustPolicy,
)


NOW = datetime(2026, 7, 15, 12, 5, tzinfo=timezone.utc)


class _PolicyActivation(PolicyActivationPort):
    def __init__(
        self,
        request: dict[str, Any],
        *,
        epoch: int | None = None,
        status: str = 'active',
        not_before: str = '2026-07-15T12:00:00Z',
        expires_at: str = '2026-07-15T13:00:00Z',
    ) -> None:
        self.request = request
        self.epoch = request['policy_epoch'] if epoch is None else epoch
        self.status = status
        self.not_before = not_before
        self.expires_at = expires_at

    def current_binding(self, policy_id: str) -> PolicyActivationBinding:
        assert policy_id == 'production-mutation'
        compiled = PolicyCompiler().compile(self.request['policy_pack'])
        assert compiled.policy_pack is not None
        pack = compiled.policy_pack
        issuer_ref = (
            pack.issuer_ref
            if pack.schema_version == 'v1'
            else 'issuer:legacy-policy'
        )
        return PolicyActivationBinding.from_mapping(
            {
                'schema_version': 'v1',
                'binding_id': 'policy-activation:production-mutation',
                'policy_id': policy_id,
                'policy_version': pack.version,
                'policy_pack_digest': self.request['policy_pack_digest'],
                'policy_epoch': self.epoch,
                'issuer_ref': issuer_ref,
                'trust_ref': 'policy-trust:production',
                'status': self.status,
                'not_before': self.not_before,
                'expires_at': self.expires_at,
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
        self.calls: list[tuple[str, str, str]] = []

    def verify_approval_signature(
        self,
        attestation: ApprovalAttestation,
        *,
        approval_digest: str,
        trust_policy_id: str,
    ) -> bool:
        self.calls.append(
            (attestation.approval_id, approval_digest, trust_policy_id)
        )
        return self.valid


class _DecisionClaims:
    def claim_governance_decision_once(
        self,
        *,
        decision_digest: str,
        nonce: str,
        attempt_id: str,
        runtime_instance_id: str,
    ) -> bool:
        return bool(decision_digest and nonce and attempt_id and runtime_instance_id)


def test_decision_claim_port_is_structural_and_storage_neutral() -> None:
    assert isinstance(_DecisionClaims(), DecisionClaimPort)
    assert not isinstance(object(), DecisionClaimPort)


def _trust_policy() -> ApprovalTrustPolicy:
    return ApprovalTrustPolicy(
        policy_id='production-approvers',
        trusted_roles=('infrastructure-admin',),
        trusted_domains=('organization:example',),
        trusted_approver_refs=('operator:alice',),
        require_signature_ref=True,
    )


def _compiled_policy(*, effect: str = 'approval_required'):
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


def _request_mapping(
    *,
    with_approval: bool,
    policy_effect: str = 'approval_required',
    scope_namespace: str = 'service.inventory',
    inventory_capabilities: tuple[str, ...] = (
        'connector.inventory.update',
        'network.tls.required',
        'receipt.terminal',
    ),
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
        'metadata': {},
    }
    requested_scope = {
        'target_namespace': scope_namespace,
        'environment': 'production',
        'requested_destination': {
            'scheme': 'https',
            'effective_port': 443,
            'address_class': 'public',
            'origin_binding_digest': 'sha256:' + '4' * 64,
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
            'execution_spec_digest': 'sha256:' + '1' * 64,
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
            'capabilities': list(inventory_capabilities),
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
        'execution_spec_digest': 'sha256:' + '1' * 64,
        'payload_digest': 'sha256:' + '2' * 64,
        'requested_scope': requested_scope,
        'requested_scope_digest': requested_scope_digest(requested_scope),
        'scope_policy_binding': scope_policy.as_dict(),
        'scope_policy_binding_digest': scope_policy_binding_digest(scope_policy),
        'capability_requirements': requirements.as_dict(),
        'capability_requirements_digest': operation_capability_requirements_digest(
            requirements
        ),
        'capability_inventory': inventory.as_dict(),
        'capability_inventory_digest': capability_inventory_binding_digest(
            inventory
        ),
        'side_effect_class': 'mutation',
        'runtime_instance_id': 'rexecop-1',
        'lease_id': 'lease-55',
        'lease_epoch': 9,
        'fencing_token_digest': 'sha256:' + '3' * 64,
    }
    if with_approval:
        subject = GovernanceRequest.from_mapping(request)
        attestation = ApprovalAttestation.from_mapping(
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
        request['approval_attestation'] = attestation.as_dict()
        request['approval_attestation_digest'] = approval_attestation_digest(
            attestation
        )
    return request


def _evaluate(request: dict[str, Any], **overrides: Any) -> GovernanceDecision:
    arguments: dict[str, Any] = {
        'policy_activation_port': _PolicyActivation(request),
        'evaluated_at': NOW,
        'approval_trust_policy': _trust_policy(),
        'approval_revocation_port': _Revocations(),
        'approval_signature_verifier': _SignatureVerifier(),
        'authorization_nonce': 'nonce-123',
        'authorization_expires_at': NOW + timedelta(seconds=30),
    }
    arguments.update(overrides)
    return evaluate_governance(request, **arguments)


def test_governance_decision_allows_only_after_all_gates_pass() -> None:
    verifier = _SignatureVerifier()
    decision = _evaluate(
        _request_mapping(with_approval=True),
        approval_signature_verifier=verifier,
    )

    assert decision.allowed is True
    assert decision.status == 'allowed'
    assert decision.reason_code == 'all_governance_gates_passed'
    assert decision.policy_evaluation_digest != decision.policy_verdict_digest
    assert decision.approval_attestation_digest.startswith('sha256:')
    assert decision.required_controls == (
        'bounded-output',
        'receipt',
        'receipt_required',
    )
    assert decision.controls.max_output_bytes == 4096
    assert decision.authorization is not None
    assert decision.authorization.attempt_id == 'attempt-2'
    assert decision.authorization.lease_id == 'lease-55'
    assert decision.authorization.lease_epoch == 9
    assert decision.authorization.runtime_instance_id == 'rexecop-1'
    assert decision.authorization.inventory_epoch == 42
    assert decision.authorization.consume_once is True
    assert governance_decision_digest(decision) == decision.decision_digest
    assert verifier.calls == [
        (
            'approval-123',
            decision.approval_attestation_digest,
            'production-approvers',
        )
    ]

    from govengine import v1

    assert v1.GovernanceDecision is GovernanceDecision
    assert v1.evaluate_governance is evaluate_governance


def test_governance_decision_is_byte_stable_for_identical_inputs() -> None:
    request = _request_mapping(with_approval=True)

    first = _evaluate(request)
    second = _evaluate(request)

    assert first.as_dict() == second.as_dict()
    assert first.decision_digest == second.decision_digest
    assert GovernanceDecision.from_mapping(first.as_dict()) == first


def test_governance_decision_json_rejects_digest_or_authorization_drift() -> None:
    decision = _evaluate(_request_mapping(with_approval=True))
    drifted = {
        **decision.as_dict(),
        'request_digest': 'sha256:' + 'f' * 64,
    }

    with pytest.raises(GovApiError, match='governance_decision_digest_mismatch'):
        GovernanceDecision.from_mapping(drifted)

    authorization = dict(decision.as_dict()['authorization'])
    authorization['consume_once'] = False
    with pytest.raises(GovApiError, match='authorization_must_be_consume_once'):
        GovernanceDecision.from_mapping(
            {**decision.as_dict(), 'authorization': authorization}
        )


def test_missing_approval_never_produces_authorization() -> None:
    decision = _evaluate(_request_mapping(with_approval=False))

    assert decision.status == 'approval_required'
    assert decision.reason_code == 'approval_attestation_required'
    assert decision.authorization is None
    assert 'approval_attestation_required' in decision.blockers


@pytest.mark.parametrize(
    'governance_request',
    [
        _request_mapping(
            with_approval=True,
            scope_namespace='service.billing',
        ),
        _request_mapping(
            with_approval=True,
            inventory_capabilities=(
                'network.tls.required',
                'receipt.terminal',
            ),
        ),
        _request_mapping(with_approval=True, policy_effect='deny'),
    ],
)
def test_denied_gate_never_produces_authorization(
    governance_request: dict[str, Any],
) -> None:
    decision = _evaluate(governance_request)

    assert decision.status == 'denied'
    assert decision.authorization is None
    assert decision.blockers


def test_policy_epoch_drift_fails_closed() -> None:
    request = _request_mapping(with_approval=True)
    with pytest.raises(GovApiError, match='policy_epoch_drift'):
        _evaluate(
            request,
            policy_activation_port=_PolicyActivation(request, epoch=43),
        )


@pytest.mark.parametrize(
    ('status', 'reason_code'),
    [
        ('superseded', 'policy_superseded'),
        ('revoked', 'policy_revoked'),
        ('expired', 'policy_expired'),
    ],
)
def test_inactive_policy_binding_fails_closed(
    status: str,
    reason_code: str,
) -> None:
    request = _request_mapping(with_approval=True)
    with pytest.raises(GovApiError, match=reason_code):
        _evaluate(
            request,
            policy_activation_port=_PolicyActivation(request, status=status),
        )


def test_policy_binding_validity_window_fails_closed() -> None:
    request = _request_mapping(with_approval=True)
    with pytest.raises(GovApiError, match='policy_not_yet_valid'):
        _evaluate(
            request,
            policy_activation_port=_PolicyActivation(
                request,
                not_before='2026-07-15T12:06:00Z',
            ),
        )
    with pytest.raises(GovApiError, match='policy_expired'):
        _evaluate(
            request,
            policy_activation_port=_PolicyActivation(
                request,
                expires_at='2026-07-15T12:05:00Z',
            ),
        )


def test_approval_signature_mismatch_fails_closed() -> None:
    with pytest.raises(GovApiError, match='approval_signature_verification_failed'):
        _evaluate(
            _request_mapping(with_approval=True),
            approval_signature_verifier=_SignatureVerifier(valid=False),
        )


def test_authorization_is_short_lived() -> None:
    with pytest.raises(GovApiError, match='authorization_lifetime_exceeded'):
        _evaluate(
            _request_mapping(with_approval=True),
            authorization_expires_at=NOW + timedelta(seconds=61),
        )


def test_policy_request_is_bound_to_transaction_and_attempt() -> None:
    request = _request_mapping(with_approval=False)
    execution_facts = {**request['execution_facts'], 'request_id': 'other'}
    request['execution_facts'] = execution_facts
    request['execution_facts_digest'] = execution_facts_digest(execution_facts)

    with pytest.raises(GovApiError, match='policy_request_id_mismatch'):
        _evaluate(request)


def _decision_signing_policy() -> SigningPolicy:
    return SigningPolicy(
        require_signature=True,
        allowed_modes=('detached_demo_digest',),
        required_signer_ids=('decision-signer',),
    )


def test_signed_governance_decision_requires_trusted_issuer() -> None:
    decision = _evaluate(_request_mapping(with_approval=True))
    artifact = sign_governance_decision(
        decision,
        signer=DemoDigestSigner(signer_id='decision-signer'),
        payload_ref='artifact://governance/decision-123',
    )

    checked = require_trusted_governance_decision(
        decision,
        artifact,
        verifier=DemoDigestVerifier(
            verifier_id='decision-verifier',
            allowed_signer_ids=('decision-signer',),
        ),
        signing_policy=_decision_signing_policy(),
        trust_policy=TrustPolicy(),
    )

    assert checked == decision
    assert artifact.metadata['decision_digest'] == decision.decision_digest
    assert artifact.metadata['purpose'] == SIGNED_GOVERNANCE_DECISION_PURPOSE


def test_signed_governance_decision_rejects_another_valid_decision() -> None:
    allowed = _evaluate(_request_mapping(with_approval=True))
    denied = _evaluate(
        _request_mapping(with_approval=True, policy_effect='deny')
    )
    artifact = sign_governance_decision(
        allowed,
        signer=DemoDigestSigner(signer_id='decision-signer'),
        payload_ref='artifact://governance/decision-allowed',
    )

    with pytest.raises(
        GovApiError,
        match='governance_decision_signature_decision_digest_mismatch',
    ):
        require_trusted_governance_decision(
            denied,
            artifact,
            verifier=DemoDigestVerifier(
                allowed_signer_ids=('decision-signer',)
            ),
            signing_policy=_decision_signing_policy(),
            trust_policy=TrustPolicy(),
        )


def test_signed_governance_decision_rejects_untrusted_signer() -> None:
    decision = _evaluate(_request_mapping(with_approval=True))
    artifact = sign_governance_decision(
        decision,
        signer=DemoDigestSigner(signer_id='untrusted-signer'),
        payload_ref='artifact://governance/decision-untrusted',
    )

    with pytest.raises(GovApiError, match='governance_decision_signer_not_allowed'):
        require_trusted_governance_decision(
            decision,
            artifact,
            verifier=DemoDigestVerifier(
                allowed_signer_ids=('untrusted-signer',)
            ),
            signing_policy=_decision_signing_policy(),
            trust_policy=TrustPolicy(),
        )


def test_signed_governance_decision_rejects_untrusted_verification() -> None:
    decision = _evaluate(_request_mapping(with_approval=True))
    artifact = sign_governance_decision(
        decision,
        signer=DemoDigestSigner(signer_id='decision-signer'),
        payload_ref='artifact://governance/decision-untrusted-verifier',
    )

    with pytest.raises(
        GovApiError,
        match='governance_decision_signature_verification_failed',
    ):
        require_trusted_governance_decision(
            decision,
            artifact,
            verifier=DemoDigestVerifier(
                allowed_signer_ids=('another-signer',)
            ),
            signing_policy=_decision_signing_policy(),
            trust_policy=TrustPolicy(),
        )
