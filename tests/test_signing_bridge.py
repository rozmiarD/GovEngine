from __future__ import annotations

from govengine.core import ArtifactDescriptor
from govengine.signing import (
    SignatureEnvelope,
    SigningPolicy,
    TrustPolicy,
    VerificationResult,
    signature_envelope_from_artifact,
    signature_transition_decision,
)


def _descriptor() -> ArtifactDescriptor:
    return ArtifactDescriptor("execution_ticket", "v0.2", "sha256:ticket")


def test_signature_envelope_from_artifact_preserves_integrity_only_mode() -> None:
    envelope = signature_envelope_from_artifact({
        "signature": {
            "mode": "not_signed_integrity_only",
            "identity_signature_required": False,
        }
    })

    assert envelope.signed is False
    assert envelope.mode == "not_signed_integrity_only"


def test_signature_gate_allows_integrity_only_when_signature_not_required() -> None:
    decision = signature_transition_decision(_descriptor(), signing_policy=SigningPolicy(require_signature=False))

    assert decision.allowed is True
    assert decision.reason_code == "ok"


def test_signature_gate_blocks_required_signature_absent() -> None:
    decision = signature_transition_decision(_descriptor(), signing_policy=SigningPolicy(require_signature=True))

    assert decision.allowed is False
    assert decision.reason_code == "signature_required"
    assert "signature_required" in decision.blockers
    assert "obtain_signature" in decision.next_actions


def test_signature_gate_blocks_digest_mismatch() -> None:
    signature = SignatureEnvelope(
        mode="detached_signature",
        signer_id="owner",
        signature="sig",
        binds_digest="sha256:old",
    )
    verification = VerificationResult(status="passed", trust_status="trusted", verifier_id="fixture")
    decision = signature_transition_decision(
        _descriptor(),
        signature=signature,
        verification=verification,
        signing_policy=SigningPolicy(require_signature=True),
    )

    assert decision.allowed is False
    assert decision.reason_code == "trust_denied"
    assert "signature_digest_mismatch" in decision.blockers


def test_signature_gate_requires_trusted_verification_for_signed_artifact() -> None:
    signature = SignatureEnvelope(
        mode="detached_signature",
        signer_id="owner",
        signature="sig",
        binds_digest="sha256:ticket",
    )
    decision = signature_transition_decision(
        _descriptor(),
        signature=signature,
        signing_policy=SigningPolicy(require_signature=True),
    )

    assert decision.allowed is False
    assert "trust_decision_required" in decision.blockers


def test_signature_gate_allows_trusted_signed_artifact() -> None:
    signature = SignatureEnvelope(
        mode="detached_signature",
        signer_id="owner",
        signature="sig",
        binds_digest="sha256:ticket",
    )
    verification = VerificationResult(status="passed", trust_status="trusted", verifier_id="fixture")
    decision = signature_transition_decision(
        _descriptor(),
        signature=signature,
        verification=verification,
        signing_policy=SigningPolicy(require_signature=True, required_signer_ids=("owner",)),
        trust_policy=TrustPolicy(allowed_trust_statuses=("trusted",)),
    )

    assert decision.allowed is True
    assert decision.context.trust_decision["verifier_id"] == "fixture"
