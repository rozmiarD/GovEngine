from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

from govengine.api import GovApiError, require_mapping


POLICY_REQUEST_SCHEMA_VERSION = 'v0.1'
POLICY_VERDICT_SCHEMA_VERSION = 'v0.1'
POLICY_VERDICT_DECISIONS = ('allow', 'allow_with_obligations', 'approval_required', 'deny')
POLICY_RISK_CLASSES = ('low', 'medium', 'high', 'critical')
FORBIDDEN_POLICY_METADATA_KEYS = (
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
class PolicyRequest:
    """GovEngine policy evaluation input without raw runtime ownership."""

    request_id: str
    subject_ref: str
    schema_version: str = POLICY_REQUEST_SCHEMA_VERSION
    principal: Mapping[str, Any] = field(default_factory=dict)
    action: Mapping[str, Any] = field(default_factory=dict)
    resource: Mapping[str, Any] = field(default_factory=dict)
    context: Mapping[str, Any] = field(default_factory=dict)
    evidence_refs: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> 'PolicyRequest':
        raw = require_mapping(value, reason_code='invalid_policy_request')
        request_id = str(raw.get('request_id') or raw.get('id') or '').strip()
        if not request_id:
            raise GovApiError('missing_policy_request_id')
        subject_ref = str(raw.get('subject_ref') or '').strip()
        if not subject_ref:
            raise GovApiError('missing_policy_request_subject_ref')
        item = cls(
            request_id=request_id,
            subject_ref=subject_ref,
            schema_version=str(raw.get('schema_version') or POLICY_REQUEST_SCHEMA_VERSION).strip(),
            principal=_safe_mapping(raw.get('principal'), reason_code='invalid_policy_request_principal'),
            action=_safe_mapping(raw.get('action'), reason_code='invalid_policy_request_action'),
            resource=_safe_mapping(raw.get('resource'), reason_code='invalid_policy_request_resource'),
            context=_safe_mapping(raw.get('context'), reason_code='invalid_policy_request_context'),
            evidence_refs=_tuple(raw.get('evidence_refs') or raw.get('evidence') or ()),
            metadata=_safe_mapping(raw.get('metadata'), reason_code='invalid_policy_request_metadata'),
        )
        return validate_policy_request(item)

    def as_dict(self) -> dict[str, Any]:
        return {
            'request_id': self.request_id,
            'subject_ref': self.subject_ref,
            'schema_version': self.schema_version,
            'principal': dict(self.principal),
            'action': dict(self.action),
            'resource': dict(self.resource),
            'context': dict(self.context),
            'evidence_refs': list(self.evidence_refs),
            'metadata': dict(self.metadata),
        }


@dataclass(frozen=True)
class PolicyObligation:
    obligation_id: str
    kind: str
    description: str = ''
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> 'PolicyObligation':
        raw = require_mapping(value, reason_code='invalid_policy_obligation')
        obligation_id = str(raw.get('obligation_id') or raw.get('id') or '').strip()
        kind = str(raw.get('kind') or raw.get('type') or '').strip()
        if not obligation_id:
            raise GovApiError('missing_policy_obligation_id')
        if not kind:
            raise GovApiError('missing_policy_obligation_kind')
        item = cls(
            obligation_id=obligation_id,
            kind=kind,
            description=str(raw.get('description') or '').strip(),
            metadata=_safe_mapping(raw.get('metadata'), reason_code='invalid_policy_obligation_metadata'),
        )
        _reject_forbidden_policy_metadata(item.metadata)
        return item

    def as_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out['metadata'] = dict(self.metadata)
        return out


@dataclass(frozen=True)
class PolicyConstraint:
    constraint_id: str
    kind: str
    value: Any = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> 'PolicyConstraint':
        raw = require_mapping(value, reason_code='invalid_policy_constraint')
        constraint_id = str(raw.get('constraint_id') or raw.get('id') or '').strip()
        kind = str(raw.get('kind') or raw.get('type') or '').strip()
        if not constraint_id:
            raise GovApiError('missing_policy_constraint_id')
        if not kind:
            raise GovApiError('missing_policy_constraint_kind')
        item = cls(
            constraint_id=constraint_id,
            kind=kind,
            value=_json_safe(raw.get('value')),
            metadata=_safe_mapping(raw.get('metadata'), reason_code='invalid_policy_constraint_metadata'),
        )
        _reject_forbidden_policy_metadata(item.metadata)
        return item

    def as_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out['metadata'] = dict(self.metadata)
        return out


@dataclass(frozen=True)
class PolicyVerdict:
    """Deterministic policy result for GovEngine enforcement/admission."""

    verdict_id: str
    request_id: str
    subject_ref: str
    decision: str
    schema_version: str = POLICY_VERDICT_SCHEMA_VERSION
    reason_code: str = ''
    risk_class: str = 'low'
    risk_score: float = 0.0
    obligations: tuple[PolicyObligation, ...] = field(default_factory=tuple)
    constraints: tuple[PolicyConstraint, ...] = field(default_factory=tuple)
    blockers: tuple[str, ...] = field(default_factory=tuple)
    evidence_refs: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> 'PolicyVerdict':
        raw = require_mapping(value, reason_code='invalid_policy_verdict')
        verdict_id = str(raw.get('verdict_id') or raw.get('policy_id') or raw.get('id') or '').strip()
        request_id = str(raw.get('request_id') or '').strip()
        subject_ref = str(raw.get('subject_ref') or '').strip()
        if not verdict_id:
            raise GovApiError('missing_policy_verdict_id')
        if not request_id:
            raise GovApiError('missing_policy_verdict_request_id')
        if not subject_ref:
            raise GovApiError('missing_policy_verdict_subject_ref')
        item = cls(
            verdict_id=verdict_id,
            request_id=request_id,
            subject_ref=subject_ref,
            decision=str(raw.get('decision') or '').strip(),
            schema_version=str(raw.get('schema_version') or POLICY_VERDICT_SCHEMA_VERSION).strip(),
            reason_code=str(raw.get('reason_code') or raw.get('decision') or '').strip(),
            risk_class=str(raw.get('risk_class') or 'low').strip(),
            risk_score=float(raw.get('risk_score') or 0.0),
            obligations=_obligations(raw.get('obligations') or ()),
            constraints=_constraints(raw.get('constraints') or ()),
            blockers=_tuple(raw.get('blockers') or ()),
            evidence_refs=_tuple(raw.get('evidence_refs') or raw.get('evidence') or ()),
            metadata=_safe_mapping(raw.get('metadata'), reason_code='invalid_policy_verdict_metadata'),
        )
        return validate_policy_verdict(item)

    def as_dict(self) -> dict[str, Any]:
        return {
            'verdict_id': self.verdict_id,
            'request_id': self.request_id,
            'subject_ref': self.subject_ref,
            'schema_version': self.schema_version,
            'decision': self.decision,
            'reason_code': self.reason_code,
            'risk_class': self.risk_class,
            'risk_score': self.risk_score,
            'obligations': [item.as_dict() for item in self.obligations],
            'constraints': [item.as_dict() for item in self.constraints],
            'blockers': list(self.blockers),
            'evidence_refs': list(self.evidence_refs),
            'metadata': dict(self.metadata),
        }


def validate_policy_request(value: Mapping[str, Any] | PolicyRequest) -> PolicyRequest:
    item = value if isinstance(value, PolicyRequest) else PolicyRequest.from_mapping(value)
    if item.schema_version != POLICY_REQUEST_SCHEMA_VERSION:
        raise GovApiError(f'unknown_policy_request_schema_version:{item.schema_version or "missing"}')
    for payload in (item.principal, item.action, item.resource, item.context, item.metadata):
        _reject_forbidden_policy_metadata(payload)
    return item


def validate_policy_verdict(value: Mapping[str, Any] | PolicyVerdict) -> PolicyVerdict:
    item = value if isinstance(value, PolicyVerdict) else PolicyVerdict.from_mapping(value)
    if item.schema_version != POLICY_VERDICT_SCHEMA_VERSION:
        raise GovApiError(f'unknown_policy_verdict_schema_version:{item.schema_version or "missing"}')
    if item.decision not in POLICY_VERDICT_DECISIONS:
        raise GovApiError(f'unknown_policy_verdict_decision:{item.decision or "missing"}')
    if item.risk_class not in POLICY_RISK_CLASSES:
        raise GovApiError(f'unknown_policy_risk_class:{item.risk_class}')
    if item.risk_score < 0.0 or item.risk_score > 1.0:
        raise GovApiError('invalid_policy_risk_score')
    if item.decision == 'deny' and not item.blockers:
        raise GovApiError('policy_deny_without_blocker')
    if item.decision == 'approval_required' and not item.blockers:
        raise GovApiError('policy_approval_without_blocker')
    _reject_forbidden_policy_metadata(item.metadata)
    return item


def _obligations(values: Any) -> tuple[PolicyObligation, ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, (list, tuple)):
        raise GovApiError('invalid_policy_obligations')
    return tuple(value if isinstance(value, PolicyObligation) else PolicyObligation.from_mapping(value) for value in values)


def _constraints(values: Any) -> tuple[PolicyConstraint, ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, (list, tuple)):
        raise GovApiError('invalid_policy_constraints')
    return tuple(value if isinstance(value, PolicyConstraint) else PolicyConstraint.from_mapping(value) for value in values)


def _safe_mapping(value: Any, *, reason_code: str) -> dict[str, Any]:
    if value is None:
        return {}
    raw = require_mapping(value, reason_code=reason_code)
    return {str(key): _json_safe(raw[key]) for key in raw}


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _tuple(values: Any) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        return (str(values),)
    if not isinstance(values, (list, tuple, set)):
        return ()
    return tuple(str(value).strip() for value in values if str(value).strip())


def _reject_forbidden_policy_metadata(value: Mapping[str, Any]) -> None:
    key = _find_forbidden_key(value)
    if key:
        raise GovApiError(f'forbidden_policy_metadata:{key}')


def _find_forbidden_key(value: Mapping[str, Any]) -> str:
    for key, item in value.items():
        name = str(key).lower()
        if name in FORBIDDEN_POLICY_METADATA_KEYS:
            return name
        if isinstance(item, Mapping):
            found = _find_forbidden_key(item)
            if found:
                return found
        if isinstance(item, (list, tuple)):
            for entry in item:
                if isinstance(entry, Mapping):
                    found = _find_forbidden_key(entry)
                    if found:
                        return found
    return ''
