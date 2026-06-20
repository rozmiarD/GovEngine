from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from govengine.api import GovApiError, require_mapping
from govengine.policy.model import PolicyConstraint, PolicyObligation


POLICY_PACK_SCHEMA_VERSION = 'v0.1'
POLICY_RULE_EFFECTS = ('allow', 'allow_with_obligations', 'approval_required', 'deny')


@dataclass(frozen=True)
class PolicyRule:
    rule_id: str
    effect: str
    conditions: Mapping[str, Any]
    priority: int = 100
    reason_code: str = ''
    risk_class: str = 'low'
    risk_score: float = 0.0
    obligations: tuple[PolicyObligation, ...] = field(default_factory=tuple)
    constraints: tuple[PolicyConstraint, ...] = field(default_factory=tuple)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> 'PolicyRule':
        raw = require_mapping(value, reason_code='invalid_policy_rule')
        rule_id = str(raw.get('rule_id') or raw.get('id') or '').strip()
        effect = str(raw.get('effect') or raw.get('decision') or '').strip()
        if not rule_id:
            raise GovApiError('missing_policy_rule_id')
        if effect not in POLICY_RULE_EFFECTS:
            raise GovApiError(f'unknown_policy_rule_effect:{effect or "missing"}')
        conditions = _safe_mapping(raw.get('conditions'), reason_code='invalid_policy_rule_conditions')
        if not conditions:
            raise GovApiError('policy_rule_without_conditions')
        return cls(
            rule_id=rule_id,
            effect=effect,
            conditions=conditions,
            priority=int(raw.get('priority') or 100),
            reason_code=str(raw.get('reason_code') or effect).strip() or effect,
            risk_class=str(raw.get('risk_class') or 'low').strip(),
            risk_score=float(raw.get('risk_score') or 0.0),
            obligations=_obligations(raw.get('obligations') or ()),
            constraints=_constraints(raw.get('constraints') or ()),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            'rule_id': self.rule_id,
            'effect': self.effect,
            'conditions': dict(self.conditions),
            'priority': self.priority,
            'reason_code': self.reason_code,
            'risk_class': self.risk_class,
            'risk_score': self.risk_score,
            'obligations': [item.as_dict() for item in self.obligations],
            'constraints': [item.as_dict() for item in self.constraints],
        }


@dataclass(frozen=True)
class CompiledPolicyPack:
    policy_id: str
    version: str
    schema_version: str = POLICY_PACK_SCHEMA_VERSION
    rules: tuple[PolicyRule, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            'policy_id': self.policy_id,
            'version': self.version,
            'schema_version': self.schema_version,
            'rules': [rule.as_dict() for rule in self.rules],
            'metadata': dict(self.metadata),
        }


@dataclass(frozen=True)
class CompileResult:
    status: str
    policy_pack: CompiledPolicyPack | None = None
    reason_code: str = 'compiled'
    diagnostics: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return self.status == 'compiled' and self.policy_pack is not None

    def as_dict(self) -> dict[str, Any]:
        return {
            'status': self.status,
            'ok': self.ok,
            'reason_code': self.reason_code,
            'diagnostics': list(self.diagnostics),
            'policy_pack': self.policy_pack.as_dict() if self.policy_pack else {},
        }


class PolicyCompiler:
    """Compile declarative policy packs into deterministic rule order."""

    def compile(self, policy_pack: Mapping[str, Any]) -> CompileResult:
        try:
            compiled = self._compile_or_raise(policy_pack)
        except GovApiError as exc:
            return CompileResult(status='rejected', reason_code=exc.reason_code, diagnostics=(str(exc),))
        return CompileResult(status='compiled', policy_pack=compiled)

    def _compile_or_raise(self, policy_pack: Mapping[str, Any]) -> CompiledPolicyPack:
        raw = require_mapping(policy_pack, reason_code='invalid_policy_pack')
        policy_id = str(raw.get('policy_id') or raw.get('id') or '').strip()
        version = str(raw.get('version') or '').strip()
        if not policy_id:
            raise GovApiError('missing_policy_pack_id')
        if not version:
            raise GovApiError('missing_policy_pack_version')
        schema_version = str(raw.get('schema_version') or POLICY_PACK_SCHEMA_VERSION).strip()
        if schema_version != POLICY_PACK_SCHEMA_VERSION:
            raise GovApiError(f'unknown_policy_pack_schema_version:{schema_version or "missing"}')
        raw_rules = raw.get('rules')
        if not isinstance(raw_rules, (list, tuple)) or not raw_rules:
            raise GovApiError('policy_pack_without_rules')
        rules = tuple(sorted((PolicyRule.from_mapping(rule) for rule in raw_rules), key=lambda item: (item.priority, item.rule_id)))
        _reject_conflicts(rules)
        return CompiledPolicyPack(
            policy_id=policy_id,
            version=version,
            schema_version=schema_version,
            rules=rules,
            metadata=_safe_mapping(raw.get('metadata'), reason_code='invalid_policy_pack_metadata'),
        )


def compile_policy_pack(policy_pack: Mapping[str, Any]) -> CompileResult:
    return PolicyCompiler().compile(policy_pack)


def _reject_conflicts(rules: tuple[PolicyRule, ...]) -> None:
    seen: dict[tuple[tuple[str, str], ...], str] = {}
    for rule in rules:
        fingerprint = tuple(sorted((str(key), repr(value)) for key, value in rule.conditions.items()))
        previous = seen.get(fingerprint)
        if previous and previous != rule.effect:
            raise GovApiError('conflicting_policy_rules')
        seen[fingerprint] = rule.effect


def _obligations(values: Any) -> tuple[PolicyObligation, ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, (list, tuple)):
        raise GovApiError('invalid_policy_rule_obligations')
    return tuple(value if isinstance(value, PolicyObligation) else PolicyObligation.from_mapping(value) for value in values)


def _constraints(values: Any) -> tuple[PolicyConstraint, ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, (list, tuple)):
        raise GovApiError('invalid_policy_rule_constraints')
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
