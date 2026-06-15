from __future__ import annotations

import pytest

from govengine.execution.gate import DryRunRunner, ExecutionGate, ExecutionGateInput, RunnerProfile
from govengine.execution.runner_protocol import GovRunnerRequest, GovRunnerStep


def _gate_input(**overrides) -> ExecutionGateInput:
    values = {
        "has_prepared_execution_contract": True,
        "policy_decision_status": "allowed",
        "execution_ticket_status": "approved",
        "trust_decision_status": "trusted",
        "runner_profile": RunnerProfile(),
    }
    values.update(overrides)
    return ExecutionGateInput(**values)


def _request(*, dry_run: bool = True) -> GovRunnerRequest:
    return GovRunnerRequest(
        request_id="r1",
        source="test",
        steps=(GovRunnerStep(index=0, tool="curl", args=("https://example.com",)),),
        dry_run=dry_run,
    )


def test_execution_gate_allows_complete_dry_run_prerequisites() -> None:
    decision = ExecutionGate().evaluate(_gate_input())

    assert decision.allowed is True
    assert decision.to_state == "runner_allowed_dry_run"
    assert decision.context.runner_profile == "dry-run"


def test_execution_gate_allows_runtime_consumable_guarded_fresh_bundle() -> None:
    decision = ExecutionGate().evaluate(_gate_input(
        runtime_consumable_bundle=True,
        guarded_bundle_status="passed",
        replay_status="fresh",
    ))

    assert decision.allowed is True
    assert decision.to_state == "runner_allowed_dry_run"


def test_execution_gate_maps_guarded_runtime_decision_to_admission() -> None:
    decision = ExecutionGate().evaluate_runtime_consumable(
        _gate_input(),
        guarded_bundle_decision={
            "status": "allowed",
            "verification_status": "passed",
            "replay_status": "fresh",
        },
    )

    assert decision.allowed is True
    assert decision.to_state == "runner_allowed_dry_run"


def test_execution_gate_blocks_runtime_decision_without_fresh_guard() -> None:
    decision = ExecutionGate().evaluate_runtime_consumable(
        _gate_input(),
        guarded_bundle_decision={
            "status": "blocked",
            "verification_status": "passed",
            "replay_status": "replayed",
        },
    )

    assert decision.allowed is False
    assert decision.reason_code == "replay_detected"
    assert "missing_or_replayed_guarded_root" in decision.blockers


def test_execution_gate_blocks_runtime_consumable_unguarded_bundle() -> None:
    decision = ExecutionGate().evaluate(_gate_input(runtime_consumable_bundle=True))

    assert decision.allowed is False
    assert decision.reason_code == "kernel_guard_required"
    assert "missing_or_invalid_kernel_guard" in decision.blockers
    assert "missing_or_replayed_guarded_root" in decision.blockers


def test_execution_gate_blocks_runtime_consumable_replayed_bundle() -> None:
    decision = ExecutionGate().evaluate(_gate_input(
        runtime_consumable_bundle=True,
        guarded_bundle_status="passed",
        replay_status="replayed",
    ))

    assert decision.allowed is False
    assert decision.reason_code == "replay_detected"
    assert "missing_or_replayed_guarded_root" in decision.blockers


@pytest.mark.parametrize("replay_status", ("stale", "expired"))
def test_execution_gate_blocks_runtime_consumable_stale_replay(replay_status: str) -> None:
    decision = ExecutionGate().evaluate(_gate_input(
        runtime_consumable_bundle=True,
        guarded_bundle_status="passed",
        replay_status=replay_status,
    ))

    assert decision.allowed is False
    assert decision.reason_code == "replay_detected"
    assert "missing_or_replayed_guarded_root" in decision.blockers


def test_execution_gate_rejects_raw_intent_missing_contract() -> None:
    decision = ExecutionGate().evaluate(_gate_input(has_prepared_execution_contract=False))

    assert decision.allowed is False
    assert decision.reason_code == "raw_intent_rejected"
    assert "missing_prepared_execution_contract" in decision.blockers


def test_execution_gate_blocks_live_by_default() -> None:
    decision = ExecutionGate().evaluate(_gate_input(), live=True)

    assert decision.allowed is False
    assert decision.reason_code == "execution_disabled"
    assert "live_backend_disabled" in decision.blockers


def test_execution_gate_blocks_live_profile_without_explicit_backend_enablement() -> None:
    decision = ExecutionGate().evaluate(
        _gate_input(runner_profile=RunnerProfile(name="local-live", allowed=True)),
        live=True,
    )

    assert decision.allowed is False
    assert decision.to_state == "runner_allowed_live"
    assert decision.reason_code == "execution_disabled"
    assert "live_backend_disabled" in decision.blockers
    assert decision.context.metadata["runner_profile"]["live_backend_enabled"] is False


def test_execution_gate_only_allows_live_when_profile_explicitly_enables_backend() -> None:
    decision = ExecutionGate().evaluate(
        _gate_input(runner_profile=RunnerProfile(name="local-live", allowed=True, live_backend_enabled=True)),
        live=True,
    )

    assert decision.allowed is True
    assert decision.to_state == "runner_allowed_live"
    assert decision.context.metadata["runner_profile"]["live_backend_enabled"] is True


@pytest.mark.parametrize(
    "ticket_status",
    ("missing", "invalid", "unapproved", "mismatch", "stale", "failed"),
)
def test_execution_gate_blocks_non_approved_execution_ticket(ticket_status: str) -> None:
    decision = ExecutionGate().evaluate(_gate_input(execution_ticket_status=ticket_status))

    assert decision.allowed is False
    assert decision.reason_code == "raw_intent_rejected"
    assert "missing_or_invalid_execution_ticket" in decision.blockers
    assert "approve_execution_ticket" in decision.next_actions


@pytest.mark.parametrize(
    "trust_status",
    ("missing", "denied", "failed", "untrusted", "unknown"),
)
def test_execution_gate_blocks_invalid_trust_decision_status(trust_status: str) -> None:
    decision = ExecutionGate().evaluate(_gate_input(trust_decision_status=trust_status))

    assert decision.allowed is False
    assert decision.reason_code == "raw_intent_rejected"
    assert "missing_or_invalid_trust_decision" in decision.blockers
    assert "verify_trust_decision" in decision.next_actions


def test_execution_gate_requires_allowed_runner_profile() -> None:
    decision = ExecutionGate().evaluate(_gate_input(runner_profile=RunnerProfile(name="local", allowed=False)))

    assert decision.allowed is False
    assert "runner_profile_not_allowed" in decision.blockers


def test_dry_run_runner_returns_dry_run_receipt() -> None:
    receipt = DryRunRunner().run(_request(dry_run=True))

    assert receipt.status == "dry-run"
    assert receipt.reason_code == "dry_run_requested"
    assert receipt.step_results[0].status == "dry-run"


def test_dry_run_runner_never_executes_live_request() -> None:
    receipt = DryRunRunner().run(_request(dry_run=False))

    assert receipt.status == "blocked"
    assert receipt.reason_code == "live_backend_disabled"
    assert receipt.step_results[0].reason_code == "live_backend_disabled"
    assert receipt.control_decisions[0]["non_claim"] == "DryRunRunner never executes live requests"
