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
            'govengine.execution.supervision',
            'govengine.execution.gate',
            'govengine.scope_ports',
            'govengine.contracts.execution',
            'govengine.ooda',
            'govengine.orchestration',
            'govengine.events',
            'govengine.control',
            'govengine.runtime_shell',
        )),
        claim=(
            'Approved-spec, execution-ticket, command-shape, runner receipt, OODA, orchestration boundary, event metadata, '
            'control-decision, runtime shell, queue snapshot, scheduler-tick, runner supervision, and dry-run-only execution gate helpers.'
        ),
        non_claims=_tuple((
            'raw-intent execution',
            'default live subprocess execution',
            'scanner/campaign execution ownership',
            'protocol adapter ownership',
            'runtime storage or scheduler ownership',
            'live backend ownership',
        )),
    )


def planning_contracts_surface() -> GovSurface:
    return GovSurface(
        name='planning_contracts_core',
        status='pre_alpha_tested',
        modules=_tuple((
            'govengine.planning',
        )),
        claim=(
            'Neutral task-contract, plan-intent, and planner-port validators for hosts that need '
            'planner-to-runtime handoff shapes without moving domain planning semantics into GovEngine.'
        ),
        non_claims=_tuple((
            'planner implementation ownership',
            'Ravenclaw security planning semantics ownership',
            'raw target or prompt ownership',
            'queue, scheduler, storage, adapter, command, or live-execution ownership',
        )),
    )


def admission_policy_surface() -> GovSurface:
    return GovSurface(
        name='admission_policy_core',
        status='pre_alpha_tested',
        modules=_tuple((
            'govengine.admission',
        )),
        claim=(
            'Neutral admission, policy-decision, approval-request, and audit-record validators for hosts '
            'that need deterministic runtime gate records without moving domain policy semantics into GovEngine.'
        ),
        non_claims=_tuple((
            'domain policy meaning ownership',
            'operator approval workflow ownership',
            'audit storage or retention ownership',
            'raw target, prompt, command, credential, adapter, scheduler, storage, or live-execution ownership',
        )),
    )


def evidence_review_surface() -> GovSurface:
    return GovSurface(
        name='evidence_review_core',
        status='pre_alpha_tested',
        modules=_tuple((
            'govengine.review',
        )),
        claim=(
            'Neutral evidence requirement, claim, qualification, and review-result validators for hosts '
            'that need receipt-bounded evidence review without moving domain finding semantics into GovEngine.'
        ),
        non_claims=_tuple((
            'SCLite review-bundle verdict ownership',
            'Ravenclaw finding taxonomy ownership',
            'raw evidence storage ownership',
            'raw target, output, command, credential, adapter, storage, or live-execution ownership',
        )),
    )


def domain_profile_sdk_surface() -> GovSurface:
    return GovSurface(
        name='domain_profile_sdk',
        status='pre_alpha_contract_only',
        modules=_tuple((
            'govengine.profiles',
        )),
        claim=(
            'Minimal domain-profile declarations, registry shapes, fixture profiles, and conformance reports '
            'for hosts that need to bind domain meaning around GovEngine without moving that meaning into the kernel.'
        ),
        non_claims=_tuple((
            'domain taxonomy ownership',
            'Ravenclaw finding taxonomy ownership',
            'Tecrax infrastructure semantics ownership',
            'default live subprocess execution',
            'carrier adapter ownership',
            'credential, PKI, KMS, or key-store ownership',
            'product UX or campaign workflow ownership',
        )),
    )


def runtime_contract_proofs_surface() -> GovSurface:
    return GovSurface(
        name='runtime_contract_proofs',
        status='pre_alpha_contract_examples',
        modules=_tuple((
            'govengine.contract_proofs',
        )),
        claim=(
            'Public-safe Ravenclaw and Tecrax runtime contract-proof fixtures plus neutral governance vocabulary '
            'over existing planning, supervision, runtime snapshot, review, and change-order contracts.'
        ),
        non_claims=_tuple((
            'new OODA surface',
            'carrier adapter ownership',
            'default live subprocess execution',
            'domain runtime ownership',
            'credential, PKI, KMS, or key-store ownership',
            'planner, scheduler, queue, or storage ownership',
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
        planning_contracts_surface(),
        admission_policy_surface(),
        evidence_review_surface(),
        domain_profile_sdk_surface(),
        runtime_contract_proofs_surface(),
        controlled_execution_surface(),
        security_profile_surface(),
    )


def surface_by_name(name: str) -> GovSurface:
    for surface in public_surface_index():
        if surface.name == name:
            return surface
    raise KeyError(name)
