from __future__ import annotations

import pytest

from govengine.api import GovApiError
from govengine.core import (
    ArtifactDescriptor,
    ArtifactEnvelope,
    ArtifactState,
    ExecutionPrerequisites,
    GovernanceContext,
    ReasonCode,
    TransitionDecision,
)


def test_artifact_descriptor_preserves_sclite_digest_boundary() -> None:
    descriptor = ArtifactDescriptor.from_mapping({
        "artifact_type": "execution_contract",
        "schema_version": "v0.2",
        "digest": "sha256:abc",
        "role": "prepared_execution_contract",
        "metadata": {"producer": "fixture"},
    })

    assert descriptor.as_dict() == {
        "artifact_type": "execution_contract",
        "schema_version": "v0.2",
        "digest": "sha256:abc",
        "role": "prepared_execution_contract",
        "path": "",
        "metadata": {"producer": "fixture"},
    }


def test_artifact_descriptor_rejects_missing_digest() -> None:
    with pytest.raises(GovApiError, match="missing_artifact_digest"):
        ArtifactDescriptor.from_mapping({
            "artifact_type": "execution_contract",
            "schema_version": "v0.2",
        })


def test_artifact_envelope_wraps_payload_and_descriptor() -> None:
    envelope = ArtifactEnvelope.from_mapping({
        "descriptor": {
            "artifact_type": "execution_ticket",
            "schema_version": "v0.2",
            "digest": "sha256:def",
        },
        "artifact": {"ticket_id": "t1"},
        "source": "fixture",
    })

    assert envelope.descriptor.artifact_type == "execution_ticket"
    assert envelope.as_dict()["artifact"] == {"ticket_id": "t1"}
    assert envelope.as_dict()["source"] == "fixture"


def test_artifact_state_reports_blockers_and_next_actions() -> None:
    descriptor = ArtifactDescriptor("execution_contract", "v0.2", "sha256:abc")
    state = ArtifactState(
        descriptor=descriptor,
        lifecycle_state="prepared",
        chain_status="verified",
        signature_status="missing",
        policy_status="pending",
        blocked_reasons=("signature_required",),
        next_actions=("obtain_signature",),
    )

    assert state.blocked is True
    assert state.as_dict()["blocked_reasons"] == ["signature_required"]
    assert state.as_dict()["next_actions"] == ["obtain_signature"]


def test_transition_decision_has_stable_envelope() -> None:
    descriptor = ArtifactDescriptor("execution_contract", "v0.2", "sha256:abc")
    decision = TransitionDecision(
        status="blocked",
        reason_code=ReasonCode.SIGNATURE_REQUIRED.value,
        from_state="prepared",
        to_state="approved",
        artifacts=(descriptor,),
        blockers=("missing_signature",),
        next_actions=("verify_trust_decision",),
        context=GovernanceContext(context_id="ctx1", runner_profile="dry-run"),
    )

    assert decision.allowed is False
    assert decision.as_dict()["reason_code"] == "signature_required"
    assert decision.as_dict()["context"]["context_id"] == "ctx1"


def test_execution_prerequisites_reject_raw_intent() -> None:
    readiness = ExecutionPrerequisites()
    decision = readiness.transition_decision()

    assert decision.allowed is False
    assert decision.reason_code == "raw_intent_rejected"
    assert "missing_prepared_execution_contract" in decision.blockers
    assert "missing_or_invalid_policy_decision" in decision.blockers
    assert "missing_or_invalid_execution_ticket" in decision.blockers
    assert "missing_or_invalid_trust_decision" in decision.blockers


def test_execution_prerequisites_keep_live_disabled_by_default() -> None:
    readiness = ExecutionPrerequisites(
        has_prepared_execution_contract=True,
        policy_decision_status="allowed",
        execution_ticket_status="approved",
        trust_decision_status="trusted",
        runner_profile_allowed=True,
        runner_profile="dry-run",
        live_backend_enabled=False,
    )

    assert readiness.transition_decision().allowed is True
    live_decision = readiness.transition_decision(live=True)
    assert live_decision.allowed is False
    assert live_decision.reason_code == "execution_disabled"
    assert "live_backend_disabled" in live_decision.blockers
