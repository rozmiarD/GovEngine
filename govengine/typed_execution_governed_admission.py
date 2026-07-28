from __future__ import annotations

from dataclasses import dataclass, fields, replace
from datetime import datetime, timezone
from hmac import compare_digest
from typing import Any, Mapping

from govengine._governance_validation import (
    parse_aware_timestamp,
    reject_unknown_fields,
    require_sha256_digest,
    required_nonnegative_int,
    required_text,
    text_tuple,
)
from govengine._json_boundary import bounded_json_copy
from govengine.api import GovApiError, require_mapping
from govengine.approvals import (
    ApprovalRevocationPort,
    ApprovalTrustPolicy,
    approval_attestation_digest,
)
from govengine.capabilities import operation_capability_requirements_digest
from govengine.governance import (
    GovernanceRequest,
    governance_request_digest,
    validate_governance_request,
)
from govengine.governance_decision import (
    ApprovalSignatureVerificationPort,
    GovernanceDecision,
    PolicyActivationPort,
    evaluate_governance,
    validate_governance_decision,
)
from govengine.signing import govengine_record_digest
from govengine.typed_execution_governance import (
    RAW_SHELL_BACKEND_CLASSES,
    SUPPORTED_BACKEND_CLASSES,
    TYPED_EXECUTION_GOVERNANCE_REQUEST_SCHEMA_VERSION,
    TypedExecutionGovernanceRequest,
    explain_typed_execution_governance,
    typed_execution_governance_request_digest,
    validate_typed_execution_governance_request,
)


TYPED_EXECUTION_GOVERNED_ADMISSION_SCHEMA_VERSION = 'v0.1'
SUPPORTED_GOVERNED_OPERATION_MODES = frozenset({'apply', 'recovery'})
TYPED_EXECUTION_MUTATION_APPROVAL_BLOCKERS = frozenset(
    {
        'mutation_requires_approval_evidence',
        'mutation_requires_approval_attestation',
    }
)

_ADMISSION_STATUSES = frozenset({'passed', 'blocked'})
_ADMISSION_FIELDS = frozenset(
    {
        'schema_version',
        'status',
        'reason_code',
        'actual_operation_mode',
        'typed_execution_operation_mode',
        'request_id',
        'transaction_id',
        'decision_id',
        'operation_id',
        'step_id',
        'attempt_id',
        'runtime_instance_id',
        'lease_id',
        'lease_epoch',
        'fencing_token_digest',
        'typed_execution_request_digest',
        'typed_execution_governance_projection_digest',
        'typed_execution_capability_compatibility_digest',
        'typed_execution_bundle_digest',
        'governance_request_digest',
        'governance_decision_digest',
        'approval_attestation_digest',
        'execution_spec_digest',
        'execution_facts_digest',
        'payload_digest',
        'requested_scope_digest',
        'capability_inventory_digest',
        'inventory_epoch',
        'policy_pack_digest',
        'policy_epoch',
        'side_effect_class',
        'discounted_typed_execution_blockers',
        'blockers',
        'admitted_at',
        'decision_expires_at',
        'admission_digest',
        'non_claims',
    }
)
_NON_CLAIMS = (
    'This projection is not an execution permit or signed decision authority.',
    'The host must verify and atomically claim the signed GovernanceDecision.',
    'The host must recheck lease, permit, expiry and revocation before connector I/O.',
    'The recovery alias does not change typed-execution v0.1 semantics.',
    'This projection does not grant mutation readiness or prove runtime I/O.',
)


@dataclass(frozen=True)
class TypedExecutionGovernedAdmission:
    """Digest-bound admission projection over unchanged typed v0.1 and v1 authority.

    The record is intentionally not execution authority. A runtime must still
    verify and atomically claim the separately signed ``GovernanceDecision``
    and enforce its own lease, permit and receipt boundaries.
    """

    schema_version: str
    status: str
    reason_code: str
    actual_operation_mode: str
    typed_execution_operation_mode: str
    request_id: str
    transaction_id: str
    decision_id: str
    operation_id: str
    step_id: str
    attempt_id: str
    runtime_instance_id: str
    lease_id: str
    lease_epoch: int
    fencing_token_digest: str
    typed_execution_request_digest: str
    typed_execution_governance_projection_digest: str
    typed_execution_capability_compatibility_digest: str
    typed_execution_bundle_digest: str
    governance_request_digest: str
    governance_decision_digest: str
    approval_attestation_digest: str
    execution_spec_digest: str
    execution_facts_digest: str
    payload_digest: str
    requested_scope_digest: str
    capability_inventory_digest: str
    inventory_epoch: int
    policy_pack_digest: str
    policy_epoch: int
    side_effect_class: str
    discounted_typed_execution_blockers: tuple[str, ...]
    blockers: tuple[str, ...]
    admitted_at: str
    decision_expires_at: str
    admission_digest: str
    non_claims: tuple[str, ...] = _NON_CLAIMS

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any],
    ) -> 'TypedExecutionGovernedAdmission':
        raw = require_mapping(
            bounded_json_copy(value),
            reason_code='invalid_typed_execution_governed_admission',
        )
        reject_unknown_fields(
            raw,
            allowed=_ADMISSION_FIELDS,
            reason_code='unknown_typed_execution_governed_admission_field',
        )
        item = cls(
            schema_version=required_text(
                raw,
                'schema_version',
                'missing_typed_execution_governed_admission_schema_version',
            ),
            status=required_text(
                raw,
                'status',
                'missing_typed_execution_governed_admission_status',
            ),
            reason_code=required_text(
                raw,
                'reason_code',
                'missing_typed_execution_governed_admission_reason_code',
            ),
            actual_operation_mode=required_text(
                raw,
                'actual_operation_mode',
                'missing_typed_execution_governed_actual_operation_mode',
            ),
            typed_execution_operation_mode=required_text(
                raw,
                'typed_execution_operation_mode',
                'missing_typed_execution_governed_compatibility_mode',
            ),
            request_id=required_text(
                raw,
                'request_id',
                'missing_typed_execution_governed_request_id',
            ),
            transaction_id=required_text(
                raw,
                'transaction_id',
                'missing_typed_execution_governed_transaction_id',
            ),
            decision_id=required_text(
                raw,
                'decision_id',
                'missing_typed_execution_governed_decision_id',
            ),
            operation_id=required_text(
                raw,
                'operation_id',
                'missing_typed_execution_governed_operation_id',
            ),
            step_id=required_text(
                raw,
                'step_id',
                'missing_typed_execution_governed_step_id',
            ),
            attempt_id=required_text(
                raw,
                'attempt_id',
                'missing_typed_execution_governed_attempt_id',
            ),
            runtime_instance_id=required_text(
                raw,
                'runtime_instance_id',
                'missing_typed_execution_governed_runtime_instance_id',
            ),
            lease_id=required_text(
                raw,
                'lease_id',
                'missing_typed_execution_governed_lease_id',
            ),
            lease_epoch=required_nonnegative_int(
                raw,
                'lease_epoch',
                'invalid_typed_execution_governed_lease_epoch',
            ),
            fencing_token_digest=_required_digest(
                raw,
                'fencing_token_digest',
            ),
            typed_execution_request_digest=_required_digest(
                raw,
                'typed_execution_request_digest',
            ),
            typed_execution_governance_projection_digest=_required_digest(
                raw,
                'typed_execution_governance_projection_digest',
            ),
            typed_execution_capability_compatibility_digest=_required_digest(
                raw,
                'typed_execution_capability_compatibility_digest',
            ),
            typed_execution_bundle_digest=_required_digest(
                raw,
                'typed_execution_bundle_digest',
            ),
            governance_request_digest=_required_digest(
                raw,
                'governance_request_digest',
            ),
            governance_decision_digest=_required_digest(
                raw,
                'governance_decision_digest',
            ),
            approval_attestation_digest=_optional_digest(
                raw,
                'approval_attestation_digest',
            ),
            execution_spec_digest=_required_digest(
                raw,
                'execution_spec_digest',
            ),
            execution_facts_digest=_required_digest(
                raw,
                'execution_facts_digest',
            ),
            payload_digest=_required_digest(raw, 'payload_digest'),
            requested_scope_digest=_required_digest(
                raw,
                'requested_scope_digest',
            ),
            capability_inventory_digest=_required_digest(
                raw,
                'capability_inventory_digest',
            ),
            inventory_epoch=required_nonnegative_int(
                raw,
                'inventory_epoch',
                'invalid_typed_execution_governed_inventory_epoch',
            ),
            policy_pack_digest=_required_digest(raw, 'policy_pack_digest'),
            policy_epoch=required_nonnegative_int(
                raw,
                'policy_epoch',
                'invalid_typed_execution_governed_policy_epoch',
            ),
            side_effect_class=required_text(
                raw,
                'side_effect_class',
                'missing_typed_execution_governed_side_effect_class',
            ),
            discounted_typed_execution_blockers=text_tuple(
                raw.get('discounted_typed_execution_blockers'),
                'invalid_discounted_typed_execution_blockers',
            ),
            blockers=text_tuple(
                raw.get('blockers'),
                'invalid_typed_execution_governed_blockers',
            ),
            admitted_at=required_text(
                raw,
                'admitted_at',
                'missing_typed_execution_governed_admitted_at',
            ),
            decision_expires_at=_optional_text(
                raw,
                'decision_expires_at',
            ),
            admission_digest=_required_digest(raw, 'admission_digest'),
            non_claims=text_tuple(
                raw.get('non_claims'),
                'invalid_typed_execution_governed_non_claims',
            ),
        )
        return _validate_admission_shape(item)

    @property
    def allowed(self) -> bool:
        return self.status == 'passed'

    def as_dict(self) -> dict[str, Any]:
        return {
            **_admission_body(self),
            'admission_digest': self.admission_digest,
            'non_claims': list(self.non_claims),
        }


def evaluate_typed_execution_governed_admission(
    typed_execution_request: (
        Mapping[str, Any] | TypedExecutionGovernanceRequest
    ),
    governance_request: Mapping[str, Any] | GovernanceRequest,
    *,
    actual_operation_mode: str,
    policy_activation_port: PolicyActivationPort,
    evaluated_at: datetime,
    admitted_at: datetime,
    approval_trust_policy: ApprovalTrustPolicy | None = None,
    approval_revocation_port: ApprovalRevocationPort | None = None,
    approval_signature_verifier: ApprovalSignatureVerificationPort | None = None,
    authorization_nonce: str = '',
    authorization_expires_at: datetime | None = None,
    decision_id: str = '',
) -> tuple[TypedExecutionGovernedAdmission, GovernanceDecision]:
    """Evaluate exact v1 authority and project its binding to typed execution.

    The returned decision remains separate so the host can sign it and the
    runtime can independently verify and claim it. Callers cannot inject a
    prebuilt decision into this function.
    """

    checked_typed = validate_typed_execution_governance_request(
        typed_execution_request
    )
    checked_governance = validate_governance_request(governance_request)
    mode = _actual_operation_mode(actual_operation_mode)
    evaluation_time = _aware_utc(
        evaluated_at,
        'typed_execution_governed_evaluation_time_timezone_required',
    )
    admission_time = _aware_utc(
        admitted_at,
        'typed_execution_governed_admission_time_timezone_required',
    )
    if admission_time < evaluation_time:
        raise GovApiError('typed_execution_governed_admission_precedes_evaluation')

    bundle, discounted = _validated_typed_mutation_precheck(checked_typed)
    _validate_typed_governance_request_binding(
        checked_typed,
        checked_governance,
        actual_operation_mode=mode,
    )
    decision = evaluate_governance(
        checked_governance,
        policy_activation_port=policy_activation_port,
        evaluated_at=evaluation_time,
        approval_trust_policy=approval_trust_policy,
        approval_revocation_port=approval_revocation_port,
        approval_signature_verifier=approval_signature_verifier,
        authorization_nonce=authorization_nonce,
        authorization_expires_at=authorization_expires_at,
        decision_id=decision_id,
    )

    blockers: list[str] = []
    if not decision.allowed:
        blockers.append('governance_decision_not_allowed')
        blockers.extend(decision.blockers)
    authorization = decision.authorization
    decision_expires_at = (
        authorization.expires_at if authorization is not None else ''
    )
    if authorization is not None:
        expires_at = parse_aware_timestamp(
            authorization.expires_at,
            'invalid_authorization_expires_at',
        )
        if admission_time >= expires_at:
            blockers.append('governance_decision_expired')
    blockers_tuple = tuple(dict.fromkeys(blockers))
    status = 'passed' if not blockers_tuple else 'blocked'
    reason_code = (
        'typed_execution_governed_admission_passed'
        if not blockers_tuple
        else blockers_tuple[0]
    )
    attestation = checked_governance.approval_attestation
    attestation_digest = (
        approval_attestation_digest(attestation)
        if attestation is not None
        else ''
    )
    item = TypedExecutionGovernedAdmission(
        schema_version=TYPED_EXECUTION_GOVERNED_ADMISSION_SCHEMA_VERSION,
        status=status,
        reason_code=reason_code,
        actual_operation_mode=mode,
        typed_execution_operation_mode=checked_typed.operation_mode,
        request_id=checked_typed.request_id,
        transaction_id=checked_governance.transaction_id,
        decision_id=decision.decision_id,
        operation_id=checked_governance.operation_id,
        step_id=checked_governance.step_id,
        attempt_id=checked_governance.attempt_id,
        runtime_instance_id=checked_governance.runtime_instance_id,
        lease_id=checked_governance.lease_id,
        lease_epoch=checked_governance.lease_epoch,
        fencing_token_digest=checked_governance.fencing_token_digest,
        typed_execution_request_digest=typed_execution_governance_request_digest(
            checked_typed
        ),
        typed_execution_governance_projection_digest=(
            bundle.governance.projection_digest
        ),
        typed_execution_capability_compatibility_digest=(
            bundle.compatibility.report_digest
        ),
        typed_execution_bundle_digest=bundle.bundle_digest,
        governance_request_digest=governance_request_digest(checked_governance),
        governance_decision_digest=decision.decision_digest,
        approval_attestation_digest=attestation_digest,
        execution_spec_digest=checked_governance.execution_spec_digest,
        execution_facts_digest=checked_governance.execution_facts_digest,
        payload_digest=checked_governance.payload_digest,
        requested_scope_digest=checked_governance.requested_scope_digest,
        capability_inventory_digest=checked_governance.capability_inventory_digest,
        inventory_epoch=checked_governance.capability_inventory.inventory_epoch,
        policy_pack_digest=checked_governance.policy_pack_digest,
        policy_epoch=checked_governance.policy_epoch,
        side_effect_class=checked_governance.side_effect_class,
        discounted_typed_execution_blockers=discounted,
        blockers=blockers_tuple,
        admitted_at=_timestamp(admission_time),
        decision_expires_at=decision_expires_at,
        admission_digest='',
    )
    item = replace(item, admission_digest=_admission_body_digest(item))
    return (
        validate_typed_execution_governed_admission(
            item,
            typed_execution_request=checked_typed,
            governance_request=checked_governance,
            governance_decision=decision,
            validated_at=admission_time,
        ),
        decision,
    )


def validate_typed_execution_governed_admission(
    admission: Mapping[str, Any] | TypedExecutionGovernedAdmission,
    *,
    typed_execution_request: (
        Mapping[str, Any] | TypedExecutionGovernanceRequest
    ),
    governance_request: Mapping[str, Any] | GovernanceRequest,
    governance_decision: GovernanceDecision,
    validated_at: datetime,
) -> TypedExecutionGovernedAdmission:
    """Recompute the projection and all owner-record bindings.

    This validates integrity and exact binding only. It does not verify the
    separate signed-decision envelope or atomically claim its authorization.
    """

    checked = (
        _validate_admission_shape(admission)
        if isinstance(admission, TypedExecutionGovernedAdmission)
        else TypedExecutionGovernedAdmission.from_mapping(admission)
    )
    checked_typed = validate_typed_execution_governance_request(
        typed_execution_request
    )
    checked_governance = validate_governance_request(governance_request)
    checked_decision = validate_governance_decision(
        governance_decision,
        request=checked_governance,
    )
    validation_time = _aware_utc(
        validated_at,
        'typed_execution_governed_validation_time_timezone_required',
    )
    admitted_at = parse_aware_timestamp(
        checked.admitted_at,
        'invalid_typed_execution_governed_admitted_at',
    )
    if admitted_at > validation_time:
        raise GovApiError('typed_execution_governed_admitted_at_in_future')
    bundle, discounted = _validated_typed_mutation_precheck(checked_typed)
    _validate_typed_governance_request_binding(
        checked_typed,
        checked_governance,
        actual_operation_mode=checked.actual_operation_mode,
    )
    attestation = checked_governance.approval_attestation
    attestation_digest = (
        approval_attestation_digest(attestation)
        if attestation is not None
        else ''
    )
    if not compare_digest(
        checked_decision.approval_attestation_digest,
        attestation_digest,
    ):
        raise GovApiError(
            'typed_execution_governed_decision_approval_attestation_digest_mismatch'
        )
    expected: tuple[tuple[Any, Any, str], ...] = (
        (
            checked.typed_execution_operation_mode,
            checked_typed.operation_mode,
            'typed_execution_governed_compatibility_mode_mismatch',
        ),
        (
            checked.request_id,
            checked_typed.request_id,
            'typed_execution_governed_request_id_mismatch',
        ),
        (
            checked.transaction_id,
            checked_governance.transaction_id,
            'typed_execution_governed_transaction_id_mismatch',
        ),
        (
            checked.decision_id,
            checked_decision.decision_id,
            'typed_execution_governed_decision_id_mismatch',
        ),
        (
            checked.operation_id,
            checked_governance.operation_id,
            'typed_execution_governed_operation_id_mismatch',
        ),
        (
            checked.step_id,
            checked_governance.step_id,
            'typed_execution_governed_step_id_mismatch',
        ),
        (
            checked.attempt_id,
            checked_governance.attempt_id,
            'typed_execution_governed_attempt_id_mismatch',
        ),
        (
            checked.runtime_instance_id,
            checked_governance.runtime_instance_id,
            'typed_execution_governed_runtime_instance_id_mismatch',
        ),
        (
            checked.lease_id,
            checked_governance.lease_id,
            'typed_execution_governed_lease_id_mismatch',
        ),
        (
            checked.lease_epoch,
            checked_governance.lease_epoch,
            'typed_execution_governed_lease_epoch_mismatch',
        ),
        (
            checked.fencing_token_digest,
            checked_governance.fencing_token_digest,
            'typed_execution_governed_fencing_token_digest_mismatch',
        ),
        (
            checked.typed_execution_request_digest,
            typed_execution_governance_request_digest(checked_typed),
            'typed_execution_governed_request_digest_mismatch',
        ),
        (
            checked.typed_execution_governance_projection_digest,
            bundle.governance.projection_digest,
            'typed_execution_governed_projection_digest_mismatch',
        ),
        (
            checked.typed_execution_capability_compatibility_digest,
            bundle.compatibility.report_digest,
            'typed_execution_governed_compatibility_digest_mismatch',
        ),
        (
            checked.typed_execution_bundle_digest,
            bundle.bundle_digest,
            'typed_execution_governed_bundle_digest_mismatch',
        ),
        (
            checked.governance_request_digest,
            governance_request_digest(checked_governance),
            'typed_execution_governed_governance_request_digest_mismatch',
        ),
        (
            checked.governance_decision_digest,
            checked_decision.decision_digest,
            'typed_execution_governed_decision_digest_mismatch',
        ),
        (
            checked.approval_attestation_digest,
            attestation_digest,
            'typed_execution_governed_approval_attestation_digest_mismatch',
        ),
        (
            checked.execution_spec_digest,
            checked_governance.execution_spec_digest,
            'typed_execution_governed_execution_spec_digest_mismatch',
        ),
        (
            checked.execution_facts_digest,
            checked_governance.execution_facts_digest,
            'typed_execution_governed_execution_facts_digest_mismatch',
        ),
        (
            checked.payload_digest,
            checked_governance.payload_digest,
            'typed_execution_governed_payload_digest_mismatch',
        ),
        (
            checked.requested_scope_digest,
            checked_governance.requested_scope_digest,
            'typed_execution_governed_requested_scope_digest_mismatch',
        ),
        (
            checked.capability_inventory_digest,
            checked_governance.capability_inventory_digest,
            'typed_execution_governed_capability_inventory_digest_mismatch',
        ),
        (
            checked.inventory_epoch,
            checked_governance.capability_inventory.inventory_epoch,
            'typed_execution_governed_inventory_epoch_mismatch',
        ),
        (
            checked.policy_pack_digest,
            checked_governance.policy_pack_digest,
            'typed_execution_governed_policy_pack_digest_mismatch',
        ),
        (
            checked.policy_epoch,
            checked_governance.policy_epoch,
            'typed_execution_governed_policy_epoch_mismatch',
        ),
        (
            checked.side_effect_class,
            checked_governance.side_effect_class,
            'typed_execution_governed_side_effect_class_mismatch',
        ),
        (
            checked.discounted_typed_execution_blockers,
            discounted,
            'discounted_typed_execution_blockers_mismatch',
        ),
    )
    for actual, wanted, reason_code in expected:
        if actual != wanted:
            raise GovApiError(reason_code)

    expected_blockers: list[str] = []
    if not checked_decision.allowed:
        expected_blockers.append('governance_decision_not_allowed')
        expected_blockers.extend(checked_decision.blockers)
    authorization = checked_decision.authorization
    expected_expires_at = authorization.expires_at if authorization is not None else ''
    if authorization is not None:
        issued_at = parse_aware_timestamp(
            authorization.issued_at,
            'invalid_authorization_issued_at',
        )
        if checked_decision.allowed and admitted_at < issued_at:
            raise GovApiError(
                'typed_execution_governed_admission_precedes_authorization'
            )
        expires_at = parse_aware_timestamp(
            authorization.expires_at,
            'invalid_authorization_expires_at',
        )
        if validation_time >= expires_at:
            if checked.allowed:
                raise GovApiError('typed_execution_governed_decision_expired')
            expected_blockers.append('governance_decision_expired')
    expected_blockers_tuple = tuple(dict.fromkeys(expected_blockers))
    if checked.blockers != expected_blockers_tuple:
        raise GovApiError('typed_execution_governed_blockers_mismatch')
    if checked.decision_expires_at != expected_expires_at:
        raise GovApiError('typed_execution_governed_decision_expiry_mismatch')
    return checked


def typed_execution_governed_admission_digest(
    admission: TypedExecutionGovernedAdmission,
) -> str:
    return _validate_admission_shape(admission).admission_digest


def _validate_typed_mutation_precheck(
    request: TypedExecutionGovernanceRequest,
) -> tuple[Any, tuple[str, ...]]:
    if request.schema_version != TYPED_EXECUTION_GOVERNANCE_REQUEST_SCHEMA_VERSION:
        raise GovApiError('unsupported_typed_execution_governed_request_version')
    if request.operation_mode != 'apply':
        raise GovApiError('typed_execution_governed_apply_alias_required')
    if request.read_only or request.side_effect_class != 'mutation':
        raise GovApiError('typed_execution_governed_mutation_posture_required')
    if request.capability_descriptor.mode != 'apply':
        raise GovApiError(
            'typed_execution_governed_capability_apply_alias_required'
        )
    bundle = explain_typed_execution_governance(request)
    blockers = tuple(
        dict.fromkeys(
            (
                *bundle.governance.blockers,
                *bundle.compatibility.blockers,
            )
        )
    )
    discounted = tuple(
        blocker
        for blocker in blockers
        if blocker in TYPED_EXECUTION_MUTATION_APPROVAL_BLOCKERS
    )
    if not discounted:
        raise GovApiError('typed_execution_mutation_approval_blocker_required')
    residual = tuple(
        blocker
        for blocker in blockers
        if blocker not in TYPED_EXECUTION_MUTATION_APPROVAL_BLOCKERS
    )
    if residual:
        raise GovApiError(
            'typed_execution_governed_precheck_blocked',
            context={'blockers': list(residual)},
        )
    return bundle, discounted


def _validated_typed_mutation_precheck(
    request: TypedExecutionGovernanceRequest,
) -> tuple[Any, tuple[str, ...]]:
    return _validate_typed_mutation_precheck(request)


def _validate_typed_governance_request_binding(
    typed: TypedExecutionGovernanceRequest,
    governance: GovernanceRequest,
    *,
    actual_operation_mode: str,
) -> None:
    mode = _actual_operation_mode(actual_operation_mode)
    typed_digest = typed_execution_governance_request_digest(typed)
    metadata = governance.execution_facts.get('metadata')
    if not isinstance(metadata, Mapping):
        raise GovApiError('typed_execution_governed_facts_metadata_required')
    bindings: tuple[tuple[Any, Any, str], ...] = (
        (
            typed.operation_id,
            governance.operation_id,
            'typed_execution_governed_operation_id_mismatch',
        ),
        (
            typed.step_id,
            governance.step_id,
            'typed_execution_governed_step_id_mismatch',
        ),
        (
            typed.step_execution_spec_digest,
            governance.execution_spec_digest,
            'typed_execution_governed_execution_spec_digest_mismatch',
        ),
        (
            typed.payload_digest,
            governance.payload_digest,
            'typed_execution_governed_payload_digest_mismatch',
        ),
        (
            typed.side_effect_class,
            governance.side_effect_class,
            'typed_execution_governed_side_effect_class_mismatch',
        ),
        (
            metadata.get('typed_execution_governance_request_digest'),
            typed_digest,
            'typed_execution_governed_facts_request_digest_mismatch',
        ),
        (
            metadata.get('actual_operation_mode'),
            mode,
            'typed_execution_governed_actual_operation_mode_mismatch',
        ),
    )
    for actual, expected, reason_code in bindings:
        if actual != expected:
            raise GovApiError(reason_code)


def _validate_admission_shape(
    item: TypedExecutionGovernedAdmission,
) -> TypedExecutionGovernedAdmission:
    if not isinstance(item, TypedExecutionGovernedAdmission):
        raise GovApiError('invalid_typed_execution_governed_admission')
    if item.schema_version != TYPED_EXECUTION_GOVERNED_ADMISSION_SCHEMA_VERSION:
        raise GovApiError('unsupported_typed_execution_governed_admission_version')
    if item.status not in _ADMISSION_STATUSES:
        raise GovApiError('unknown_typed_execution_governed_admission_status')
    if item.actual_operation_mode not in SUPPORTED_GOVERNED_OPERATION_MODES:
        raise GovApiError('unsupported_typed_execution_governed_operation_mode')
    if item.typed_execution_operation_mode != 'apply':
        raise GovApiError('typed_execution_governed_apply_alias_required')
    if item.side_effect_class != 'mutation':
        raise GovApiError('typed_execution_governed_mutation_posture_required')
    if not item.discounted_typed_execution_blockers:
        raise GovApiError('typed_execution_mutation_approval_blocker_required')
    if any(
        blocker not in TYPED_EXECUTION_MUTATION_APPROVAL_BLOCKERS
        for blocker in item.discounted_typed_execution_blockers
    ):
        raise GovApiError('invalid_discounted_typed_execution_blocker')
    for value, reason_code in (
        (item.request_id, 'missing_typed_execution_governed_request_id'),
        (item.transaction_id, 'missing_typed_execution_governed_transaction_id'),
        (item.decision_id, 'missing_typed_execution_governed_decision_id'),
        (item.operation_id, 'missing_typed_execution_governed_operation_id'),
        (item.step_id, 'missing_typed_execution_governed_step_id'),
        (item.attempt_id, 'missing_typed_execution_governed_attempt_id'),
        (
            item.runtime_instance_id,
            'missing_typed_execution_governed_runtime_instance_id',
        ),
        (item.lease_id, 'missing_typed_execution_governed_lease_id'),
    ):
        if not isinstance(value, str) or not value.strip():
            raise GovApiError(reason_code)
    for value, reason_code in (
        (item.lease_epoch, 'invalid_typed_execution_governed_lease_epoch'),
        (item.inventory_epoch, 'invalid_typed_execution_governed_inventory_epoch'),
        (item.policy_epoch, 'invalid_typed_execution_governed_policy_epoch'),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise GovApiError(reason_code)
    for field_name in (
        'fencing_token_digest',
        'typed_execution_request_digest',
        'typed_execution_governance_projection_digest',
        'typed_execution_capability_compatibility_digest',
        'typed_execution_bundle_digest',
        'governance_request_digest',
        'governance_decision_digest',
        'execution_spec_digest',
        'execution_facts_digest',
        'payload_digest',
        'requested_scope_digest',
        'capability_inventory_digest',
        'policy_pack_digest',
        'admission_digest',
    ):
        require_sha256_digest(
            getattr(item, field_name),
            f'invalid_typed_execution_governed_{field_name}',
        )
    if item.approval_attestation_digest:
        require_sha256_digest(
            item.approval_attestation_digest,
            'invalid_typed_execution_governed_approval_attestation_digest',
        )
    admitted_at = parse_aware_timestamp(
        item.admitted_at,
        'invalid_typed_execution_governed_admitted_at',
    )
    if item.decision_expires_at:
        parse_aware_timestamp(
            item.decision_expires_at,
            'invalid_typed_execution_governed_decision_expires_at',
        )
    if item.allowed:
        if item.blockers:
            raise GovApiError('allowed_typed_execution_governed_admission_with_blockers')
        if item.reason_code != 'typed_execution_governed_admission_passed':
            raise GovApiError('typed_execution_governed_admission_reason_mismatch')
        if not item.approval_attestation_digest:
            raise GovApiError('typed_execution_governed_approval_attestation_required')
        if not item.decision_expires_at:
            raise GovApiError('typed_execution_governed_decision_expiry_required')
        if admitted_at >= parse_aware_timestamp(
            item.decision_expires_at,
            'invalid_typed_execution_governed_decision_expires_at',
        ):
            raise GovApiError('allowed_typed_execution_governed_admission_expired')
    else:
        if not item.blockers:
            raise GovApiError('blocked_typed_execution_governed_admission_without_blockers')
        if item.reason_code != item.blockers[0]:
            raise GovApiError('typed_execution_governed_admission_reason_mismatch')
    if item.non_claims != _NON_CLAIMS:
        raise GovApiError('typed_execution_governed_non_claims_mismatch')
    expected_digest = _admission_body_digest(item)
    if not compare_digest(expected_digest, item.admission_digest):
        raise GovApiError('typed_execution_governed_admission_digest_mismatch')
    return item


def _admission_body(item: TypedExecutionGovernedAdmission) -> dict[str, Any]:
    return {
        'schema_version': item.schema_version,
        'status': item.status,
        'reason_code': item.reason_code,
        'actual_operation_mode': item.actual_operation_mode,
        'typed_execution_operation_mode': item.typed_execution_operation_mode,
        'request_id': item.request_id,
        'transaction_id': item.transaction_id,
        'decision_id': item.decision_id,
        'operation_id': item.operation_id,
        'step_id': item.step_id,
        'attempt_id': item.attempt_id,
        'runtime_instance_id': item.runtime_instance_id,
        'lease_id': item.lease_id,
        'lease_epoch': item.lease_epoch,
        'fencing_token_digest': item.fencing_token_digest,
        'typed_execution_request_digest': item.typed_execution_request_digest,
        'typed_execution_governance_projection_digest': (
            item.typed_execution_governance_projection_digest
        ),
        'typed_execution_capability_compatibility_digest': (
            item.typed_execution_capability_compatibility_digest
        ),
        'typed_execution_bundle_digest': item.typed_execution_bundle_digest,
        'governance_request_digest': item.governance_request_digest,
        'governance_decision_digest': item.governance_decision_digest,
        'approval_attestation_digest': item.approval_attestation_digest,
        'execution_spec_digest': item.execution_spec_digest,
        'execution_facts_digest': item.execution_facts_digest,
        'payload_digest': item.payload_digest,
        'requested_scope_digest': item.requested_scope_digest,
        'capability_inventory_digest': item.capability_inventory_digest,
        'inventory_epoch': item.inventory_epoch,
        'policy_pack_digest': item.policy_pack_digest,
        'policy_epoch': item.policy_epoch,
        'side_effect_class': item.side_effect_class,
        'discounted_typed_execution_blockers': list(
            item.discounted_typed_execution_blockers
        ),
        'blockers': list(item.blockers),
        'admitted_at': item.admitted_at,
        'decision_expires_at': item.decision_expires_at,
    }


def _admission_body_digest(item: TypedExecutionGovernedAdmission) -> str:
    return govengine_record_digest(
        _admission_body(item),
        record_type=(
            'govengine.typed_execution_governed_admission.'
            'TypedExecutionGovernedAdmission'
        ),
        schema_version=TYPED_EXECUTION_GOVERNED_ADMISSION_SCHEMA_VERSION,
    )


def _actual_operation_mode(value: str) -> str:
    mode = str(value or '').strip()
    if mode not in SUPPORTED_GOVERNED_OPERATION_MODES:
        raise GovApiError('unsupported_typed_execution_governed_operation_mode')
    return mode


def _required_digest(value: Mapping[str, Any], key: str) -> str:
    return require_sha256_digest(
        required_text(
            value,
            key,
            f'missing_typed_execution_governed_{key}',
        ),
        f'invalid_typed_execution_governed_{key}',
    )


def _optional_digest(value: Mapping[str, Any], key: str) -> str:
    digest = _optional_text(value, key)
    if digest:
        require_sha256_digest(
            digest,
            f'invalid_typed_execution_governed_{key}',
        )
    return digest


def _optional_text(value: Mapping[str, Any], key: str) -> str:
    raw = value.get(key, '')
    if raw is None:
        return ''
    if not isinstance(raw, str):
        raise GovApiError(f'invalid_typed_execution_governed_{key}')
    return raw.strip()


def _aware_utc(value: datetime, reason_code: str) -> datetime:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise GovApiError(reason_code)
    return value.astimezone(timezone.utc)


def _timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


TYPED_EXECUTION_GOVERNED_ADMISSION_V02_SCHEMA_VERSION = 'v0.2'
TYPED_EXECUTION_GOVERNED_ADMISSION_V02_EGRESS_CLASSES = frozenset(
    {'local_subprocess', 'no_network'}
)
TYPED_EXECUTION_GOVERNED_ADMISSION_V02_IDENTITY_CLASSES = frozenset(
    {'none', 'plugin_declared'}
)
TYPED_EXECUTION_GOVERNED_ADMISSION_V02_DISCOUNTABLE_BLOCKERS = frozenset(
    {*TYPED_EXECUTION_MUTATION_APPROVAL_BLOCKERS, 'unsupported_backend_class'}
)

_ADMISSION_V02_FIELDS = frozenset(
    {
        *_ADMISSION_FIELDS,
        'plugin_backend_class',
        'plugin_egress_class',
        'plugin_identity_class',
        'declared_capability_descriptors',
        'capability_requirements_digest',
        'decision_allowed_backend_classes',
        'decision_allowed_network_egress',
    }
)
_V02_NON_CLAIMS = (
    'This projection is not an execution permit or signed decision authority.',
    'The host must verify and atomically claim the signed GovernanceDecision.',
    'The host must recheck lease, permit, expiry and revocation before connector I/O.',
    'The recovery alias does not change typed-execution v0.1 semantics.',
    'This projection does not certify plugin code, entry-point provenance or wrapper implementation.',
    'This projection does not provide process or network isolation.',
    'This projection does not grant mutation readiness or prove live Chrony or runtime I/O.',
    'This projection does not guarantee exactly-once I/O or crash/power-loss recovery.',
    'This projection does not provide production approval infrastructure.',
    'This projection does not authorize a release or publication.',
)


@dataclass(frozen=True, kw_only=True)
class TypedExecutionGovernedAdmissionV02(TypedExecutionGovernedAdmission):
    """Additive policy-bound plugin admission over frozen typed v0.1 and v1.

    This deep-module record binds one non-built-in plugin backend and its exact
    local egress posture to controls produced by the actual governance
    evaluation. It remains a projection; the separately signed decision is the
    authority that a runtime must verify and atomically claim.
    """

    plugin_backend_class: str
    plugin_egress_class: str
    plugin_identity_class: str
    declared_capability_descriptors: tuple[str, ...]
    capability_requirements_digest: str
    decision_allowed_backend_classes: tuple[str, ...]
    decision_allowed_network_egress: tuple[str, ...]
    non_claims: tuple[str, ...] = _V02_NON_CLAIMS

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any],
    ) -> 'TypedExecutionGovernedAdmissionV02':
        raw = require_mapping(
            bounded_json_copy(value),
            reason_code='invalid_typed_execution_governed_admission_v02',
        )
        reject_unknown_fields(
            raw,
            allowed=_ADMISSION_V02_FIELDS,
            reason_code='unknown_typed_execution_governed_admission_v02_field',
        )
        schema = required_text(
            raw,
            'schema_version',
            'missing_typed_execution_governed_admission_v02_schema_version',
        )
        if schema != TYPED_EXECUTION_GOVERNED_ADMISSION_V02_SCHEMA_VERSION:
            raise GovApiError(
                'unsupported_typed_execution_governed_admission_v02_version'
            )
        reason_code = required_text(
            raw,
            'reason_code',
            'missing_typed_execution_governed_admission_v02_reason_code',
        )

        discounted = text_tuple(
            raw.get('discounted_typed_execution_blockers'),
            'invalid_discounted_typed_execution_v02_blockers',
        )
        approval_discount = tuple(
            blocker
            for blocker in discounted
            if blocker in TYPED_EXECUTION_MUTATION_APPROVAL_BLOCKERS
        )
        base_raw = dict(raw)
        for key in _ADMISSION_V02_FIELDS - _ADMISSION_FIELDS:
            base_raw.pop(key, None)
        base_raw['schema_version'] = TYPED_EXECUTION_GOVERNED_ADMISSION_SCHEMA_VERSION
        base_raw['discounted_typed_execution_blockers'] = list(approval_discount)
        base_raw['non_claims'] = list(_NON_CLAIMS)
        if base_raw.get('status') == 'passed':
            base_raw['reason_code'] = 'typed_execution_governed_admission_passed'
        base_body = {
            key: item
            for key, item in base_raw.items()
            if key not in {'admission_digest', 'non_claims'}
        }
        base_raw['admission_digest'] = govengine_record_digest(
            base_body,
            record_type=(
                'govengine.typed_execution_governed_admission.'
                'TypedExecutionGovernedAdmission'
            ),
            schema_version=TYPED_EXECUTION_GOVERNED_ADMISSION_SCHEMA_VERSION,
        )
        base = TypedExecutionGovernedAdmission.from_mapping(base_raw)
        inherited = {
            field.name: getattr(base, field.name)
            for field in fields(TypedExecutionGovernedAdmission)
        }
        inherited.update(
            {
                'schema_version': schema,
                'reason_code': reason_code,
                'discounted_typed_execution_blockers': discounted,
                'admission_digest': _required_digest(raw, 'admission_digest'),
                'non_claims': text_tuple(
                    raw.get('non_claims'),
                    'invalid_typed_execution_governed_admission_v02_non_claims',
                ),
            }
        )
        item = cls(
            **inherited,
            plugin_backend_class=required_text(
                raw,
                'plugin_backend_class',
                'missing_typed_execution_governed_plugin_backend_class',
            ),
            plugin_egress_class=required_text(
                raw,
                'plugin_egress_class',
                'missing_typed_execution_governed_plugin_egress_class',
            ),
            plugin_identity_class=required_text(
                raw,
                'plugin_identity_class',
                'missing_typed_execution_governed_plugin_identity_class',
            ),
            declared_capability_descriptors=text_tuple(
                raw.get('declared_capability_descriptors'),
                'invalid_typed_execution_governed_plugin_capabilities',
            ),
            capability_requirements_digest=_required_digest(
                raw,
                'capability_requirements_digest',
            ),
            decision_allowed_backend_classes=text_tuple(
                raw.get('decision_allowed_backend_classes'),
                'invalid_typed_execution_governed_decision_backend_classes',
            ),
            decision_allowed_network_egress=text_tuple(
                raw.get('decision_allowed_network_egress'),
                'invalid_typed_execution_governed_decision_network_egress',
            ),
        )
        return _validate_admission_v02_shape(item)

    def as_dict(self) -> dict[str, Any]:
        return {
            **_admission_v02_body(self),
            'admission_digest': self.admission_digest,
            'non_claims': list(self.non_claims),
        }


def evaluate_typed_execution_governed_admission_v02(
    typed_execution_request: (
        Mapping[str, Any] | TypedExecutionGovernanceRequest
    ),
    governance_request: Mapping[str, Any] | GovernanceRequest,
    *,
    actual_operation_mode: str,
    policy_activation_port: PolicyActivationPort,
    evaluated_at: datetime,
    admitted_at: datetime,
    approval_trust_policy: ApprovalTrustPolicy | None = None,
    approval_revocation_port: ApprovalRevocationPort | None = None,
    approval_signature_verifier: ApprovalSignatureVerificationPort | None = None,
    authorization_nonce: str = '',
    authorization_expires_at: datetime | None = None,
    decision_id: str = '',
) -> tuple[TypedExecutionGovernedAdmissionV02, GovernanceDecision]:
    """Evaluate v1 governance and bind exact signed-policy plugin controls."""

    checked_typed = validate_typed_execution_governance_request(
        typed_execution_request
    )
    checked_governance = validate_governance_request(governance_request)
    mode = _actual_operation_mode(actual_operation_mode)
    evaluation_time = _aware_utc(
        evaluated_at,
        'typed_execution_governed_v02_evaluation_time_timezone_required',
    )
    admission_time = _aware_utc(
        admitted_at,
        'typed_execution_governed_v02_admission_time_timezone_required',
    )
    if admission_time < evaluation_time:
        raise GovApiError(
            'typed_execution_governed_v02_admission_precedes_evaluation'
        )

    (
        bundle,
        discounted,
        backend,
        egress,
        identity,
        declared_capabilities,
        requirements_digest,
    ) = _validated_typed_plugin_mutation_precheck(
        checked_typed,
        checked_governance,
    )
    _validate_typed_governance_request_binding(
        checked_typed,
        checked_governance,
        actual_operation_mode=mode,
    )
    decision = evaluate_governance(
        checked_governance,
        policy_activation_port=policy_activation_port,
        evaluated_at=evaluation_time,
        approval_trust_policy=approval_trust_policy,
        approval_revocation_port=approval_revocation_port,
        approval_signature_verifier=approval_signature_verifier,
        authorization_nonce=authorization_nonce,
        authorization_expires_at=authorization_expires_at,
        decision_id=decision_id,
    )

    blockers = _governed_v02_decision_blockers(
        decision,
        backend=backend,
        egress=egress,
        at=admission_time,
    )
    status = 'passed' if not blockers else 'blocked'
    reason_code = (
        'typed_execution_governed_admission_v02_passed'
        if not blockers
        else blockers[0]
    )
    attestation = checked_governance.approval_attestation
    attestation_digest = (
        approval_attestation_digest(attestation)
        if attestation is not None
        else ''
    )
    authorization = decision.authorization
    decision_expires_at = (
        authorization.expires_at if authorization is not None else ''
    )
    item = TypedExecutionGovernedAdmissionV02(
        schema_version=TYPED_EXECUTION_GOVERNED_ADMISSION_V02_SCHEMA_VERSION,
        status=status,
        reason_code=reason_code,
        actual_operation_mode=mode,
        typed_execution_operation_mode=checked_typed.operation_mode,
        request_id=checked_typed.request_id,
        transaction_id=checked_governance.transaction_id,
        decision_id=decision.decision_id,
        operation_id=checked_governance.operation_id,
        step_id=checked_governance.step_id,
        attempt_id=checked_governance.attempt_id,
        runtime_instance_id=checked_governance.runtime_instance_id,
        lease_id=checked_governance.lease_id,
        lease_epoch=checked_governance.lease_epoch,
        fencing_token_digest=checked_governance.fencing_token_digest,
        typed_execution_request_digest=typed_execution_governance_request_digest(
            checked_typed
        ),
        typed_execution_governance_projection_digest=(
            bundle.governance.projection_digest
        ),
        typed_execution_capability_compatibility_digest=(
            bundle.compatibility.report_digest
        ),
        typed_execution_bundle_digest=bundle.bundle_digest,
        governance_request_digest=governance_request_digest(checked_governance),
        governance_decision_digest=decision.decision_digest,
        approval_attestation_digest=attestation_digest,
        execution_spec_digest=checked_governance.execution_spec_digest,
        execution_facts_digest=checked_governance.execution_facts_digest,
        payload_digest=checked_governance.payload_digest,
        requested_scope_digest=checked_governance.requested_scope_digest,
        capability_inventory_digest=checked_governance.capability_inventory_digest,
        inventory_epoch=checked_governance.capability_inventory.inventory_epoch,
        policy_pack_digest=checked_governance.policy_pack_digest,
        policy_epoch=checked_governance.policy_epoch,
        side_effect_class=checked_governance.side_effect_class,
        discounted_typed_execution_blockers=discounted,
        blockers=blockers,
        admitted_at=_timestamp(admission_time),
        decision_expires_at=decision_expires_at,
        admission_digest='',
        plugin_backend_class=backend,
        plugin_egress_class=egress,
        plugin_identity_class=identity,
        declared_capability_descriptors=declared_capabilities,
        capability_requirements_digest=requirements_digest,
        decision_allowed_backend_classes=decision.controls.allowed_backend_classes,
        decision_allowed_network_egress=decision.controls.allowed_network_egress,
    )
    item = replace(item, admission_digest=_admission_v02_body_digest(item))
    return (
        validate_typed_execution_governed_admission_v02(
            item,
            typed_execution_request=checked_typed,
            governance_request=checked_governance,
            governance_decision=decision,
            validated_at=admission_time,
        ),
        decision,
    )


def validate_typed_execution_governed_admission_v02(
    admission: Mapping[str, Any] | TypedExecutionGovernedAdmissionV02,
    *,
    typed_execution_request: (
        Mapping[str, Any] | TypedExecutionGovernanceRequest
    ),
    governance_request: Mapping[str, Any] | GovernanceRequest,
    governance_decision: GovernanceDecision,
    validated_at: datetime,
) -> TypedExecutionGovernedAdmissionV02:
    """Recompute v0.2 posture plus every unchanged typed/v1 owner binding."""

    checked = (
        _validate_admission_v02_shape(admission)
        if isinstance(admission, TypedExecutionGovernedAdmissionV02)
        else TypedExecutionGovernedAdmissionV02.from_mapping(admission)
    )
    checked_typed = validate_typed_execution_governance_request(
        typed_execution_request
    )
    checked_governance = validate_governance_request(governance_request)
    checked_decision = validate_governance_decision(
        governance_decision,
        request=checked_governance,
    )
    validation_time = _aware_utc(
        validated_at,
        'typed_execution_governed_v02_validation_time_timezone_required',
    )
    admitted_at = parse_aware_timestamp(
        checked.admitted_at,
        'invalid_typed_execution_governed_v02_admitted_at',
    )
    if admitted_at > validation_time:
        raise GovApiError('typed_execution_governed_v02_admitted_at_in_future')
    (
        bundle,
        discounted,
        backend,
        egress,
        identity,
        declared_capabilities,
        requirements_digest,
    ) = _validated_typed_plugin_mutation_precheck(
        checked_typed,
        checked_governance,
    )
    _validate_typed_governance_request_binding(
        checked_typed,
        checked_governance,
        actual_operation_mode=checked.actual_operation_mode,
    )
    attestation = checked_governance.approval_attestation
    attestation_digest = (
        approval_attestation_digest(attestation)
        if attestation is not None
        else ''
    )
    if not compare_digest(
        checked_decision.approval_attestation_digest,
        attestation_digest,
    ):
        raise GovApiError(
            'typed_execution_governed_v02_decision_approval_digest_mismatch'
        )

    expected: tuple[tuple[Any, Any, str], ...] = (
        (
            checked.typed_execution_operation_mode,
            checked_typed.operation_mode,
            'typed_execution_governed_v02_compatibility_mode_mismatch',
        ),
        (
            checked.request_id,
            checked_typed.request_id,
            'typed_execution_governed_v02_request_id_mismatch',
        ),
        (
            checked.transaction_id,
            checked_governance.transaction_id,
            'typed_execution_governed_v02_transaction_id_mismatch',
        ),
        (
            checked.decision_id,
            checked_decision.decision_id,
            'typed_execution_governed_v02_decision_id_mismatch',
        ),
        (
            checked.operation_id,
            checked_governance.operation_id,
            'typed_execution_governed_v02_operation_id_mismatch',
        ),
        (
            checked.step_id,
            checked_governance.step_id,
            'typed_execution_governed_v02_step_id_mismatch',
        ),
        (
            checked.attempt_id,
            checked_governance.attempt_id,
            'typed_execution_governed_v02_attempt_id_mismatch',
        ),
        (
            checked.runtime_instance_id,
            checked_governance.runtime_instance_id,
            'typed_execution_governed_v02_runtime_instance_id_mismatch',
        ),
        (
            checked.lease_id,
            checked_governance.lease_id,
            'typed_execution_governed_v02_lease_id_mismatch',
        ),
        (
            checked.lease_epoch,
            checked_governance.lease_epoch,
            'typed_execution_governed_v02_lease_epoch_mismatch',
        ),
        (
            checked.fencing_token_digest,
            checked_governance.fencing_token_digest,
            'typed_execution_governed_v02_fencing_token_digest_mismatch',
        ),
        (
            checked.typed_execution_request_digest,
            typed_execution_governance_request_digest(checked_typed),
            'typed_execution_governed_v02_request_digest_mismatch',
        ),
        (
            checked.typed_execution_governance_projection_digest,
            bundle.governance.projection_digest,
            'typed_execution_governed_v02_projection_digest_mismatch',
        ),
        (
            checked.typed_execution_capability_compatibility_digest,
            bundle.compatibility.report_digest,
            'typed_execution_governed_v02_compatibility_digest_mismatch',
        ),
        (
            checked.typed_execution_bundle_digest,
            bundle.bundle_digest,
            'typed_execution_governed_v02_bundle_digest_mismatch',
        ),
        (
            checked.governance_request_digest,
            governance_request_digest(checked_governance),
            'typed_execution_governed_v02_governance_request_digest_mismatch',
        ),
        (
            checked.governance_decision_digest,
            checked_decision.decision_digest,
            'typed_execution_governed_v02_decision_digest_mismatch',
        ),
        (
            checked.approval_attestation_digest,
            attestation_digest,
            'typed_execution_governed_v02_approval_attestation_digest_mismatch',
        ),
        (
            checked.execution_spec_digest,
            checked_governance.execution_spec_digest,
            'typed_execution_governed_v02_execution_spec_digest_mismatch',
        ),
        (
            checked.execution_facts_digest,
            checked_governance.execution_facts_digest,
            'typed_execution_governed_v02_execution_facts_digest_mismatch',
        ),
        (
            checked.payload_digest,
            checked_governance.payload_digest,
            'typed_execution_governed_v02_payload_digest_mismatch',
        ),
        (
            checked.requested_scope_digest,
            checked_governance.requested_scope_digest,
            'typed_execution_governed_v02_requested_scope_digest_mismatch',
        ),
        (
            checked.capability_inventory_digest,
            checked_governance.capability_inventory_digest,
            'typed_execution_governed_v02_inventory_digest_mismatch',
        ),
        (
            checked.inventory_epoch,
            checked_governance.capability_inventory.inventory_epoch,
            'typed_execution_governed_v02_inventory_epoch_mismatch',
        ),
        (
            checked.policy_pack_digest,
            checked_governance.policy_pack_digest,
            'typed_execution_governed_v02_policy_pack_digest_mismatch',
        ),
        (
            checked.policy_epoch,
            checked_governance.policy_epoch,
            'typed_execution_governed_v02_policy_epoch_mismatch',
        ),
        (
            checked.side_effect_class,
            checked_governance.side_effect_class,
            'typed_execution_governed_v02_side_effect_class_mismatch',
        ),
        (
            checked.discounted_typed_execution_blockers,
            discounted,
            'discounted_typed_execution_v02_blockers_mismatch',
        ),
        (
            checked.plugin_backend_class,
            backend,
            'typed_execution_governed_v02_plugin_backend_mismatch',
        ),
        (
            checked.plugin_egress_class,
            egress,
            'typed_execution_governed_v02_plugin_egress_mismatch',
        ),
        (
            checked.plugin_identity_class,
            identity,
            'typed_execution_governed_v02_plugin_identity_mismatch',
        ),
        (
            checked.declared_capability_descriptors,
            declared_capabilities,
            'typed_execution_governed_v02_declared_capabilities_mismatch',
        ),
        (
            checked.capability_requirements_digest,
            requirements_digest,
            'typed_execution_governed_v02_requirements_digest_mismatch',
        ),
        (
            checked.decision_allowed_backend_classes,
            checked_decision.controls.allowed_backend_classes,
            'typed_execution_governed_v02_decision_backend_controls_mismatch',
        ),
        (
            checked.decision_allowed_network_egress,
            checked_decision.controls.allowed_network_egress,
            'typed_execution_governed_v02_decision_egress_controls_mismatch',
        ),
    )
    for actual, wanted, reason_code in expected:
        if actual != wanted:
            raise GovApiError(reason_code)

    expected_blockers = _governed_v02_decision_blockers(
        checked_decision,
        backend=backend,
        egress=egress,
        at=validation_time,
    )
    authorization = checked_decision.authorization
    expected_expires_at = authorization.expires_at if authorization is not None else ''
    if authorization is not None:
        issued_at = parse_aware_timestamp(
            authorization.issued_at,
            'invalid_authorization_issued_at',
        )
        if checked_decision.allowed and admitted_at < issued_at:
            raise GovApiError(
                'typed_execution_governed_v02_admission_precedes_authorization'
            )
    if checked.blockers != expected_blockers:
        raise GovApiError('typed_execution_governed_v02_blockers_mismatch')
    if checked.decision_expires_at != expected_expires_at:
        raise GovApiError('typed_execution_governed_v02_decision_expiry_mismatch')
    return checked


def typed_execution_governed_admission_v02_digest(
    admission: TypedExecutionGovernedAdmissionV02,
) -> str:
    return _validate_admission_v02_shape(admission).admission_digest


def _validated_typed_plugin_mutation_precheck(
    request: TypedExecutionGovernanceRequest,
    governance: GovernanceRequest,
) -> tuple[Any, tuple[str, ...], str, str, str, tuple[str, ...], str]:
    if request.schema_version != TYPED_EXECUTION_GOVERNANCE_REQUEST_SCHEMA_VERSION:
        raise GovApiError('unsupported_typed_execution_governed_v02_request_version')
    if request.operation_mode != 'apply':
        raise GovApiError('typed_execution_governed_v02_apply_alias_required')
    if request.read_only or request.side_effect_class != 'mutation':
        raise GovApiError('typed_execution_governed_v02_mutation_posture_required')
    descriptor = request.capability_descriptor
    if descriptor.mode != 'apply':
        raise GovApiError(
            'typed_execution_governed_v02_capability_apply_alias_required'
        )

    backend = descriptor.backend_class
    if request.backend_class != backend:
        raise GovApiError('typed_execution_governed_v02_backend_binding_mismatch')
    if backend in SUPPORTED_BACKEND_CLASSES:
        raise GovApiError('typed_execution_governed_v02_builtin_backend_forbidden')
    if backend in RAW_SHELL_BACKEND_CLASSES:
        raise GovApiError('typed_execution_governed_v02_raw_shell_backend_forbidden')
    if descriptor.certification_tier != 'plugin':
        raise GovApiError('typed_execution_governed_v02_plugin_tier_required')
    identity = descriptor.identity_class
    if identity not in TYPED_EXECUTION_GOVERNED_ADMISSION_V02_IDENTITY_CLASSES:
        raise GovApiError('typed_execution_governed_v02_plugin_identity_required')
    if descriptor.secret_ref_requirements:
        raise GovApiError('typed_execution_governed_v02_secret_requirements_forbidden')

    declared_capabilities = descriptor.declared_capability_descriptors
    if not declared_capabilities:
        raise GovApiError('typed_execution_governed_v02_plugin_capabilities_required')
    if declared_capabilities != tuple(sorted(set(declared_capabilities))):
        raise GovApiError('invalid_typed_execution_governed_v02_plugin_capabilities')
    egress = descriptor.egress_class
    if egress not in TYPED_EXECUTION_GOVERNED_ADMISSION_V02_EGRESS_CLASSES:
        raise GovApiError('typed_execution_governed_v02_plugin_egress_forbidden')
    boundary_egress = str(descriptor.network_boundary.get('egress') or '').strip()
    if boundary_egress != egress:
        raise GovApiError('typed_execution_governed_v02_boundary_egress_mismatch')
    if request.allowed_network_egress != (egress,):
        raise GovApiError('typed_execution_governed_v02_declared_egress_mismatch')

    required_capabilities = request.required_capability_descriptors
    requirements = governance.capability_requirements
    inventory = governance.capability_inventory
    if requirements.required_backend_class != backend:
        raise GovApiError('typed_execution_governed_v02_requirements_backend_mismatch')
    if required_capabilities != requirements.required_capabilities:
        raise GovApiError(
            'typed_execution_governed_v02_required_capabilities_mismatch'
        )
    if declared_capabilities != required_capabilities:
        raise GovApiError(
            'typed_execution_governed_v02_declared_capabilities_mismatch'
        )
    if backend not in inventory.backend_classes:
        raise GovApiError('typed_execution_governed_v02_inventory_backend_mismatch')
    if not set(required_capabilities).issubset(inventory.capabilities):
        raise GovApiError(
            'typed_execution_governed_v02_inventory_capabilities_mismatch'
        )

    bundle = explain_typed_execution_governance(request)
    blockers = tuple(
        dict.fromkeys(
            (
                *bundle.governance.blockers,
                *bundle.compatibility.blockers,
            )
        )
    )
    approval_blockers = tuple(
        blocker
        for blocker in blockers
        if blocker in TYPED_EXECUTION_MUTATION_APPROVAL_BLOCKERS
    )
    if len(approval_blockers) != 1:
        raise GovApiError(
            'typed_execution_governed_v02_single_approval_blocker_required'
        )
    if 'unsupported_backend_class' not in blockers:
        raise GovApiError(
            'typed_execution_governed_v02_unsupported_backend_blocker_required'
        )
    discounted = tuple(
        blocker
        for blocker in blockers
        if blocker in TYPED_EXECUTION_GOVERNED_ADMISSION_V02_DISCOUNTABLE_BLOCKERS
    )
    if len(discounted) != 2:
        raise GovApiError('invalid_discounted_typed_execution_v02_blockers')
    residual = tuple(
        blocker
        for blocker in blockers
        if blocker
        not in TYPED_EXECUTION_GOVERNED_ADMISSION_V02_DISCOUNTABLE_BLOCKERS
    )
    if residual:
        raise GovApiError(
            'typed_execution_governed_v02_precheck_blocked',
            context={'blockers': list(residual)},
        )
    return (
        bundle,
        discounted,
        backend,
        egress,
        identity,
        declared_capabilities,
        operation_capability_requirements_digest(requirements),
    )


def _governed_v02_decision_blockers(
    decision: GovernanceDecision,
    *,
    backend: str,
    egress: str,
    at: datetime,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if not decision.allowed:
        blockers.append('governance_decision_not_allowed')
        blockers.extend(decision.blockers)
    if decision.controls.allowed_backend_classes != (backend,):
        blockers.append('plugin_backend_policy_control_mismatch')
    if decision.controls.allowed_network_egress != (egress,):
        blockers.append('plugin_egress_policy_control_mismatch')
    authorization = decision.authorization
    if authorization is not None:
        expires_at = parse_aware_timestamp(
            authorization.expires_at,
            'invalid_authorization_expires_at',
        )
        if at >= expires_at:
            blockers.append('governance_decision_expired')
    return tuple(dict.fromkeys(blockers))


def _validate_admission_v02_shape(
    item: TypedExecutionGovernedAdmissionV02,
) -> TypedExecutionGovernedAdmissionV02:
    if not isinstance(item, TypedExecutionGovernedAdmissionV02):
        raise GovApiError('invalid_typed_execution_governed_admission_v02')
    if item.schema_version != TYPED_EXECUTION_GOVERNED_ADMISSION_V02_SCHEMA_VERSION:
        raise GovApiError(
            'unsupported_typed_execution_governed_admission_v02_version'
        )
    approval_discount = tuple(
        blocker
        for blocker in item.discounted_typed_execution_blockers
        if blocker in TYPED_EXECUTION_MUTATION_APPROVAL_BLOCKERS
    )
    if len(approval_discount) != 1:
        raise GovApiError(
            'typed_execution_governed_v02_single_approval_blocker_required'
        )
    if (
        len(item.discounted_typed_execution_blockers) != 2
        or set(item.discounted_typed_execution_blockers)
        != {*approval_discount, 'unsupported_backend_class'}
    ):
        raise GovApiError('invalid_discounted_typed_execution_v02_blockers')

    inherited = {
        field.name: getattr(item, field.name)
        for field in fields(TypedExecutionGovernedAdmission)
    }
    inherited.update(
        {
            'schema_version': TYPED_EXECUTION_GOVERNED_ADMISSION_SCHEMA_VERSION,
            'reason_code': (
                'typed_execution_governed_admission_passed'
                if item.allowed
                else item.reason_code
            ),
            'discounted_typed_execution_blockers': approval_discount,
            'admission_digest': '',
            'non_claims': _NON_CLAIMS,
        }
    )
    base = TypedExecutionGovernedAdmission(**inherited)
    base = replace(base, admission_digest=_admission_body_digest(base))
    _validate_admission_shape(base)

    if (
        not item.plugin_backend_class
        or item.plugin_backend_class in SUPPORTED_BACKEND_CLASSES
        or item.plugin_backend_class in RAW_SHELL_BACKEND_CLASSES
    ):
        raise GovApiError('invalid_typed_execution_governed_v02_plugin_backend')
    if item.plugin_egress_class not in (
        TYPED_EXECUTION_GOVERNED_ADMISSION_V02_EGRESS_CLASSES
    ):
        raise GovApiError('invalid_typed_execution_governed_v02_plugin_egress')
    if item.plugin_identity_class not in (
        TYPED_EXECUTION_GOVERNED_ADMISSION_V02_IDENTITY_CLASSES
    ):
        raise GovApiError('invalid_typed_execution_governed_v02_plugin_identity')
    if (
        not item.declared_capability_descriptors
        or item.declared_capability_descriptors
        != tuple(sorted(set(item.declared_capability_descriptors)))
    ):
        raise GovApiError('invalid_typed_execution_governed_v02_plugin_capabilities')
    require_sha256_digest(
        item.capability_requirements_digest,
        'invalid_typed_execution_governed_v02_capability_requirements_digest',
    )
    for controls, reason_code in (
        (
            item.decision_allowed_backend_classes,
            'invalid_typed_execution_governed_v02_decision_backend_controls',
        ),
        (
            item.decision_allowed_network_egress,
            'invalid_typed_execution_governed_v02_decision_egress_controls',
        ),
    ):
        if controls != tuple(sorted(set(controls))):
            raise GovApiError(reason_code)
    if item.allowed:
        if item.decision_allowed_backend_classes != (item.plugin_backend_class,):
            raise GovApiError(
                'typed_execution_governed_v02_decision_backend_control_mismatch'
            )
        if item.decision_allowed_network_egress != (item.plugin_egress_class,):
            raise GovApiError(
                'typed_execution_governed_v02_decision_egress_control_mismatch'
            )
    if item.allowed and item.reason_code != (
        'typed_execution_governed_admission_v02_passed'
    ):
        raise GovApiError('typed_execution_governed_v02_admission_reason_mismatch')
    if item.non_claims != _V02_NON_CLAIMS:
        raise GovApiError('typed_execution_governed_v02_non_claims_mismatch')
    if not compare_digest(_admission_v02_body_digest(item), item.admission_digest):
        raise GovApiError('typed_execution_governed_admission_v02_digest_mismatch')
    return item


def _admission_v02_body(
    item: TypedExecutionGovernedAdmissionV02,
) -> dict[str, Any]:
    return {
        **_admission_body(item),
        'plugin_backend_class': item.plugin_backend_class,
        'plugin_egress_class': item.plugin_egress_class,
        'plugin_identity_class': item.plugin_identity_class,
        'declared_capability_descriptors': list(
            item.declared_capability_descriptors
        ),
        'capability_requirements_digest': item.capability_requirements_digest,
        'decision_allowed_backend_classes': list(
            item.decision_allowed_backend_classes
        ),
        'decision_allowed_network_egress': list(
            item.decision_allowed_network_egress
        ),
    }


def _admission_v02_body_digest(
    item: TypedExecutionGovernedAdmissionV02,
) -> str:
    return govengine_record_digest(
        _admission_v02_body(item),
        record_type=(
            'govengine.typed_execution_governed_admission.'
            'TypedExecutionGovernedAdmissionV02'
        ),
        schema_version=TYPED_EXECUTION_GOVERNED_ADMISSION_V02_SCHEMA_VERSION,
    )
