from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Mapping

from govengine.api import GovApiError, require_mapping


ADMISSION_OUTCOMES = ('allowed', 'denied', 'deferred', 'dry_run_only', 'record_only')
SUBJECT_KINDS = ('task', 'run', 'host', 'artifact', 'profile', 'operator_action', 'generic')
POLICY_DECISIONS = ('allow', 'deny', 'defer', 'require_approval', 'dry_run_only', 'record_only')
APPROVAL_STATES = ('not_required', 'requested', 'approved', 'denied', 'expired', 'cancelled')
AUDIT_RECORD_TYPES = ('admission_decision', 'policy_decision', 'approval_request', 'operator_review')

FORBIDDEN_ADMISSION_METADATA_KEYS = (
    'raw_intent',
    'prompt',
    'credential',
    'credentials',
    'secret',
    'token',
    'password',
    'api_key',
    'command',
    'commands',
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
