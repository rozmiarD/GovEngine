from __future__ import annotations

from govengine.ooda import GovObservation, GovOodaController, GovOrientation


def test_ooda_continues_when_everything_is_clean() -> None:
    decision = GovOodaController().decide(
        observations=[GovObservation(kind="step_ready", subject="example.com")],
        orientation=GovOrientation(),
    )

    assert decision.decision == "continue"
    assert decision.interrupting is False
    assert decision.as_dict()["reason_code"] == "ok"


def test_ooda_aborts_scope_drift_before_next_action() -> None:
    decision = GovOodaController().decide(orientation=GovOrientation(scope_ok=False))

    assert decision.decision == "abort"
    assert decision.reason_code == "scope_drift_detected"
    assert decision.interrupting is True


def test_ooda_requires_review_for_policy_mismatch() -> None:
    decision = GovOodaController().decide(orientation={"policy_ok": False})

    assert decision.decision == "require_owner_review"
    assert decision.reason_code == "policy_mismatch"


def test_ooda_cools_down_noisy_host() -> None:
    decision = GovOodaController().decide(
        observations=[{"kind": "transport_anomaly", "subject": "api.example.com", "severity": "warning"}],
        orientation={"host_health": "transport_noise"},
    )

    assert decision.decision == "cooldown"
    assert decision.cooldown_subject == "api.example.com"


def test_ooda_degrades_untrusted_output_to_dry_run() -> None:
    decision = GovOodaController().decide(orientation={"output_shape": "raw_leak_risk"})

    assert decision.decision == "degrade_to_dry_run"
    assert decision.reason_code == "output_shape_raw_leak_risk"


def test_ooda_honors_operator_pause_and_stop() -> None:
    pause = GovOodaController().decide(orientation={"operator_control": "pause"})
    stop = GovOodaController().decide(orientation={"operator_control": "stop"})

    assert pause.decision == "pause"
    assert stop.decision == "abort"


def test_ooda_replan_after_step_signal_is_non_interrupting() -> None:
    decision = GovOodaController().decide(observations=[{"kind": "step_completed_with_followup"}])

    assert decision.decision == "replan_after_step"
    assert decision.interrupting is False
