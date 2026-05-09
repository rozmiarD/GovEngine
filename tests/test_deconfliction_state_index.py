from __future__ import annotations

from govengine.core import ArtifactDescriptor, ArtifactState
from govengine.deconfliction import ConflictDetector
from govengine.state_index import ArtifactStateIndex


def _state(role: str, digest: str = "sha256:ok", *, blocked: bool = False) -> ArtifactState:
    return ArtifactState(
        descriptor=ArtifactDescriptor(role, "v0.2", digest, role=role),
        lifecycle_state="present",
        blocked_reasons=("digest_mismatch",) if blocked else (),
        next_actions=("repair_artifact",) if blocked else (),
    )


def test_conflict_detector_reports_digest_conflict_and_invalidates_downstream() -> None:
    detector = ConflictDetector()
    order = detector.evaluate(
        [_state("execution_contract", "sha256:new")],
        expected_digests={"execution_contract": "sha256:old"},
    )

    assert order.required is True
    assert order.conflicts[0].reason_code == "artifact_digest_mismatch"
    assert "execution_ticket" in order.invalidated_roles
    assert "rebuild_bindings_for:execution_contract" in order.required_actions


def test_conflict_detector_reports_blocked_artifact_state() -> None:
    order = ConflictDetector().evaluate([_state("policy_decision", blocked=True)])

    assert order.required is True
    assert order.conflicts[0].reason_code == "lifecycle_blocked"
    assert "repair_artifact:policy_decision" in order.required_actions


def test_state_index_reports_missing_and_blocked_roles() -> None:
    index = ArtifactStateIndex.from_states([
        _state("intent_contract"),
        _state("policy_decision", blocked=True),
    ])

    summary = index.summary(required_roles=("intent_contract", "policy_decision", "execution_contract"))

    assert summary["status"] == "blocked"
    assert summary["missing_roles"] == ["execution_contract"]
    assert summary["blocked_roles"] == ["policy_decision"]
    assert "provide_artifact:execution_contract" in summary["next_actions"]
    assert "repair_artifact" in summary["next_actions"]


def test_state_index_ready_when_required_roles_present_and_no_conflicts() -> None:
    index = ArtifactStateIndex.from_states([
        _state("intent_contract"),
        _state("policy_decision"),
    ])

    summary = index.summary(required_roles=("intent_contract", "policy_decision"))

    assert summary["status"] == "ready"
    assert summary["next_actions"] == []
