from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

from govengine.api import GovApiError, require_mapping


ORCHESTRATOR_KERNEL_CONTROLS = (
    'state_transition_routing',
    'between_step_control_decisions',
    'receipt_reference_routing',
    'profile_boundary_checks',
)

ORCHESTRATOR_RUNTIME_OWNS = (
    'event_loop_liveness',
    'workflow_scheduling',
    'operator_ui',
    'credential_handling',
    'carrier_delivery',
    'concrete_execution',
)

FORBIDDEN_ORCHESTRATION_AUTHORITY = (
    'llm_agent_loop',
    'workflow_scheduler',
    'operator_ui',
    'credential_access',
    'live_execution',
    'carrier_adapter',
)

ALLOWED_STEP_STAGES = (
    'admission',
    'policy_check',
    'trust_check',
    'runner_gate',
    'between_step_control',
    'receipt_review',
    'profile_handoff',
)


@dataclass(frozen=True)
class OrchestratorBoundary:
    """Neutral orchestration boundary for deterministic control flow."""

    kernel_controls: tuple[str, ...] = ORCHESTRATOR_KERNEL_CONTROLS
    runtime_owns: tuple[str, ...] = ORCHESTRATOR_RUNTIME_OWNS
    forbidden_authority: tuple[str, ...] = FORBIDDEN_ORCHESTRATION_AUTHORITY
    non_claims: tuple[str, ...] = (
        'GovEngine does not own an agent loop.',
        'GovEngine does not schedule background work by itself.',
        'GovEngine does not own operator UI or carrier delivery.',
        'GovEngine does not access credentials or execute live work.',
    )

    def as_dict(self) -> dict[str, Any]:
        return {
            'kernel_controls': list(self.kernel_controls),
            'runtime_owns': list(self.runtime_owns),
            'forbidden_authority': list(self.forbidden_authority),
            'non_claims': list(self.non_claims),
        }


@dataclass(frozen=True)
class OrchestrationStep:
    """One deterministic orchestration handoff, not an executable task."""

    step_id: str
    stage: str
    profile: str = 'generic'
    consumes: tuple[str, ...] = field(default_factory=tuple)
    produces: tuple[str, ...] = field(default_factory=tuple)
    required_decisions: tuple[str, ...] = field(default_factory=tuple)
    forbidden_authority: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> 'OrchestrationStep':
        raw = require_mapping(value, reason_code='invalid_orchestration_step')
        if 'raw_intent' in raw or 'prompt' in raw:
            raise GovApiError('raw_intent_not_orchestration_step')
        step_id = str(raw.get('step_id') or raw.get('id') or '').strip()
        if not step_id:
            raise GovApiError('missing_orchestration_step_id')
        stage = str(raw.get('stage') or '').strip()
        if not stage:
            raise GovApiError('missing_orchestration_stage')
        if stage not in ALLOWED_STEP_STAGES:
            raise GovApiError(f'unknown_orchestration_stage:{stage}')
        metadata = raw.get('metadata') if isinstance(raw.get('metadata'), Mapping) else {}
        step = cls(
            step_id=step_id,
            stage=stage,
            profile=str(raw.get('profile') or 'generic'),
            consumes=_tuple(raw.get('consumes') or ()),
            produces=_tuple(raw.get('produces') or ()),
            required_decisions=_tuple(raw.get('required_decisions') or ()),
            forbidden_authority=_tuple(raw.get('forbidden_authority') or ()),
            metadata=dict(metadata),
        )
        step.assert_boundary()
        return step

    def assert_boundary(self) -> None:
        forbidden = set(FORBIDDEN_ORCHESTRATION_AUTHORITY)
        claimed = forbidden.intersection(self.forbidden_authority)
        if claimed:
            raise GovApiError(f'forbidden_orchestration_authority:{sorted(claimed)[0]}')

    def as_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out['consumes'] = list(self.consumes)
        out['produces'] = list(self.produces)
        out['required_decisions'] = list(self.required_decisions)
        out['forbidden_authority'] = list(self.forbidden_authority)
        out['metadata'] = dict(self.metadata)
        return out


def orchestrator_boundary_contract() -> OrchestratorBoundary:
    return OrchestratorBoundary()


def validate_orchestration_step(value: Mapping[str, Any] | OrchestrationStep) -> OrchestrationStep:
    step = value if isinstance(value, OrchestrationStep) else OrchestrationStep.from_mapping(value)
    step.assert_boundary()
    if step.stage not in ALLOWED_STEP_STAGES:
        raise GovApiError(f'unknown_orchestration_stage:{step.stage}')
    return step


def _tuple(values: Any) -> tuple[str, ...]:
    if isinstance(values, str):
        return (values,)
    try:
        return tuple(str(value) for value in values)
    except TypeError as exc:
        raise GovApiError('invalid_orchestration_sequence') from exc
