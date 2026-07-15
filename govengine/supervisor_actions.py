from __future__ import annotations

from dataclasses import asdict, dataclass, field
from string import hexdigits
from typing import Any, Mapping

from govengine.admission import (
    GovAdmissionDecision,
    _admission_decision_from_planning_adapter,
    validate_admission_decision,
)
from govengine.api import GovApiError, require_mapping
from govengine.signing import govengine_record_digest

SUPERVISOR_ACTION_REQUEST_SCHEMA_VERSION = 'v0.1'
SUPERVISOR_ACTIONS = (
    'record_health',
    'renew_lease',
    'mark_stale',
    'move_to_dead_letter',
    'retry_later',
    'escalate_operator',
    'block_autostart',
)
SUPERVISOR_RECORD_ONLY_ACTIONS = ('record_health',)
SUPERVISOR_HUMAN_SIGNOFF_ACTIONS = ('renew_lease', 'mark_stale', 'escalate_operator')
FORBIDDEN_SUPERVISOR_METADATA_KEYS = (
    'api_key',
    'command',
    'commands',
    'credential',
    'credentials',
    'event_payload',
    'host',
    'hostname',
    'ip',
    'password',
    'raw_event',
    'raw_output',
    'secret',
    'stderr',
    'stdout',
    'subprocess',
    'target',
    'target_url',
    'token',
    'url',
)


@dataclass(frozen=True)
class SupervisorActionRequest:
    """GovEngine-owned admission request for neutral runner-supervisor actions.

    RExecOp owns watchdog mechanics, queue/inbox handling and worker state.
    This request carries only bounded identifiers, digests and limits so
    GovEngine can decide whether the supervisor action is admissible.
    """

    request_id: str
    action: str
    reason: str
    watchdog_record_ref: str
    observation: str
    affected_kind: str = ''
    operation_id: str = ''
    event_ref: str = ''
    trigger_ref: str = ''
    inbox_item_name: str = ''
    actor_ref: str = ''
    scope: str = ''
    attempt_count: int = 0
    max_attempts: int = 0
    age_seconds: float = 0.0
    max_age_seconds: float = 0.0
    human_signoff: bool = False
    schema_version: str = SUPERVISOR_ACTION_REQUEST_SCHEMA_VERSION
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> SupervisorActionRequest:
        raw = require_mapping(value, reason_code='invalid_supervisor_action_request')
        item = cls(
            request_id=str(raw.get('request_id') or '').strip(),
            action=str(raw.get('action') or raw.get('decision') or '').strip(),
            reason=str(raw.get('reason') or '').strip(),
            watchdog_record_ref=str(
                raw.get('watchdog_record_ref') or raw.get('watchdog_record_digest') or ''
            ).strip(),
            observation=str(raw.get('observation') or '').strip(),
            affected_kind=str(raw.get('affected_kind') or '').strip(),
            operation_id=str(raw.get('operation_id') or '').strip(),
            event_ref=str(raw.get('event_ref') or '').strip(),
            trigger_ref=str(raw.get('trigger_ref') or '').strip(),
            inbox_item_name=str(raw.get('inbox_item_name') or '').strip(),
            actor_ref=str(raw.get('actor_ref') or '').strip(),
            scope=str(raw.get('scope') or '').strip(),
            attempt_count=_int(raw.get('attempt_count')),
            max_attempts=_int(raw.get('max_attempts')),
            age_seconds=_float(raw.get('age_seconds')),
            max_age_seconds=_float(raw.get('max_age_seconds')),
            human_signoff=bool(raw.get('human_signoff', False)),
            schema_version=str(
                raw.get('schema_version') or SUPERVISOR_ACTION_REQUEST_SCHEMA_VERSION
            ).strip(),
            metadata=_metadata(raw.get('metadata')),
        )
        validate_supervisor_action_request(item)
        return item

    def as_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out['metadata'] = dict(self.metadata)
        return out


def validate_supervisor_action_request(
    value: Mapping[str, Any] | SupervisorActionRequest,
) -> SupervisorActionRequest:
    item = value if isinstance(value, SupervisorActionRequest) else SupervisorActionRequest.from_mapping(value)
    if item.schema_version != SUPERVISOR_ACTION_REQUEST_SCHEMA_VERSION:
        raise GovApiError('unknown_supervisor_action_request_schema')
    for field_name in ('request_id', 'action', 'reason', 'watchdog_record_ref', 'observation'):
        if not getattr(item, field_name):
            raise GovApiError(f'missing_supervisor_action_{field_name}')
    if item.action not in SUPERVISOR_ACTIONS:
        raise GovApiError(f'unsupported_supervisor_action:{item.action}')
    _require_digest_ref(item.watchdog_record_ref, 'invalid_supervisor_watchdog_record_ref')
    if item.event_ref:
        _require_digest_ref(item.event_ref, 'invalid_supervisor_event_ref')
    if item.trigger_ref:
        _require_digest_ref(item.trigger_ref, 'invalid_supervisor_trigger_ref')
    if item.action in {'move_to_dead_letter', 'retry_later'} and not item.inbox_item_name:
        raise GovApiError(f'supervisor_action_missing_inbox_item:{item.action}')
    if item.action == 'block_autostart' and not item.operation_id:
        raise GovApiError('supervisor_action_missing_operation:block_autostart')
    if item.action in SUPERVISOR_HUMAN_SIGNOFF_ACTIONS and item.human_signoff:
        if not item.actor_ref:
            raise GovApiError(f'supervisor_action_missing_actor:{item.action}')
        if not item.scope:
            raise GovApiError(f'supervisor_action_missing_scope:{item.action}')
    if item.attempt_count < 0 or item.max_attempts < 0:
        raise GovApiError('invalid_supervisor_attempt_limits')
    if item.age_seconds < 0 or item.max_age_seconds < 0:
        raise GovApiError('invalid_supervisor_age_limits')
    _reject_forbidden_supervisor_metadata(item.metadata)
    return item


def supervisor_action_request_digest(
    request: Mapping[str, Any] | SupervisorActionRequest,
) -> str:
    checked = validate_supervisor_action_request(request)
    return govengine_record_digest(
        checked,
        record_type='govengine.supervisor_actions.SupervisorActionRequest',
    )


def admit_supervisor_action(
    request: Mapping[str, Any] | SupervisorActionRequest,
) -> GovAdmissionDecision:
    checked = validate_supervisor_action_request(request)
    outcome = 'allowed'
    reason_code = 'supervisor_action_allowed'
    blockers: tuple[str, ...] = ()

    if checked.action in SUPERVISOR_RECORD_ONLY_ACTIONS:
        outcome = 'record_only'
        reason_code = 'supervisor_action_record_only'
    elif checked.action in SUPERVISOR_HUMAN_SIGNOFF_ACTIONS and not checked.human_signoff:
        outcome = 'deferred'
        reason_code = 'supervisor_action_requires_human_signoff'
        blockers = ('human_signoff_required',)
    elif checked.action in {'move_to_dead_letter', 'retry_later'} and not _within_retry_budget(checked):
        outcome = 'denied'
        reason_code = 'supervisor_action_retry_budget_exceeded'
        blockers = ('retry_budget_exceeded',)
    elif checked.action == 'block_autostart' and not _stale_age_exceeded(checked):
        outcome = 'denied'
        reason_code = 'supervisor_action_stale_age_not_exceeded'
        blockers = ('stale_age_not_exceeded',)

    return _admission_decision_from_planning_adapter(
        decision_id=f'supervisor-admission:{checked.request_id}',
        subject_ref=supervisor_action_request_digest(checked),
        subject_kind='operator_action',
        outcome=outcome,
        reason_code=reason_code,
        blockers=blockers,
        signal={
            'request_id': checked.request_id,
            'action': checked.action,
            'reason': checked.reason,
            'watchdog_record_ref': checked.watchdog_record_ref,
            'observation': checked.observation,
            'affected_kind': checked.affected_kind,
            'operation_id': checked.operation_id,
            'event_ref': checked.event_ref,
            'trigger_ref': checked.trigger_ref,
            'inbox_item_name': checked.inbox_item_name,
            'actor_ref': checked.actor_ref,
            'scope': checked.scope,
            'attempt_count': checked.attempt_count,
            'max_attempts': checked.max_attempts,
            'age_seconds': checked.age_seconds,
            'max_age_seconds': checked.max_age_seconds,
        },
        metadata={
            'source': 'supervisor_action_request',
            'schema_version': checked.schema_version,
        },
    )


def supervisor_action_admission_digest(
    admission: Mapping[str, Any] | GovAdmissionDecision,
) -> str:
    checked = validate_admission_decision(admission)
    return govengine_record_digest(
        checked,
        record_type='govengine.admission.GovAdmissionDecision',
    )


def validate_supervisor_action_admission(
    admission: Mapping[str, Any] | GovAdmissionDecision,
    *,
    request: Mapping[str, Any] | SupervisorActionRequest,
) -> GovAdmissionDecision:
    checked = validate_admission_decision(admission)
    expected = admit_supervisor_action(request)
    if checked.as_dict() != expected.as_dict():
        raise GovApiError('supervisor_action_admission_drift')
    return checked


def _within_retry_budget(item: SupervisorActionRequest) -> bool:
    if item.max_attempts <= 0:
        return True
    return item.attempt_count <= item.max_attempts


def _stale_age_exceeded(item: SupervisorActionRequest) -> bool:
    if item.max_age_seconds <= 0:
        return True
    return item.age_seconds >= item.max_age_seconds


def _metadata(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    raw = require_mapping(value, reason_code='invalid_supervisor_action_metadata')
    return dict(raw)


def _reject_forbidden_supervisor_metadata(value: Mapping[str, Any]) -> None:
    lowered = {str(key).lower() for key in value}
    for key in FORBIDDEN_SUPERVISOR_METADATA_KEYS:
        if key in lowered:
            raise GovApiError(f'forbidden_supervisor_action_metadata:{key}')
    for nested in value.values():
        if isinstance(nested, Mapping):
            _reject_forbidden_supervisor_metadata(nested)


def _require_digest_ref(value: str, reason_code: str) -> None:
    text = str(value or '').strip()
    prefix, separator, digest = text.partition(':')
    if separator != ':' or prefix != 'sha256' or len(digest) != 64:
        raise GovApiError(reason_code)
    if not all(char in hexdigits for char in digest):
        raise GovApiError(reason_code)


def _int(value: Any) -> int:
    if value in (None, ''):
        return 0
    return int(value)


def _float(value: Any) -> float:
    if value in (None, ''):
        return 0.0
    return float(value)
