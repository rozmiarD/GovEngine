from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from govengine.api import GovApiError, require_mapping


RUNTIME_STATES = (
    'idle',
    'admitted',
    'policy_checked',
    'trust_checked',
    'gated',
    'running',
    'running_dry_run',
    'paused',
    'cooldown',
    'stopped',
    'cancelled',
    'blocked',
    'completed',
)

CONTROL_ACTIONS = (
    'start',
    'pause',
    'resume',
    'stop',
    'cancel',
    'replan',
    'degrade_to_dry_run',
    'cooldown',
    'retry',
    'archive',
    'record_only',
)

ACTION_TARGET_STATE = {
    'start': 'running',
    'pause': 'paused',
    'resume': 'running',
    'stop': 'stopped',
    'cancel': 'cancelled',
    'replan': 'idle',
    'degrade_to_dry_run': 'running_dry_run',
    'cooldown': 'cooldown',
    'retry': 'running',
    'archive': 'completed',
    'record_only': '',
}

FORBIDDEN_RUNTIME_METADATA_KEYS = (
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
)


@dataclass(frozen=True)
class GovControlAction:
    """High-level host control action, not an execution command."""

    action_id: str
    run_id: str
    action: str
    reason_code: str = 'operator_requested'
    requested_state: str = ''
    profile: str = 'generic'
    event_refs: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.requested_state and self.action in ACTION_TARGET_STATE:
            object.__setattr__(self, 'requested_state', ACTION_TARGET_STATE[self.action])

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> 'GovControlAction':
        raw = require_mapping(value, reason_code='invalid_control_action')
        action_id = str(raw.get('action_id') or raw.get('id') or '').strip()
        if not action_id:
            raise GovApiError('missing_control_action_id')
        run_id = str(raw.get('run_id') or '').strip()
        if not run_id:
            raise GovApiError('missing_run_id')
        action = str(raw.get('action') or '').strip()
        if action not in CONTROL_ACTIONS:
            raise GovApiError(f'unknown_control_action:{action}')
        requested_state = str(raw.get('requested_state') or ACTION_TARGET_STATE[action]).strip()
        if requested_state and requested_state not in RUNTIME_STATES:
            raise GovApiError(f'unknown_runtime_state:{requested_state}')
        metadata = _metadata(raw.get('metadata'))
        item = cls(
            action_id=action_id,
            run_id=run_id,
            action=action,
            reason_code=str(raw.get('reason_code') or 'operator_requested'),
            requested_state=requested_state,
            profile=str(raw.get('profile') or 'generic'),
            event_refs=_tuple(raw.get('event_refs') or ()),
            metadata=metadata,
        )
        validate_control_action(item)
        return item

    def as_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out['event_refs'] = list(self.event_refs)
        out['metadata'] = dict(self.metadata)
        return out


@dataclass(frozen=True)
class GovQueueLane:
    """Redaction-bounded summary of one host-owned work lane."""

    name: str
    count: int = 0
    preview: tuple[Mapping[str, Any], ...] = field(default_factory=tuple)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> 'GovQueueLane':
        raw = require_mapping(value, reason_code='invalid_queue_lane')
        name = str(raw.get('name') or '').strip()
        if not name:
            raise GovApiError('missing_queue_lane_name')
        count = _int(raw.get('count'), 0)
        if count < 0:
            raise GovApiError('negative_queue_lane_count')
        preview = tuple(_metadata(item) for item in list(raw.get('preview') or ()))
        if len(preview) > count:
            raise GovApiError('queue_preview_exceeds_count')
        return cls(name=name, count=count, preview=preview)

    def as_dict(self) -> dict[str, Any]:
        return {
            'name': self.name,
            'count': self.count,
            'preview': [dict(item) for item in self.preview],
        }


@dataclass(frozen=True)
class GovQueueSnapshot:
    """Storage-neutral queue summary. The host owns queue persistence."""

    snapshot_id: str
    run_id: str
    lanes: tuple[GovQueueLane, ...] = field(default_factory=tuple)
    telemetry: Mapping[str, Any] = field(default_factory=dict)
    saved_at: str = ''
    profile: str = 'generic'
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> 'GovQueueSnapshot':
        raw = require_mapping(value, reason_code='invalid_queue_snapshot')
        snapshot_id = str(raw.get('snapshot_id') or raw.get('id') or '').strip()
        if not snapshot_id:
            raise GovApiError('missing_queue_snapshot_id')
        run_id = str(raw.get('run_id') or '').strip()
        if not run_id:
            raise GovApiError('missing_run_id')
        lanes = tuple(GovQueueLane.from_mapping(item) for item in list(raw.get('lanes') or ()))
        item = cls(
            snapshot_id=snapshot_id,
            run_id=run_id,
            lanes=lanes,
            telemetry=_metadata(raw.get('telemetry')),
            saved_at=str(raw.get('saved_at') or ''),
            profile=str(raw.get('profile') or 'generic'),
            metadata=_metadata(raw.get('metadata')),
        )
        validate_queue_snapshot(item)
        return item

    def as_dict(self) -> dict[str, Any]:
        return {
            'snapshot_id': self.snapshot_id,
            'run_id': self.run_id,
            'lanes': [lane.as_dict() for lane in self.lanes],
            'telemetry': dict(self.telemetry),
            'saved_at': self.saved_at,
            'profile': self.profile,
            'metadata': dict(self.metadata),
        }


@dataclass(frozen=True)
class GovRuntimeSnapshot:
    """Neutral runtime snapshot assembled from host-provided projections."""

    snapshot_id: str
    run_id: str
    state: str = 'idle'
    control_actions: tuple[GovControlAction, ...] = field(default_factory=tuple)
    queue_snapshot: GovQueueSnapshot | None = None
    updated_at: str = ''
    profile: str = 'generic'
    non_claims: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> 'GovRuntimeSnapshot':
        raw = require_mapping(value, reason_code='invalid_runtime_snapshot')
        snapshot_id = str(raw.get('snapshot_id') or raw.get('id') or '').strip()
        if not snapshot_id:
            raise GovApiError('missing_runtime_snapshot_id')
        run_id = str(raw.get('run_id') or '').strip()
        if not run_id:
            raise GovApiError('missing_run_id')
        state = str(raw.get('state') or 'idle').strip()
        if state not in RUNTIME_STATES:
            raise GovApiError(f'unknown_runtime_state:{state}')
        queue_raw = raw.get('queue_snapshot')
        queue_snapshot = GovQueueSnapshot.from_mapping(queue_raw) if isinstance(queue_raw, Mapping) else None
        if queue_snapshot is not None and queue_snapshot.run_id != run_id:
            raise GovApiError('queue_snapshot_run_mismatch')
        item = cls(
            snapshot_id=snapshot_id,
            run_id=run_id,
            state=state,
            control_actions=tuple(GovControlAction.from_mapping(action) for action in list(raw.get('control_actions') or ())),
            queue_snapshot=queue_snapshot,
            updated_at=str(raw.get('updated_at') or ''),
            profile=str(raw.get('profile') or 'generic'),
            non_claims=_tuple(raw.get('non_claims') or ()),
            metadata=_metadata(raw.get('metadata')),
        )
        validate_runtime_snapshot(item)
        return item

    def as_dict(self) -> dict[str, Any]:
        return {
            'snapshot_id': self.snapshot_id,
            'run_id': self.run_id,
            'state': self.state,
            'control_actions': [action.as_dict() for action in self.control_actions],
            'queue_snapshot': self.queue_snapshot.as_dict() if self.queue_snapshot is not None else None,
            'updated_at': self.updated_at,
            'profile': self.profile,
            'non_claims': list(self.non_claims),
            'metadata': dict(self.metadata),
        }


@dataclass(frozen=True)
class GovSchedulerTick:
    """Deterministic tick metadata. It does not schedule or enqueue work."""

    tick_id: str
    run_id: str
    due_action_refs: tuple[str, ...] = field(default_factory=tuple)
    heartbeat_status: str = 'unknown'
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> 'GovSchedulerTick':
        raw = require_mapping(value, reason_code='invalid_scheduler_tick')
        tick_id = str(raw.get('tick_id') or raw.get('id') or '').strip()
        if not tick_id:
            raise GovApiError('missing_scheduler_tick_id')
        run_id = str(raw.get('run_id') or '').strip()
        if not run_id:
            raise GovApiError('missing_run_id')
        item = cls(
            tick_id=tick_id,
            run_id=run_id,
            due_action_refs=_tuple(raw.get('due_action_refs') or ()),
            heartbeat_status=str(raw.get('heartbeat_status') or 'unknown'),
            metadata=_metadata(raw.get('metadata')),
        )
        validate_scheduler_tick(item)
        return item

    def as_dict(self) -> dict[str, Any]:
        return {
            'tick_id': self.tick_id,
            'run_id': self.run_id,
            'due_action_refs': list(self.due_action_refs),
            'heartbeat_status': self.heartbeat_status,
            'metadata': dict(self.metadata),
        }


def validate_control_action(value: Mapping[str, Any] | GovControlAction) -> GovControlAction:
    item = value if isinstance(value, GovControlAction) else GovControlAction.from_mapping(value)
    if item.action not in CONTROL_ACTIONS:
        raise GovApiError(f'unknown_control_action:{item.action}')
    if item.requested_state and item.requested_state not in RUNTIME_STATES:
        raise GovApiError(f'unknown_runtime_state:{item.requested_state}')
    _reject_forbidden_metadata(item.metadata)
    return item


def validate_queue_snapshot(value: Mapping[str, Any] | GovQueueSnapshot) -> GovQueueSnapshot:
    item = value if isinstance(value, GovQueueSnapshot) else GovQueueSnapshot.from_mapping(value)
    _reject_forbidden_metadata(item.telemetry)
    _reject_forbidden_metadata(item.metadata)
    for lane in item.lanes:
        GovQueueLane.from_mapping(lane.as_dict())
    return item


def validate_runtime_snapshot(value: Mapping[str, Any] | GovRuntimeSnapshot) -> GovRuntimeSnapshot:
    item = value if isinstance(value, GovRuntimeSnapshot) else GovRuntimeSnapshot.from_mapping(value)
    if item.state not in RUNTIME_STATES:
        raise GovApiError(f'unknown_runtime_state:{item.state}')
    _reject_forbidden_metadata(item.metadata)
    for action in item.control_actions:
        if action.run_id != item.run_id:
            raise GovApiError('control_action_run_mismatch')
        validate_control_action(action)
    if item.queue_snapshot is not None:
        validate_queue_snapshot(item.queue_snapshot)
    return item


def validate_scheduler_tick(value: Mapping[str, Any] | GovSchedulerTick) -> GovSchedulerTick:
    item = value if isinstance(value, GovSchedulerTick) else GovSchedulerTick.from_mapping(value)
    _reject_forbidden_metadata(item.metadata)
    return item


def control_action_from_host_action(
    *,
    action: str,
    run_id: str,
    action_id: str = '',
    reason_code: str = 'operator_requested',
    profile: str = 'generic',
    metadata: Mapping[str, Any] | None = None,
) -> GovControlAction:
    normalized = str(action or '').strip()
    if normalized not in CONTROL_ACTIONS:
        raise GovApiError(f'unknown_control_action:{normalized}')
    return validate_control_action(GovControlAction(
        action_id=action_id or f'{run_id}:{normalized}',
        run_id=run_id,
        action=normalized,
        reason_code=reason_code,
        requested_state=ACTION_TARGET_STATE[normalized],
        profile=profile,
        metadata=_metadata(metadata),
    ))


def queue_snapshot_from_lanes(
    *,
    snapshot_id: str,
    run_id: str,
    lanes: Mapping[str, Sequence[Mapping[str, Any]]],
    profile: str = 'generic',
    saved_at: str = '',
    telemetry: Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> GovQueueSnapshot:
    queue_lanes = tuple(
        GovQueueLane(name=str(name), count=len(items), preview=tuple(_metadata(item) for item in items))
        for name, items in sorted(lanes.items())
    )
    return validate_queue_snapshot(GovQueueSnapshot(
        snapshot_id=snapshot_id,
        run_id=run_id,
        lanes=queue_lanes,
        telemetry=_metadata(telemetry),
        saved_at=saved_at,
        profile=profile,
        metadata=_metadata(metadata),
    ))


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _tuple(values: Iterable[Any]) -> tuple[str, ...]:
    if isinstance(values, str):
        return (values,)
    try:
        return tuple(str(value) for value in values)
    except TypeError as exc:
        raise GovApiError('invalid_runtime_sequence') from exc


def _metadata(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise GovApiError('invalid_runtime_metadata')
    data = dict(value)
    _reject_forbidden_metadata(data)
    return data


def _reject_forbidden_metadata(value: Mapping[str, Any]) -> None:
    reason = _find_forbidden_key(value)
    if reason:
        raise GovApiError(f'forbidden_runtime_metadata:{reason}')


def _find_forbidden_key(value: Any) -> str:
    if isinstance(value, Mapping):
        forbidden = set(FORBIDDEN_RUNTIME_METADATA_KEYS)
        for key, item in value.items():
            normalized = str(key).lower()
            if normalized in forbidden:
                return normalized
            nested = _find_forbidden_key(item)
            if nested:
                return nested
    elif isinstance(value, (list, tuple)):
        for item in value:
            nested = _find_forbidden_key(item)
            if nested:
                return nested
    return ''
