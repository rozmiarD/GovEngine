from __future__ import annotations

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


def test_execution_gate_blocks_runtime_consumable_unguarded_bundle() -> None:
    decision = ExecutionGate().evaluate(_gate_input(runtime_consumable_bundle=True))

    assert decision.allowed is False
    assert decision.reason_code == "signature_required"
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
