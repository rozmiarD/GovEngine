from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
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
    runtime_consumable_bundle: bool = False
    guarded_bundle_status: str = "not_required"
    replay_status: str = "not_required"

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
            "runtime_consumable_bundle": self.runtime_consumable_bundle,
            "guarded_bundle_status": self.guarded_bundle_status,
            "replay_status": self.replay_status,
        }


@dataclass(frozen=True)
class ExecutionGate:
    """Controlled execution gate for approved runner requests.

    This gate does not execute. It verifies that the request is not raw intent
    and that the selected runner profile is allowed for dry-run/live mode.
    """

    def evaluate(self, gate_input: ExecutionGateInput, *, live: bool = False) -> TransitionDecision:
        decision = gate_input.prerequisites().transition_decision(live=live)
        guarded_blockers: list[str] = []
        if gate_input.runtime_consumable_bundle:
            if gate_input.guarded_bundle_status not in {"passed", "ok", "allowed"}:
                guarded_blockers.append("missing_or_invalid_kernel_guard")
            if gate_input.replay_status != "fresh":
                guarded_blockers.append("missing_or_replayed_guarded_root")
        if guarded_blockers:
            return TransitionDecision(
                status="blocked",
                reason_code=ReasonCode.REPLAY_DETECTED.value if gate_input.replay_status == "replayed" else ReasonCode.SIGNATURE_REQUIRED.value,
                from_state="execution_gated",
                to_state="runner_allowed_live" if live else "runner_allowed_dry_run",
                blockers=tuple((*decision.blockers, *guarded_blockers)),
                next_actions=(
                    *decision.next_actions,
                    "verify_guarded_strict_bundle",
                    "record_guard_replay_freshness",
                ),
                context=GovernanceContext(
                    runner_profile=gate_input.runner_profile.name,
                    metadata={"runner_profile": gate_input.runner_profile.as_dict(), "gate_input": gate_input.as_dict()},
                ),
            )
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

    def evaluate_runtime_consumable(
        self,
        gate_input: ExecutionGateInput,
        *,
        guarded_bundle_decision: Mapping[str, Any],
        live: bool = False,
    ) -> TransitionDecision:
        """Evaluate an execution gate with a verified GovEngine replay decision.

        Runtime-consumable SCLite bundles must enter the gate through the
        guarded+fresh decision produced by `verify_guard_and_record_replay()`.
        This method keeps that mapping explicit instead of requiring hosts to
        hand-copy replay fields into `ExecutionGateInput`.
        """

        guarded_status = str(
            guarded_bundle_decision.get("verification_status")
            or guarded_bundle_decision.get("status")
            or ""
        )
        replay_status = str(guarded_bundle_decision.get("replay_status") or "")
        return self.evaluate(
            replace(
                gate_input,
                runtime_consumable_bundle=True,
                guarded_bundle_status=guarded_status,
                replay_status=replay_status,
            ),
            live=live,
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
