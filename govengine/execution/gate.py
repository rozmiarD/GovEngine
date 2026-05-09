from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

from govengine.core import ExecutionPrerequisites, GovernanceContext, ReasonCode, TransitionDecision
from govengine.execution.runner_protocol import GovRunnerRequest, GovRunnerReceipt, GovRunnerStepResult, dry_run_runner_receipt


@dataclass(frozen=True)
class RunnerProfile:
    """Policy-visible runner profile.

    Live backends are disabled by default. `dry-run` is the safe default runner
    profile for GovEngine controlled execution.
    """

    name: str = "dry-run"
    allowed: bool = True
    live_backend_enabled: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["metadata"] = dict(self.metadata)
        return out


@dataclass(frozen=True)
class ExecutionGateInput:
    """Boundary inputs required before a runner request can proceed."""

    has_prepared_execution_contract: bool
    policy_decision_status: str
    execution_ticket_status: str
    trust_decision_status: str
    runner_profile: RunnerProfile = field(default_factory=RunnerProfile)

    def prerequisites(self) -> ExecutionPrerequisites:
        return ExecutionPrerequisites(
            has_prepared_execution_contract=self.has_prepared_execution_contract,
            policy_decision_status=self.policy_decision_status,
            execution_ticket_status=self.execution_ticket_status,
            trust_decision_status=self.trust_decision_status,
            runner_profile_allowed=self.runner_profile.allowed,
            runner_profile=self.runner_profile.name,
            live_backend_enabled=self.runner_profile.live_backend_enabled,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "has_prepared_execution_contract": self.has_prepared_execution_contract,
            "policy_decision_status": self.policy_decision_status,
            "execution_ticket_status": self.execution_ticket_status,
            "trust_decision_status": self.trust_decision_status,
            "runner_profile": self.runner_profile.as_dict(),
        }


@dataclass(frozen=True)
class ExecutionGate:
    """Controlled execution gate for approved runner requests.

    This gate does not execute. It verifies that the request is not raw intent
    and that the selected runner profile is allowed for dry-run/live mode.
    """

    def evaluate(self, gate_input: ExecutionGateInput, *, live: bool = False) -> TransitionDecision:
        decision = gate_input.prerequisites().transition_decision(live=live)
        if decision.allowed:
            return TransitionDecision(
                status="allowed",
                reason_code=ReasonCode.OK.value,
                from_state="execution_gated",
                to_state="runner_allowed_live" if live else "runner_allowed_dry_run",
                context=GovernanceContext(
                    runner_profile=gate_input.runner_profile.name,
                    metadata={"runner_profile": gate_input.runner_profile.as_dict()},
                ),
            )
        return TransitionDecision(
            status="blocked",
            reason_code=decision.reason_code,
            from_state="execution_gated",
            to_state="runner_allowed_live" if live else "runner_allowed_dry_run",
            blockers=decision.blockers,
            next_actions=decision.next_actions,
            context=GovernanceContext(
                runner_profile=gate_input.runner_profile.name,
                metadata={"runner_profile": gate_input.runner_profile.as_dict(), "gate_input": gate_input.as_dict()},
            ),
        )


class DryRunRunner:
    """Default safe runner implementation.

    It never performs live IO/subprocess execution. If a request asks for live
    behavior (`dry_run=False`), it returns a blocked receipt.
    """

    def run(self, request: GovRunnerRequest) -> GovRunnerReceipt:
        if request.dry_run:
            return dry_run_runner_receipt(request)
        return GovRunnerReceipt(
            status="blocked",
            request_id=request.request_id,
            source=request.source,
            step_results=tuple(
                GovRunnerStepResult(
                    index=step.index,
                    status="blocked",
                    reason_code="live_backend_disabled",
                )
                for step in request.steps
            ),
            reason_code="live_backend_disabled",
            control_decisions=(
                {
                    "status": "blocked",
                    "reason_code": "live_backend_disabled",
                    "non_claim": "DryRunRunner never executes live requests",
                },
            ),
        )
