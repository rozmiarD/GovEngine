from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timezone
import math
import re
from typing import Any, Mapping

from govengine._json_boundary import bounded_json_copy
from govengine._governance_validation import parse_aware_timestamp
from govengine.api import GovApiError, require_mapping
from govengine.policy.model import POLICY_RISK_CLASSES, PolicyConstraint, PolicyObligation
from govengine.policy.reasons import validate_policy_reason_code
from govengine.signing import govengine_record_digest


POLICY_PACK_SCHEMA_VERSION = 'v0.1'
POLICY_PACK_V1_SCHEMA_VERSION = 'v1'
POLICY_PACK_SCHEMA_VERSIONS = (POLICY_PACK_SCHEMA_VERSION, POLICY_PACK_V1_SCHEMA_VERSION)
POLICY_RULE_EFFECTS = ('allow', 'allow_with_obligations', 'approval_required', 'deny')
POLICY_CONDITION_OPERATORS = (
    'eq',
    'neq',
    'in',
    'not_in',
    'contains',
    'exists',
    'lt',
    'lte',
    'gt',
    'gte',
    'subset_of',
    'matches_namespace',
)
POLICY_CONDITION_NAMESPACES = (
    'principal',
    'action',
    'resource',
    'request_context',
    'context',
)
_PATH_SEGMENT = re.compile(r'^[A-Za-z_][A-Za-z0-9_-]*$')
_NUMERIC_OPERATORS = frozenset({'lt', 'lte', 'gt', 'gte'})
_LIST_OPERATORS = frozenset({'in', 'not_in', 'subset_of'})
MAX_POLICY_RULES = 256
MAX_POLICY_CONDITIONS_PER_RULE = 32
MAX_POLICY_TOTAL_CONDITIONS = 4096
MAX_POLICY_CONTROLS_PER_RULE = 64
_POLICY_PACK_V1_FIELDS = frozenset(
    {
        'policy_id',
        'version',
        'schema_version',
        'issuer_ref',
        'policy_epoch',
        'validity',
        'supersedes',
        'rules',
        'metadata',
    }
)
_POLICY_RULE_V1_FIELDS = frozenset(
    {
        'rule_id',
        'effect',
        'conditions',
        'priority',
        'reason_code',
        'risk_class',
        'risk_score',
        'obligations',
        'constraints',
    }
)
_POLICY_VALIDITY_V1_FIELDS = frozenset({'not_before', 'expires_at'})
_POLICY_CONDITION_V1_FIELDS = frozenset({'path', 'operator', 'value'})


def _reject_unknown_fields(
    value: Mapping[str, Any],
    *,
    allowed: frozenset[str],
    reason_code: str,
) -> None:
    unknown = set(value) - allowed
    if unknown:
        raise GovApiError(
            reason_code,
            context={'field': sorted(str(item) for item in unknown)[0]},
        )


@dataclass(frozen=True)
class PolicyCondition:
    """One typed, deterministic policy predicate."""

    path: str
    operator: str
    value: Any

    def __post_init__(self) -> None:
        _validate_condition(self)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> 'PolicyCondition':
        raw = require_mapping(value, reason_code='invalid_policy_condition')
        _reject_unknown_fields(
            raw,
            allowed=_POLICY_CONDITION_V1_FIELDS,
            reason_code='unknown_policy_condition_field',
        )
        if 'value' not in raw:
            raise GovApiError('missing_policy_condition_value')
        return cls(
            path=str(raw.get('path') or '').strip(),
            operator=str(raw.get('operator') or '').strip(),
            value=bounded_json_copy(raw['value']),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            'path': self.path,
            'operator': self.operator,
            'value': bounded_json_copy(self.value),
        }


@dataclass(frozen=True)
class PolicyRule:
    rule_id: str
    effect: str
    conditions: tuple[PolicyCondition, ...]
    priority: int = 100
    reason_code: str = ''
    risk_class: str = 'low'
    risk_score: float = 0.0
    obligations: tuple[PolicyObligation, ...] = field(default_factory=tuple)
    constraints: tuple[PolicyConstraint, ...] = field(default_factory=tuple)

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any],
        *,
        schema_version: str = POLICY_PACK_SCHEMA_VERSION,
    ) -> 'PolicyRule':
        raw = require_mapping(value, reason_code='invalid_policy_rule')
        if schema_version == POLICY_PACK_V1_SCHEMA_VERSION:
            _reject_unknown_fields(
                raw,
                allowed=_POLICY_RULE_V1_FIELDS,
                reason_code='invalid_policy_rule',
            )
        rule_id = str(raw.get('rule_id') or raw.get('id') or '').strip()
        effect = str(raw.get('effect') or raw.get('decision') or '').strip()
        if not rule_id:
            raise GovApiError('missing_policy_rule_id')
        if effect not in POLICY_RULE_EFFECTS:
            raise GovApiError(f'unknown_policy_rule_effect:{effect or "missing"}')
        conditions = _conditions(raw.get('conditions'), schema_version=schema_version)
        raw_priority = raw.get('priority', 100)
        if (
            isinstance(raw_priority, bool)
            or not isinstance(raw_priority, int)
            or raw_priority < 0
            or raw_priority > 1_000_000
        ):
            raise GovApiError('invalid_policy_rule_priority')
        obligations = _obligations(raw.get('obligations') or ())
        constraints = _constraints(raw.get('constraints') or ())
        if len(obligations) + len(constraints) > MAX_POLICY_CONTROLS_PER_RULE:
            raise GovApiError('policy_rule_control_limit_exceeded')
        raw_reason_code = raw.get('reason_code')
        reason_code = (
            effect
            if raw_reason_code is None or raw_reason_code == ''
            else validate_policy_reason_code(raw_reason_code)
        )
        raw_risk_class = raw.get('risk_class', 'low')
        if not isinstance(raw_risk_class, str) or raw_risk_class not in POLICY_RISK_CLASSES:
            raise GovApiError('invalid_policy_risk_class')
        raw_risk_score = raw.get('risk_score', 0.0)
        if (
            isinstance(raw_risk_score, bool)
            or not isinstance(raw_risk_score, (int, float))
            or not math.isfinite(raw_risk_score)
            or raw_risk_score < 0
            or raw_risk_score > 1
        ):
            raise GovApiError('invalid_policy_risk_score')
        return cls(
            rule_id=rule_id,
            effect=effect,
            conditions=conditions,
            priority=raw_priority,
            reason_code=reason_code,
            risk_class=raw_risk_class,
            risk_score=float(raw_risk_score),
            obligations=obligations,
            constraints=constraints,
        )

    def as_dict(self, *, schema_version: str = POLICY_PACK_SCHEMA_VERSION) -> dict[str, Any]:
        if schema_version == 'v0.1':
            conditions: Any = {item.path: bounded_json_copy(item.value) for item in self.conditions}
        else:
            conditions = [item.as_dict() for item in self.conditions]
        return {
            'rule_id': self.rule_id,
            'effect': self.effect,
            'conditions': conditions,
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
    issuer_ref: str = ''
    policy_epoch: int = 0
    not_before: str = ''
    expires_at: str = ''
    supersedes: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            'policy_id': self.policy_id,
            'version': self.version,
            'schema_version': self.schema_version,
            'rules': [
                rule.as_dict(schema_version=self.schema_version)
                for rule in self.rules
            ],
            'metadata': dict(self.metadata),
        }
        if self.schema_version == 'v1':
            payload.update(
                {
                    'issuer_ref': self.issuer_ref,
                    'policy_epoch': self.policy_epoch,
                    'validity': {
                        'not_before': self.not_before,
                        'expires_at': self.expires_at,
                    },
                    'supersedes': list(self.supersedes),
                }
            )
        return payload


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
        raw = require_mapping(
            bounded_json_copy(policy_pack),
            reason_code='invalid_policy_pack',
        )
        policy_id = str(raw.get('policy_id') or raw.get('id') or '').strip()
        version = str(raw.get('version') or '').strip()
        if not policy_id:
            raise GovApiError('missing_policy_pack_id')
        if not version:
            raise GovApiError('missing_policy_pack_version')
        schema_version = str(raw.get('schema_version') or POLICY_PACK_SCHEMA_VERSION).strip()
        if schema_version not in POLICY_PACK_SCHEMA_VERSIONS:
            raise GovApiError(f'unknown_policy_pack_schema_version:{schema_version or "missing"}')
        if schema_version == POLICY_PACK_V1_SCHEMA_VERSION:
            _reject_unknown_fields(
                raw,
                allowed=_POLICY_PACK_V1_FIELDS,
                reason_code='invalid_policy_pack',
            )
        issuer_ref = ''
        policy_epoch = 0
        not_before = ''
        expires_at = ''
        supersedes: tuple[str, ...] = ()
        if schema_version == 'v1':
            issuer_ref = str(raw.get('issuer_ref') or '').strip()
            if not issuer_ref:
                raise GovApiError('missing_policy_issuer_ref')
            raw_epoch = raw.get('policy_epoch')
            if isinstance(raw_epoch, bool) or not isinstance(raw_epoch, int) or raw_epoch < 0:
                raise GovApiError('invalid_policy_epoch')
            policy_epoch = raw_epoch
            validity = require_mapping(
                raw.get('validity'),
                reason_code='invalid_policy_validity',
            )
            _reject_unknown_fields(
                validity,
                allowed=_POLICY_VALIDITY_V1_FIELDS,
                reason_code='invalid_policy_validity',
            )
            not_before = _policy_timestamp(
                validity.get('not_before'),
                'invalid_policy_not_before',
            )
            expires_at = _policy_timestamp(
                validity.get('expires_at'),
                'invalid_policy_expires_at',
            )
            if parse_aware_timestamp(expires_at, 'invalid_policy_expires_at') <= (
                parse_aware_timestamp(not_before, 'invalid_policy_not_before')
            ):
                raise GovApiError('invalid_policy_validity_window')
            supersedes = _text_tuple(
                raw.get('supersedes') or (),
                reason_code='invalid_policy_supersedes',
            )
        raw_rules = raw.get('rules')
        if not isinstance(raw_rules, (list, tuple)) or not raw_rules:
            raise GovApiError('policy_pack_without_rules')
        if len(raw_rules) > MAX_POLICY_RULES:
            raise GovApiError('policy_rule_limit_exceeded')
        rules = tuple(
            sorted(
                (
                    PolicyRule.from_mapping(rule, schema_version=schema_version)
                    for rule in raw_rules
                ),
                key=lambda item: (item.priority, item.rule_id),
            )
        )
        if sum(len(rule.conditions) for rule in rules) > MAX_POLICY_TOTAL_CONDITIONS:
            raise GovApiError('policy_condition_limit_exceeded')
        _reject_conflicts(rules)
        _reject_control_conflicts(rules)
        return CompiledPolicyPack(
            policy_id=policy_id,
            version=version,
            schema_version=schema_version,
            rules=rules,
            metadata=_safe_mapping(raw.get('metadata'), reason_code='invalid_policy_pack_metadata'),
            issuer_ref=issuer_ref,
            policy_epoch=policy_epoch,
            not_before=not_before,
            expires_at=expires_at,
            supersedes=supersedes,
        )


def compile_policy_pack(policy_pack: Mapping[str, Any]) -> CompileResult:
    return PolicyCompiler().compile(policy_pack)


def _reject_conflicts(rules: tuple[PolicyRule, ...]) -> None:
    rule_ids: set[str] = set()
    seen: dict[str, str] = {}
    for rule in rules:
        if rule.rule_id in rule_ids:
            raise GovApiError('duplicate_policy_rule_id')
        rule_ids.add(rule.rule_id)
        fingerprint = govengine_record_digest(
            [condition.as_dict() for condition in rule.conditions],
            record_type='govengine.policy.PolicyConditionSet',
        )
        previous = seen.get(fingerprint)
        if previous and previous != rule.effect:
            raise GovApiError('conflicting_policy_rules')
        if previous == rule.effect:
            raise GovApiError('redundant_policy_rules')
        seen[fingerprint] = rule.effect


def _reject_control_conflicts(rules: tuple[PolicyRule, ...]) -> None:
    seen: dict[tuple[str, str], str] = {}
    for rule in rules:
        controls = (
            ('obligation', item.obligation_id, item.as_dict())
            for item in rule.obligations
        )
        constraints = (
            ('constraint', item.constraint_id, item.as_dict())
            for item in rule.constraints
        )
        for control_type, control_id, payload in (*controls, *constraints):
            key = (control_type, control_id)
            fingerprint = govengine_record_digest(
                payload,
                record_type=f'govengine.policy.{control_type}',
            )
            previous = seen.get(key)
            if previous is not None and previous != fingerprint:
                raise GovApiError('conflicting_policy_controls')
            seen[key] = fingerprint


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
    copied = bounded_json_copy(raw)
    return dict(require_mapping(copied, reason_code=reason_code))


def _conditions(value: Any, *, schema_version: str) -> tuple[PolicyCondition, ...]:
    if schema_version == 'v0.1':
        raw = _safe_mapping(value, reason_code='invalid_policy_rule_conditions')
        if not raw:
            raise GovApiError('policy_rule_without_conditions')
        if len(raw) > MAX_POLICY_CONDITIONS_PER_RULE:
            raise GovApiError('policy_rule_condition_limit_exceeded')
        conditions = tuple(
            PolicyCondition(path=path, operator='eq', value=expected)
            for path, expected in raw.items()
        )
    else:
        if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
            raise GovApiError('invalid_policy_rule_conditions')
        if not value:
            raise GovApiError('policy_rule_without_conditions')
        if len(value) > MAX_POLICY_CONDITIONS_PER_RULE:
            raise GovApiError('policy_rule_condition_limit_exceeded')
        conditions = tuple(
            item if isinstance(item, PolicyCondition) else PolicyCondition.from_mapping(item)
            for item in value
        )
    canonical = tuple(
        sorted(
            conditions,
            key=lambda item: (
                item.path,
                item.operator,
                govengine_record_digest(
                    item.value,
                    record_type='govengine.policy.PolicyConditionValue',
                ),
            ),
        )
    )
    fingerprints = [
        govengine_record_digest(
            item.as_dict(),
            record_type='govengine.policy.PolicyCondition',
        )
        for item in canonical
    ]
    if len(fingerprints) != len(set(fingerprints)):
        raise GovApiError('duplicate_policy_condition')
    return canonical


def _validate_condition(item: PolicyCondition) -> None:
    if not item.path:
        raise GovApiError('missing_policy_condition_path')
    parts = item.path.split('.')
    if (
        len(parts) < 2
        or parts[0] not in POLICY_CONDITION_NAMESPACES
        or any(not _PATH_SEGMENT.fullmatch(part) for part in parts)
    ):
        raise GovApiError(
            'unknown_policy_condition_path',
            context={'path': item.path},
        )
    if item.operator not in POLICY_CONDITION_OPERATORS:
        raise GovApiError(
            'unknown_policy_condition_operator',
            context={'operator': item.operator},
        )
    value = bounded_json_copy(item.value)
    if item.operator == 'exists' and not isinstance(value, bool):
        raise GovApiError('invalid_policy_condition_operand')
    if item.operator in _NUMERIC_OPERATORS and (
        isinstance(value, bool) or not isinstance(value, (int, float))
    ):
        raise GovApiError('invalid_policy_condition_operand')
    if item.operator in _LIST_OPERATORS and not isinstance(value, list):
        raise GovApiError('invalid_policy_condition_operand')
    if item.operator == 'matches_namespace' and (
        not isinstance(value, str) or not _valid_namespace(value)
    ):
        raise GovApiError('invalid_policy_condition_operand')


def _valid_namespace(value: str) -> bool:
    parts = value.split('.')
    return bool(parts) and all(_PATH_SEGMENT.fullmatch(part) for part in parts)


def _policy_timestamp(value: Any, reason_code: str) -> str:
    parsed = parse_aware_timestamp(value, reason_code)
    return parsed.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


def _text_tuple(value: Any, *, reason_code: str) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        raise GovApiError(reason_code)
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise GovApiError(reason_code)
        result.append(item.strip())
    if len(result) != len(set(result)):
        raise GovApiError(reason_code)
    return tuple(result)
