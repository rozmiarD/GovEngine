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
    validate_governance_request,
)
from govengine.policy import CompiledPolicyPack, PolicyCompiler, policy_pack_digest
from govengine.scope_policy import ScopePolicyBinding, scope_policy_binding_digest
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


def _compiled_v1_policy() -> CompiledPolicyPack:
    result = PolicyCompiler().compile(
        {
            'schema_version': 'v1',
            'policy_id': 'typed-policy',
            'version': '1.0.0',
            'issuer_ref': 'organization:example',
            'policy_epoch': 42,
            'validity': {
                'not_before': '2026-07-15T00:00:00Z',
                'expires_at': '2026-08-15T00:00:00Z',
            },
            'supersedes': [],
            'rules': [
                {
                    'rule_id': 'typed-approval',
                    'effect': 'approval_required',
                    'conditions': [
                        {
                            'path': 'action.mode',
                            'operator': 'eq',
                            'value': 'mutation',
                        }
                    ],
                }
            ],
            'metadata': {'owner': 'governance'},
        }
    )
    assert result.ok
    assert result.policy_pack is not None
    return result.policy_pack


def _base_request_mapping() -> dict[str, Any]:
    policy_pack = _compiled_policy()
    compiled_policy_digest = policy_pack_digest(policy_pack)
    execution_facts = {
        'backend_class': 'http_api',
        'connector': 'connector.inventory',
        'action': 'update',
    }
    requested_scope = {
        'target_namespace': 'service.inventory',
        'environment': 'production',
        'requested_destination': {
            'scheme': 'https',
            'effective_port': 443,
            'address_class': 'public',
            'origin_binding_digest': 'sha256:' + '4' * 64,
        },
    }
    scope_policy_binding = ScopePolicyBinding.from_mapping(
        {
            'schema_version': 'v1',
            'binding_id': 'scope-policy-1',
            'policy_pack_digest': compiled_policy_digest,
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
    capability_requirements = OperationCapabilityRequirements.from_mapping(
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
    capability_inventory = CapabilityInventoryBinding.from_mapping(
        {
            'schema_version': 'v1',
            'inventory_id': 'runtime-inventory-42',
            'runtime_instance_id': 'rexecop-1',
            'runtime_version': '0.3.0rc2',
            'inventory_epoch': 42,
            'source_ref': 'runtime-registry:rexecop-1',
            'attestation_ref': 'runtime-inventory-attestation:42',
            'backend_classes': ['http_api'],
            'side_effect_classes': ['read_only', 'mutation'],
            'capabilities': [
                'connector.inventory.update',
                'network.tls.required',
                'receipt.terminal',
            ],
        }
    )
    return {
        'schema_version': 'v1',
        'transaction_id': 'gov-tx-123',
        'operation_id': 'op-123',
        'step_id': 'step-4',
        'attempt_id': 'attempt-2',
        'policy_pack': policy_pack.as_dict(),
        'policy_pack_digest': compiled_policy_digest,
        'policy_epoch': 42,
        'execution_facts': execution_facts,
        'execution_facts_digest': execution_facts_digest(execution_facts),
        'execution_spec_digest': 'sha256:' + '1' * 64,
        'payload_digest': 'sha256:' + '2' * 64,
        'requested_scope': requested_scope,
        'requested_scope_digest': requested_scope_digest(requested_scope),
        'scope_policy_binding': scope_policy_binding.as_dict(),
        'scope_policy_binding_digest': scope_policy_binding_digest(
            scope_policy_binding
        ),
        'capability_requirements': capability_requirements.as_dict(),
        'capability_requirements_digest': operation_capability_requirements_digest(
            capability_requirements
        ),
        'capability_inventory': capability_inventory.as_dict(),
        'capability_inventory_digest': capability_inventory_binding_digest(
            capability_inventory
        ),
        'side_effect_class': 'mutation',
        'runtime_instance_id': 'rexecop-1',
        'lease_id': 'lease-55',
        'lease_epoch': 9,
        'fencing_token_digest': 'sha256:' + '3' * 64,
    }


def _request_mapping_for_policy_pack(
    policy_pack: CompiledPolicyPack,
    *,
    rebound_policy_pack_digest: str | None = None,
) -> dict[str, Any]:
    request = _base_request_mapping()
    compiled_policy_digest = (
        rebound_policy_pack_digest
        if rebound_policy_pack_digest is not None
        else policy_pack_digest(policy_pack)
    )
    scope_policy_payload = dict(request['scope_policy_binding'])
    scope_policy_payload['policy_pack_digest'] = compiled_policy_digest
    scope_policy = ScopePolicyBinding.from_mapping(scope_policy_payload)
    request['policy_pack'] = policy_pack
    request['policy_pack_digest'] = compiled_policy_digest
    request['scope_policy_binding'] = scope_policy.as_dict()
    request['scope_policy_binding_digest'] = scope_policy_binding_digest(scope_policy)
    return request


def _raw_policy_pack_digest_for_mutation_fixture(
    policy_pack: CompiledPolicyPack,
) -> str:
    return govengine_record_digest(
        policy_pack,
        record_type='govengine.policy.compiler.CompiledPolicyPack',
    )


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
    validated = validate_governance_request(request)

    assert validated == request
    assert validated.policy_pack is not request.policy_pack
    assert GovernanceRequest.from_mapping(request.as_dict()) == request
    assert request.approval_attestation is not None
    assert governance_request_digest(request).startswith('sha256:')


def test_governance_request_rejects_mutated_typed_policy_pack_metadata() -> None:
    policy_pack = _compiled_policy()
    assert isinstance(policy_pack.metadata, dict)
    policy_pack.metadata['password'] = 'REDACTED-FIXTURE'
    with pytest.raises(GovApiError, match='invalid_compiled_policy_pack'):
        policy_pack_digest(policy_pack)
    request = _request_mapping_for_policy_pack(
        policy_pack,
        rebound_policy_pack_digest=_raw_policy_pack_digest_for_mutation_fixture(
            policy_pack
        ),
    )

    with pytest.raises(GovApiError, match='forbidden_policy_metadata'):
        GovernanceRequest.from_mapping(request)


def test_direct_governance_request_rejects_mutated_typed_policy_pack_metadata() -> None:
    request = GovernanceRequest.from_mapping(
        _request_mapping_for_policy_pack(_compiled_policy())
    )
    assert isinstance(request.policy_pack.metadata, dict)
    request.policy_pack.metadata['password'] = 'REDACTED-FIXTURE'
    with pytest.raises(GovApiError, match='invalid_compiled_policy_pack'):
        policy_pack_digest(request.policy_pack)
    compiled_policy_digest = _raw_policy_pack_digest_for_mutation_fixture(
        request.policy_pack
    )
    scope_policy_payload = request.scope_policy_binding.as_dict()
    scope_policy_payload['policy_pack_digest'] = compiled_policy_digest
    scope_policy = ScopePolicyBinding.from_mapping(scope_policy_payload)
    request = replace(
        request,
        policy_pack_digest=compiled_policy_digest,
        scope_policy_binding=scope_policy,
        scope_policy_binding_digest=scope_policy_binding_digest(scope_policy),
    )

    with pytest.raises(GovApiError, match='forbidden_policy_metadata'):
        validate_governance_request(request)


def test_subject_digest_rejects_mutated_typed_policy_pack_metadata() -> None:
    request = GovernanceRequest.from_mapping(_base_request_mapping())
    assert isinstance(request.policy_pack.metadata, dict)
    request.policy_pack.metadata['password'] = 'REDACTED-FIXTURE'
    with pytest.raises(GovApiError, match='invalid_compiled_policy_pack'):
        policy_pack_digest(request.policy_pack)
    compiled_policy_digest = _raw_policy_pack_digest_for_mutation_fixture(
        request.policy_pack
    )
    scope_policy_payload = request.scope_policy_binding.as_dict()
    scope_policy_payload['policy_pack_digest'] = compiled_policy_digest
    scope_policy = ScopePolicyBinding.from_mapping(scope_policy_payload)
    request = replace(
        request,
        policy_pack_digest=compiled_policy_digest,
        scope_policy_binding=scope_policy,
        scope_policy_binding_digest=scope_policy_binding_digest(scope_policy),
    )

    with pytest.raises(GovApiError, match='forbidden_policy_metadata'):
        governance_subject_digest(request)


def test_approval_subject_digest_has_mapping_and_typed_request_parity() -> None:
    request_mapping = _request_mapping_with_approval()
    request = GovernanceRequest.from_mapping(request_mapping)
    assert request.approval_attestation is not None
    expected = request.approval_attestation.subject_digest

    assert governance_subject_digest(request_mapping) == expected
    assert governance_subject_digest(request) == expected


def test_governance_request_rejects_invalid_approval_subject_binding() -> None:
    request = _request_mapping_with_approval()
    attestation_payload = dict(request['approval_attestation'])
    attestation_payload['subject_digest'] = 'sha256:' + 'f' * 64
    attestation = ApprovalAttestation.from_mapping(attestation_payload)
    request['approval_attestation'] = attestation.as_dict()
    request['approval_attestation_digest'] = approval_attestation_digest(attestation)

    with pytest.raises(GovApiError, match='approval_subject_digest_mismatch'):
        GovernanceRequest.from_mapping(request)


def test_approval_binding_rejects_non_ascii_identifier_with_typed_error() -> None:
    request = _request_mapping_with_approval(
        attestation_patch={'operation_id': 'operacja-ż'}
    )

    with pytest.raises(GovApiError, match='invalid_approval_binding_identifier'):
        GovernanceRequest.from_mapping(request)


@pytest.mark.parametrize(
    'schema_version',
    ['v0.1', 'v1'],
    ids=['legacy-v0.1', 'v1'],
)
def test_safe_typed_policy_pack_matches_mapping_request(
    schema_version: str,
) -> None:
    policy_pack = (
        _compiled_v1_policy() if schema_version == 'v1' else _compiled_policy()
    )
    typed_payload = _request_mapping_for_policy_pack(policy_pack)
    mapping_payload = {**typed_payload, 'policy_pack': policy_pack.as_dict()}

    typed_request = GovernanceRequest.from_mapping(typed_payload)
    mapping_request = GovernanceRequest.from_mapping(mapping_payload)

    assert typed_request == mapping_request
    assert typed_request.policy_pack == policy_pack
    assert typed_request.policy_pack is not policy_pack
    assert governance_request_digest(typed_request) == governance_request_digest(
        mapping_request
    )


def test_governance_request_rejects_directly_constructed_invalid_typed_pack() -> None:
    policy_pack = replace(_compiled_v1_policy(), issuer_ref='')
    request = _request_mapping_for_policy_pack(
        policy_pack,
        rebound_policy_pack_digest=_raw_policy_pack_digest_for_mutation_fixture(
            policy_pack
        ),
    )

    with pytest.raises(GovApiError, match='missing_policy_issuer_ref'):
        GovernanceRequest.from_mapping(request)


@pytest.mark.parametrize(
    ('constructor', 'field', 'known_reference'),
    [
        (lambda payload: ApprovalAttestation(**payload), 'signature_ref', 'sigstore:bundle-123'),
        (ApprovalAttestation.from_mapping, 'signature_ref', 'sigstore:bundle-123'),
        (
            lambda payload: ApprovalAttestation(**payload),
            'revocation_ref',
            'approval-revocations:v1',
        ),
        (
            ApprovalAttestation.from_mapping,
            'revocation_ref',
            'approval-revocations:v1',
        ),
    ],
    ids=[
        'signature-direct',
        'signature-mapping',
        'revocation-direct',
        'revocation-mapping',
    ],
)
def test_approval_trust_references_preserve_known_valid_forms(
    constructor,
    field: str,
    known_reference: str,
) -> None:
    payload = dict(_request_mapping_with_approval()['approval_attestation'])
    payload[field] = known_reference

    attestation = constructor(payload)

    assert getattr(attestation, field) == known_reference


@pytest.mark.parametrize(
    ('constructor', 'field', 'reason_code'),
    [
        (
            lambda payload: ApprovalAttestation(**payload),
            'signature_ref',
            'invalid_signature_ref',
        ),
        (
            ApprovalAttestation.from_mapping,
            'signature_ref',
            'invalid_signature_ref',
        ),
        (
            lambda payload: ApprovalAttestation(**payload),
            'revocation_ref',
            'invalid_revocation_ref',
        ),
        (
            ApprovalAttestation.from_mapping,
            'revocation_ref',
            'invalid_revocation_ref',
        ),
    ],
    ids=[
        'signature-direct',
        'signature-mapping',
        'revocation-direct',
        'revocation-mapping',
    ],
)
@pytest.mark.parametrize(
    'reference',
    [
        'sigstore:bundle\x00-123',
        'sigstore:bundle\x1f-123',
        'sigstore:bundle\n123',
        '\nsigstore:bundle-123',
        '\u2028sigstore:bundle-123',
        'sigstore:bundle-123\u2029',
        'sigstore:-----PRIVATEKEY-----',
        'sigstore:-----ENDCERTIFICATE-----',
        'sigstore:-----' + ('x' * 129) + 'PRIVATEKEY-----',
        'sigstore:-----bEgInEnCrYpTeDPrIvAtEkEy-----',
        'sigstore:-----BEGIN   PRIVATE   KEY-----',
        'pem:opaque-id',
        'data:application/pkcs8;base64,QUJD',
        'pkcs8:QUJDREVGR0g=',
        'pkcs-8:QUJDREVGR0g=',
        'private-key-material:opaque-id',
        'private_key_material:opaque-id',
        'raw-private-material',
        'sigstore:',
        ':bundle-123',
        '1sigstore:bundle-123',
        'sigstore:////',
        'sigstore:bundle 123',
        'sigstore:' + ('x' * 2_040),
    ],
    ids=[
        'nul',
        'control',
        'newline',
        'leading-newline',
        'leading-unicode-line-separator',
        'trailing-unicode-paragraph-separator',
        'bare-private-key-armor',
        'end-certificate-armor',
        'long-armored-private-key-bypass',
        'compact-pem-marker',
        'spaced-pem-marker',
        'pem-namespace',
        'data-namespace',
        'pkcs8-namespace',
        'punctuated-pkcs8-namespace',
        'private-key-material-namespace',
        'punctuated-private-key-material-namespace',
        'missing-namespace',
        'missing-opaque-id',
        'missing-namespace-name',
        'invalid-namespace',
        'punctuation-only-id',
        'embedded-space',
        'over-limit',
    ],
)
def test_approval_trust_references_reject_material_without_echo(
    constructor,
    field: str,
    reason_code: str,
    reference: str,
) -> None:
    payload = dict(_request_mapping_with_approval()['approval_attestation'])
    payload[field] = reference

    with pytest.raises(GovApiError, match=reason_code) as exc_info:
        constructor(payload)

    assert reference not in str(exc_info.value)
    assert reference not in repr(exc_info.value.as_dict())


@pytest.mark.parametrize(
    ('constructor', 'field', 'namespace'),
    [
        (
            lambda payload: ApprovalAttestation(**payload),
            'signature_ref',
            'sigstore:',
        ),
        (ApprovalAttestation.from_mapping, 'signature_ref', 'sigstore:'),
        (
            lambda payload: ApprovalAttestation(**payload),
            'revocation_ref',
            'approval-revocations:',
        ),
        (
            ApprovalAttestation.from_mapping,
            'revocation_ref',
            'approval-revocations:',
        ),
    ],
    ids=[
        'signature-direct',
        'signature-mapping',
        'revocation-direct',
        'revocation-mapping',
    ],
)
def test_approval_trust_reference_length_boundary(
    constructor,
    field: str,
    namespace: str,
) -> None:
    payload = dict(_request_mapping_with_approval()['approval_attestation'])
    maximum = namespace + ('x' * (2_048 - len(namespace)))
    payload[field] = maximum

    assert getattr(constructor(payload), field) == maximum
    payload[field] = maximum + 'x'
    with pytest.raises(GovApiError):
        constructor(payload)


def test_approval_optional_empty_signature_reference_has_constructor_parity() -> None:
    payload = dict(_request_mapping_with_approval()['approval_attestation'])
    payload['signature_ref'] = ''

    direct = ApprovalAttestation(**payload)
    parsed = ApprovalAttestation.from_mapping(payload)

    assert direct.signature_ref == ''
    assert parsed.signature_ref == ''


@pytest.mark.parametrize(
    ('field', 'reason_code'),
    [
        ('policy_pack_digest', 'policy_pack_digest_mismatch'),
        ('execution_facts_digest', 'execution_facts_digest_mismatch'),
        ('requested_scope_digest', 'requested_scope_digest_mismatch'),
        ('approval_attestation_digest', 'approval_attestation_digest_mismatch'),
        ('scope_policy_binding_digest', 'scope_policy_binding_digest_mismatch'),
        (
            'capability_requirements_digest',
            'capability_requirements_digest_mismatch',
        ),
        ('capability_inventory_digest', 'capability_inventory_digest_mismatch'),
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


@pytest.mark.parametrize(
    ('record_field', 'patch', 'digest_field', 'reason_code'),
    [
        (
            'scope_policy_binding',
            {'policy_epoch': 43},
            'scope_policy_binding_digest',
            'scope_policy_epoch_mismatch',
        ),
        (
            'capability_requirements',
            {'operation_id': 'op-other'},
            'capability_requirements_digest',
            'capability_requirements_operation_id_mismatch',
        ),
        (
            'capability_requirements',
            {'execution_spec_digest': 'sha256:' + 'a' * 64},
            'capability_requirements_digest',
            'capability_requirements_execution_spec_digest_mismatch',
        ),
        (
            'capability_inventory',
            {'runtime_instance_id': 'rexecop-other'},
            'capability_inventory_digest',
            'capability_inventory_runtime_instance_id_mismatch',
        ),
    ],
)
def test_governance_request_rejects_scope_or_capability_binding_drift(
    record_field: str,
    patch: Mapping[str, Any],
    digest_field: str,
    reason_code: str,
) -> None:
    request = _base_request_mapping()
    record = {**request[record_field], **patch}
    request[record_field] = record
    if record_field == 'scope_policy_binding':
        request[digest_field] = scope_policy_binding_digest(record)
    elif record_field == 'capability_requirements':
        request[digest_field] = operation_capability_requirements_digest(record)
    else:
        request[digest_field] = capability_inventory_binding_digest(record)

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


def test_governance_request_rejects_self_authorized_scope_policy() -> None:
    request = _base_request_mapping()
    request['requested_scope']['allowed_schemes'] = ['https']
    request['requested_scope_digest'] = govengine_record_digest(
        request['requested_scope'],
        record_type='govengine.governance.RequestedScope',
    )

    with pytest.raises(GovApiError, match='self_authorized_scope_policy'):
        GovernanceRequest.from_mapping(request)


def test_governance_request_rejects_legacy_approval_claim_field() -> None:
    request = _base_request_mapping()
    request['approval_evidence_ref'] = 'admission:opaque-reference'

    with pytest.raises(GovApiError, match='unknown_governance_request_field'):
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
    ('field', 'reason_code'),
    [
        ('execution_spec_digest', 'invalid_governance_execution_spec_digest'),
        ('fencing_token_digest', 'invalid_governance_fencing_token_digest'),
    ],
)
def test_governance_request_rejects_uppercase_sha256_digest(
    field: str,
    reason_code: str,
) -> None:
    request = _base_request_mapping()
    request[field] = 'sha256:' + 'A' * 64

    with pytest.raises(GovApiError, match=reason_code):
        GovernanceRequest.from_mapping(request)


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


def test_approval_attestation_rejects_uppercase_sha256_digest() -> None:
    payload = _request_mapping_with_approval()['approval_attestation']
    assert isinstance(payload, dict)
    payload['subject_digest'] = 'sha256:' + 'A' * 64

    with pytest.raises(GovApiError, match='invalid_approval_subject_digest'):
        ApprovalAttestation.from_mapping(payload)
