from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hmac import compare_digest
from typing import TYPE_CHECKING, Any, Mapping, Protocol

from govengine._governance_validation import (
    optional_text,
    parse_aware_timestamp,
    require_sha256_digest,
    reject_unknown_fields,
    required_nonnegative_int,
    required_text,
    schema_version,
    text_tuple,
)
from govengine._trust_references import validate_opaque_trust_reference
from govengine.api import GovApiError, require_mapping
from govengine.signing import govengine_record_digest

if TYPE_CHECKING:
    from govengine.governance import GovernanceRequest


APPROVAL_ATTESTATION_SCHEMA_VERSION = 'v1'
APPROVAL_ATTESTATION_FIELDS = frozenset(
    {
        'schema_version',
        'approval_id',
        'subject_digest',
        'operation_id',
        'step_id',
        'attempt_id',
        'execution_spec_digest',
        'execution_facts_digest',
        'target_scope_digest',
        'policy_pack_digest',
        'policy_epoch',
        'approved_side_effect_class',
        'approver_ref',
        'approver_role',
        'trust_domain',
        'issued_at',
        'not_before',
        'expires_at',
        'revocation_ref',
        'signature_ref',
    }
)


@dataclass(frozen=True)
class ApprovalAttestation:
    """Approval by one identified principal for one digest-bound subject.

    This record is not admission and does not grant runtime execution authority.
    Signature verification and revocation storage remain host-provided trust
    boundaries; GovEngine validates their bounded policy inputs.
    """

    approval_id: str
    subject_digest: str
    operation_id: str
    step_id: str
    attempt_id: str
    execution_spec_digest: str
    execution_facts_digest: str
    target_scope_digest: str
    policy_pack_digest: str
    policy_epoch: int
    approved_side_effect_class: str
    approver_ref: str
    approver_role: str
    trust_domain: str
    issued_at: str
    not_before: str
    expires_at: str
    revocation_ref: str
    schema_version: str = APPROVAL_ATTESTATION_SCHEMA_VERSION
    signature_ref: str = ''

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            'revocation_ref',
            validate_opaque_trust_reference(
                self.revocation_ref,
                allow_empty=False,
                reason_code='invalid_revocation_ref',
            ),
        )
        object.__setattr__(
            self,
            'signature_ref',
            validate_opaque_trust_reference(
                self.signature_ref,
                allow_empty=True,
                reason_code='invalid_signature_ref',
            ),
        )

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> 'ApprovalAttestation':
        raw = require_mapping(value, reason_code='invalid_approval_attestation')
        reject_unknown_fields(
            raw,
            allowed=APPROVAL_ATTESTATION_FIELDS,
            reason_code='unknown_approval_attestation_field',
        )
        revocation_ref = required_text(
            raw,
            'revocation_ref',
            'missing_approval_revocation_ref',
        )
        signature_ref = optional_text(raw, 'signature_ref')
        if isinstance(raw.get('revocation_ref'), str):
            revocation_ref = raw['revocation_ref']
        if isinstance(raw.get('signature_ref'), str):
            signature_ref = raw['signature_ref']
        item = cls(
            approval_id=required_text(raw, 'approval_id', 'missing_approval_id'),
            subject_digest=require_sha256_digest(
                required_text(raw, 'subject_digest', 'missing_approval_subject_digest'),
                'invalid_approval_subject_digest',
            ),
            operation_id=required_text(raw, 'operation_id', 'missing_approval_operation_id'),
            step_id=required_text(raw, 'step_id', 'missing_approval_step_id'),
            attempt_id=required_text(raw, 'attempt_id', 'missing_approval_attempt_id'),
            execution_spec_digest=require_sha256_digest(
                required_text(
                    raw,
                    'execution_spec_digest',
                    'missing_approval_execution_spec_digest',
                ),
                'invalid_approval_execution_spec_digest',
            ),
            execution_facts_digest=require_sha256_digest(
                required_text(
                    raw,
                    'execution_facts_digest',
                    'missing_approval_execution_facts_digest',
                ),
                'invalid_approval_execution_facts_digest',
            ),
            target_scope_digest=require_sha256_digest(
                required_text(
                    raw,
                    'target_scope_digest',
                    'missing_approval_target_scope_digest',
                ),
                'invalid_approval_target_scope_digest',
            ),
            policy_pack_digest=require_sha256_digest(
                required_text(
                    raw,
                    'policy_pack_digest',
                    'missing_approval_policy_pack_digest',
                ),
                'invalid_approval_policy_pack_digest',
            ),
            policy_epoch=required_nonnegative_int(
                raw,
                'policy_epoch',
                'invalid_approval_policy_epoch',
            ),
            approved_side_effect_class=required_text(
                raw,
                'approved_side_effect_class',
                'missing_approved_side_effect_class',
            ),
            approver_ref=required_text(raw, 'approver_ref', 'missing_approval_approver_ref'),
            approver_role=required_text(raw, 'approver_role', 'missing_approval_approver_role'),
            trust_domain=required_text(raw, 'trust_domain', 'missing_approval_trust_domain'),
            issued_at=required_text(raw, 'issued_at', 'missing_approval_issued_at'),
            not_before=required_text(raw, 'not_before', 'missing_approval_not_before'),
            expires_at=required_text(raw, 'expires_at', 'missing_approval_expires_at'),
            revocation_ref=revocation_ref,
            schema_version=schema_version(
                raw,
                default=APPROVAL_ATTESTATION_SCHEMA_VERSION,
                reason_code='invalid_approval_attestation_schema_version',
            ),
            signature_ref=signature_ref,
        )
        _validate_approval_attestation_shape(item)
        return item

    def as_dict(self) -> dict[str, Any]:
        return {
            'schema_version': self.schema_version,
            'approval_id': self.approval_id,
            'subject_digest': self.subject_digest,
            'operation_id': self.operation_id,
            'step_id': self.step_id,
            'attempt_id': self.attempt_id,
            'execution_spec_digest': self.execution_spec_digest,
            'execution_facts_digest': self.execution_facts_digest,
            'target_scope_digest': self.target_scope_digest,
            'policy_pack_digest': self.policy_pack_digest,
            'policy_epoch': self.policy_epoch,
            'approved_side_effect_class': self.approved_side_effect_class,
            'approver_ref': self.approver_ref,
            'approver_role': self.approver_role,
            'trust_domain': self.trust_domain,
            'issued_at': self.issued_at,
            'not_before': self.not_before,
            'expires_at': self.expires_at,
            'revocation_ref': self.revocation_ref,
            'signature_ref': self.signature_ref,
        }


@dataclass(frozen=True)
class ApprovalTrustPolicy:
    """Bounded trust requirements for one approval validation domain."""

    policy_id: str
    trusted_roles: tuple[str, ...]
    trusted_domains: tuple[str, ...]
    trusted_approver_refs: tuple[str, ...] = ()
    require_signature_ref: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.policy_id, str) or not self.policy_id.strip():
            raise GovApiError('missing_approval_trust_policy_id')
        roles = text_tuple(self.trusted_roles, 'invalid_approval_trusted_roles')
        domains = text_tuple(
            self.trusted_domains,
            'invalid_approval_trusted_domains',
        )
        refs = text_tuple(
            self.trusted_approver_refs,
            'invalid_approval_trusted_approver_refs',
        )
        if not roles:
            raise GovApiError('approval_trust_policy_without_roles')
        if not domains:
            raise GovApiError('approval_trust_policy_without_domains')
        if not isinstance(self.require_signature_ref, bool):
            raise GovApiError('invalid_approval_signature_requirement')
        object.__setattr__(self, 'policy_id', self.policy_id.strip())
        object.__setattr__(self, 'trusted_roles', roles)
        object.__setattr__(self, 'trusted_domains', domains)
        object.__setattr__(self, 'trusted_approver_refs', refs)


class ApprovalRevocationPort(Protocol):
    """Host-owned revocation lookup; production adapters must be current."""

    def is_revoked(
        self,
        approval_id: str,
        *,
        approval_digest: str,
        revocation_ref: str,
    ) -> bool:
        ...


def approval_attestation_digest(
    attestation: Mapping[str, Any] | ApprovalAttestation,
) -> str:
    checked = (
        attestation
        if isinstance(attestation, ApprovalAttestation)
        else ApprovalAttestation.from_mapping(attestation)
    )
    _validate_approval_attestation_shape(checked)
    return govengine_record_digest(
        checked,
        record_type='govengine.approvals.ApprovalAttestation',
    )


def validate_approval_attestation(
    attestation: Mapping[str, Any] | ApprovalAttestation | None,
    *,
    request: 'GovernanceRequest | Mapping[str, Any]',
    trust_policy: ApprovalTrustPolicy,
    revocation_port: ApprovalRevocationPort,
    now: datetime | None = None,
) -> ApprovalAttestation:
    """Validate subject binding, trust policy, time window and revocation."""

    from govengine.governance import validate_governance_request

    if attestation is None:
        raise GovApiError('approval_attestation_required')
    checked = (
        attestation
        if isinstance(attestation, ApprovalAttestation)
        else ApprovalAttestation.from_mapping(attestation)
    )
    _validate_approval_attestation_shape(checked)
    checked_request = validate_governance_request(request)
    _validate_request_binding(checked, checked_request)

    digest = approval_attestation_digest(checked)
    if not checked_request.approval_attestation_digest or not compare_digest(
        checked_request.approval_attestation_digest,
        digest,
    ):
        raise GovApiError('approval_attestation_digest_mismatch')
    if checked.approver_role not in trust_policy.trusted_roles:
        raise GovApiError('approval_role_not_trusted')
    if checked.trust_domain not in trust_policy.trusted_domains:
        raise GovApiError('approval_trust_domain_not_trusted')
    if (
        trust_policy.trusted_approver_refs
        and checked.approver_ref not in trust_policy.trusted_approver_refs
    ):
        raise GovApiError('approval_approver_not_trusted')
    if trust_policy.require_signature_ref and not checked.signature_ref:
        raise GovApiError('approval_signature_ref_required')

    validation_time = now or datetime.now(timezone.utc)
    if validation_time.tzinfo is None or validation_time.utcoffset() is None:
        raise GovApiError('approval_validation_time_timezone_required')
    not_before = parse_aware_timestamp(
        checked.not_before,
        'invalid_approval_not_before',
    )
    expires_at = parse_aware_timestamp(
        checked.expires_at,
        'invalid_approval_expires_at',
    )
    if validation_time < not_before:
        raise GovApiError('approval_not_yet_valid')
    if validation_time >= expires_at:
        raise GovApiError('approval_expired')
    if revocation_port.is_revoked(
        checked.approval_id,
        approval_digest=digest,
        revocation_ref=checked.revocation_ref,
    ):
        raise GovApiError('approval_revoked')
    return checked


def _validate_approval_attestation_shape(item: ApprovalAttestation) -> None:
    if item.schema_version != APPROVAL_ATTESTATION_SCHEMA_VERSION:
        raise GovApiError('unknown_approval_attestation_schema_version')
    payload = item.as_dict()
    for key, reason_code in (
        ('approval_id', 'missing_approval_id'),
        ('operation_id', 'missing_approval_operation_id'),
        ('step_id', 'missing_approval_step_id'),
        ('attempt_id', 'missing_approval_attempt_id'),
        ('approved_side_effect_class', 'missing_approved_side_effect_class'),
        ('approver_ref', 'missing_approval_approver_ref'),
        ('approver_role', 'missing_approval_approver_role'),
        ('trust_domain', 'missing_approval_trust_domain'),
        ('issued_at', 'missing_approval_issued_at'),
        ('not_before', 'missing_approval_not_before'),
        ('expires_at', 'missing_approval_expires_at'),
        ('revocation_ref', 'missing_approval_revocation_ref'),
    ):
        required_text(payload, key, reason_code)
    for key, reason_code in (
        ('subject_digest', 'invalid_approval_subject_digest'),
        ('execution_spec_digest', 'invalid_approval_execution_spec_digest'),
        ('execution_facts_digest', 'invalid_approval_execution_facts_digest'),
        ('target_scope_digest', 'invalid_approval_target_scope_digest'),
        ('policy_pack_digest', 'invalid_approval_policy_pack_digest'),
    ):
        require_sha256_digest(getattr(item, key), reason_code)
    if (
        isinstance(item.policy_epoch, bool)
        or not isinstance(item.policy_epoch, int)
        or item.policy_epoch < 0
    ):
        raise GovApiError('invalid_approval_policy_epoch')
    if not isinstance(item.signature_ref, str):
        raise GovApiError('invalid_signature_ref')
    if item.approved_side_effect_class not in {'read_only', 'mutation'}:
        raise GovApiError('unsupported_approval_side_effect_class')
    issued_at = parse_aware_timestamp(item.issued_at, 'invalid_approval_issued_at')
    not_before = parse_aware_timestamp(
        item.not_before,
        'invalid_approval_not_before',
    )
    expires_at = parse_aware_timestamp(
        item.expires_at,
        'invalid_approval_expires_at',
    )
    if issued_at >= expires_at or not_before >= expires_at:
        raise GovApiError('invalid_approval_validity_window')


def _validate_request_binding(
    attestation: ApprovalAttestation,
    request: 'GovernanceRequest',
) -> None:
    from govengine.governance import _validated_governance_subject_digest

    bindings = (
        (
            attestation.subject_digest,
            _validated_governance_subject_digest(request),
            'approval_subject_digest_mismatch',
        ),
        (attestation.operation_id, request.operation_id, 'approval_operation_id_mismatch'),
        (attestation.step_id, request.step_id, 'approval_step_id_mismatch'),
        (attestation.attempt_id, request.attempt_id, 'approval_attempt_id_mismatch'),
        (
            attestation.execution_spec_digest,
            request.execution_spec_digest,
            'approval_execution_spec_digest_mismatch',
        ),
        (
            attestation.execution_facts_digest,
            request.execution_facts_digest,
            'approval_execution_facts_digest_mismatch',
        ),
        (
            attestation.target_scope_digest,
            request.requested_scope_digest,
            'approval_target_scope_digest_mismatch',
        ),
        (
            attestation.policy_pack_digest,
            request.policy_pack_digest,
            'approval_policy_pack_digest_mismatch',
        ),
        (
            attestation.approved_side_effect_class,
            request.side_effect_class,
            'approval_side_effect_class_mismatch',
        ),
    )
    for actual, expected, reason_code in bindings:
        if not compare_digest(actual, expected):
            raise GovApiError(reason_code)
    if attestation.policy_epoch != request.policy_epoch:
        raise GovApiError('approval_policy_epoch_mismatch')
