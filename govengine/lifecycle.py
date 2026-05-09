from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence

from govengine.core import ArtifactDescriptor, ArtifactState, GovernanceContext, ReasonCode, TransitionDecision

DEFAULT_LIFECYCLE_TRANSITIONS: Mapping[str, tuple[str, ...]] = {
    "missing": ("intent_prepared",),
    "intent_prepared": ("policy_decided",),
    "policy_decided": ("execution_contract_prepared",),
    "execution_contract_prepared": ("execution_ticket_approved",),
    "execution_ticket_approved": ("execution_receipt_recorded",),
    "execution_receipt_recorded": ("evidence_recorded",),
    "evidence_recorded": ("chain_verified",),
    "chain_verified": ("lifecycle_verified",),
    "verified_chain": ("verified_lifecycle",),
    "verified_lifecycle": (),
    "blocked": ("intent_prepared", "policy_decided", "execution_contract_prepared", "execution_ticket_approved", "verified_chain"),
}

SCLITE_LIFECYCLE_REQUIREMENTS: Mapping[str, tuple[str, ...]] = {
    "intent_prepared": ("intent_contract",),
    "policy_decided": ("intent_contract", "policy_decision"),
    "execution_contract_prepared": ("intent_contract", "policy_decision", "execution_contract"),
    "execution_ticket_approved": ("intent_contract", "policy_decision", "execution_contract", "execution_ticket"),
    "execution_receipt_recorded": ("execution_contract", "execution_ticket", "execution_receipt"),
    "evidence_recorded": ("execution_ticket", "execution_receipt", "evidence_contract"),
    "chain_verified": ("artifact_chain_manifest",),
    "verified_chain": ("artifact_chain_manifest",),
    "verified_lifecycle": ("artifact_chain_manifest",),
    "lifecycle_verified": ("artifact_chain_manifest",),
}


@dataclass(frozen=True)
class TransitionPolicy:
    """Small allow-list for lifecycle state transitions."""

    allowed_transitions: Mapping[str, tuple[str, ...]] = field(default_factory=lambda: dict(DEFAULT_LIFECYCLE_TRANSITIONS))

    def allows(self, from_state: str, to_state: str) -> bool:
        return to_state in self.allowed_transitions.get(from_state, ())

    def next_states(self, from_state: str) -> tuple[str, ...]:
        return tuple(self.allowed_transitions.get(from_state, ()))


@dataclass(frozen=True)
class TransitionGate:
    """Validate a lifecycle transition against policy and required artifacts."""

    policy: TransitionPolicy = field(default_factory=TransitionPolicy)

    def evaluate(
        self,
        *,
        from_state: str,
        to_state: str,
        artifact_states: Sequence[ArtifactState] = (),
        context: GovernanceContext | None = None,
    ) -> TransitionDecision:
        context = context or GovernanceContext()
        artifacts = tuple(state.descriptor for state in artifact_states)
        blockers: list[str] = []
        next_actions: list[str] = []

        if not self.policy.allows(from_state, to_state):
            blockers.append("transition_not_allowed")
            next_actions.extend(f"transition_to:{state}" for state in self.policy.next_states(from_state))

        blocked_states = [state for state in artifact_states if state.blocked]
        if blocked_states:
            blockers.extend(f"artifact_blocked:{state.descriptor.role or state.descriptor.artifact_type}" for state in blocked_states)
            for state in blocked_states:
                next_actions.extend(state.next_actions)

        present_roles = {state.descriptor.role or state.descriptor.artifact_type for state in artifact_states}
        missing_roles = [role for role in SCLITE_LIFECYCLE_REQUIREMENTS.get(to_state, ()) if role not in present_roles]
        if missing_roles:
            blockers.extend(f"missing_artifact:{role}" for role in missing_roles)
            next_actions.extend(f"provide_artifact:{role}" for role in missing_roles)

        if blockers:
            return TransitionDecision(
                status="blocked",
                reason_code=ReasonCode.LIFECYCLE_BLOCKED.value,
                from_state=from_state,
                to_state=to_state,
                artifacts=artifacts,
                blockers=tuple(dict.fromkeys(blockers)),
                next_actions=tuple(dict.fromkeys(next_actions)),
                context=context,
            )

        return TransitionDecision(
            status="allowed",
            reason_code=ReasonCode.OK.value,
            from_state=from_state,
            to_state=to_state,
            artifacts=artifacts,
            context=context,
        )


@dataclass(frozen=True)
class ArtifactLifecycleController:
    """Lightweight controller for artifact lifecycle transitions.

    This is intentionally not a workflow engine. It only evaluates whether a
    proposed transition is allowed and which artifacts/actions block it.
    """

    gate: TransitionGate = field(default_factory=TransitionGate)

    def decide_transition(
        self,
        *,
        from_state: str,
        to_state: str,
        artifact_states: Sequence[ArtifactState] = (),
        context: GovernanceContext | None = None,
    ) -> TransitionDecision:
        return self.gate.evaluate(
            from_state=from_state,
            to_state=to_state,
            artifact_states=artifact_states,
            context=context,
        )

    def next_actions(
        self,
        *,
        current_state: str,
        artifact_states: Sequence[ArtifactState] = (),
    ) -> tuple[str, ...]:
        actions: list[str] = []
        for state in self.gate.policy.next_states(current_state):
            decision = self.decide_transition(from_state=current_state, to_state=state, artifact_states=artifact_states)
            if decision.allowed:
                actions.append(f"transition_to:{state}")
            else:
                actions.extend(decision.next_actions)
        return tuple(dict.fromkeys(actions))


def artifact_state_for_role(
    role: str,
    *,
    digest: str = "fixture-digest",
    lifecycle_state: str = "present",
    blocked_reasons: Sequence[str] = (),
) -> ArtifactState:
    """Convenience helper for tests and adapters that already know the role."""

    return ArtifactState(
        descriptor=ArtifactDescriptor(
            artifact_type=role,
            schema_version="v0.2",
            digest=digest,
            role=role,
        ),
        lifecycle_state=lifecycle_state,
        chain_status="unknown",
        signature_status="not_required",
        policy_status="unknown",
        blocked_reasons=tuple(blocked_reasons),
        next_actions=("repair_artifact",) if blocked_reasons else (),
    )
