from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
from typing import Any

import pytest

import govengine
import govengine.v1 as govengine_v1
from govengine.api import GovApiError
from govengine.approvals import ApprovalAttestation, approval_attestation_digest
from govengine.capabilities import (
    CapabilityInventoryBinding,
    OperationCapabilityRequirements,
    capability_inventory_binding_digest,
    operation_capability_requirements_digest,
)
from govengine.governance import GovernanceRequest, governance_subject_digest
from govengine.policy import PolicyCompiler, policy_pack_digest
from govengine.scope_policy import ScopePolicyBinding, scope_policy_binding_digest
from govengine.typed_execution_governance import (
    runtime_capability_descriptor_digest,
)
from govengine.typed_execution_governed_admission import (
    TYPED_EXECUTION_GOVERNED_ADMISSION_SCHEMA_VERSION,
    TYPED_EXECUTION_GOVERNED_ADMISSION_V02_SCHEMA_VERSION,
    TypedExecutionGovernedAdmissionV02,
    _admission_v02_body_digest,
    evaluate_typed_execution_governed_admission,
    evaluate_typed_execution_governed_admission_v02,
    typed_execution_governed_admission_v02_digest,
    validate_typed_execution_governed_admission_v02,
)
from tests import test_typed_execution_governed_admission as v01


BACKEND = 'tecrax_chrony_ntp'
CAPABILITY = 'connector.tecrax.chrony'


def _plugin_typed_request(
    *,
    approval_evidence_ref: str = '',
    egress: str = 'no_network',
    identity: str = 'plugin_declared',
    backend: str = BACKEND,
    certification_tier: str = 'plugin',
    declared_capabilities: tuple[str, ...] = (CAPABILITY,),
    required_capabilities: tuple[str, ...] = (CAPABILITY,),
    secret_ref_requirements: tuple[dict[str, Any], ...] = (),
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    request = v01._typed_request(
        approval_evidence_ref=approval_evidence_ref,
        required_capabilities=required_capabilities,
    )
    descriptor = deepcopy(request['capability_descriptor'])
    descriptor.update(
        {
            'backend_class': backend,
            'identity_class': identity,
            'egress_class': egress,
            'network_boundary': {
                'egress': egress,
                'host_declared': False,
            },
            'secret_ref_requirements': list(secret_ref_requirements),
            'declared_capability_descriptors': list(declared_capabilities),
            'certification_tier': certification_tier,
        }
    )
    request.update(
        {
            'backend_class': backend,
            'connector': backend,
            'capability_descriptor': descriptor,
            'capability_descriptor_digest': runtime_capability_descriptor_digest(
                descriptor
            ),
            'allowed_network_egress': [egress],
            'required_capability_descriptors': list(required_capabilities),
            'metadata': dict(metadata or {}),
        }
    )
    return request


def _plugin_policy(
    *,
    backend_controls: tuple[str, ...] | None = (BACKEND,),
    egress_controls: tuple[str, ...] | None = ('no_network',),
):
    constraints: list[dict[str, Any]] = [
        {
            'constraint_id': 'bounded-output',
            'kind': 'output_limit',
            'value': 4096,
        }
    ]
    if backend_controls is not None:
        constraints.append(
            {
                'constraint_id': 'plugin-backend',
                'kind': 'allowed_backend_classes',
                'value': list(backend_controls),
            }
        )
    if egress_controls is not None:
        constraints.append(
            {
                'constraint_id': 'plugin-egress',
                'kind': 'allowed_network_egress',
                'value': list(egress_controls),
            }
        )
    result = PolicyCompiler().compile(
        {
            'policy_id': 'production-plugin-mutation',
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
                    'rule_id': 'govern-plugin-mutation',
                    'effect': 'approval_required',
                    'conditions': [
                        {
                            'path': 'action.mode',
                            'operator': 'eq',
                            'value': 'mutation',
                        }
                    ],
                    'reason_code': 'mutation_requires_approval',
                    'obligations': [
                        {'obligation_id': 'receipt', 'kind': 'receipt'}
                    ],
                    'constraints': constraints,
                }
            ],
        }
    )
    assert result.ok
    assert result.policy_pack is not None
    return result.policy_pack


def _plugin_governance_request(
    typed_request: dict[str, Any],
    *,
    actual_operation_mode: str = 'apply',
    backend_controls: tuple[str, ...] | None = None,
    egress_controls: tuple[str, ...] | None = None,
    requirements_backend: str | None = None,
    requirements_capabilities: tuple[str, ...] | None = None,
    inventory_backends: tuple[str, ...] | None = None,
    inventory_capabilities: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    backend = typed_request['backend_class']
    egress = typed_request['capability_descriptor']['egress_class']
    required = tuple(typed_request['required_capability_descriptors'])
    request = v01._governance_request(
        typed_request,
        actual_operation_mode=actual_operation_mode,
        with_approval=False,
    )
    policy_pack = _plugin_policy(
        backend_controls=(backend,) if backend_controls is None else backend_controls,
        egress_controls=(egress,) if egress_controls is None else egress_controls,
    )
    pack_digest = policy_pack_digest(policy_pack)
    request['policy_pack'] = policy_pack.as_dict()
    request['policy_pack_digest'] = pack_digest

    scope_policy_payload = dict(request['scope_policy_binding'])
    scope_policy_payload['policy_pack_digest'] = pack_digest
    scope_policy = ScopePolicyBinding.from_mapping(scope_policy_payload)
    request['scope_policy_binding'] = scope_policy.as_dict()
    request['scope_policy_binding_digest'] = scope_policy_binding_digest(scope_policy)

    requirements = OperationCapabilityRequirements.from_mapping(
        {
            'schema_version': 'v1',
            'requirements_id': 'plugin-requirements-1',
            'operation_id': request['operation_id'],
            'step_id': request['step_id'],
            'execution_spec_digest': request['execution_spec_digest'],
            'required_backend_class': requirements_backend or backend,
            'side_effect_class': 'mutation',
            'required_capabilities': list(requirements_capabilities or required),
        }
    )
    request['capability_requirements'] = requirements.as_dict()
    request['capability_requirements_digest'] = (
        operation_capability_requirements_digest(requirements)
    )

    inventory = CapabilityInventoryBinding.from_mapping(
        {
            'schema_version': 'v1',
            'inventory_id': 'plugin-runtime-inventory-42',
            'runtime_instance_id': request['runtime_instance_id'],
            'runtime_version': '1.0.0rc1',
            'inventory_epoch': 42,
            'source_ref': 'runtime-registry:rexecop-1',
            'attestation_ref': 'runtime-inventory-attestation:plugin-42',
            'backend_classes': list(inventory_backends or (backend,)),
            'side_effect_classes': ['mutation'],
            'capabilities': list(inventory_capabilities or required),
        }
    )
    request['capability_inventory'] = inventory.as_dict()
    request['capability_inventory_digest'] = capability_inventory_binding_digest(
        inventory
    )

    subject = GovernanceRequest.from_mapping(request)
    approval = ApprovalAttestation.from_mapping(
        {
            'schema_version': 'v1',
            'approval_id': 'approval-plugin-123',
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
            'signature_ref': 'sigstore:bundle-plugin-123',
        }
    )
    request['approval_attestation'] = approval.as_dict()
    request['approval_attestation_digest'] = approval_attestation_digest(approval)
    return request


def _evaluate(
    typed_request: dict[str, Any],
    governance_request: dict[str, Any],
    *,
    actual_operation_mode: str = 'apply',
):
    return evaluate_typed_execution_governed_admission_v02(
        typed_request,
        governance_request,
        actual_operation_mode=actual_operation_mode,
        policy_activation_port=v01._PolicyActivation(governance_request),
        evaluated_at=v01.NOW,
        admitted_at=v01.NOW,
        approval_trust_policy=v01._trust_policy(),
        approval_revocation_port=v01._Revocations(),
        approval_signature_verifier=v01._SignatureVerifier(),
        authorization_nonce='plugin-nonce-123',
        authorization_expires_at=v01.NOW + timedelta(seconds=30),
    )


@pytest.mark.parametrize(
    (
        'egress',
        'identity',
        'actual_operation_mode',
        'approval_evidence_ref',
        'approval_blocker',
    ),
    [
        (
            'no_network',
            'plugin_declared',
            'apply',
            '',
            'mutation_requires_approval_evidence',
        ),
        (
            'local_subprocess',
            'plugin_declared',
            'recovery',
            v01._digest('a'),
            'mutation_requires_approval_attestation',
        ),
        (
            'no_network',
            'none',
            'apply',
            '',
            'mutation_requires_approval_evidence',
        ),
    ],
)
def test_v02_allows_only_exact_policy_bound_plugin_posture(
    egress: str,
    identity: str,
    actual_operation_mode: str,
    approval_evidence_ref: str,
    approval_blocker: str,
) -> None:
    typed = _plugin_typed_request(
        approval_evidence_ref=approval_evidence_ref,
        egress=egress,
        identity=identity,
    )
    governance = _plugin_governance_request(
        typed,
        actual_operation_mode=actual_operation_mode,
    )

    admission, decision = _evaluate(
        typed,
        governance,
        actual_operation_mode=actual_operation_mode,
    )

    assert admission.allowed is True
    assert admission.schema_version == 'v0.2'
    assert admission.plugin_backend_class == BACKEND
    assert admission.plugin_egress_class == egress
    assert admission.plugin_identity_class == identity
    assert admission.declared_capability_descriptors == (CAPABILITY,)
    assert set(admission.discounted_typed_execution_blockers) == {
        'unsupported_backend_class',
        approval_blocker,
    }
    assert decision.allowed is True
    assert decision.controls.allowed_backend_classes == (BACKEND,)
    assert decision.controls.allowed_network_egress == (egress,)
    assert admission.governance_decision_digest == decision.decision_digest
    assert typed_execution_governed_admission_v02_digest(admission) == (
        admission.admission_digest
    )
    assert TypedExecutionGovernedAdmissionV02.from_mapping(
        admission.as_dict()
    ) == admission
    assert validate_typed_execution_governed_admission_v02(
        admission.as_dict(),
        typed_execution_request=typed,
        governance_request=governance,
        governance_decision=decision,
        validated_at=v01.NOW,
    ) == admission


def test_request_metadata_never_substitutes_for_signed_policy_controls() -> None:
    typed = _plugin_typed_request(
        metadata={
            'allowed_backend_classes': [BACKEND],
            'allowed_network_egress': ['no_network'],
        }
    )
    governance = _plugin_governance_request(
        typed,
        backend_controls=('request_claimed_only',),
        egress_controls=('outbound_http',),
    )

    admission, decision = _evaluate(typed, governance)

    assert decision.allowed is True
    assert decision.controls.allowed_backend_classes == ('request_claimed_only',)
    assert decision.controls.allowed_network_egress == ('outbound_http',)
    assert admission.allowed is False
    assert admission.blockers == (
        'plugin_backend_policy_control_mismatch',
        'plugin_egress_policy_control_mismatch',
    )


@pytest.mark.parametrize(
    ('backend_controls', 'egress_controls', 'expected'),
    [
        (
            (BACKEND, 'unrelated_plugin'),
            ('no_network',),
            'plugin_backend_policy_control_mismatch',
        ),
        (
            (BACKEND,),
            ('local_subprocess', 'no_network'),
            'plugin_egress_policy_control_mismatch',
        ),
    ],
)
def test_policy_control_membership_is_not_singleton_equality(
    backend_controls: tuple[str, ...],
    egress_controls: tuple[str, ...],
    expected: str,
) -> None:
    typed = _plugin_typed_request()
    governance = _plugin_governance_request(
        typed,
        backend_controls=backend_controls,
        egress_controls=egress_controls,
    )

    admission, decision = _evaluate(typed, governance)

    assert decision.allowed is True
    assert admission.allowed is False
    assert expected in admission.blockers


@pytest.mark.parametrize(
    ('typed_kwargs', 'reason'),
    [
        ({'backend': 'static_fixture'}, 'builtin_backend_forbidden'),
        ({'backend': 'raw_shell'}, 'raw_shell_backend_forbidden'),
        ({'certification_tier': 'core'}, 'plugin_tier_required'),
        ({'identity': 'api_token_optional'}, 'plugin_identity_required'),
        ({'declared_capabilities': ()}, 'plugin_capabilities_required'),
        (
            {
                'secret_ref_requirements': (
                    {'path': 'secret://chrony', 'required': False, 'present': False},
                )
            },
            'secret_requirements_forbidden',
        ),
        ({'egress': 'plugin_undeclared'}, 'plugin_egress_forbidden'),
        ({'egress': 'outbound_http'}, 'plugin_egress_forbidden'),
    ],
)
def test_non_plugin_or_undeclared_posture_fails_before_governance(
    typed_kwargs: dict[str, Any],
    reason: str,
) -> None:
    typed = _plugin_typed_request(**typed_kwargs)
    governance = _plugin_governance_request(typed)

    with pytest.raises(GovApiError, match=reason):
        _evaluate(typed, governance)


def test_every_non_discountable_v01_blocker_remains_fatal() -> None:
    typed = _plugin_typed_request(
        metadata={'require_destination_binding': True}
    )
    governance = _plugin_governance_request(typed)

    with pytest.raises(
        GovApiError,
        match='typed_execution_governed_v02_precheck_blocked',
    ) as caught:
        _evaluate(typed, governance)

    assert caught.value.context == {
        'blockers': ['network_destination_binding_match']
    }


@pytest.mark.parametrize(
    ('governance_kwargs', 'reason'),
    [
        (
            {'requirements_backend': 'other_plugin'},
            'requirements_backend_mismatch',
        ),
        (
            {'requirements_capabilities': ('connector.other',)},
            'required_capabilities_mismatch',
        ),
        (
            {'inventory_backends': ('other_plugin',)},
            'inventory_backend_mismatch',
        ),
        (
            {'inventory_capabilities': ('connector.other',)},
            'inventory_capabilities_mismatch',
        ),
    ],
)
def test_frozen_v1_requirements_and_attested_inventory_must_agree_exactly(
    governance_kwargs: dict[str, Any],
    reason: str,
) -> None:
    typed = _plugin_typed_request()
    governance = _plugin_governance_request(typed, **governance_kwargs)

    with pytest.raises(GovApiError, match=reason):
        _evaluate(typed, governance)


def test_v02_digest_and_owner_bindings_reject_tamper() -> None:
    typed = _plugin_typed_request()
    governance = _plugin_governance_request(typed)
    admission, decision = _evaluate(typed, governance)
    payload = admission.as_dict()
    payload['governance_decision_digest'] = v01._digest('f')

    with pytest.raises(
        GovApiError,
        match='typed_execution_governed_admission_v02_digest_mismatch',
    ):
        TypedExecutionGovernedAdmissionV02.from_mapping(payload)

    rebound = replace(
        admission,
        declared_capability_descriptors=('connector.other',),
    )
    rebound = replace(rebound, admission_digest=_admission_v02_body_digest(rebound))
    with pytest.raises(GovApiError, match='declared_capabilities_mismatch'):
        validate_typed_execution_governed_admission_v02(
            rebound,
            typed_execution_request=typed,
            governance_request=governance,
            governance_decision=decision,
            validated_at=v01.NOW,
        )


def test_v01_and_frozen_public_facades_remain_unchanged() -> None:
    typed = _plugin_typed_request()
    governance = _plugin_governance_request(typed)

    assert TYPED_EXECUTION_GOVERNED_ADMISSION_SCHEMA_VERSION == 'v0.1'
    assert TYPED_EXECUTION_GOVERNED_ADMISSION_V02_SCHEMA_VERSION == 'v0.2'
    assert 'TypedExecutionGovernedAdmissionV02' not in govengine.__all__
    assert not hasattr(govengine, 'TypedExecutionGovernedAdmissionV02')
    assert not hasattr(govengine_v1, 'TypedExecutionGovernedAdmissionV02')
    with pytest.raises(
        GovApiError,
        match='typed_execution_governed_precheck_blocked',
    ):
        evaluate_typed_execution_governed_admission(
            typed,
            governance,
            actual_operation_mode='apply',
            policy_activation_port=v01._PolicyActivation(governance),
            evaluated_at=v01.NOW,
            admitted_at=v01.NOW,
            approval_trust_policy=v01._trust_policy(),
            approval_revocation_port=v01._Revocations(),
            approval_signature_verifier=v01._SignatureVerifier(),
            authorization_nonce='v01-plugin-nonce',
            authorization_expires_at=v01.NOW + timedelta(seconds=30),
        )
