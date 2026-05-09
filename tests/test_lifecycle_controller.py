from __future__ import annotations

from govengine.lifecycle import ArtifactLifecycleController, TransitionGate, artifact_state_for_role


def test_transition_gate_allows_ordered_sclite_lifecycle_step() -> None:
    gate = TransitionGate()
    decision = gate.evaluate(
        from_state="policy_decided",
        to_state="execution_contract_prepared",
        artifact_states=(
            artifact_state_for_role("intent_contract"),
            artifact_state_for_role("policy_decision"),
            artifact_state_for_role("execution_contract"),
        ),
    )

    assert decision.allowed is True
    assert decision.reason_code == "ok"


def test_transition_gate_blocks_out_of_order_transition() -> None:
    gate = TransitionGate()
    decision = gate.evaluate(
        from_state="intent_prepared",
        to_state="execution_ticket_approved",
        artifact_states=(artifact_state_for_role("intent_contract"),),
    )

    assert decision.allowed is False
    assert "transition_not_allowed" in decision.blockers
    assert "missing_artifact:policy_decision" in decision.blockers
    assert "missing_artifact:execution_contract" in decision.blockers
    assert "missing_artifact:execution_ticket" in decision.blockers


def test_transition_gate_blocks_when_required_artifact_state_is_blocked() -> None:
    gate = TransitionGate()
    decision = gate.evaluate(
        from_state="execution_contract_prepared",
        to_state="execution_ticket_approved",
        artifact_states=(
            artifact_state_for_role("intent_contract"),
            artifact_state_for_role("policy_decision"),
            artifact_state_for_role("execution_contract", blocked_reasons=("digest_mismatch",)),
            artifact_state_for_role("execution_ticket"),
        ),
    )

    assert decision.allowed is False
    assert "artifact_blocked:execution_contract" in decision.blockers
    assert "repair_artifact" in decision.next_actions


def test_lifecycle_controller_reports_next_actions() -> None:
    controller = ArtifactLifecycleController()
    actions = controller.next_actions(
        current_state="policy_decided",
        artifact_states=(
            artifact_state_for_role("intent_contract"),
            artifact_state_for_role("policy_decision"),
        ),
    )

    assert actions == ("provide_artifact:execution_contract",)
