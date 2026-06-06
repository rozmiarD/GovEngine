from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Mapping

from govengine.api import GovApiError, require_mapping


ADMISSION_OUTCOMES = ('allowed', 'denied', 'deferred', 'dry_run_only', 'record_only')
SUBJECT_KINDS = ('task', 'run', 'host', 'artifact', 'profile', 'operator_action', 'generic')
POLICY_DECISIONS = ('allow', 'deny', 'defer', 'require_approval', 'dry_run_only', 'record_only')
APPROVAL_STATES = ('not_required', 'requested', 'approved', 'denied', 'expired', 'cancelled')
AUDIT_RECORD_TYPES = ('admission_decision', 'policy_decision', 'approval_request', 'operator_review')
RUNTIME_ADMISSION_STATUSES = ('allowed', 'blocked', 'dry_run_only', 'needs_review', 'record_only')
PREPARED_EXECUTION_CONTRACT_STATUSES = ('prepared', 'passed', 'ok', 'allowed')
RECEIPT_OBLIGATION_STATUSES = ('required', 'passed', 'ok')
POLICY_RUNTIME_BLOCKERS = {
    'deny': 'policy_denied',
    'denied': 'policy_denied',
    'defer': 'policy_deferred',
    'deferred': 'policy_deferred',
    'require_approval': 'policy_requires_approval',
    'dry_run_only': 'policy_dry_run_only',
    'record_only': 'policy_record_only',
}
POLICY_RUNTIME_ACTIONS = {
    'policy_denied': 'revise_request_or_policy',
    'policy_deferred': 'resolve_policy_deferral',
    'policy_requires_approval': 'obtain_operator_approval',
    'policy_dry_run_only': 'use_dry_run_only_path',
    'policy_record_only': 'record_without_execution',
    'unknown_policy_decision': 'obtain_valid_policy_decision',
    'missing_or_invalid_policy_decision': 'obtain_policy_decision',
}
TICKET_RUNTIME_BLOCKERS = {
    'invalid': 'invalid_execution_ticket',
    'malformed': 'invalid_execution_ticket',
    'denied': 'execution_ticket_not_approved',
    'deny': 'execution_ticket_not_approved',
    'rejected': 'execution_ticket_not_approved',
    'unapproved': 'execution_ticket_not_approved',
    'pending': 'execution_ticket_not_approved',
    'mismatch': 'execution_ticket_mismatch',
    'mismatched': 'execution_ticket_mismatch',
    'scope_mismatch': 'execution_ticket_mismatch',
    'digest_mismatch': 'execution_ticket_mismatch',
    'stale': 'execution_ticket_stale',
    'expired': 'execution_ticket_stale',
    'failed': 'execution_ticket_failed',
    'failure': 'execution_ticket_failed',
    'error': 'execution_ticket_failed',
}
TICKET_RUNTIME_ACTIONS = {
    'missing_or_invalid_execution_ticket': 'approve_execution_ticket',
    'invalid_execution_ticket': 'repair_or_reissue_execution_ticket',
    'execution_ticket_not_approved': 'approve_execution_ticket',
    'execution_ticket_mismatch': 'reconcile_execution_ticket_scope',
    'execution_ticket_stale': 'refresh_execution_ticket',
    'execution_ticket_failed': 'revalidate_execution_ticket',
    'unknown_execution_ticket_status': 'obtain_valid_execution_ticket',
}

FORBIDDEN_ADMISSION_METADATA_KEYS = (
    'raw_intent',
    'raw_payload',
    'raw_evidence',
    'raw_output',
    'prompt',
    'credential',
    'credentials',
    'secret',
    'token',
    'password',
    'api_key',
    'command',
    'commands',
    'stdout',
    'stderr',
    'subprocess',
    'shell',
    'live_execution',
    'live_backend',
    'carrier_payload',
    'transport_payload',
    'runtime_storage',
    'storage_path',
    'scheduler',
    'schedule',
    'target',
    'target_url',
    'url',
)


@dataclass(frozen=True)
class GovAdmissionDecision:
    """Neutral admission result. Host runtimes own the policy meaning."""

    decision_id: str
    subject_ref: str
    subject_kind: str = 'task'
    outcome: str = 'allowed'
    allowed: bool = True
    reason_code: str = 'allowed'
    detail: str = ''
    blockers: tuple[str, ...] = field(default_factory=tuple)
    context: Mapping[str, Any] = field(default_factory=dict)
    signal: Mapping[str, Any] = field(default_factory=dict)
    explainability: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> 'GovAdmissionDecision':
        raw = require_mapping(value, reason_code='invalid_admission_decision')
        decision_id = str(raw.get('decision_id') or raw.get('id') or '').strip()
        if not decision_id:
            raise GovApiError('missing_admission_decision_id')
        subject_ref = str(raw.get('subject_ref') or '').strip()
        if not subject_ref:
            raise GovApiError('missing_admission_subject_ref')
        outcome = _enum(raw.get('outcome'), ADMISSION_OUTCOMES, 'allowed')
        item = cls(
            decision_id=decision_id,
            subject_ref=subject_ref,
            subject_kind=_enum(raw.get('subject_kind'), SUBJECT_KINDS, 'task'),
            outcome=outcome,
            allowed=bool(raw.get('allowed', outcome == 'allowed')),
            reason_code=str(raw.get('reason_code') or outcome).strip() or outcome,
            detail=str(raw.get('detail') or '').strip(),
            blockers=_tuple(raw.get('blockers') or ()),
            context=_metadata(raw.get('context')),
            signal=_metadata(raw.get('signal')),
            explainability=_metadata(raw.get('explainability')),
            metadata=_metadata(raw.get('metadata')),
        )
        validate_admission_decision(item)
        return item

    def as_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out['blockers'] = list(self.blockers)
        out['context'] = dict(self.context)
        out['signal'] = dict(self.signal)
        out['explainability'] = dict(self.explainability)
        out['metadata'] = dict(self.metadata)
        return out


@dataclass(frozen=True)
class GovPolicyDecision:
    """Policy decision envelope without embedding domain policy semantics."""

    policy_id: str
    subject_ref: str
    subject_kind: str = 'task'
    decision: str = 'allow'
    reason_code: str = 'allowed'
    controls: tuple[str, ...] = field(default_factory=tuple)
    blockers: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> 'GovPolicyDecision':
        raw = require_mapping(value, reason_code='invalid_policy_decision')
        policy_id = str(raw.get('policy_id') or raw.get('id') or '').strip()
        if not policy_id:
            raise GovApiError('missing_policy_decision_id')
        subject_ref = str(raw.get('subject_ref') or '').strip()
        if not subject_ref:
            raise GovApiError('missing_policy_subject_ref')
        decision = _enum(raw.get('decision'), POLICY_DECISIONS, 'allow')
        item = cls(
            policy_id=policy_id,
            subject_ref=subject_ref,
            subject_kind=_enum(raw.get('subject_kind'), SUBJECT_KINDS, 'task'),
            decision=decision,
            reason_code=str(raw.get('reason_code') or decision).strip() or decision,
            controls=_tuple(raw.get('controls') or ()),
            blockers=_tuple(raw.get('blockers') or ()),
            metadata=_metadata(raw.get('metadata')),
        )
        validate_policy_decision(item)
        return item

    def as_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out['controls'] = list(self.controls)
        out['blockers'] = list(self.blockers)
        out['metadata'] = dict(self.metadata)
        return out


@dataclass(frozen=True)
class GovApprovalRequest:
    """Operator approval request shape. Approval workflow remains host-owned."""

    request_id: str
    subject_ref: str
    subject_kind: str = 'task'
    state: str = 'requested'
    reason_code: str = 'operator_approval_required'
    requested_by: str = ''
    approver_ref: str = ''
    expires_at: str = ''
    policy_refs: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> 'GovApprovalRequest':
        raw = require_mapping(value, reason_code='invalid_approval_request')
        request_id = str(raw.get('request_id') or raw.get('id') or '').strip()
        if not request_id:
            raise GovApiError('missing_approval_request_id')
        subject_ref = str(raw.get('subject_ref') or '').strip()
        if not subject_ref:
            raise GovApiError('missing_approval_subject_ref')
        item = cls(
            request_id=request_id,
            subject_ref=subject_ref,
            subject_kind=_enum(raw.get('subject_kind'), SUBJECT_KINDS, 'task'),
            state=_enum(raw.get('state'), APPROVAL_STATES, 'requested'),
            reason_code=str(raw.get('reason_code') or 'operator_approval_required').strip() or 'operator_approval_required',
            requested_by=str(raw.get('requested_by') or '').strip(),
            approver_ref=str(raw.get('approver_ref') or '').strip(),
            expires_at=str(raw.get('expires_at') or '').strip(),
            policy_refs=_tuple(raw.get('policy_refs') or ()),
            metadata=_metadata(raw.get('metadata')),
        )
        validate_approval_request(item)
        return item

    def as_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out['policy_refs'] = list(self.policy_refs)
        out['metadata'] = dict(self.metadata)
        return out


@dataclass(frozen=True)
class GovAuditRecord:
    """Append-only audit record shape. Storage and retention are host-owned."""

    record_id: str
    record_type: str
    subject_ref: str
    subject_kind: str = 'task'
    decision_ref: str = ''
    reason_code: str = 'recorded'
    event_refs: tuple[str, ...] = field(default_factory=tuple)
    recorded_at: str = ''
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> 'GovAuditRecord':
        raw = require_mapping(value, reason_code='invalid_audit_record')
        record_id = str(raw.get('record_id') or raw.get('id') or '').strip()
        if not record_id:
            raise GovApiError('missing_audit_record_id')
        subject_ref = str(raw.get('subject_ref') or '').strip()
        if not subject_ref:
            raise GovApiError('missing_audit_subject_ref')
        item = cls(
            record_id=record_id,
            record_type=_enum(raw.get('record_type'), AUDIT_RECORD_TYPES, 'admission_decision'),
            subject_ref=subject_ref,
            subject_kind=_enum(raw.get('subject_kind'), SUBJECT_KINDS, 'task'),
            decision_ref=str(raw.get('decision_ref') or '').strip(),
            reason_code=str(raw.get('reason_code') or 'recorded').strip() or 'recorded',
            event_refs=_tuple(raw.get('event_refs') or ()),
            recorded_at=str(raw.get('recorded_at') or '').strip(),
            metadata=_metadata(raw.get('metadata')),
        )
        validate_audit_record(item)
        return item

    def as_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out['event_refs'] = list(self.event_refs)
        out['metadata'] = dict(self.metadata)
        return out


@dataclass(frozen=True)
class RuntimeAdmissionResult:
    """Canonical runtime admission record.

    This is the bounded machine-readable decision surface for the governed
    runtime MVP. It composes gate summaries, not raw execution authority. Hosts
    still own domain policy meaning, operator approval, live backends, raw
    evidence storage, and production identity/key management.
    """

    admission_id: str
    subject_ref: str
    status: str = 'blocked'
    allowed: bool = False
    reason_code: str = 'blocked'
    blockers: tuple[str, ...] = field(default_factory=tuple)
    required_next_actions: tuple[str, ...] = field(default_factory=tuple)
    prepared_execution_contract: Mapping[str, Any] = field(default_factory=dict)
    policy_decision: Mapping[str, Any] = field(default_factory=dict)
    execution_ticket: Mapping[str, Any] = field(default_factory=dict)
    trust_decision: Mapping[str, Any] = field(default_factory=dict)
    sclite_guarded_strict: Mapping[str, Any] = field(default_factory=dict)
    replay_freshness: Mapping[str, Any] = field(default_factory=dict)
    runner_profile: Mapping[str, Any] = field(default_factory=dict)
    receipt_obligation: Mapping[str, Any] = field(default_factory=dict)
    artifact_refs: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> 'RuntimeAdmissionResult':
        raw = require_mapping(value, reason_code='invalid_runtime_admission_result')
        admission_id = str(raw.get('admission_id') or raw.get('id') or '').strip()
        if not admission_id:
            raise GovApiError('missing_runtime_admission_id')
        subject_ref = str(raw.get('subject_ref') or '').strip()
        if not subject_ref:
            raise GovApiError('missing_runtime_admission_subject_ref')
        status = _strict_enum(raw.get('status'), RUNTIME_ADMISSION_STATUSES, 'runtime_admission_status')
        item = cls(
            admission_id=admission_id,
            subject_ref=subject_ref,
            status=status,
            allowed=_bool_value(raw.get('allowed'), default=status == 'allowed'),
            reason_code=str(raw.get('reason_code') or status).strip() or status,
            blockers=_tuple(raw.get('blockers') or ()),
            required_next_actions=_tuple(raw.get('required_next_actions') or ()),
            prepared_execution_contract=_metadata(raw.get('prepared_execution_contract')),
            policy_decision=_metadata(raw.get('policy_decision')),
            execution_ticket=_metadata(raw.get('execution_ticket')),
            trust_decision=_metadata(raw.get('trust_decision')),
            sclite_guarded_strict=_metadata(raw.get('sclite_guarded_strict')),
            replay_freshness=_metadata(raw.get('replay_freshness')),
            runner_profile=_metadata(raw.get('runner_profile')),
            receipt_obligation=_metadata(raw.get('receipt_obligation')),
            artifact_refs=_metadata(raw.get('artifact_refs')),
            metadata=_metadata(raw.get('metadata')),
        )
        validate_runtime_admission_result(item)
        return item

    def as_dict(self) -> dict[str, Any]:
        return {
            'admission_id': self.admission_id,
            'subject_ref': self.subject_ref,
            'status': self.status,
            'allowed': self.allowed,
            'reason_code': self.reason_code,
            'blockers': list(self.blockers),
            'required_next_actions': list(self.required_next_actions),
            'prepared_execution_contract': dict(self.prepared_execution_contract),
            'policy_decision': dict(self.policy_decision),
            'execution_ticket': dict(self.execution_ticket),
            'trust_decision': dict(self.trust_decision),
            'sclite_guarded_strict': dict(self.sclite_guarded_strict),
            'replay_freshness': dict(self.replay_freshness),
            'runner_profile': dict(self.runner_profile),
            'receipt_obligation': dict(self.receipt_obligation),
            'artifact_refs': dict(self.artifact_refs),
            'metadata': dict(self.metadata),
        }


def validate_admission_decision(value: Mapping[str, Any] | GovAdmissionDecision) -> GovAdmissionDecision:
    item = value if isinstance(value, GovAdmissionDecision) else GovAdmissionDecision.from_mapping(value)
    if item.subject_kind not in SUBJECT_KINDS:
        raise GovApiError(f'unknown_admission_subject_kind:{item.subject_kind}')
    if item.outcome not in ADMISSION_OUTCOMES:
        raise GovApiError(f'unknown_admission_outcome:{item.outcome}')
    if item.allowed and item.outcome in {'denied', 'deferred'}:
        raise GovApiError('admission_allowed_outcome_mismatch')
    if not item.allowed and item.outcome == 'allowed':
        raise GovApiError('admission_denied_outcome_mismatch')
    _reject_forbidden_metadata(item.context)
    _reject_forbidden_metadata(item.signal)
    _reject_forbidden_metadata(item.explainability)
    _reject_forbidden_metadata(item.metadata)
    return item


def validate_policy_decision(value: Mapping[str, Any] | GovPolicyDecision) -> GovPolicyDecision:
    item = value if isinstance(value, GovPolicyDecision) else GovPolicyDecision.from_mapping(value)
    if item.subject_kind not in SUBJECT_KINDS:
        raise GovApiError(f'unknown_policy_subject_kind:{item.subject_kind}')
    if item.decision not in POLICY_DECISIONS:
        raise GovApiError(f'unknown_policy_decision:{item.decision}')
    _reject_forbidden_metadata(item.metadata)
    return item


def validate_approval_request(value: Mapping[str, Any] | GovApprovalRequest) -> GovApprovalRequest:
    item = value if isinstance(value, GovApprovalRequest) else GovApprovalRequest.from_mapping(value)
    if item.subject_kind not in SUBJECT_KINDS:
        raise GovApiError(f'unknown_approval_subject_kind:{item.subject_kind}')
    if item.state not in APPROVAL_STATES:
        raise GovApiError(f'unknown_approval_state:{item.state}')
    _reject_forbidden_metadata(item.metadata)
    return item


def validate_audit_record(value: Mapping[str, Any] | GovAuditRecord) -> GovAuditRecord:
    item = value if isinstance(value, GovAuditRecord) else GovAuditRecord.from_mapping(value)
    if item.subject_kind not in SUBJECT_KINDS:
        raise GovApiError(f'unknown_audit_subject_kind:{item.subject_kind}')
    if item.record_type not in AUDIT_RECORD_TYPES:
        raise GovApiError(f'unknown_audit_record_type:{item.record_type}')
    _reject_forbidden_metadata(item.metadata)
    return item


def validate_runtime_admission_result(value: Mapping[str, Any] | RuntimeAdmissionResult) -> RuntimeAdmissionResult:
    item = value if isinstance(value, RuntimeAdmissionResult) else RuntimeAdmissionResult.from_mapping(value)
    if item.status not in RUNTIME_ADMISSION_STATUSES:
        raise GovApiError(f'unknown_runtime_admission_status:{item.status}')
    if item.allowed and item.status != 'allowed':
        raise GovApiError('runtime_admission_allowed_status_mismatch')
    if not item.allowed and item.status == 'allowed':
        raise GovApiError('runtime_admission_blocked_status_mismatch')
    if item.allowed and (item.blockers or item.required_next_actions):
        raise GovApiError('runtime_admission_allowed_with_blockers')
    if item.status != 'allowed' and not (item.blockers or item.required_next_actions):
        raise GovApiError('runtime_admission_blocked_without_evidence')
    for payload in (
        item.prepared_execution_contract,
        item.policy_decision,
        item.execution_ticket,
        item.trust_decision,
        item.sclite_guarded_strict,
        item.replay_freshness,
        item.runner_profile,
        item.receipt_obligation,
        item.artifact_refs,
        item.metadata,
    ):
        _reject_forbidden_metadata(payload)
    return item


def compose_runtime_admission_result(
    *,
    admission_id: str,
    subject_ref: str,
    prepared_execution_contract: Mapping[str, Any] | Any | None,
    policy_decision: Mapping[str, Any] | Any | None,
    execution_ticket: Mapping[str, Any] | Any | None,
    trust_decision: Mapping[str, Any] | Any | None,
    runner_profile: Mapping[str, Any] | Any | None,
    receipt_obligation: Mapping[str, Any] | Any | None,
    sclite_guarded_strict: Mapping[str, Any] | Any | None = None,
    replay_freshness: Mapping[str, Any] | Any | None = None,
    runtime_consumable: bool = False,
    live: bool = False,
    artifact_refs: Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> RuntimeAdmissionResult:
    """Compose bounded gate summaries into the canonical runtime admission.

    The helper consumes decisions produced by existing GovEngine/SCLite-aware
    gates. It does not validate SCLite tickets, verify signatures, record
    replay state, store raw evidence, or execute live work.
    """

    from govengine.execution.gate import ExecutionGate, ExecutionGateInput, RunnerProfile

    prepared_summary = _runtime_signal(prepared_execution_contract)
    policy_summary = _runtime_signal(policy_decision)
    ticket_summary = _runtime_signal(execution_ticket)
    trust_summary = _runtime_signal(trust_decision)
    runner_summary = _runtime_signal(runner_profile)
    receipt_summary = _runtime_signal(receipt_obligation)
    guarded_summary = _runtime_signal(sclite_guarded_strict)
    replay_summary = _runtime_signal(replay_freshness)

    has_prepared_contract = not _explicit_false(prepared_summary, 'allowed') and _status_in(
        _signal_status(prepared_summary, ('status', 'contract_status')),
        PREPARED_EXECUTION_CONTRACT_STATUSES,
    )
    policy_status = _policy_signal_status(policy_summary)
    ticket_status = _ticket_signal_status(ticket_summary)
    trust_status = _trust_signal_status(trust_summary)
    guarded_status = _signal_status(guarded_summary, ('verification_status', 'guarded_status', 'status'))
    replay_status = _signal_status(replay_summary, ('replay_status', 'status')) or _signal_status(guarded_summary, ('replay_status',))

    runner = RunnerProfile(
        name=str(runner_summary.get('name') or runner_summary.get('profile') or '').strip() or 'missing',
        allowed=_bool_value(runner_summary.get('allowed'), default=False),
        live_backend_enabled=_bool_value(runner_summary.get('live_backend_enabled'), default=False),
        metadata=_metadata(runner_summary.get('metadata')),
    )
    gate_input = ExecutionGateInput(
        has_prepared_execution_contract=has_prepared_contract,
        policy_decision_status=policy_status or 'missing',
        execution_ticket_status=ticket_status or 'missing',
        trust_decision_status=trust_status or 'missing',
        runner_profile=runner,
        runtime_consumable_bundle=bool(runtime_consumable),
        guarded_bundle_status=guarded_status or 'missing',
        replay_status=replay_status or 'missing',
    )
    gate_decision = ExecutionGate().evaluate(gate_input, live=live)
    blockers = list(gate_decision.blockers)
    required_next_actions = list(gate_decision.next_actions)
    policy_blocker = _policy_runtime_blocker(policy_status)
    if policy_blocker:
        blockers = _replace_or_append(blockers, 'missing_or_invalid_policy_decision', policy_blocker)
        required_next_actions = _replace_or_append(
            required_next_actions,
            'obtain_policy_decision',
            POLICY_RUNTIME_ACTIONS[policy_blocker],
        )
    ticket_blocker = _ticket_runtime_blocker(ticket_status)
    if ticket_blocker:
        blockers = _replace_or_append(blockers, 'missing_or_invalid_execution_ticket', ticket_blocker)
        required_next_actions = _replace_or_append(
            required_next_actions,
            'approve_execution_ticket',
            TICKET_RUNTIME_ACTIONS[ticket_blocker],
        )

    if not _receipt_obligation_required(receipt_summary):
        blockers.append('receipt_obligation_required')
        required_next_actions.append('require_runner_receipt_obligation')

    blockers_tuple = _dedupe(blockers)
    actions_tuple = _dedupe(required_next_actions)
    allowed = gate_decision.allowed and not blockers_tuple
    reason_code = 'all_required_gates_passed' if allowed else policy_blocker or ticket_blocker or (
        gate_decision.reason_code if not gate_decision.allowed else blockers_tuple[0]
    )
    status = 'allowed' if allowed else _policy_runtime_status(policy_status)

    return validate_runtime_admission_result(RuntimeAdmissionResult(
        admission_id=admission_id,
        subject_ref=subject_ref,
        status=status,
        allowed=allowed,
        reason_code=reason_code,
        blockers=blockers_tuple,
        required_next_actions=actions_tuple,
        prepared_execution_contract=prepared_summary,
        policy_decision=policy_summary,
        execution_ticket=ticket_summary,
        trust_decision=trust_summary,
        sclite_guarded_strict=guarded_summary,
        replay_freshness=replay_summary,
        runner_profile=runner.as_dict(),
        receipt_obligation=receipt_summary,
        artifact_refs=_metadata(artifact_refs),
        metadata=_metadata(metadata),
    ))


def admission_decision_from_host_gate(
    *,
    decision_id: str,
    subject_ref: str,
    subject_kind: str = 'task',
    allowed: bool,
    reason_code: str = '',
    detail: str = '',
    blockers: Iterable[Any] = (),
    context: Mapping[str, Any] | None = None,
    signal: Mapping[str, Any] | None = None,
    explainability: Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> GovAdmissionDecision:
    outcome = 'allowed' if allowed else 'denied'
    return validate_admission_decision(GovAdmissionDecision(
        decision_id=decision_id,
        subject_ref=subject_ref,
        subject_kind=subject_kind,
        outcome=outcome,
        allowed=bool(allowed),
        reason_code=reason_code or outcome,
        detail=detail,
        blockers=_tuple(blockers),
        context=_metadata(context),
        signal=_metadata(signal),
        explainability=_metadata(explainability),
        metadata=_metadata(metadata),
    ))


def _enum(value: Any, allowed: tuple[str, ...], default: str) -> str:
    normalized = str(value or '').strip().lower() or default
    return normalized if normalized in allowed else default


def _strict_enum(value: Any, allowed: tuple[str, ...], field_name: str) -> str:
    normalized = str(value or '').strip().lower()
    if normalized not in allowed:
        raise GovApiError(f'unknown_{field_name}:{normalized or "missing"}')
    return normalized


def _bool_value(value: Any, *, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {'true', '1', 'yes', 'y'}:
            return True
        if normalized in {'false', '0', 'no', 'n'}:
            return False
        raise GovApiError(f'invalid_boolean:{normalized or "missing"}')
    return bool(value)


def _runtime_signal(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return _metadata(value)
    as_dict = getattr(value, 'as_dict', None)
    if callable(as_dict):
        payload = as_dict()
        if isinstance(payload, Mapping):
            return _metadata(payload)
    raise GovApiError('invalid_runtime_admission_signal')


def _signal_status(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = payload.get(key)
        if value is not None:
            return str(value).strip().lower()
    return ''


def _policy_signal_status(payload: Mapping[str, Any]) -> str:
    if not payload:
        return 'missing'
    if 'allowed' in payload:
        return 'allowed' if _bool_value(payload.get('allowed'), default=False) else 'denied'
    return _signal_status(payload, ('decision', 'status', 'outcome', 'policy_decision_status')) or 'unknown'


def _ticket_signal_status(payload: Mapping[str, Any]) -> str:
    if not payload:
        return 'missing'
    if 'allowed' in payload and not _bool_value(payload.get('allowed'), default=False):
        return 'denied'
    status = _signal_status(payload, ('status', 'approval_status', 'ticket_status'))
    approval = payload.get('approval') if isinstance(payload.get('approval'), Mapping) else {}
    return status or _signal_status(approval, ('status',)) or 'unknown'


def _trust_signal_status(payload: Mapping[str, Any]) -> str:
    if not payload:
        return 'missing'
    if 'trusted' in payload:
        return 'trusted' if _bool_value(payload.get('trusted'), default=False) else 'denied'
    return _signal_status(payload, ('trust_status', 'status', 'verification_status')) or 'unknown'


def _status_in(value: str, allowed: tuple[str, ...]) -> bool:
    return value in allowed


def _policy_runtime_blocker(policy_status: str) -> str:
    if policy_status in {'allow', 'allowed', 'passed', 'ok'}:
        return ''
    if policy_status == 'missing':
        return 'missing_or_invalid_policy_decision'
    return POLICY_RUNTIME_BLOCKERS.get(policy_status, 'unknown_policy_decision')


def _policy_runtime_status(policy_status: str) -> str:
    if policy_status == 'dry_run_only':
        return 'dry_run_only'
    if policy_status == 'record_only':
        return 'record_only'
    if policy_status in {'defer', 'deferred', 'require_approval'}:
        return 'needs_review'
    return 'blocked'


def _ticket_runtime_blocker(ticket_status: str) -> str:
    if ticket_status in {'approve', 'approved', 'approved_for_dry_run', 'passed', 'ok'}:
        return ''
    if ticket_status == 'missing':
        return 'missing_or_invalid_execution_ticket'
    return TICKET_RUNTIME_BLOCKERS.get(ticket_status, 'unknown_execution_ticket_status')


def _replace_or_append(values: Iterable[Any], old: str, new: str) -> list[str]:
    out: list[str] = []
    replaced = False
    for value in values:
        item = str(value).strip()
        if item == old:
            out.append(new)
            replaced = True
        else:
            out.append(item)
    if not replaced:
        out.append(new)
    return out


def _explicit_false(payload: Mapping[str, Any], key: str) -> bool:
    return key in payload and not _bool_value(payload.get(key), default=False)


def _receipt_obligation_required(payload: Mapping[str, Any]) -> bool:
    if not payload:
        return False
    if _bool_value(payload.get('required'), default=False):
        return True
    return _status_in(_signal_status(payload, ('status', 'obligation_status')), RECEIPT_OBLIGATION_STATUSES)


def _dedupe(values: Iterable[Any]) -> tuple[str, ...]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        item = str(value).strip()
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return tuple(out)


def _tuple(values: Iterable[Any]) -> tuple[str, ...]:
    if isinstance(values, str):
        return (values,)
    try:
        return tuple(str(value) for value in values)
    except TypeError as exc:
        raise GovApiError('invalid_admission_sequence') from exc


def _metadata(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise GovApiError('invalid_admission_metadata')
    data = _json_safe_mapping(value)
    _reject_forbidden_metadata(data)
    return data


def _json_safe_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key): _json_safe_value(item) for key, item in value.items()}


def _json_safe_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _json_safe_mapping(value)
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_safe_value(item) for item in value]
    return value


def _reject_forbidden_metadata(value: Mapping[str, Any]) -> None:
    reason = _find_forbidden_key(value)
    if reason:
        raise GovApiError(f'forbidden_admission_metadata:{reason}')


def _find_forbidden_key(value: Any) -> str:
    if isinstance(value, Mapping):
        forbidden = set(FORBIDDEN_ADMISSION_METADATA_KEYS)
        for key, item in value.items():
            normalized = str(key).lower()
            if normalized in forbidden:
                return normalized
            nested = _find_forbidden_key(item)
            if nested:
                return nested
    elif isinstance(value, (list, tuple, set, frozenset)):
        for item in value:
            nested = _find_forbidden_key(item)
            if nested:
                return nested
    return ''
