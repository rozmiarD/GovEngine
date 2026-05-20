from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Tuple


@dataclass(frozen=True)
class GovSurface:
    """Public GovEngine surface metadata.

    The registry is intentionally descriptive rather than dynamic import magic.
    It gives hosts and reviewers a compact, testable map of which modules belong
    to the neutral artifact-governance core and which modules are optional
    security-profile helpers retained for Ravenclaw-style hosts.
    """

    name: str
    status: str
    modules: Tuple[str, ...]
    claim: str
    non_claims: Tuple[str, ...] = field(default_factory=tuple)
    optional_profile: bool = False

    def as_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'status': self.status,
            'modules': list(self.modules),
            'claim': self.claim,
            'non_claims': list(self.non_claims),
            'optional_profile': self.optional_profile,
        }


def _tuple(values: Iterable[str]) -> Tuple[str, ...]:
    return tuple(str(value) for value in values)


def artifact_governance_surface() -> GovSurface:
    return GovSurface(
        name='artifact_governance_core',
        status='pre_alpha_tested',
        modules=_tuple((
            'govengine.core',
            'govengine.boundary',
            'govengine.sclite_contracts',
            'govengine.lifecycle',
            'govengine.signing',
            'govengine.deconfliction',
            'govengine.state_index',
            'govengine.state_machine',
            'govengine.state_store',
        )),
        claim=(
            'Portable kernel/profile boundary, artifact descriptor/state/transition, '
            'SCLite lifecycle bridge, signing/trust decision, deconfliction, state-machine, and state-index helpers.'
        ),
        non_claims=_tuple((
            'SCLite schema/canonicalization ownership',
            'PKI/key-store ownership',
            'raw artifact storage ownership',
            'workflow scheduling or event bus ownership',
        )),
    )


def controlled_execution_surface() -> GovSurface:
    return GovSurface(
        name='controlled_execution_core',
        status='pre_alpha_dry_run_default',
        modules=_tuple((
            'govengine.execution.approved_spec',
            'govengine.execution.ticket_gate',
            'govengine.execution.command_shape',
            'govengine.execution.runner',
            'govengine.execution.runner_protocol',
            'govengine.execution.gate',
            'govengine.contracts.execution',
            'govengine.ooda',
            'govengine.orchestration',
            'govengine.events',
            'govengine.control',
            'govengine.runtime_shell',
        )),
        claim=(
            'Approved-spec, execution-ticket, command-shape, runner receipt, OODA, orchestration boundary, event metadata, '
            'control-decision, runtime shell, queue snapshot, scheduler-tick, and dry-run-only execution gate helpers.'
        ),
        non_claims=_tuple((
            'raw-intent execution',
            'default live subprocess execution',
            'scanner/campaign execution ownership',
            'protocol adapter ownership',
            'runtime storage or scheduler ownership',
        )),
    )


def security_profile_surface() -> GovSurface:
    return GovSurface(
        name='security_profile_helpers',
        status='pre_alpha_optional_profile',
        modules=_tuple((
            'govengine.action_schema',
            'govengine.action_validators',
            'govengine.action_compiler',
            'govengine.capability_recipes',
            'govengine.tool_registry',
            'govengine.semantic_loss_policy',
            'govengine.policy.core',
            'govengine.policy.gateway',
            'govengine.scope',
            'govengine.contracts.signal',
            'govengine.contracts.analysis',
            'govengine.contracts.evidence_policy',
        )),
        claim=(
            'Optional security-oriented action/tool/scope/policy/signal helpers for '
            'hosts such as Ravenclaw that need a bounded public-safe security profile.'
        ),
        non_claims=_tuple((
            'live exploit/scanner capability',
            'authorization to test targets',
            'bug-bounty campaign orchestration',
            'Logdash or Ravenclaw runtime ownership',
            'OpenClaw/MCP/A2A adapter ownership',
        )),
        optional_profile=True,
    )


def public_surface_index() -> Tuple[GovSurface, ...]:
    return (
        artifact_governance_surface(),
        controlled_execution_surface(),
        security_profile_surface(),
    )


def surface_by_name(name: str) -> GovSurface:
    for surface in public_surface_index():
        if surface.name == name:
            return surface
    raise KeyError(name)
