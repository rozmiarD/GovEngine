from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

from govengine.api import GovApiError, require_mapping
from govengine.state_machine import GovRunState, StateTransition, apply_state_transition, validate_state_transition


ALLOWED_CONTROL_ACTIONS = (
    'advance_state',
    'record_only',
    'pause',
    'block',
    'request_profile_handoff',
)

FORBIDDEN_CONTROL_METADATA_KEYS = (
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
    'queue',
    'scheduler',
    'schedule',
    'delivery',
    'transport_payload',
    'runtime_storage',
    'storage_path',
    'live_execution',
    'live_backend',
)


@dataclass(frozen=True)
class ControlDecision:
    """Deterministic between-step control decision, not a runtime command."""

    decision_id: str
    run_id: str
    action: str
    reason_code: str = 'ok'
    from_state: str = ''
    to_state: str = ''
    profile: str = 'generic'
    event_refs: tuple[str, ...] = field(default_factory=tuple)
    required_decisions: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> 'ControlDecision':
        raw = require_mapping(value, reason_code='invalid_control_decision')
        if 'raw_intent' in raw or 'prompt' in raw:
            raise GovApiError('raw_intent_not_control_decision')
        decision_id = str(raw.get('decision_id') or raw.get('id') or '').strip()
        if not decision_id:
            raise GovApiError('missing_control_decision_id')
        run_id = str(raw.get('run_id') or '').strip()
        if not run_id:
            raise GovApiError('missing_run_id')
        action = str(raw.get('action') or '').strip()
        if action not in ALLOWED_CONTROL_ACTIONS:
            raise GovApiError(f'unknown_control_action:{action}')
        metadata = raw.get('metadata') if isinstance(raw.get('metadata'), Mapping) else {}
        _reject_forbidden_metadata(metadata)
        decision = cls(
            decision_id=decision_id,
            run_id=run_id,
            action=action,
            reason_code=str(raw.get('reason_code') or 'ok'),
            from_state=str(raw.get('from_state') or '').strip(),
            to_state=str(raw.get('to_state') or '').strip(),
            profile=str(raw.get('profile') or 'generic'),
            event_refs=_tuple(raw.get('event_refs') or ()),
            required_decisions=_tuple(raw.get('required_decisions') or ()),
            metadata=dict(metadata),
        )
        validate_control_decision(decision)
        return decision

    @property
    def state_transition(self) -> StateTransition | None:
        if self.action not in {'advance_state', 'pause', 'block'}:
            return None
        if not self.from_state or not self.to_state:
            return None
        return StateTransition(
            run_id=self.run_id,
            from_state=self.from_state,
            to_state=self.to_state,
            reason_code=self.reason_code,
            event_ref=self.event_refs[-1] if self.event_refs else '',
            required_decisions=self.required_decisions,
            metadata=self.metadata,
        )

    def as_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out['event_refs'] = list(self.event_refs)
        out['required_decisions'] = list(self.required_decisions)
        out['metadata'] = dict(self.metadata)
        return out


def validate_control_decision(value: Mapping[str, Any] | ControlDecision) -> ControlDecision:
    decision = value if isinstance(value, ControlDecision) else ControlDecision.from_mapping(value)
    if decision.action not in ALLOWED_CONTROL_ACTIONS:
        raise GovApiError(f'unknown_control_action:{decision.action}')
    _reject_forbidden_metadata(decision.metadata)
    if decision.action in {'advance_state', 'pause', 'block'}:
        if not decision.from_state or not decision.to_state:
            raise GovApiError('control_decision_missing_state_transition')
        if decision.action == 'pause' and decision.to_state != 'paused':
            raise GovApiError('pause_control_must_target_paused')
        if decision.action == 'block' and decision.to_state != 'blocked':
            raise GovApiError('block_control_must_target_blocked')
        transition = decision.state_transition
        if transition is None:
            raise GovApiError('control_decision_missing_state_transition')
        validate_state_transition(transition)
    elif decision.from_state or decision.to_state:
        raise GovApiError('record_control_must_not_claim_state_transition')
    return decision


def apply_control_decision(state: GovRunState, decision: ControlDecision) -> GovRunState:
    checked = validate_control_decision(decision)
    transition = checked.state_transition
    if transition is None:
        if state.run_id != checked.run_id:
            raise GovApiError('control_decision_run_mismatch')
        return state
    return apply_state_transition(state, transition)


def _tuple(values: Any) -> tuple[str, ...]:
    if isinstance(values, str):
        return (values,)
    try:
        return tuple(str(value) for value in values)
    except TypeError as exc:
        raise GovApiError('invalid_control_sequence') from exc


def _reject_forbidden_metadata(value: Mapping[str, Any]) -> None:
    reason = _find_forbidden_key(value)
    if reason:
        raise GovApiError(f'forbidden_control_metadata:{reason}')


def _find_forbidden_key(value: Any) -> str:
    if isinstance(value, Mapping):
        forbidden = set(FORBIDDEN_CONTROL_METADATA_KEYS)
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
