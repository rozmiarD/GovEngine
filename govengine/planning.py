from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Mapping

from govengine.api import GovApiError, require_mapping


PRIORITY_TIERS = ('high', 'medium', 'low')
EXPECTED_DEPTHS = ('deep', 'medium', 'light')
ACTIVATION_MODES = ('immediate', 'if_signal', 'if_confirmed', 'background')
SURFACE_ROLES = ('primary', 'supporting', 'background')

FORBIDDEN_PLANNING_METADATA_KEYS = (
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
class GovTaskContract:
    """Neutral task contract shape. The host owns domain semantics."""

    contract_id: str
    task_family: str = 'generic'
    objective: str = ''
    capability: str = ''
    action_type: str = ''
    target_ref: str = ''
    target_kind: str = 'host'
    evidence_goal: str = ''
    priority_tier: str = 'medium'
    expected_depth: str = 'medium'
    activation_phase: int = 1
    activation_mode: str = 'immediate'
    conditional_gate: str = ''
    surface_role: str = 'primary'
    constraints: Mapping[str, Any] = field(default_factory=dict)
    preferences: Mapping[str, Any] = field(default_factory=dict)
    rationale: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> 'GovTaskContract':
        raw = require_mapping(value, reason_code='invalid_task_contract')
        if raw.get('target') or raw.get('target_url') or raw.get('url'):
            raise GovApiError('raw_target_not_allowed')
        contract_id = str(raw.get('contract_id') or raw.get('id') or raw.get('intent_id') or '').strip()
        if not contract_id:
            raise GovApiError('missing_task_contract_id')
        item = cls(
            contract_id=contract_id,
            task_family=str(raw.get('task_family') or 'generic').strip() or 'generic',
            objective=str(raw.get('objective') or '').strip(),
            capability=str(raw.get('capability') or '').strip(),
            action_type=str(raw.get('action_type') or '').strip(),
            target_ref=str(raw.get('target_ref') or '').strip(),
            target_kind=str(raw.get('target_kind') or 'host').strip() or 'host',
            evidence_goal=str(raw.get('evidence_goal') or '').strip(),
            priority_tier=_enum(raw.get('priority_tier'), PRIORITY_TIERS, 'medium'),
            expected_depth=_enum(raw.get('expected_depth'), EXPECTED_DEPTHS, 'medium'),
            activation_phase=_phase(raw.get('activation_phase')),
            activation_mode=_enum(raw.get('activation_mode'), ACTIVATION_MODES, 'immediate'),
            conditional_gate=str(raw.get('conditional_gate') or '').strip(),
            surface_role=_enum(raw.get('surface_role'), SURFACE_ROLES, 'primary'),
            constraints=_metadata(raw.get('constraints')),
            preferences=_metadata(raw.get('preferences')),
            rationale=_metadata(raw.get('rationale')),
            metadata=_metadata(raw.get('metadata')),
        )
        validate_task_contract(item)
        return item

    def as_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out['constraints'] = dict(self.constraints)
        out['preferences'] = dict(self.preferences)
        out['rationale'] = dict(self.rationale)
        out['metadata'] = dict(self.metadata)
        return out


@dataclass(frozen=True)
class GovPlanIntentContract:
    """Neutral planner handoff envelope over host-provided task contracts."""

    intent_id: str
    profile: str = 'generic'
    planner_id: str = ''
    goal: str = ''
    task_contracts: tuple[GovTaskContract, ...] = field(default_factory=tuple)
    non_claims: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> 'GovPlanIntentContract':
        raw = require_mapping(value, reason_code='invalid_plan_intent_contract')
        intent_id = str(raw.get('intent_id') or raw.get('id') or '').strip()
        if not intent_id:
            raise GovApiError('missing_plan_intent_id')
        tasks = tuple(GovTaskContract.from_mapping(item) for item in list(raw.get('task_contracts') or ()))
        item = cls(
            intent_id=intent_id,
            profile=str(raw.get('profile') or 'generic').strip() or 'generic',
            planner_id=str(raw.get('planner_id') or '').strip(),
            goal=str(raw.get('goal') or '').strip(),
            task_contracts=tasks,
            non_claims=_tuple(raw.get('non_claims') or ()),
            metadata=_metadata(raw.get('metadata')),
        )
        validate_plan_intent_contract(item)
        return item

    def as_dict(self) -> dict[str, Any]:
        return {
            'intent_id': self.intent_id,
            'profile': self.profile,
            'planner_id': self.planner_id,
            'goal': self.goal,
            'task_contracts': [task.as_dict() for task in self.task_contracts],
            'non_claims': list(self.non_claims),
            'metadata': dict(self.metadata),
        }


@dataclass(frozen=True)
class PlannerPort:
    """Planner capability descriptor, not a planner implementation."""

    name: str
    profile: str = 'generic'
    supported_contracts: tuple[str, ...] = ('gov_task_contract', 'gov_plan_intent_contract')
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> 'PlannerPort':
        raw = require_mapping(value, reason_code='invalid_planner_port')
        name = str(raw.get('name') or '').strip()
        if not name:
            raise GovApiError('missing_planner_port_name')
        item = cls(
            name=name,
            profile=str(raw.get('profile') or 'generic').strip() or 'generic',
            supported_contracts=_tuple(raw.get('supported_contracts') or ('gov_task_contract', 'gov_plan_intent_contract')),
            metadata=_metadata(raw.get('metadata')),
        )
        validate_planner_port(item)
        return item

    def as_dict(self) -> dict[str, Any]:
        return {
            'name': self.name,
            'profile': self.profile,
            'supported_contracts': list(self.supported_contracts),
            'metadata': dict(self.metadata),
        }


def validate_task_contract(value: Mapping[str, Any] | GovTaskContract) -> GovTaskContract:
    item = value if isinstance(value, GovTaskContract) else GovTaskContract.from_mapping(value)
    if item.priority_tier not in PRIORITY_TIERS:
        raise GovApiError(f'unknown_priority_tier:{item.priority_tier}')
    if item.expected_depth not in EXPECTED_DEPTHS:
        raise GovApiError(f'unknown_expected_depth:{item.expected_depth}')
    if item.activation_mode not in ACTIVATION_MODES:
        raise GovApiError(f'unknown_activation_mode:{item.activation_mode}')
    if item.surface_role not in SURFACE_ROLES:
        raise GovApiError(f'unknown_surface_role:{item.surface_role}')
    if item.activation_phase < 1 or item.activation_phase > 3:
        raise GovApiError('invalid_activation_phase')
    _reject_forbidden_metadata(item.constraints)
    _reject_forbidden_metadata(item.preferences)
    _reject_forbidden_metadata(item.rationale)
    _reject_forbidden_metadata(item.metadata)
    return item


def validate_plan_intent_contract(value: Mapping[str, Any] | GovPlanIntentContract) -> GovPlanIntentContract:
    item = value if isinstance(value, GovPlanIntentContract) else GovPlanIntentContract.from_mapping(value)
    ids: set[str] = set()
    for task in item.task_contracts:
        validate_task_contract(task)
        if task.contract_id in ids:
            raise GovApiError('duplicate_task_contract_id')
        ids.add(task.contract_id)
    _reject_forbidden_metadata(item.metadata)
    return item


def validate_planner_port(value: Mapping[str, Any] | PlannerPort) -> PlannerPort:
    item = value if isinstance(value, PlannerPort) else PlannerPort.from_mapping(value)
    if not item.supported_contracts:
        raise GovApiError('missing_supported_contracts')
    _reject_forbidden_metadata(item.metadata)
    return item


def task_contract_from_host_task(
    *,
    contract_id: str,
    task_family: str = 'generic',
    objective: str = '',
    capability: str = '',
    action_type: str = '',
    target_ref: str = '',
    target_kind: str = 'host',
    evidence_goal: str = '',
    priority_tier: str = 'medium',
    expected_depth: str = 'medium',
    activation_phase: int = 1,
    activation_mode: str = 'immediate',
    conditional_gate: str = '',
    surface_role: str = 'primary',
    constraints: Mapping[str, Any] | None = None,
    preferences: Mapping[str, Any] | None = None,
    rationale: Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> GovTaskContract:
    return validate_task_contract(GovTaskContract(
        contract_id=contract_id,
        task_family=task_family,
        objective=objective,
        capability=capability,
        action_type=action_type,
        target_ref=target_ref,
        target_kind=target_kind,
        evidence_goal=evidence_goal,
        priority_tier=priority_tier,
        expected_depth=expected_depth,
        activation_phase=activation_phase,
        activation_mode=activation_mode,
        conditional_gate=conditional_gate,
        surface_role=surface_role,
        constraints=_metadata(constraints),
        preferences=_metadata(preferences),
        rationale=_metadata(rationale),
        metadata=_metadata(metadata),
    ))


def _enum(value: Any, allowed: tuple[str, ...], default: str) -> str:
    normalized = str(value or '').strip().lower() or default
    return normalized if normalized in allowed else default


def _phase(value: Any) -> int:
    try:
        return max(1, min(3, int(value)))
    except Exception:
        return 1


def _tuple(values: Iterable[Any]) -> tuple[str, ...]:
    if isinstance(values, str):
        return (values,)
    try:
        return tuple(str(value) for value in values)
    except TypeError as exc:
        raise GovApiError('invalid_planning_sequence') from exc


def _metadata(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise GovApiError('invalid_planning_metadata')
    data = dict(value)
    _reject_forbidden_metadata(data)
    return data


def _reject_forbidden_metadata(value: Mapping[str, Any]) -> None:
    reason = _find_forbidden_key(value)
    if reason:
        raise GovApiError(f'forbidden_planning_metadata:{reason}')


def _find_forbidden_key(value: Any) -> str:
    if isinstance(value, Mapping):
        forbidden = set(FORBIDDEN_PLANNING_METADATA_KEYS)
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
