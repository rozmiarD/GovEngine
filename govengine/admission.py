from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Protocol

from govengine._json_boundary import bounded_json_copy
from govengine.api import GovApiError, require_mapping


ADMISSION_OUTCOMES = ('allowed', 'denied', 'deferred', 'dry_run_only', 'record_only')
SUBJECT_KINDS = ('task', 'run', 'host', 'artifact', 'profile', 'operator_action', 'generic')
POLICY_DECISIONS = ('allow', 'deny', 'defer', 'require_approval', 'dry_run_only', 'record_only')
APPROVAL_STATES = ('not_required', 'requested', 'approved', 'denied', 'expired', 'cancelled')
AUDIT_RECORD_TYPES = ('admission_decision', 'policy_decision', 'approval_request', 'operator_review')
AUDIT_LEDGER_APPEND_STATUSES = ('appended', 'rejected')
AUDIT_LEDGER_VERIFY_STATUSES = ('verified', 'failed', 'empty')
RUNTIME_ADMISSION_STATUSES = ('allowed', 'blocked', 'dry_run_only', 'needs_review', 'record_only')
RUNTIME_ADMISSION_SCHEMA_VERSION = 'v0.1'
AUDIT_RECORD_SCHEMA_VERSION = 'v0.1'
AUDIT_LEDGER_ENTRY_SCHEMA_VERSION = 'v0.1'
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
TRUST_RUNTIME_BLOCKERS = {
    'denied': 'trust_decision_denied',
    'deny': 'trust_decision_denied',
    'untrusted': 'trust_decision_denied',
    'not_trusted': 'trust_decision_denied',
    'trust_status_not_allowed': 'trust_decision_denied',
    'failed': 'trust_verification_failed',
    'failure': 'trust_verification_failed',
    'error': 'trust_verification_failed',
    'signature_value_mismatch': 'trust_verification_failed',
    'unsupported_signature_mode': 'trust_verification_failed',
    'signature_digest_mismatch': 'signature_digest_mismatch',
    'digest_mismatch': 'signature_digest_mismatch',
    'signer_not_allowed': 'trust_signer_not_allowed',
    'unknown_signer': 'trust_signer_not_allowed',
    'wrong_signer': 'trust_signer_not_allowed',
    'wrong_key': 'trust_verification_failed',
}
TRUST_RUNTIME_ACTIONS = {
    'missing_or_invalid_trust_decision': 'verify_trust_decision',
    'trust_decision_denied': 'obtain_trusted_verification',
    'trust_verification_failed': 'rerun_trust_verification',
    'signature_digest_mismatch': 'rebind_or_reissue_signature',
    'trust_signer_not_allowed': 'use_allowed_signer_or_update_trust_policy',
    'unknown_trust_decision_status': 'obtain_valid_trust_decision',
}
RUNNER_RUNTIME_ACTIONS = {
    'missing_runner_profile': 'select_allowed_runner_profile',
    'runner_profile_not_allowed': 'select_allowed_runner_profile',
    'live_backend_disabled': 'use_dry_run_or_select_host_enabled_live_profile',
}
ADMISSION_ARTIFACT_INPUTS = (
    'prepared_execution_contract',
    'policy_decision',
    'execution_ticket',
    'trust_decision',
    'sclite_guarded_strict',
    'replay_freshness',
    'runner_profile',
    'receipt_obligation',
)
ADMISSION_REF_KEYS = (
    'admission_id',
    'artifact_id',
    'artifact_ref',
    'chain_id',
    'decision_id',
    'id',
    'path',
    'policy_id',
    'profile',
    'receipt_id',
    'ref',
    'request_id',
    'runner_profile',
    'ticket_id',
    'verifier_id',
)
ADMISSION_DIGEST_KEYS = (
    'admission_digest',
    'artifact_digest',
    'binds_digest',
    'digest',
    'root_chain_digest',
    'sha256',
    'ticket_digest',
)

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
        outcome = _enum(raw.get('outcome'), ADMISSION_OUTCOMES, 'allowed', 'admission_outcome')
        item = cls(
            decision_id=decision_id,
            subject_ref=subject_ref,
            subject_kind=_enum(raw.get('subject_kind'), SUBJECT_KINDS, 'task', 'admission_subject_kind'),
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
        decision = _enum(raw.get('decision'), POLICY_DECISIONS, 'allow', 'policy_decision')
        item = cls(
            policy_id=policy_id,
            subject_ref=subject_ref,
            subject_kind=_enum(raw.get('subject_kind'), SUBJECT_KINDS, 'task', 'policy_subject_kind'),
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
            subject_kind=_enum(raw.get('subject_kind'), SUBJECT_KINDS, 'task', 'approval_subject_kind'),
            state=_enum(raw.get('state'), APPROVAL_STATES, 'requested', 'approval_state'),
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
    schema_version: str = AUDIT_RECORD_SCHEMA_VERSION
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
            record_type=_enum(raw.get('record_type'), AUDIT_RECORD_TYPES, 'admission_decision', 'audit_record_type'),
            subject_ref=subject_ref,
            schema_version=str(raw.get('schema_version') or AUDIT_RECORD_SCHEMA_VERSION).strip(),
            subject_kind=_enum(raw.get('subject_kind'), SUBJECT_KINDS, 'task', 'audit_subject_kind'),
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
class AuditLedgerEntry:
    """Bounded append-only ledger entry over one GovEngine audit record.

    This is the neutral record shape a host or development adapter may append.
    Storage, locking, clocks, retention, and production concurrency remain
    host-owned.
    """

    entry_id: str
    sequence: int
    record: GovAuditRecord | Mapping[str, Any]
    record_digest: str
    schema_version: str = AUDIT_LEDGER_ENTRY_SCHEMA_VERSION
    event_digest: str = ''
    previous_entry_digest: str = ''
    entry_digest: str = ''
    recorded_at: str = ''
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        record = self.record if isinstance(self.record, GovAuditRecord) else GovAuditRecord.from_mapping(self.record)
        object.__setattr__(self, 'entry_id', str(self.entry_id or '').strip())
        object.__setattr__(self, 'sequence', int(self.sequence))
        object.__setattr__(self, 'record', record)
        object.__setattr__(self, 'record_digest', str(self.record_digest or '').strip())
        object.__setattr__(self, 'schema_version', str(self.schema_version or '').strip())
        object.__setattr__(self, 'event_digest', str(self.event_digest or '').strip())
        object.__setattr__(self, 'previous_entry_digest', str(self.previous_entry_digest or '').strip())
        object.__setattr__(self, 'entry_digest', str(self.entry_digest or '').strip())
        object.__setattr__(self, 'recorded_at', str(self.recorded_at or '').strip())
        object.__setattr__(self, 'metadata', _metadata(self.metadata))
        validate_audit_ledger_entry(self)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> 'AuditLedgerEntry':
        raw = require_mapping(value, reason_code='invalid_audit_ledger_entry')
        record_value = raw.get('record')
        if not isinstance(record_value, Mapping):
            raise GovApiError('missing_audit_ledger_record')
        return cls(
            entry_id=str(raw.get('entry_id') or raw.get('id') or '').strip(),
            sequence=int(raw.get('sequence') or 0),
            record=record_value,
            record_digest=str(raw.get('record_digest') or '').strip(),
            schema_version=str(raw.get('schema_version') or '').strip(),
            event_digest=str(raw.get('event_digest') or '').strip(),
            previous_entry_digest=str(raw.get('previous_entry_digest') or '').strip(),
            entry_digest=str(raw.get('entry_digest') or '').strip(),
            recorded_at=str(raw.get('recorded_at') or '').strip(),
            metadata=_metadata(raw.get('metadata')),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            'entry_id': self.entry_id,
            'sequence': self.sequence,
            'record': self.record.as_dict(),
            'record_digest': self.record_digest,
            'schema_version': self.schema_version,
            'event_digest': self.event_digest,
            'previous_entry_digest': self.previous_entry_digest,
            'entry_digest': self.entry_digest,
            'recorded_at': self.recorded_at,
            'metadata': dict(self.metadata),
        }


@dataclass(frozen=True)
class AuditLedgerAppendResult:
    """Append result returned by a host-owned ledger adapter."""

    status: str
    entry_id: str = ''
    sequence: int = -1
    entry_digest: str = ''
    reason_code: str = 'recorded'
    blockers: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, 'status', str(self.status or '').strip())
        object.__setattr__(self, 'entry_id', str(self.entry_id or '').strip())
        object.__setattr__(self, 'sequence', int(self.sequence))
        object.__setattr__(self, 'entry_digest', str(self.entry_digest or '').strip())
        object.__setattr__(self, 'reason_code', str(self.reason_code or 'recorded').strip() or 'recorded')
        object.__setattr__(self, 'blockers', _tuple(self.blockers))
        object.__setattr__(self, 'metadata', _metadata(self.metadata))
        validate_audit_ledger_append_result(self)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> 'AuditLedgerAppendResult':
        raw = require_mapping(value, reason_code='invalid_audit_ledger_append_result')
        return cls(
            status=str(raw.get('status') or '').strip(),
            entry_id=str(raw.get('entry_id') or '').strip(),
            sequence=int(raw.get('sequence') if raw.get('sequence') is not None else -1),
            entry_digest=str(raw.get('entry_digest') or '').strip(),
            reason_code=str(raw.get('reason_code') or 'recorded').strip() or 'recorded',
            blockers=_tuple(raw.get('blockers') or ()),
            metadata=_metadata(raw.get('metadata')),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            'status': self.status,
            'entry_id': self.entry_id,
            'sequence': self.sequence,
            'entry_digest': self.entry_digest,
            'reason_code': self.reason_code,
            'blockers': list(self.blockers),
            'metadata': dict(self.metadata),
        }


@dataclass(frozen=True)
class AuditLedgerVerificationResult:
    """Verification summary for a bounded ledger entry sequence."""

    status: str
    verified: bool = False
    checked_entries: int = 0
    last_entry_id: str = ''
    last_entry_digest: str = ''
    reason_code: str = 'verified'
    blockers: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        status = str(self.status or '').strip()
        object.__setattr__(self, 'status', status)
        object.__setattr__(self, 'checked_entries', int(self.checked_entries))
        object.__setattr__(self, 'last_entry_id', str(self.last_entry_id or '').strip())
        object.__setattr__(self, 'last_entry_digest', str(self.last_entry_digest or '').strip())
        object.__setattr__(self, 'reason_code', str(self.reason_code or status or 'verified').strip() or 'verified')
        object.__setattr__(self, 'blockers', _tuple(self.blockers))
        object.__setattr__(self, 'metadata', _metadata(self.metadata))
        validate_audit_ledger_verification_result(self)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> 'AuditLedgerVerificationResult':
        raw = require_mapping(value, reason_code='invalid_audit_ledger_verification_result')
        return cls(
            status=str(raw.get('status') or '').strip(),
            verified=bool(raw.get('verified', False)),
            checked_entries=int(raw.get('checked_entries') or 0),
            last_entry_id=str(raw.get('last_entry_id') or '').strip(),
            last_entry_digest=str(raw.get('last_entry_digest') or '').strip(),
            reason_code=str(raw.get('reason_code') or raw.get('status') or 'verified').strip() or 'verified',
            blockers=_tuple(raw.get('blockers') or ()),
            metadata=_metadata(raw.get('metadata')),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            'status': self.status,
            'verified': self.verified,
            'checked_entries': self.checked_entries,
            'last_entry_id': self.last_entry_id,
            'last_entry_digest': self.last_entry_digest,
            'reason_code': self.reason_code,
            'blockers': list(self.blockers),
            'metadata': dict(self.metadata),
        }


class AuditLedgerPort(Protocol):
    """Host-owned append/read/verify port for audit ledger adapters."""

    def append(
        self,
        record: GovAuditRecord,
        *,
        record_digest: str,
        event_digest: str = '',
        previous_entry_digest: str = '',
    ) -> AuditLedgerAppendResult:
        ...

    def read(self, *, after_entry_id: str = '', limit: int = 100) -> tuple[AuditLedgerEntry, ...]:
        ...

    def verify(self, entries: Iterable[AuditLedgerEntry]) -> AuditLedgerVerificationResult:
        ...


class JsonlAuditLedgerAdapter:
    """Development JSONL hash-chain adapter for bounded audit ledger entries.

    This adapter is for local development and smoke validation. It is not a
    production persistence, locking, retention, or concurrency implementation.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def append(
        self,
        record: GovAuditRecord,
        *,
        record_digest: str,
        event_digest: str = '',
        previous_entry_digest: str = '',
    ) -> AuditLedgerAppendResult:
        checked_record = validate_audit_record(record)
        existing = self.read()
        expected_previous = existing[-1].entry_digest if existing else ''
        supplied_previous = str(previous_entry_digest or '').strip()
        if supplied_previous and supplied_previous != expected_previous:
            return AuditLedgerAppendResult(
                status='rejected',
                reason_code='audit_ledger_previous_digest_mismatch',
                blockers=('audit_ledger_previous_digest_mismatch',),
            )
        sequence = len(existing)
        entry = AuditLedgerEntry(
            entry_id=f'audit-ledger-entry-{sequence + 1}',
            sequence=sequence,
            record=checked_record,
            record_digest=record_digest,
            event_digest=event_digest,
            previous_entry_digest=expected_previous,
            metadata={'adapter': 'jsonl_hash_chain_dev', 'storage': 'development_only'},
        )
        digest = audit_ledger_entry_digest(entry)
        stored = AuditLedgerEntry(**{**entry.as_dict(), 'entry_digest': digest})
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open('a', encoding='utf-8') as handle:
            handle.write(json.dumps(stored.as_dict(), ensure_ascii=True, sort_keys=True, separators=(',', ':')))
            handle.write('\n')
        return AuditLedgerAppendResult(
            status='appended',
            entry_id=stored.entry_id,
            sequence=stored.sequence,
            entry_digest=stored.entry_digest,
        )

    def read(self, *, after_entry_id: str = '', limit: int = 100) -> tuple[AuditLedgerEntry, ...]:
        if limit < 1:
            raise GovApiError('invalid_audit_ledger_read_limit')
        if not self.path.exists():
            return ()
        entries: list[AuditLedgerEntry] = []
        seen_after = not after_entry_id
        with self.path.open('r', encoding='utf-8') as handle:
            for line_number, line in enumerate(handle, start=1):
                text = line.strip()
                if not text:
                    continue
                try:
                    raw = json.loads(text)
                except json.JSONDecodeError as exc:
                    raise GovApiError(f'invalid_audit_ledger_jsonl:{line_number}') from exc
                entry = validate_audit_ledger_entry(raw)
                if not seen_after:
                    seen_after = entry.entry_id == after_entry_id
                    continue
                entries.append(entry)
                if len(entries) >= limit:
                    break
        return tuple(entries)

    def verify(self, entries: Iterable[AuditLedgerEntry]) -> AuditLedgerVerificationResult:
        checked = tuple(validate_audit_ledger_entry(entry) for entry in entries)
        if not checked:
            return AuditLedgerVerificationResult(status='empty', verified=False, checked_entries=0, reason_code='empty')
        previous_digest = ''
        for index, entry in enumerate(checked):
            if entry.sequence != index:
                return _audit_ledger_failed(
                    checked,
                    reason_code='audit_ledger_sequence_mismatch',
                    blocker='audit_ledger_sequence_mismatch',
                )
            if entry.previous_entry_digest != previous_digest:
                return _audit_ledger_failed(
                    checked,
                    reason_code='audit_ledger_previous_digest_mismatch',
                    blocker='audit_ledger_previous_digest_mismatch',
                )
            if entry.entry_digest != audit_ledger_entry_digest(entry):
                return _audit_ledger_failed(
                    checked,
                    reason_code='audit_ledger_entry_digest_mismatch',
                    blocker='audit_ledger_entry_digest_mismatch',
                )
            previous_digest = entry.entry_digest
        last = checked[-1]
        return AuditLedgerVerificationResult(
            status='verified',
            verified=True,
            checked_entries=len(checked),
            last_entry_id=last.entry_id,
            last_entry_digest=last.entry_digest,
        )


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
    schema_version: str = RUNTIME_ADMISSION_SCHEMA_VERSION
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
            schema_version=str(raw.get('schema_version') or RUNTIME_ADMISSION_SCHEMA_VERSION).strip(),
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
            'schema_version': self.schema_version,
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


def policy_verdict_to_gov_policy_decision(
    value: Mapping[str, Any] | Any,
    *,
    policy_id: str = '',
    subject_kind: str = 'task',
) -> GovPolicyDecision:
    """Project a PolicyEngine verdict into the legacy admission decision shape."""

    raw = _runtime_signal(value)
    verdict_id = str(policy_id or raw.get('verdict_id') or raw.get('policy_id') or raw.get('id') or '').strip()
    if not verdict_id:
        raise GovApiError('missing_policy_verdict_id')
    subject_ref = str(raw.get('subject_ref') or '').strip()
    if not subject_ref:
        raise GovApiError('missing_policy_verdict_subject_ref')
    decision = _policy_verdict_admission_decision(str(raw.get('decision') or '').strip())
    reason_code = str(raw.get('reason_code') or decision).strip() or decision
    obligations = _policy_verdict_items(raw.get('obligations') or ())
    constraints = _policy_verdict_items(raw.get('constraints') or ())
    controls = tuple(
        item
        for item in (
            *(f'obligation:{entry}' for entry in obligations),
            *(f'constraint:{entry}' for entry in constraints),
        )
        if item
    )
    blockers = _tuple(raw.get('blockers') or ())
    if decision == 'require_approval' and not blockers:
        blockers = ('operator_approval_required',)
    if decision == 'deny' and not blockers:
        blockers = (reason_code,)
    return validate_policy_decision(GovPolicyDecision(
        policy_id=verdict_id,
        subject_ref=subject_ref,
        subject_kind=_enum(subject_kind, SUBJECT_KINDS, 'task', 'policy_subject_kind'),
        decision=decision,
        reason_code=reason_code,
        controls=controls,
        blockers=blockers,
        metadata={
            'policy_verdict_schema_version': str(raw.get('schema_version') or ''),
            'policy_request_id': str(raw.get('request_id') or ''),
            'risk_class': str(raw.get('risk_class') or ''),
            'risk_score': raw.get('risk_score', 0.0),
        },
    ))


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
    if item.schema_version != AUDIT_RECORD_SCHEMA_VERSION:
        raise GovApiError(f'unknown_audit_record_schema_version:{item.schema_version or "missing"}')
    _reject_forbidden_metadata(item.metadata)
    return item


def validate_audit_ledger_entry(value: Mapping[str, Any] | AuditLedgerEntry) -> AuditLedgerEntry:
    item = value if isinstance(value, AuditLedgerEntry) else AuditLedgerEntry.from_mapping(value)
    if not item.entry_id:
        raise GovApiError('missing_audit_ledger_entry_id')
    if item.sequence < 0:
        raise GovApiError('invalid_audit_ledger_sequence')
    if item.schema_version and item.schema_version != AUDIT_LEDGER_ENTRY_SCHEMA_VERSION:
        raise GovApiError(f'unknown_audit_ledger_entry_schema_version:{item.schema_version}')
    validate_audit_record(item.record)
    _require_digest_ref(item.record_digest, 'missing_audit_ledger_record_digest', 'invalid_audit_ledger_record_digest')
    _validate_optional_digest_ref(item.event_digest, 'invalid_audit_ledger_event_digest')
    _validate_optional_digest_ref(item.previous_entry_digest, 'invalid_audit_ledger_previous_digest')
    _validate_optional_digest_ref(item.entry_digest, 'invalid_audit_ledger_entry_digest')
    _reject_forbidden_metadata(item.metadata)
    return item


def validate_audit_ledger_append_result(
    value: Mapping[str, Any] | AuditLedgerAppendResult,
) -> AuditLedgerAppendResult:
    item = value if isinstance(value, AuditLedgerAppendResult) else AuditLedgerAppendResult.from_mapping(value)
    if item.status not in AUDIT_LEDGER_APPEND_STATUSES:
        raise GovApiError(f'unknown_audit_ledger_append_status:{item.status}')
    if item.status == 'appended':
        if not item.entry_id:
            raise GovApiError('missing_audit_ledger_append_entry_id')
        if item.sequence < 0:
            raise GovApiError('invalid_audit_ledger_append_sequence')
        _require_digest_ref(item.entry_digest, 'missing_audit_ledger_append_digest', 'invalid_audit_ledger_append_digest')
    if item.status == 'rejected' and not (item.blockers or item.reason_code != 'recorded'):
        raise GovApiError('audit_ledger_rejection_without_reason')
    _reject_forbidden_metadata(item.metadata)
    return item


def validate_audit_ledger_verification_result(
    value: Mapping[str, Any] | AuditLedgerVerificationResult,
) -> AuditLedgerVerificationResult:
    item = value if isinstance(value, AuditLedgerVerificationResult) else AuditLedgerVerificationResult.from_mapping(value)
    if item.status not in AUDIT_LEDGER_VERIFY_STATUSES:
        raise GovApiError(f'unknown_audit_ledger_verification_status:{item.status}')
    if item.checked_entries < 0:
        raise GovApiError('invalid_audit_ledger_checked_entries')
    _validate_optional_digest_ref(item.last_entry_digest, 'invalid_audit_ledger_last_digest')
    if item.status == 'verified':
        if not item.verified:
            raise GovApiError('audit_ledger_verified_status_mismatch')
        if item.checked_entries < 1:
            raise GovApiError('audit_ledger_verified_without_entries')
        if not item.last_entry_id:
            raise GovApiError('missing_audit_ledger_last_entry_id')
        _require_digest_ref(item.last_entry_digest, 'missing_audit_ledger_last_digest', 'invalid_audit_ledger_last_digest')
        if item.blockers:
            raise GovApiError('audit_ledger_verified_with_blockers')
    if item.status == 'failed' and not item.blockers:
        raise GovApiError('audit_ledger_failed_without_blockers')
    if item.status == 'empty' and item.checked_entries != 0:
        raise GovApiError('audit_ledger_empty_with_entries')
    _reject_forbidden_metadata(item.metadata)
    return item


def audit_ledger_entry_digest(value: Mapping[str, Any] | AuditLedgerEntry) -> str:
    """Return the GovEngine-owned digest for an audit ledger entry.

    The self-referential `entry_digest` field is cleared before digesting. This
    does not canonicalize SCLite artifacts or raw evidence.
    """

    item = value if isinstance(value, AuditLedgerEntry) else AuditLedgerEntry.from_mapping(value)
    payload = item.as_dict()
    payload['entry_digest'] = ''
    if not payload.get('schema_version'):
        payload.pop('schema_version', None)
    from govengine.signing import govengine_record_digest

    return govengine_record_digest(payload, record_type='govengine.admission.AuditLedgerEntry')


def validate_runtime_admission_result(value: Mapping[str, Any] | RuntimeAdmissionResult) -> RuntimeAdmissionResult:
    item = value if isinstance(value, RuntimeAdmissionResult) else RuntimeAdmissionResult.from_mapping(value)
    if item.schema_version != RUNTIME_ADMISSION_SCHEMA_VERSION:
        raise GovApiError(f'unknown_runtime_admission_schema_version:{item.schema_version or "missing"}')
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


def runtime_admission_public_summary(
    value: Mapping[str, Any] | RuntimeAdmissionResult,
    *,
    show_artifact_refs: bool = False,
) -> dict[str, Any]:
    """Return a bounded public summary of a runtime admission result."""

    item = validate_runtime_admission_result(value)
    summary: dict[str, Any] = {
        'schema_version': item.schema_version,
        'admission_id': item.admission_id,
        'subject_ref': item.subject_ref,
        'status': item.status,
        'allowed': item.allowed,
        'reason_code': item.reason_code,
        'blocker_count': len(item.blockers),
        'required_next_action_count': len(item.required_next_actions),
        'receipt_obligation': _receipt_obligation_public_status(item.receipt_obligation),
    }
    if show_artifact_refs:
        summary['artifact_refs'] = dict(item.artifact_refs)
    return summary


def audit_record_public_summary(value: Mapping[str, Any] | GovAuditRecord) -> dict[str, Any]:
    """Return public-safe audit record identifiers without raw metadata."""

    item = validate_audit_record(value)
    return {
        'schema_version': item.schema_version,
        'record_id': item.record_id,
        'record_type': item.record_type,
        'subject_ref': item.subject_ref,
        'decision_ref': item.decision_ref,
        'reason_code': item.reason_code,
        'event_ref_count': len(item.event_refs),
    }


def audit_ledger_verification_public_summary(
    value: Mapping[str, Any] | AuditLedgerVerificationResult,
) -> dict[str, Any]:
    """Return a bounded ledger verification summary without raw records."""

    item = validate_audit_ledger_verification_result(value)
    return {
        'status': item.status,
        'verified': item.verified,
        'reason_code': item.reason_code,
        'blocker_count': len(item.blockers),
        'checked_entries': item.checked_entries,
        'last_entry_id': item.last_entry_id,
        'last_entry_digest': item.last_entry_digest,
    }


def validate_runtime_admission_proof_inputs(
    value: Mapping[str, Any] | RuntimeAdmissionResult,
) -> RuntimeAdmissionResult:
    """Validate that an allowed admission carries the expected proof summaries.

    This checks presence and status of already-produced bounded records. It does
    not verify SCLite artifacts, check signatures, evaluate policy meaning, or
    authorize execution.
    """

    item = validate_runtime_admission_result(value)
    if not item.allowed:
        raise GovApiError('runtime_admission_proof_not_allowed')
    if _guarded_runtime_status(item.sclite_guarded_strict) != 'passed':
        raise GovApiError('runtime_admission_proof_guarded_strict_missing')
    if (
        _replay_runtime_status(
            item.replay_freshness,
            item.sclite_guarded_strict,
            runtime_consumable=True,
        )
        != 'fresh'
    ):
        raise GovApiError('runtime_admission_proof_replay_freshness_missing')
    if _trust_signal_status(item.trust_decision) not in {'trusted', 'passed', 'ok'}:
        raise GovApiError('runtime_admission_proof_trust_decision_missing')
    if _ticket_signal_status(item.execution_ticket) not in {'approve', 'approved', 'approved_for_dry_run', 'passed', 'ok'}:
        raise GovApiError('runtime_admission_proof_execution_ticket_missing')
    if not _receipt_obligation_required(item.receipt_obligation):
        raise GovApiError('runtime_admission_proof_receipt_obligation_missing')
    if not _bool_value(item.runner_profile.get('allowed'), default=False):
        raise GovApiError('runtime_admission_proof_runner_profile_missing')
    if _bool_value(item.runner_profile.get('live_backend_enabled'), default=False):
        raise GovApiError('runtime_admission_proof_live_backend_not_allowed')
    if not _proof_ref(item.artifact_refs, 'sclite_guarded_strict', 'root_chain_digest'):
        raise GovApiError('runtime_admission_proof_guard_digest_missing')
    if not _proof_ref(item.artifact_refs, 'execution_ticket', 'ticket_id'):
        raise GovApiError('runtime_admission_proof_ticket_ref_missing')
    if not _proof_ref(item.artifact_refs, 'execution_ticket', 'ticket_digest', 'digest'):
        raise GovApiError('runtime_admission_proof_ticket_digest_missing')
    binds = {str(item) for item in item.receipt_obligation.get('binds', ()) if not isinstance(item, Mapping)}
    if not {'admission', 'ticket'} <= binds:
        raise GovApiError('runtime_admission_proof_receipt_binding_incomplete')
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
    artifact_ref_summary = _normalize_admission_artifact_refs_from_summaries(
        {
            'prepared_execution_contract': prepared_summary,
            'policy_decision': policy_summary,
            'execution_ticket': ticket_summary,
            'trust_decision': trust_summary,
            'sclite_guarded_strict': guarded_summary,
            'replay_freshness': replay_summary,
            'runner_profile': runner_summary,
            'receipt_obligation': receipt_summary,
        },
        explicit_refs=artifact_refs,
    )

    has_prepared_contract = not _explicit_false(prepared_summary, 'allowed') and _status_in(
        _signal_status(prepared_summary, ('status', 'contract_status')),
        PREPARED_EXECUTION_CONTRACT_STATUSES,
    )
    policy_status = _policy_signal_status(policy_summary)
    ticket_status = _ticket_signal_status(ticket_summary)
    trust_status = _trust_signal_status(trust_summary)
    guarded_status = _guarded_runtime_status(guarded_summary)
    replay_status = _replay_runtime_status(
        replay_summary,
        guarded_summary,
        runtime_consumable=bool(runtime_consumable),
    )

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
    trust_blocker = _trust_runtime_blocker(trust_status)
    if trust_blocker:
        blockers = _replace_or_append(blockers, 'missing_or_invalid_trust_decision', trust_blocker)
        required_next_actions = _replace_or_append(
            required_next_actions,
            'verify_trust_decision',
            TRUST_RUNTIME_ACTIONS[trust_blocker],
        )

    runner_blocker = _runner_runtime_blocker(runner_summary, runner, live)
    if runner_blocker:
        blockers = _replace_or_append(blockers, 'runner_profile_not_allowed', runner_blocker)
        required_next_actions = _replace_or_append(
            required_next_actions,
            'select_allowed_runner_profile',
            RUNNER_RUNTIME_ACTIONS[runner_blocker],
        )

    receipt_blocker = ''
    if not _receipt_obligation_required(receipt_summary):
        receipt_blocker = 'receipt_obligation_required'
        blockers.append(receipt_blocker)
        required_next_actions.append('require_runner_receipt_obligation')

    blockers_tuple = _dedupe(blockers)
    actions_tuple = _dedupe(required_next_actions)
    allowed = gate_decision.allowed and not blockers_tuple
    reason_code = 'all_required_gates_passed' if allowed else (
        policy_blocker or ticket_blocker or trust_blocker or runner_blocker or receipt_blocker or (
            gate_decision.reason_code if not gate_decision.allowed else blockers_tuple[0]
        )
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
        artifact_refs=artifact_ref_summary,
        metadata=_metadata(metadata),
    ))


def normalize_admission_artifact_refs(
    *,
    prepared_execution_contract: Mapping[str, Any] | Any | None = None,
    policy_decision: Mapping[str, Any] | Any | None = None,
    execution_ticket: Mapping[str, Any] | Any | None = None,
    trust_decision: Mapping[str, Any] | Any | None = None,
    sclite_guarded_strict: Mapping[str, Any] | Any | None = None,
    replay_freshness: Mapping[str, Any] | Any | None = None,
    runner_profile: Mapping[str, Any] | Any | None = None,
    receipt_obligation: Mapping[str, Any] | Any | None = None,
    artifact_refs: Mapping[str, Any] | Any | None = None,
) -> dict[str, Any]:
    """Return bounded references/digests for admission review.

    This helper normalizes existing GovEngine-owned reference fields. It does
    not compute content digests and does not claim SCLite canonicalization or
    artifact-chain authority.
    """

    summaries = {
        'prepared_execution_contract': _artifact_reference_signal(prepared_execution_contract),
        'policy_decision': _artifact_reference_signal(policy_decision),
        'execution_ticket': _artifact_reference_signal(execution_ticket),
        'trust_decision': _artifact_reference_signal(trust_decision),
        'sclite_guarded_strict': _artifact_reference_signal(sclite_guarded_strict),
        'replay_freshness': _artifact_reference_signal(replay_freshness),
        'runner_profile': _artifact_reference_signal(runner_profile),
        'receipt_obligation': _artifact_reference_signal(receipt_obligation),
    }
    return _normalize_admission_artifact_refs_from_summaries(summaries, explicit_refs=artifact_refs)


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


def _enum(
    value: Any,
    allowed: tuple[str, ...],
    default: str,
    field_name: str,
) -> str:
    normalized = str(value or '').strip().lower()
    if not normalized:
        return default
    if normalized not in allowed:
        raise GovApiError(f'unknown_{field_name}:{normalized}')
    return normalized


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


def _policy_verdict_admission_decision(decision: str) -> str:
    if decision == 'allow_with_obligations':
        return 'allow'
    if decision == 'approval_required':
        return 'require_approval'
    if decision in {'allow', 'deny'}:
        return decision
    raise GovApiError(f'unknown_policy_verdict_decision:{decision or "missing"}')


def _policy_verdict_items(values: Any) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, (list, tuple)):
        return ()
    items: list[str] = []
    for value in values:
        if isinstance(value, Mapping):
            item_id = str(
                value.get('obligation_id')
                or value.get('constraint_id')
                or value.get('id')
                or value.get('kind')
                or value.get('type')
                or ''
            ).strip()
            if item_id:
                items.append(item_id)
            continue
        items.append(str(value).strip())
    return tuple(item for item in items if item)


def _artifact_reference_signal(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return _json_safe_mapping(value)
    as_dict = getattr(value, 'as_dict', None)
    if callable(as_dict):
        payload = as_dict()
        if isinstance(payload, Mapping):
            return _json_safe_mapping(payload)
    raise GovApiError('invalid_admission_artifact_refs')


def _normalize_admission_artifact_refs_from_summaries(
    summaries: Mapping[str, Mapping[str, Any]],
    *,
    explicit_refs: Mapping[str, Any] | Any | None,
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for role in ADMISSION_ARTIFACT_INPUTS:
        bounded = _bounded_artifact_reference(summaries.get(role) or {})
        if bounded:
            out[role] = bounded
    explicit = _bounded_artifact_reference(_artifact_reference_signal(explicit_refs))
    if explicit:
        out['explicit'] = explicit
    return out


def _bounded_artifact_reference(payload: Mapping[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key in sorted(str(item) for item in payload):
        if key in FORBIDDEN_ADMISSION_METADATA_KEYS:
            continue
        value = payload.get(key)
        if not _is_bounded_scalar(value):
            continue
        item = str(value).strip()
        if not item:
            continue
        if key in ADMISSION_DIGEST_KEYS:
            out[key] = _normalize_digest_reference(item)
        elif key in ADMISSION_REF_KEYS:
            out[key] = item
    return out


def _is_bounded_scalar(value: Any) -> bool:
    return isinstance(value, (str, int, float)) and not isinstance(value, bool)


def _normalize_digest_reference(value: str) -> str:
    item = value.strip()
    if item.lower().startswith('sha256:'):
        return 'sha256:' + item.split(':', 1)[1].strip().lower()
    if len(item) == 64 and all(char in '0123456789abcdefABCDEF' for char in item):
        return 'sha256:' + item.lower()
    return item


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
    reason_code = _signal_status(payload, ('reason_code', 'blocker', 'error_code'))
    if reason_code in TRUST_RUNTIME_BLOCKERS:
        return reason_code
    if 'trusted' in payload:
        return 'trusted' if _bool_value(payload.get('trusted'), default=False) else 'denied'
    return _signal_status(payload, ('trust_status', 'status', 'verification_status')) or 'unknown'


def _guarded_bundle_decision_failed(payload: Mapping[str, Any]) -> bool:
    """Return True when a guarded-bundle summary reports a failed decision."""

    if not payload:
        return False
    decision_status = _signal_status(payload, ('status',))
    if decision_status in {'blocked', 'failed', 'denied'}:
        return True
    if 'allowed' in payload and not _bool_value(payload.get('allowed'), default=True):
        return True
    return False


def _guarded_runtime_status(payload: Mapping[str, Any]) -> str:
    if not payload:
        return ''
    if _explicit_false(payload, 'guarded') or _explicit_false(payload, 'kernel_guard_present'):
        return 'not_guarded'
    if (
        _explicit_false(payload, 'strict')
        or _explicit_false(payload, 'strict_lifecycle')
        or _explicit_false(payload, 'guarded_strict')
    ):
        return 'not_strict'
    if _guarded_bundle_decision_failed(payload):
        return 'failed'
    return _signal_status(payload, ('verification_status', 'guarded_status', 'status'))


_REPLAY_FAILURE_STATUSES = frozenset({'replayed', 'stale', 'expired', 'blocked', 'failed'})


def _replay_runtime_status(
    replay_payload: Mapping[str, Any],
    guarded_payload: Mapping[str, Any],
    *,
    runtime_consumable: bool = False,
) -> str:
    guarded_replay = _signal_status(guarded_payload, ('replay_status',))
    replay_only = _signal_status(replay_payload, ('replay_status', 'status'))

    if not runtime_consumable:
        return replay_only or guarded_replay

    if guarded_replay in _REPLAY_FAILURE_STATUSES:
        return guarded_replay
    if replay_only in _REPLAY_FAILURE_STATUSES:
        return replay_only

    if replay_payload and replay_only:
        if not guarded_replay:
            return 'missing'
        if guarded_replay != replay_only:
            return 'replayed'

    return guarded_replay or replay_only or 'missing'


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


def _trust_runtime_blocker(trust_status: str) -> str:
    if trust_status in {'trusted', 'passed', 'ok'}:
        return ''
    if trust_status == 'missing':
        return 'missing_or_invalid_trust_decision'
    return TRUST_RUNTIME_BLOCKERS.get(trust_status, 'unknown_trust_decision_status')


def _runner_runtime_blocker(payload: Mapping[str, Any], runner: Any, live: bool) -> str:
    if not payload:
        return 'missing_runner_profile'
    if not runner.allowed:
        return 'runner_profile_not_allowed'
    if live and not runner.live_backend_enabled:
        return 'live_backend_disabled'
    return ''


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


def _receipt_obligation_public_status(payload: Mapping[str, Any]) -> str:
    if not payload:
        return 'missing'
    if _receipt_obligation_required(payload):
        return 'required'
    return str(payload.get('status') or 'missing').strip() or 'missing'


def _proof_ref(refs: Mapping[str, Any], group: str, *keys: str) -> str:
    value = refs.get(group)
    if not isinstance(value, Mapping):
        return ''
    for key in keys:
        item = value.get(key)
        if isinstance(item, Mapping) or isinstance(item, (list, tuple, set)):
            continue
        normalized = str(item or '').strip()
        if normalized:
            return normalized
    return ''


def _dedupe(values: Iterable[Any]) -> tuple[str, ...]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        item = str(value).strip()
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return tuple(out)


def _audit_ledger_failed(
    entries: tuple[AuditLedgerEntry, ...],
    *,
    reason_code: str,
    blocker: str,
) -> AuditLedgerVerificationResult:
    last = entries[-1] if entries else None
    return AuditLedgerVerificationResult(
        status='failed',
        verified=False,
        checked_entries=len(entries),
        last_entry_id=last.entry_id if last else '',
        last_entry_digest=last.entry_digest if last else '',
        reason_code=reason_code,
        blockers=(blocker,),
    )


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
    data = bounded_json_copy(value)
    _reject_forbidden_metadata(data)
    return data


def _json_safe_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    return bounded_json_copy(value)


def _reject_forbidden_metadata(value: Mapping[str, Any]) -> None:
    reason = _find_forbidden_key(value)
    if reason:
        raise GovApiError(f'forbidden_admission_metadata:{reason}')


def _require_digest_ref(value: str, missing_reason: str, invalid_reason: str) -> str:
    text = str(value or '').strip()
    if not text:
        raise GovApiError(missing_reason)
    _validate_optional_digest_ref(text, invalid_reason)
    return text


def _validate_optional_digest_ref(value: str, invalid_reason: str) -> None:
    text = str(value or '').strip()
    if text and not text.startswith('sha256:'):
        raise GovApiError(invalid_reason)


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
