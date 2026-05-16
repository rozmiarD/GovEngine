from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

from govengine.api import GovApiError, require_mapping


ALLOWED_EVENT_TYPES = (
    'artifact_state_changed',
    'policy_decision_recorded',
    'trust_decision_recorded',
    'runner_receipt_recorded',
    'ooda_control_decision_recorded',
    'profile_handoff_requested',
    'profile_handoff_completed',
)

FORBIDDEN_EVENT_PAYLOAD_KEYS = (
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
    'carrier_delivery',
    'transport_payload',
)


@dataclass(frozen=True)
class GovEvent:
    """Neutral event metadata consumed by GovEngine orchestration contracts."""

    event_type: str
    subject: str
    status: str = 'recorded'
    profile: str = 'generic'
    refs: tuple[str, ...] = field(default_factory=tuple)
    payload: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> 'GovEvent':
        raw = require_mapping(value, reason_code='invalid_gov_event')
        event_type = str(raw.get('event_type') or raw.get('type') or '').strip()
        if not event_type:
            raise GovApiError('missing_event_type')
        if event_type not in ALLOWED_EVENT_TYPES:
            raise GovApiError(f'unknown_event_type:{event_type}')
        subject = str(raw.get('subject') or '').strip()
        if not subject:
            raise GovApiError('missing_event_subject')
        payload = raw.get('payload') if isinstance(raw.get('payload'), Mapping) else {}
        _reject_forbidden_payload(payload)
        return cls(
            event_type=event_type,
            subject=subject,
            status=str(raw.get('status') or 'recorded'),
            profile=str(raw.get('profile') or 'generic'),
            refs=_tuple(raw.get('refs') or ()),
            payload=dict(payload),
        )

    def as_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out['refs'] = list(self.refs)
        out['payload'] = dict(self.payload)
        return out


@dataclass(frozen=True)
class EventEnvelope:
    """Transport-neutral event envelope without scheduling or delivery authority."""

    event: GovEvent
    source: str = 'host_runtime'
    correlation_id: str = ''
    sequence: int = 0
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> 'EventEnvelope':
        raw = require_mapping(value, reason_code='invalid_event_envelope')
        if 'delivery' in raw or 'transport' in raw or 'schedule' in raw:
            raise GovApiError('event_envelope_must_not_claim_delivery_or_schedule')
        event_value = raw.get('event')
        if not isinstance(event_value, Mapping):
            raise GovApiError('missing_event')
        metadata = raw.get('metadata') if isinstance(raw.get('metadata'), Mapping) else {}
        _reject_forbidden_payload(metadata)
        return cls(
            event=GovEvent.from_mapping(event_value),
            source=str(raw.get('source') or 'host_runtime'),
            correlation_id=str(raw.get('correlation_id') or ''),
            sequence=int(raw.get('sequence') or 0),
            metadata=dict(metadata),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            'event': self.event.as_dict(),
            'source': self.source,
            'correlation_id': self.correlation_id,
            'sequence': self.sequence,
            'metadata': dict(self.metadata),
        }


def validate_gov_event(value: Mapping[str, Any] | GovEvent) -> GovEvent:
    event = value if isinstance(value, GovEvent) else GovEvent.from_mapping(value)
    if event.event_type not in ALLOWED_EVENT_TYPES:
        raise GovApiError(f'unknown_event_type:{event.event_type}')
    if not event.subject.strip():
        raise GovApiError('missing_event_subject')
    _reject_forbidden_payload(event.payload)
    return event


def validate_event_envelope(value: Mapping[str, Any] | EventEnvelope) -> EventEnvelope:
    envelope = value if isinstance(value, EventEnvelope) else EventEnvelope.from_mapping(value)
    validate_gov_event(envelope.event)
    _reject_forbidden_payload(envelope.metadata)
    return envelope


def _tuple(values: Any) -> tuple[str, ...]:
    if isinstance(values, str):
        return (values,)
    try:
        return tuple(str(value) for value in values)
    except TypeError as exc:
        raise GovApiError('invalid_event_refs') from exc


def _reject_forbidden_payload(value: Mapping[str, Any]) -> None:
    reason = _find_forbidden_payload_key(value)
    if reason:
        raise GovApiError(f'forbidden_event_payload:{reason}')


def _find_forbidden_payload_key(value: Any) -> str:
    if isinstance(value, Mapping):
        forbidden = set(FORBIDDEN_EVENT_PAYLOAD_KEYS)
        for key, item in value.items():
            normalized = str(key).lower()
            if normalized in forbidden:
                return normalized
            nested = _find_forbidden_payload_key(item)
            if nested:
                return nested
    elif isinstance(value, (list, tuple)):
        for item in value:
            nested = _find_forbidden_payload_key(item)
            if nested:
                return nested
    return ''
