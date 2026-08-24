from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

from govengine.api import GovApiError, require_mapping
from govengine._governance_validation import find_bounded_governance_key


RUN_STATES = (
    'new',
    'admitted',
    'policy_checked',
    'trust_checked',
    'gated',
    'running_dry_run',
    'receipt_recorded',
    'paused',
    'blocked',
    'completed',
)

ALLOWED_TRANSITIONS = {
    'new': ('admitted', 'blocked'),
    'admitted': ('policy_checked', 'blocked'),
    'policy_checked': ('trust_checked', 'blocked'),
    'trust_checked': ('gated', 'blocked'),
    'gated': ('running_dry_run', 'paused', 'blocked'),
    'running_dry_run': ('receipt_recorded', 'paused', 'blocked'),
    'receipt_recorded': ('completed', 'blocked'),
    'paused': ('gated', 'blocked'),
    'blocked': ('admitted',),
    'completed': (),
}

FORBIDDEN_STATE_METADATA_KEYS = (
    'raw_intent',
    'prompt',
    'credential',
    'credentials',
    'secret',
    'token',
    'password',
    'api_key',
    'runtime_storage',
    'storage_path',
    'queue',
    'scheduler',
    'schedule',
    'live_execution',
    'live_backend',
    'command',
    'subprocess',
    'shell',
)


@dataclass(frozen=True)
class GovRunState:
    """Transport- and storage-neutral run state summary."""

    run_id: str
    state: str = 'new'
    profile: str = 'generic'
    event_refs: tuple[str, ...] = field(default_factory=tuple)
    artifact_refs: tuple[str, ...] = field(default_factory=tuple)
    blockers: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> 'GovRunState':
        raw = require_mapping(value, reason_code='invalid_run_state')
        run_id = str(raw.get('run_id') or raw.get('id') or '').strip()
        if not run_id:
            raise GovApiError('missing_run_id')
        state = str(raw.get('state') or 'new')
        if state not in RUN_STATES:
            raise GovApiError(f'unknown_run_state:{state}')
        metadata = raw.get('metadata') if isinstance(raw.get('metadata'), Mapping) else {}
        _reject_forbidden_metadata(metadata)
        return cls(
            run_id=run_id,
            state=state,
            profile=str(raw.get('profile') or 'generic'),
            event_refs=_tuple(raw.get('event_refs') or ()),
            artifact_refs=_tuple(raw.get('artifact_refs') or ()),
            blockers=_tuple(raw.get('blockers') or ()),
            metadata=dict(metadata),
        )

    @property
    def terminal(self) -> bool:
        return self.state == 'completed'

    @property
    def blocked(self) -> bool:
        return self.state == 'blocked' or bool(self.blockers)

    def as_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out['event_refs'] = list(self.event_refs)
        out['artifact_refs'] = list(self.artifact_refs)
        out['blockers'] = list(self.blockers)
        out['metadata'] = dict(self.metadata)
        out['terminal'] = self.terminal
        out['blocked'] = self.blocked
        return out


@dataclass(frozen=True)
class StateTransition:
    """Deterministic state transition request, not a runtime mutation."""

    run_id: str
    from_state: str
    to_state: str
    reason_code: str = 'ok'
    event_ref: str = ''
    required_decisions: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> 'StateTransition':
        raw = require_mapping(value, reason_code='invalid_state_transition')
        if any(
            str(key).strip().casefold() in {'raw_intent', 'prompt'}
            for key in raw
        ):
            raise GovApiError('raw_intent_not_state_transition')
        run_id = str(raw.get('run_id') or '').strip()
        if not run_id:
            raise GovApiError('missing_run_id')
        from_state = str(raw.get('from_state') or '').strip()
        to_state = str(raw.get('to_state') or '').strip()
        if not from_state or not to_state:
            raise GovApiError('missing_state_transition_endpoint')
        metadata = raw.get('metadata') if isinstance(raw.get('metadata'), Mapping) else {}
        _reject_forbidden_metadata(metadata)
        transition = cls(
            run_id=run_id,
            from_state=from_state,
            to_state=to_state,
            reason_code=str(raw.get('reason_code') or 'ok'),
            event_ref=str(raw.get('event_ref') or ''),
            required_decisions=_tuple(raw.get('required_decisions') or ()),
            metadata=dict(metadata),
        )
        validate_state_transition(transition)
        return transition

    def as_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out['required_decisions'] = list(self.required_decisions)
        out['metadata'] = dict(self.metadata)
        return out


def validate_run_state(value: Mapping[str, Any] | GovRunState) -> GovRunState:
    state = value if isinstance(value, GovRunState) else GovRunState.from_mapping(value)
    if state.state not in RUN_STATES:
        raise GovApiError(f'unknown_run_state:{state.state}')
    _reject_forbidden_metadata(state.metadata)
    return state


def validate_state_transition(value: Mapping[str, Any] | StateTransition) -> StateTransition:
    transition = value if isinstance(value, StateTransition) else StateTransition.from_mapping(value)
    if transition.from_state not in RUN_STATES:
        raise GovApiError(f'unknown_run_state:{transition.from_state}')
    if transition.to_state not in RUN_STATES:
        raise GovApiError(f'unknown_run_state:{transition.to_state}')
    allowed = ALLOWED_TRANSITIONS[transition.from_state]
    if transition.to_state not in allowed:
        raise GovApiError(f'invalid_state_transition:{transition.from_state}->{transition.to_state}')
    if transition.to_state == 'running_dry_run' and 'runner_gate_decision' not in transition.required_decisions:
        raise GovApiError('missing_runner_gate_decision')
    _reject_forbidden_metadata(transition.metadata)
    return transition


def apply_state_transition(state: GovRunState, transition: StateTransition) -> GovRunState:
    current = validate_run_state(state)
    step = validate_state_transition(transition)
    if current.run_id != step.run_id:
        raise GovApiError('state_transition_run_mismatch')
    if current.state != step.from_state:
        raise GovApiError(f'state_transition_from_mismatch:{current.state}!={step.from_state}')
    event_refs = current.event_refs + ((step.event_ref,) if step.event_ref else ())
    blockers = current.blockers
    if step.to_state == 'blocked' and step.reason_code != 'ok':
        blockers = tuple(dict.fromkeys(current.blockers + (step.reason_code,)))
    return GovRunState(
        run_id=current.run_id,
        state=step.to_state,
        profile=current.profile,
        event_refs=event_refs,
        artifact_refs=current.artifact_refs,
        blockers=blockers,
        metadata=current.metadata,
    )


def _tuple(values: Any) -> tuple[str, ...]:
    if isinstance(values, str):
        return (values,)
    try:
        return tuple(str(value) for value in values)
    except TypeError as exc:
        raise GovApiError('invalid_state_sequence') from exc


def _reject_forbidden_metadata(value: Mapping[str, Any]) -> None:
    reason = _find_forbidden_key(value)
    if reason:
        raise GovApiError(f'forbidden_state_metadata:{reason}')


def _find_forbidden_key(value: Any) -> str:
    return find_bounded_governance_key(value, FORBIDDEN_STATE_METADATA_KEYS)
