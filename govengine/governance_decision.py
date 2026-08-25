from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from hmac import compare_digest
from typing import Any, Mapping, Protocol, runtime_checkable

from govengine._governance_validation import (
    parse_aware_timestamp,
    reject_unknown_fields,
    require_sha256_digest,
    required_nonnegative_int,
    required_text,
    schema_version,
    text_tuple,
)
from govengine.api import GovApiError, require_mapping
from govengine.approvals import (
    ApprovalAttestation,
    ApprovalRevocationPort,
    ApprovalTrustPolicy,
    approval_attestation_digest,
    validate_approval_attestation,
)
from govengine.capabilities import (
    capability_compatibility_decision_digest,
    evaluate_capability_compatibility,
)
from govengine.governance import (
    GovernanceRequest,
    governance_request_digest,
    validate_governance_request,
)
from govengine.governance_trace import project_governance_trace
from govengine.policy import (
    PolicyEnforcementPlan,
    PolicyRequest,
    PolicyVerdict,
    RuntimeControlProjection,
    admit_policy_execution,
    evaluate_policy,
    policy_enforcement_admission,
    policy_enforcement_admission_digest,
    policy_enforcement_plan_digest,
    policy_verdict_digest,
    validate_policy_request,
    validate_policy_verdict,
)
from govengine.policy.activation import (
    PolicyActivationBinding,
    validate_policy_activation_binding,
)
from govengine.scope_policy import evaluate_scope_policy, scope_decision_digest
from govengine.signing import govengine_record_digest


GOVERNANCE_AUTHORIZATION_SCHEMA_VERSION = 'v1'
GOVERNANCE_DECISION_SCHEMA_VERSION = 'v1'
GOVERNANCE_DECISION_STATUSES = frozenset({'allowed', 'approval_required', 'denied'})
MAX_AUTHORIZATION_LIFETIME_SECONDS = 60
GOVERNANCE_AUTHORIZATION_FIELDS = frozenset(
    {
        'schema_version',
        'authorization_id',
        'operation_id',
        'step_id',
        'attempt_id',
        'runtime_instance_id',
        'lease_id',
        'lease_epoch',
        'fencing_token_digest',
        'execution_spec_digest',
        'payload_digest',
        'requested_scope_digest',
        'capability_inventory_digest',
        'inventory_epoch',
        'policy_pack_digest',
        'policy_epoch',
        'issued_at',
        'expires_at',
        'nonce',
        'consume_once',
    }
)
GOVERNANCE_DECISION_FIELDS = frozenset(
    {
        'schema_version',
        'decision_id',
        'transaction_id',
        'request_digest',
        'status',
        'allowed',
        'reason_code',
        'policy_evaluation_digest',
        'policy_verdict_digest',
        'enforcement_plan_digest',
        'governance_trace_digest',
        'scope_decision_digest',
        'capability_compatibility_digest',
        'approval_attestation_digest',
        'controls',
        'required_controls',
        'blockers',
        'authorization',
        'decision_digest',
    }
)


class PolicyActivationPort(Protocol):
    """Host-owned authenticated view of the current policy binding."""

    def current_binding(self, policy_id: str) -> PolicyActivationBinding:
        ...


class ApprovalSignatureVerificationPort(Protocol):
    """Host-owned cryptographic verification of one approval attestation."""

    def verify_approval_signature(
        self,
        attestation: ApprovalAttestation,
        *,
        approval_digest: str,
        trust_policy_id: str,
    ) -> bool:
        ...


@runtime_checkable
class DecisionClaimPort(Protocol):
    """Host-owned atomic claim-once boundary for runtime consumption.

    The caller must verify decision authenticity, exact runtime bindings and
    expiry before invoking this port. A production adapter must atomically
    record both ``decision_digest`` and ``nonce``: it returns ``True`` only
    when neither value has been claimed, and ``False`` when either value was
    claimed previously. ``attempt_id`` and ``runtime_instance_id`` are audit
    bindings, not namespaces that permit reuse. A successful production claim
    must remain consumed across runtime restart and recovery while the
    authorization or its attempt can still be recovered; a rejected claim
    must not reassign or overwrite the existing owner binding.

    GovEngine defines this structural contract only. RExecOp owns persistence,
    locking, recovery durability, retention and the final pre-I/O call.
    """

    def claim_governance_decision_once(
        self,
        *,
        decision_digest: str,
        nonce: str,
        attempt_id: str,
        runtime_instance_id: str,
    ) -> bool:
        """Atomically claim an unclaimed decision digest and nonce together."""
        ...


@dataclass(frozen=True)
class GovernanceAuthorization:
    """Short-lived, attempt-bound governance authority for runtime claiming.

    This record is not a runtime permit and does not perform its own atomic
    claim. RExecOp must claim the nonce/digest once immediately before I/O.
    """

    authorization_id: str
    operation_id: str
    step_id: str
    attempt_id: str
    runtime_instance_id: str
    lease_id: str
    lease_epoch: int
    fencing_token_digest: str
    execution_spec_digest: str
    payload_digest: str
    requested_scope_digest: str
    capability_inventory_digest: str
    inventory_epoch: int
    policy_pack_digest: str
    policy_epoch: int
    issued_at: str
    expires_at: str
    nonce: str
    consume_once: bool = True
    schema_version: str = GOVERNANCE_AUTHORIZATION_SCHEMA_VERSION

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> 'GovernanceAuthorization':
        raw = require_mapping(value, reason_code='invalid_governance_authorization')
        reject_unknown_fields(
            raw,
            allowed=GOVERNANCE_AUTHORIZATION_FIELDS,
            reason_code='unknown_governance_authorization_field',
        )
        consume_once = raw.get('consume_once')
        if consume_once is not True:
            raise GovApiError('authorization_must_be_consume_once')
        item = cls(
            authorization_id=required_text(
                raw,
                'authorization_id',
                'missing_governance_authorization_id',
            ),
            operation_id=required_text(
                raw,
                'operation_id',
                'missing_governance_authorization_operation_id',
            ),
            step_id=required_text(
                raw,
                'step_id',
                'missing_governance_authorization_step_id',
            ),
            attempt_id=required_text(
                raw,
                'attempt_id',
                'missing_governance_authorization_attempt_id',
            ),
            runtime_instance_id=required_text(
                raw,
                'runtime_instance_id',
                'missing_governance_authorization_runtime_instance_id',
            ),
            lease_id=required_text(
                raw,
                'lease_id',
                'missing_governance_authorization_lease_id',
            ),
            lease_epoch=required_nonnegative_int(
                raw,
                'lease_epoch',
                'invalid_authorization_lease_epoch',
            ),
            fencing_token_digest=require_sha256_digest(
                required_text(
                    raw,
                    'fencing_token_digest',
                    'missing_authorization_fencing_token_digest',
                ),
                'invalid_authorization_fencing_token_digest',
            ),
            execution_spec_digest=require_sha256_digest(
                required_text(
                    raw,
                    'execution_spec_digest',
                    'missing_authorization_execution_spec_digest',
                ),
                'invalid_authorization_execution_spec_digest',
            ),
            payload_digest=require_sha256_digest(
                required_text(
                    raw,
                    'payload_digest',
                    'missing_authorization_payload_digest',
                ),
                'invalid_authorization_payload_digest',
            ),
            requested_scope_digest=require_sha256_digest(
                required_text(
                    raw,
                    'requested_scope_digest',
                    'missing_authorization_requested_scope_digest',
                ),
                'invalid_authorization_requested_scope_digest',
            ),
            capability_inventory_digest=require_sha256_digest(
                required_text(
                    raw,
                    'capability_inventory_digest',
                    'missing_authorization_capability_inventory_digest',
                ),
                'invalid_authorization_capability_inventory_digest',
            ),
            inventory_epoch=required_nonnegative_int(
                raw,
                'inventory_epoch',
                'invalid_authorization_inventory_epoch',
            ),
            policy_pack_digest=require_sha256_digest(
                required_text(
                    raw,
                    'policy_pack_digest',
                    'missing_authorization_policy_pack_digest',
                ),
                'invalid_authorization_policy_pack_digest',
            ),
            policy_epoch=required_nonnegative_int(
                raw,
                'policy_epoch',
                'invalid_authorization_policy_epoch',
            ),
            issued_at=required_text(
                raw,
                'issued_at',
                'missing_authorization_issued_at',
            ),
            expires_at=required_text(
                raw,
                'expires_at',
                'missing_authorization_expires_at',
            ),
            nonce=required_text(raw, 'nonce', 'authorization_nonce_required'),
            consume_once=True,
            schema_version=schema_version(
                raw,
                default=GOVERNANCE_AUTHORIZATION_SCHEMA_VERSION,
                reason_code='invalid_governance_authorization_schema_version',
            ),
        )
        _validate_authorization(item)
        return item

    def as_dict(self) -> dict[str, Any]:
        return {
            'schema_version': self.schema_version,
            'authorization_id': self.authorization_id,
            'operation_id': self.operation_id,
            'step_id': self.step_id,
            'attempt_id': self.attempt_id,
            'runtime_instance_id': self.runtime_instance_id,
            'lease_id': self.lease_id,
            'lease_epoch': self.lease_epoch,
            'fencing_token_digest': self.fencing_token_digest,
            'execution_spec_digest': self.execution_spec_digest,
            'payload_digest': self.payload_digest,
            'requested_scope_digest': self.requested_scope_digest,
            'capability_inventory_digest': self.capability_inventory_digest,
            'inventory_epoch': self.inventory_epoch,
            'policy_pack_digest': self.policy_pack_digest,
            'policy_epoch': self.policy_epoch,
            'issued_at': self.issued_at,
            'expires_at': self.expires_at,
            'nonce': self.nonce,
            'consume_once': self.consume_once,
        }


@dataclass(frozen=True)
class GovernanceDecision:
    """Canonical result of policy, approval, scope and capability gates."""

    decision_id: str
    transaction_id: str
    request_digest: str
    status: str
    reason_code: str
    policy_evaluation_digest: str
    policy_verdict_digest: str
    enforcement_plan_digest: str
    governance_trace_digest: str
    scope_decision_digest: str
    capability_compatibility_digest: str
    approval_attestation_digest: str
    controls: RuntimeControlProjection
    required_controls: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
    authorization: GovernanceAuthorization | None = None
    schema_version: str = GOVERNANCE_DECISION_SCHEMA_VERSION
    decision_digest: str = ''

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> 'GovernanceDecision':
        raw = require_mapping(value, reason_code='invalid_governance_decision')
        reject_unknown_fields(
            raw,
            allowed=GOVERNANCE_DECISION_FIELDS,
            reason_code='unknown_governance_decision_field',
        )
        raw_authorization = raw.get('authorization')
        if raw_authorization is None:
            authorization = None
        else:
            authorization = GovernanceAuthorization.from_mapping(
                require_mapping(
                    raw_authorization,
                    reason_code='invalid_governance_authorization',
                )
            )
        raw_controls = raw.get('controls')
        controls = RuntimeControlProjection.from_mapping(
            require_mapping(
                raw_controls,
                reason_code='invalid_governance_decision_controls',
            )
        )
        item = cls(
            decision_id=required_text(
                raw,
                'decision_id',
                'missing_governance_decision_id',
            ),
            transaction_id=required_text(
                raw,
                'transaction_id',
                'missing_governance_decision_transaction_id',
            ),
            request_digest=require_sha256_digest(
                required_text(
                    raw,
                    'request_digest',
                    'missing_governance_decision_request_digest',
                ),
                'invalid_governance_decision_request_digest',
            ),
            status=required_text(
                raw,
                'status',
                'missing_governance_decision_status',
            ),
            reason_code=required_text(
                raw,
                'reason_code',
                'missing_governance_decision_reason_code',
            ),
            policy_evaluation_digest=require_sha256_digest(
                required_text(
                    raw,
                    'policy_evaluation_digest',
                    'missing_policy_evaluation_digest',
                ),
                'invalid_policy_evaluation_digest',
            ),
            policy_verdict_digest=require_sha256_digest(
                required_text(
                    raw,
                    'policy_verdict_digest',
                    'missing_governance_policy_verdict_digest',
                ),
                'invalid_governance_policy_verdict_digest',
            ),
            enforcement_plan_digest=require_sha256_digest(
                required_text(
                    raw,
                    'enforcement_plan_digest',
                    'missing_governance_enforcement_plan_digest',
                ),
                'invalid_governance_enforcement_plan_digest',
            ),
            governance_trace_digest=require_sha256_digest(
                required_text(
                    raw,
                    'governance_trace_digest',
                    'missing_governance_trace_digest',
                ),
                'invalid_governance_trace_digest',
            ),
            scope_decision_digest=require_sha256_digest(
                required_text(
                    raw,
                    'scope_decision_digest',
                    'missing_governance_scope_decision_digest',
                ),
                'invalid_governance_scope_decision_digest',
            ),
            capability_compatibility_digest=require_sha256_digest(
                required_text(
                    raw,
                    'capability_compatibility_digest',
                    'missing_governance_capability_compatibility_digest',
                ),
                'invalid_governance_capability_compatibility_digest',
            ),
            approval_attestation_digest=str(
                raw.get('approval_attestation_digest') or ''
            ).strip(),
            controls=controls,
            required_controls=text_tuple(
                raw.get('required_controls'),
                'invalid_governance_required_controls',
            ),
            blockers=text_tuple(
                raw.get('blockers'),
                'invalid_governance_decision_blockers',
            ),
            authorization=authorization,
            schema_version=schema_version(
                raw,
                default=GOVERNANCE_DECISION_SCHEMA_VERSION,
                reason_code='invalid_governance_decision_schema_version',
            ),
            decision_digest=require_sha256_digest(
                required_text(
                    raw,
                    'decision_digest',
                    'missing_governance_decision_digest',
                ),
                'invalid_governance_decision_digest',
            ),
        )
        if item.status not in GOVERNANCE_DECISION_STATUSES:
            raise GovApiError('unknown_governance_decision_status')
        supplied_allowed = raw.get('allowed')
        if not isinstance(supplied_allowed, bool) or supplied_allowed != item.allowed:
            raise GovApiError('governance_decision_allowed_mismatch')
        return validate_governance_decision(item)

    @property
    def allowed(self) -> bool:
        return self.status == 'allowed'

    def as_dict(self) -> dict[str, Any]:
        return {
            **_governance_decision_body(self),
            'decision_digest': self.decision_digest,
        }


def evaluate_governance(
    request: Mapping[str, Any] | GovernanceRequest,
    *,
    policy_activation_port: PolicyActivationPort,
    evaluated_at: datetime,
    approval_trust_policy: ApprovalTrustPolicy | None = None,
    approval_revocation_port: ApprovalRevocationPort | None = None,
    approval_signature_verifier: ApprovalSignatureVerificationPort | None = None,
    authorization_nonce: str = '',
    authorization_expires_at: datetime | None = None,
    decision_id: str = '',
) -> GovernanceDecision:
    """Evaluate one deterministic governance transaction without runtime I/O."""

    checked = validate_governance_request(request)
    evaluation_time = _aware_utc(evaluated_at, 'governance_evaluation_time_timezone_required')
    policy_activation_expires_at = _validate_policy_activation(
        checked,
        policy_activation_port,
        evaluated_at=evaluation_time,
    )
    policy_request = _policy_request_from_execution_facts(checked)
    initial_verdict = evaluate_policy(policy_request, checked.policy_pack)

    approval_required = (
        checked.side_effect_class == 'mutation'
        or initial_verdict.decision == 'approval_required'
    )
    validated_approval = _validated_approval(
        checked,
        trust_policy=approval_trust_policy,
        revocation_port=approval_revocation_port,
        signature_verifier=approval_signature_verifier,
        evaluated_at=evaluation_time,
    )
    effective_verdict = _resolve_approval_requirement(
        initial_verdict,
        validated_approval,
    )
    plan = admit_policy_execution(checked.policy_pack, effective_verdict)
    admission = policy_enforcement_admission(plan)
    enforcement = {
        'plan': plan.as_dict(),
        'plan_digest': policy_enforcement_plan_digest(plan),
        'admission': admission.as_dict(),
        'admission_digest': policy_enforcement_admission_digest(admission),
    }
    trace = project_governance_trace(
        policy_request=policy_request,
        policy_verdict=effective_verdict,
        policy_enforcement=enforcement,
        trace_id=f'gov-trace:{checked.transaction_id}',
    )
    scope = evaluate_scope_policy(
        checked.requested_scope,
        checked.scope_policy_binding,
    )
    capability = evaluate_capability_compatibility(
        checked.capability_requirements,
        checked.capability_inventory,
    )

    status, reason_code, blockers = _decision_outcome(
        initial_verdict=initial_verdict,
        plan=plan,
        scope_allowed=scope.allowed,
        scope_reason=scope.reason_code,
        capability_compatible=capability.compatible,
        capability_reason=capability.reason_code,
        approval_required=approval_required,
        approval_validated=validated_approval is not None,
    )
    resolved_decision_id = decision_id.strip() or f'gov-decision:{checked.transaction_id}'
    authorization = None
    if status == 'allowed':
        authorization = _authorization(
            checked,
            authorization_id=f'gov-auth:{resolved_decision_id}',
            nonce=authorization_nonce,
            issued_at=evaluation_time,
            expires_at=authorization_expires_at,
            approval=validated_approval,
            policy_activation_expires_at=policy_activation_expires_at,
        )

    item = GovernanceDecision(
        decision_id=resolved_decision_id,
        transaction_id=checked.transaction_id,
        request_digest=governance_request_digest(checked),
        status=status,
        reason_code=reason_code,
        policy_evaluation_digest=policy_verdict_digest(initial_verdict),
        policy_verdict_digest=policy_verdict_digest(effective_verdict),
        enforcement_plan_digest=enforcement['plan_digest'],
        governance_trace_digest=trace.trace_digest,
        scope_decision_digest=scope_decision_digest(scope),
        capability_compatibility_digest=capability_compatibility_decision_digest(
            capability
        ),
        approval_attestation_digest=(
            approval_attestation_digest(validated_approval)
            if validated_approval is not None
            else ''
        ),
        controls=plan.controls,
        required_controls=trace.required_controls,
        blockers=blockers,
        authorization=authorization,
    )
    digest = _governance_decision_body_digest(item)
    return validate_governance_decision(
        replace(item, decision_digest=digest),
        request=checked,
    )


def governance_decision_digest(
    decision: GovernanceDecision,
) -> str:
    checked = validate_governance_decision(decision)
    return checked.decision_digest


def validate_governance_decision(
    decision: GovernanceDecision,
    *,
    request: Mapping[str, Any] | GovernanceRequest | None = None,
) -> GovernanceDecision:
    if not isinstance(decision, GovernanceDecision):
        raise GovApiError('invalid_governance_decision')
    if decision.schema_version != GOVERNANCE_DECISION_SCHEMA_VERSION:
        raise GovApiError('unknown_governance_decision_schema_version')
    for value, reason_code in (
        (decision.decision_id, 'missing_governance_decision_id'),
        (decision.transaction_id, 'missing_governance_decision_transaction_id'),
        (decision.reason_code, 'missing_governance_decision_reason_code'),
    ):
        if not isinstance(value, str) or not value.strip():
            raise GovApiError(reason_code)
    if decision.status not in GOVERNANCE_DECISION_STATUSES:
        raise GovApiError('unknown_governance_decision_status')
    for digest, reason_code in (
        (decision.request_digest, 'invalid_governance_decision_request_digest'),
        (decision.policy_evaluation_digest, 'invalid_policy_evaluation_digest'),
        (decision.policy_verdict_digest, 'invalid_governance_policy_verdict_digest'),
        (decision.enforcement_plan_digest, 'invalid_governance_enforcement_plan_digest'),
        (decision.governance_trace_digest, 'invalid_governance_trace_digest'),
        (decision.scope_decision_digest, 'invalid_governance_scope_decision_digest'),
        (
            decision.capability_compatibility_digest,
            'invalid_governance_capability_compatibility_digest',
        ),
        (decision.decision_digest, 'invalid_governance_decision_digest'),
    ):
        require_sha256_digest(digest, reason_code)
    if decision.approval_attestation_digest:
        require_sha256_digest(
            decision.approval_attestation_digest,
            'invalid_governance_approval_attestation_digest',
        )
    if not isinstance(decision.controls, RuntimeControlProjection):
        raise GovApiError('invalid_governance_decision_controls')
    if decision.allowed:
        if decision.authorization is None:
            raise GovApiError('allowed_governance_decision_without_authorization')
        if decision.blockers:
            raise GovApiError('allowed_governance_decision_with_blockers')
    else:
        if decision.authorization is not None:
            raise GovApiError('non_allowed_governance_decision_with_authorization')
        if not decision.blockers:
            raise GovApiError('non_allowed_governance_decision_without_blockers')
    if decision.authorization is not None:
        _validate_authorization(decision.authorization)
    expected_digest = _governance_decision_body_digest(decision)
    if not compare_digest(expected_digest, decision.decision_digest):
        raise GovApiError('governance_decision_digest_mismatch')
    if request is not None:
        checked_request = validate_governance_request(request)
        _validate_decision_request_binding(decision, checked_request)
    return decision


def _policy_request_from_execution_facts(request: GovernanceRequest) -> PolicyRequest:
    policy_request = validate_policy_request(request.execution_facts)
    if policy_request.request_id != request.transaction_id:
        raise GovApiError('policy_request_id_mismatch')
    expected_subject = (
        f'governance:{request.operation_id}:{request.step_id}:{request.attempt_id}'
    )
    if policy_request.subject_ref != expected_subject:
        raise GovApiError('policy_request_subject_ref_mismatch')
    return policy_request


def _validate_policy_activation(
    request: GovernanceRequest,
    port: PolicyActivationPort,
    *,
    evaluated_at: datetime,
) -> datetime:
    current = validate_policy_activation_binding(
        port.current_binding(request.policy_pack.policy_id)
    )
    if current.policy_id != request.policy_pack.policy_id:
        raise GovApiError('policy_activation_id_mismatch')
    if current.policy_version != request.policy_pack.version:
        raise GovApiError('policy_activation_version_mismatch')
    if not compare_digest(current.policy_pack_digest, request.policy_pack_digest):
        raise GovApiError('policy_activation_digest_mismatch')
    if current.policy_epoch != request.policy_epoch:
        raise GovApiError('policy_epoch_drift')
    if request.policy_pack.schema_version == 'v1':
        if current.issuer_ref != request.policy_pack.issuer_ref:
            raise GovApiError('policy_activation_issuer_mismatch')
        declared_not_before = parse_aware_timestamp(
            request.policy_pack.not_before,
            'invalid_policy_not_before',
        )
        declared_expires_at = parse_aware_timestamp(
            request.policy_pack.expires_at,
            'invalid_policy_expires_at',
        )
        active_not_before = parse_aware_timestamp(
            current.not_before,
            'invalid_policy_activation_not_before',
        )
        active_expires_at = parse_aware_timestamp(
            current.expires_at,
            'invalid_policy_activation_expires_at',
        )
        if active_not_before < declared_not_before:
            raise GovApiError('policy_activation_not_before_mismatch')
        if active_expires_at > declared_expires_at:
            raise GovApiError('policy_activation_expires_at_mismatch')
    if current.status != 'active':
        reason_codes = {
            'superseded': 'policy_superseded',
            'revoked': 'policy_revoked',
            'expired': 'policy_expired',
        }
        raise GovApiError(reason_codes[current.status])
    not_before = parse_aware_timestamp(
        current.not_before,
        'invalid_policy_activation_not_before',
    )
    expires_at = parse_aware_timestamp(
        current.expires_at,
        'invalid_policy_activation_expires_at',
    )
    if evaluated_at < not_before:
        raise GovApiError('policy_not_yet_valid')
    if evaluated_at >= expires_at:
        raise GovApiError('policy_expired')
    return expires_at


def _validated_approval(
    request: GovernanceRequest,
    *,
    trust_policy: ApprovalTrustPolicy | None,
    revocation_port: ApprovalRevocationPort | None,
    signature_verifier: ApprovalSignatureVerificationPort | None,
    evaluated_at: datetime,
) -> ApprovalAttestation | None:
    if request.approval_attestation is None:
        return None
    if trust_policy is None:
        raise GovApiError('approval_trust_policy_required')
    if revocation_port is None:
        raise GovApiError('approval_revocation_port_required')
    checked = validate_approval_attestation(
        request.approval_attestation,
        request=request,
        trust_policy=trust_policy,
        revocation_port=revocation_port,
        now=evaluated_at,
    )
    if signature_verifier is None:
        raise GovApiError('approval_signature_verifier_required')
    digest = approval_attestation_digest(checked)
    if not signature_verifier.verify_approval_signature(
        checked,
        approval_digest=digest,
        trust_policy_id=trust_policy.policy_id,
    ):
        raise GovApiError('approval_signature_verification_failed')
    return checked


def _resolve_approval_requirement(
    verdict: PolicyVerdict,
    approval: ApprovalAttestation | None,
) -> PolicyVerdict:
    if verdict.decision != 'approval_required' or approval is None:
        return verdict
    digest = approval_attestation_digest(approval)
    metadata = dict(verdict.metadata)
    metadata['approval_attestation_digest'] = digest
    return validate_policy_verdict(
        replace(
            verdict,
            decision='allow_with_obligations',
            reason_code='approval_requirement_satisfied',
            blockers=(),
            evidence_refs=tuple(sorted(set(verdict.evidence_refs) | {digest})),
            metadata=metadata,
        )
    )


def _decision_outcome(
    *,
    initial_verdict: PolicyVerdict,
    plan: PolicyEnforcementPlan,
    scope_allowed: bool,
    scope_reason: str,
    capability_compatible: bool,
    capability_reason: str,
    approval_required: bool,
    approval_validated: bool,
) -> tuple[str, str, tuple[str, ...]]:
    blockers: list[str] = []
    if not plan.allowed:
        blockers.extend(plan.blockers or (plan.reason_code,))
    if not scope_allowed:
        blockers.append(scope_reason)
    if not capability_compatible:
        blockers.append(capability_reason)
    if approval_required and not approval_validated:
        blockers.append('approval_attestation_required')
    merged = tuple(dict.fromkeys(item for item in blockers if item))
    if initial_verdict.decision == 'deny' or (
        not plan.allowed and initial_verdict.decision != 'approval_required'
    ):
        return 'denied', plan.reason_code, merged
    if not scope_allowed:
        return 'denied', scope_reason, merged
    if not capability_compatible:
        return 'denied', capability_reason, merged
    if approval_required and not approval_validated:
        return 'approval_required', 'approval_attestation_required', merged
    if not plan.allowed:
        return 'denied', plan.reason_code, merged
    return 'allowed', 'all_governance_gates_passed', ()


def _authorization(
    request: GovernanceRequest,
    *,
    authorization_id: str,
    nonce: str,
    issued_at: datetime,
    expires_at: datetime | None,
    approval: ApprovalAttestation | None,
    policy_activation_expires_at: datetime,
) -> GovernanceAuthorization:
    if not isinstance(nonce, str) or not nonce.strip():
        raise GovApiError('authorization_nonce_required')
    if len(nonce.strip()) > 256:
        raise GovApiError('authorization_nonce_too_long')
    if expires_at is None:
        raise GovApiError('authorization_expiry_required')
    checked_expiry = _aware_utc(
        expires_at,
        'authorization_expiry_timezone_required',
    )
    if checked_expiry <= issued_at:
        raise GovApiError('authorization_expiry_not_after_issue')
    lifetime = (checked_expiry - issued_at).total_seconds()
    if lifetime > MAX_AUTHORIZATION_LIFETIME_SECONDS:
        raise GovApiError('authorization_lifetime_exceeded')
    if checked_expiry > policy_activation_expires_at:
        raise GovApiError('authorization_outlives_policy_activation')
    if approval is not None:
        approval_expiry = parse_aware_timestamp(
            approval.expires_at,
            'invalid_approval_expires_at',
        )
        if checked_expiry > approval_expiry:
            raise GovApiError('authorization_outlives_approval')
    item = GovernanceAuthorization(
        authorization_id=authorization_id,
        operation_id=request.operation_id,
        step_id=request.step_id,
        attempt_id=request.attempt_id,
        runtime_instance_id=request.runtime_instance_id,
        lease_id=request.lease_id,
        lease_epoch=request.lease_epoch,
        fencing_token_digest=request.fencing_token_digest,
        execution_spec_digest=request.execution_spec_digest,
        payload_digest=request.payload_digest,
        requested_scope_digest=request.requested_scope_digest,
        capability_inventory_digest=request.capability_inventory_digest,
        inventory_epoch=request.capability_inventory.inventory_epoch,
        policy_pack_digest=request.policy_pack_digest,
        policy_epoch=request.policy_epoch,
        issued_at=_timestamp(issued_at),
        expires_at=_timestamp(checked_expiry),
        nonce=nonce.strip(),
    )
    _validate_authorization(item)
    return item


def _validate_authorization(item: GovernanceAuthorization) -> None:
    if item.schema_version != GOVERNANCE_AUTHORIZATION_SCHEMA_VERSION:
        raise GovApiError('unknown_governance_authorization_schema_version')
    payload = item.as_dict()
    for key, reason_code in (
        ('authorization_id', 'missing_governance_authorization_id'),
        ('operation_id', 'missing_governance_authorization_operation_id'),
        ('step_id', 'missing_governance_authorization_step_id'),
        ('attempt_id', 'missing_governance_authorization_attempt_id'),
        ('runtime_instance_id', 'missing_governance_authorization_runtime_instance_id'),
        ('lease_id', 'missing_governance_authorization_lease_id'),
        ('nonce', 'authorization_nonce_required'),
    ):
        required_text(payload, key, reason_code)
    for digest, reason_code in (
        (item.fencing_token_digest, 'invalid_authorization_fencing_token_digest'),
        (item.execution_spec_digest, 'invalid_authorization_execution_spec_digest'),
        (item.payload_digest, 'invalid_authorization_payload_digest'),
        (item.requested_scope_digest, 'invalid_authorization_requested_scope_digest'),
        (
            item.capability_inventory_digest,
            'invalid_authorization_capability_inventory_digest',
        ),
        (item.policy_pack_digest, 'invalid_authorization_policy_pack_digest'),
    ):
        require_sha256_digest(digest, reason_code)
    for value, reason_code in (
        (item.lease_epoch, 'invalid_authorization_lease_epoch'),
        (item.inventory_epoch, 'invalid_authorization_inventory_epoch'),
        (item.policy_epoch, 'invalid_authorization_policy_epoch'),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise GovApiError(reason_code)
    if item.consume_once is not True:
        raise GovApiError('authorization_must_be_consume_once')
    issued_at = parse_aware_timestamp(item.issued_at, 'invalid_authorization_issued_at')
    expires_at = parse_aware_timestamp(item.expires_at, 'invalid_authorization_expires_at')
    if expires_at <= issued_at:
        raise GovApiError('authorization_expiry_not_after_issue')
    if (expires_at - issued_at).total_seconds() > MAX_AUTHORIZATION_LIFETIME_SECONDS:
        raise GovApiError('authorization_lifetime_exceeded')


def _validate_decision_request_binding(
    decision: GovernanceDecision,
    request: GovernanceRequest,
) -> None:
    if decision.transaction_id != request.transaction_id:
        raise GovApiError('governance_decision_transaction_id_mismatch')
    if not compare_digest(decision.request_digest, governance_request_digest(request)):
        raise GovApiError('governance_decision_request_digest_mismatch')
    authorization = decision.authorization
    if authorization is None:
        return
    for actual, expected, reason_code in (
        (authorization.operation_id, request.operation_id, 'authorization_operation_id_mismatch'),
        (authorization.step_id, request.step_id, 'authorization_step_id_mismatch'),
        (authorization.attempt_id, request.attempt_id, 'authorization_attempt_id_mismatch'),
        (
            authorization.runtime_instance_id,
            request.runtime_instance_id,
            'authorization_runtime_instance_id_mismatch',
        ),
        (authorization.lease_id, request.lease_id, 'authorization_lease_id_mismatch'),
        (authorization.lease_epoch, request.lease_epoch, 'authorization_lease_epoch_mismatch'),
        (
            authorization.fencing_token_digest,
            request.fencing_token_digest,
            'authorization_fencing_token_digest_mismatch',
        ),
        (
            authorization.execution_spec_digest,
            request.execution_spec_digest,
            'authorization_execution_spec_digest_mismatch',
        ),
        (authorization.payload_digest, request.payload_digest, 'authorization_payload_digest_mismatch'),
        (
            authorization.requested_scope_digest,
            request.requested_scope_digest,
            'authorization_requested_scope_digest_mismatch',
        ),
        (
            authorization.capability_inventory_digest,
            request.capability_inventory_digest,
            'authorization_capability_inventory_digest_mismatch',
        ),
        (
            authorization.inventory_epoch,
            request.capability_inventory.inventory_epoch,
            'authorization_inventory_epoch_mismatch',
        ),
        (
            authorization.policy_pack_digest,
            request.policy_pack_digest,
            'authorization_policy_pack_digest_mismatch',
        ),
        (authorization.policy_epoch, request.policy_epoch, 'authorization_policy_epoch_mismatch'),
    ):
        if actual != expected:
            raise GovApiError(reason_code)


def _governance_decision_body(item: GovernanceDecision) -> dict[str, Any]:
    return {
        'schema_version': item.schema_version,
        'decision_id': item.decision_id,
        'transaction_id': item.transaction_id,
        'request_digest': item.request_digest,
        'status': item.status,
        'allowed': item.allowed,
        'reason_code': item.reason_code,
        'policy_evaluation_digest': item.policy_evaluation_digest,
        'policy_verdict_digest': item.policy_verdict_digest,
        'enforcement_plan_digest': item.enforcement_plan_digest,
        'governance_trace_digest': item.governance_trace_digest,
        'scope_decision_digest': item.scope_decision_digest,
        'capability_compatibility_digest': item.capability_compatibility_digest,
        'approval_attestation_digest': item.approval_attestation_digest,
        'controls': item.controls.as_dict(),
        'required_controls': list(item.required_controls),
        'blockers': list(item.blockers),
        'authorization': (
            item.authorization.as_dict() if item.authorization is not None else None
        ),
    }


def _governance_decision_body_digest(item: GovernanceDecision) -> str:
    return govengine_record_digest(
        _governance_decision_body(item),
        record_type='govengine.governance_decision.GovernanceDecision',
        schema_version=GOVERNANCE_DECISION_SCHEMA_VERSION,
    )


def _aware_utc(value: datetime, reason_code: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise GovApiError(reason_code)
    return value.astimezone(timezone.utc)


def _timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
