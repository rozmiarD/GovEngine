from __future__ import annotations

import json
from math import nan

import pytest

from govengine import compose_runtime_admission_result
from govengine.api import GovApiError
from govengine.core import ArtifactDescriptor
from govengine.signing import (
    DemoDigestSigner,
    DemoDigestVerifier,
    KeyResolutionRequest,
    KeyResolutionResult,
    KeyResolverPort,
    SigningPolicy,
    SigningRequest,
    SignatureEnvelope,
    SignedArtifact,
    TrustPolicy,
    TrustStoreDecision,
    TrustStorePort,
    VerificationResult,
    canonical_govengine_record,
    demo_sign_and_verify,
    demo_sign_govengine_record,
    govengine_record_digest,
    signed_artifact_from_record,
    signature_envelope_from_artifact,
    signature_transition_decision,
    verify_signed_govengine_record,
)


def _descriptor() -> ArtifactDescriptor:
    return ArtifactDescriptor("execution_ticket", "v0.2", "sha256:ticket")


def _runtime_admission_inputs(**overrides):
    values = {
        "admission_id": "runtime-admission-signing-1",
        "subject_ref": "sha256:prepared-contract",
        "prepared_execution_contract": {"status": "prepared", "digest": "sha256:contract"},
        "policy_decision": {"decision": "allow", "policy_id": "policy-1"},
        "execution_ticket": {"status": "passed", "ticket_id": "ticket-1", "digest": "sha256:ticket"},
        "trust_decision": {"status": "passed", "trust_status": "trusted", "verifier_id": "fixture"},
        "runner_profile": {"name": "dry-run", "allowed": True, "live_backend_enabled": False},
        "receipt_obligation": {"required": True, "binds": ["admission", "ticket"]},
    }
    values.update(overrides)
    return values


def _signed_runtime_record() -> tuple[dict[str, str], SignedArtifact]:
    record = {"status": "allowed", "reason_code": "ok"}
    signed = demo_sign_govengine_record(
        record,
        record_type="govengine.admission.RuntimeAdmissionResult",
        payload_ref="artifact://admission/runtime-1",
        signer_id="owner-demo",
    )
    return record, signed


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

def test_demo_digest_signer_and_verifier_bind_signature_to_descriptor_digest() -> None:
    descriptor = _descriptor()
    signer = DemoDigestSigner(signer_id="owner-demo")
    signing = signer.sign(SigningRequest(descriptor=descriptor, purpose="execution_ticket"))
    verifier = DemoDigestVerifier(allowed_signer_ids=("owner-demo",))

    verification = verifier.verify(descriptor, signing.signature)
    decision = signature_transition_decision(
        descriptor,
        signature=signing.signature,
        verification=verification,
        signing_policy=SigningPolicy(require_signature=True, allowed_modes=("detached_demo_digest",), required_signer_ids=("owner-demo",)),
        trust_policy=TrustPolicy(allowed_trust_statuses=("trusted",)),
    )

    assert signing.status == "signed"
    assert signing.signature.mode == "detached_demo_digest"
    assert signing.signature.binds_digest == descriptor.digest
    assert verification.trusted is True
    assert verification.metadata["demo_only"] is True
    assert decision.allowed is True


def test_demo_digest_verifier_rejects_tampered_digest() -> None:
    descriptor = _descriptor()
    other = ArtifactDescriptor("execution_ticket", "v0.2", "sha256:other")
    signing, _verification = demo_sign_and_verify(descriptor, purpose="execution_ticket", signer_id="owner-demo")

    verification = DemoDigestVerifier(allowed_signer_ids=("owner-demo",)).verify(other, signing.signature)

    assert verification.status == "failed"
    assert verification.reason_code == "signature_digest_mismatch"


def test_demo_digest_verifier_rejects_unsupported_signature_mode() -> None:
    verification = DemoDigestVerifier(allowed_signer_ids=("owner-demo",)).verify(
        _descriptor(),
        SignatureEnvelope(
            mode="detached_signature",
            signer_id="owner-demo",
            signature="host-signature",
            binds_digest="sha256:ticket",
        ),
    )

    assert verification.status == "failed"
    assert verification.trust_status == "denied"
    assert verification.reason_code == "unsupported_signature_mode"


def test_runtime_admission_blocks_digest_mismatch_verification_result() -> None:
    descriptor = _descriptor()
    other = ArtifactDescriptor("execution_ticket", "v0.2", "sha256:other")
    signing, _verification = demo_sign_and_verify(
        descriptor,
        purpose="execution_ticket",
        signer_id="owner-demo",
    )
    verification = DemoDigestVerifier(allowed_signer_ids=("owner-demo",)).verify(
        other,
        signing.signature,
    )

    result = compose_runtime_admission_result(
        **_runtime_admission_inputs(trust_decision=verification.as_dict())
    )

    assert result.allowed is False
    assert result.reason_code == "signature_digest_mismatch"
    assert "signature_digest_mismatch" in result.blockers


def test_runtime_admission_blocks_untrusted_signer_verification_result() -> None:
    descriptor = _descriptor()
    signing, _verification = demo_sign_and_verify(
        descriptor,
        purpose="execution_ticket",
        signer_id="owner-demo",
    )
    verification = DemoDigestVerifier(allowed_signer_ids=("another-owner",)).verify(
        descriptor,
        signing.signature,
    )

    result = compose_runtime_admission_result(
        **_runtime_admission_inputs(trust_decision=verification.as_dict())
    )

    assert result.allowed is False
    assert result.reason_code == "trust_signer_not_allowed"
    assert "trust_signer_not_allowed" in result.blockers


def test_demo_sign_and_verify_helper_has_no_pki_claim() -> None:
    signing, verification = demo_sign_and_verify(_descriptor(), purpose="fixture")

    assert signing.signature.metadata["demo_only"] is True
    assert verification.metadata["demo_only"] is True
    assert signing.signature.algorithm == "demo-sha256-digest-binding"


def test_key_resolver_and_trust_store_ports_carry_references_only() -> None:
    class FixtureResolver:
        def resolve_key(self, request: KeyResolutionRequest) -> KeyResolutionResult:
            return KeyResolutionResult(
                status="resolved",
                signer_id=request.signer_id,
                key_ref="host-key://owner-demo/current",
                metadata={"purpose": request.purpose},
            )

    class FixtureTrustStore:
        def lookup_signer(self, signer_id: str, *, purpose: str = "") -> TrustStoreDecision:
            return TrustStoreDecision(
                status="trusted",
                signer_id=signer_id,
                trust_anchor_ref="host-trust://anchors/demo",
                metadata={"purpose": purpose},
            )

    resolver: KeyResolverPort = FixtureResolver()
    trust_store: TrustStorePort = FixtureTrustStore()

    key_result = resolver.resolve_key(KeyResolutionRequest(signer_id="owner-demo", purpose="admission"))
    trust_result = trust_store.lookup_signer("owner-demo", purpose="admission")

    assert key_result.resolved is True
    assert key_result.as_dict()["key_ref"] == "host-key://owner-demo/current"
    assert "key_material" not in key_result.as_dict()
    assert trust_result.trusted is True
    assert trust_result.as_dict()["trust_anchor_ref"] == "host-trust://anchors/demo"


def test_key_resolution_result_rejects_private_key_material() -> None:
    with pytest.raises(GovApiError, match="forbidden_trust_material"):
        KeyResolutionResult.from_mapping({
            "status": "resolved",
            "signer_id": "owner-demo",
            "key_ref": "host-key://owner-demo/current",
            "private_key": "must-not-cross-boundary",
        })


def test_trust_store_decision_rejects_secret_metadata() -> None:
    with pytest.raises(GovApiError, match="forbidden_trust_material"):
        TrustStoreDecision.from_mapping({
            "status": "trusted",
            "signer_id": "owner-demo",
            "trust_anchor_ref": "host-trust://anchors/demo",
            "metadata": {"token": "must-not-cross-boundary"},
        })


def test_key_resolution_request_rejects_api_key_metadata() -> None:
    with pytest.raises(GovApiError, match="forbidden_trust_material"):
        KeyResolutionRequest(signer_id="owner-demo", metadata={"api_key": "must-not-cross-boundary"})


def test_trust_store_decision_unknown_signer_is_not_trusted() -> None:
    decision = TrustStoreDecision.from_mapping({
        "status": "unknown",
        "signer_id": "unknown",
        "reason_code": "unknown_signer",
    })

    assert decision.trusted is False
    assert decision.reason_code == "unknown_signer"


def test_canonical_govengine_record_serializes_mapping_deterministically() -> None:
    first = canonical_govengine_record(
        {"status": "allowed", "blockers": [], "subject": {"b": 2, "a": 1}},
        record_type="govengine.admission.RuntimeAdmissionResult",
    )
    second = canonical_govengine_record(
        {"subject": {"a": 1, "b": 2}, "blockers": [], "status": "allowed"},
        record_type="govengine.admission.RuntimeAdmissionResult",
    )

    assert first == second
    payload = json.loads(first)
    assert payload["owner"] == "govengine"
    assert payload["record_type"] == "govengine.admission.RuntimeAdmissionResult"
    assert payload["record"]["subject"] == {"a": 1, "b": 2}


def test_govengine_record_digest_changes_when_owned_record_changes() -> None:
    record = {"status": "allowed", "reason_code": "ok"}
    mutated = {"status": "blocked", "reason_code": "missing_policy"}

    first = govengine_record_digest(record, record_type="govengine.admission.RuntimeAdmissionResult")
    second = govengine_record_digest(mutated, record_type="govengine.admission.RuntimeAdmissionResult")

    assert first.startswith("sha256:")
    assert second.startswith("sha256:")
    assert first != second


def test_govengine_record_digest_can_scope_govengine_dataclasses() -> None:
    descriptor = _descriptor()

    digest = govengine_record_digest(descriptor)

    assert digest.startswith("sha256:")


def test_canonical_govengine_record_rejects_non_govengine_record_type() -> None:
    with pytest.raises(GovApiError, match="invalid_govengine_record_type"):
        canonical_govengine_record({"schema": "external"}, record_type="sclite.review.Bundle")


def test_canonical_govengine_record_requires_type_for_mappings() -> None:
    with pytest.raises(GovApiError, match="missing_govengine_record_type"):
        canonical_govengine_record({"status": "allowed"})


def test_canonical_govengine_record_rejects_non_finite_float() -> None:
    with pytest.raises(GovApiError, match="unsupported_govengine_record_value"):
        canonical_govengine_record(
            {"status": "allowed", "score": nan},
            record_type="govengine.admission.RuntimeAdmissionResult",
        )


def test_canonical_govengine_record_rejects_non_string_mapping_keys() -> None:
    with pytest.raises(GovApiError, match="unsupported_govengine_record_key"):
        canonical_govengine_record(
            {"status": "allowed", 1: "colliding-key"},
            record_type="govengine.admission.RuntimeAdmissionResult",
        )


def test_demo_signed_govengine_record_binds_digest_signer_and_payload_ref() -> None:
    record = {"status": "allowed", "reason_code": "ok"}

    signed = demo_sign_govengine_record(
        record,
        record_type="govengine.admission.RuntimeAdmissionResult",
        payload_ref="artifact://admission/runtime-1",
        signer_id="owner-demo",
    )

    expected_digest = govengine_record_digest(record, record_type="govengine.admission.RuntimeAdmissionResult")
    parsed = SignedArtifact.from_mapping(signed.as_dict())

    assert parsed.as_dict() == signed.as_dict()
    assert signed.record_digest == expected_digest
    assert signed.payload_ref == "artifact://admission/runtime-1"
    assert signed.signer_id == "owner-demo"
    assert signed.signature.binds_digest == expected_digest
    assert signed.signature.metadata["demo_only"] is True
    assert signed.signature.metadata["payload_ref"] == "artifact://admission/runtime-1"


def test_verify_signed_govengine_record_uses_host_verifier_port() -> None:
    record = {"status": "allowed", "reason_code": "ok"}
    signed = demo_sign_govengine_record(
        record,
        record_type="govengine.admission.RuntimeAdmissionResult",
        payload_ref="artifact://admission/runtime-1",
        signer_id="owner-demo",
    )

    verification = verify_signed_govengine_record(
        record,
        signed,
        verifier=DemoDigestVerifier(allowed_signer_ids=("owner-demo",)),
    )

    assert verification.status == "passed"
    assert verification.trusted is True


def test_verify_signed_govengine_record_rejects_one_field_tamper() -> None:
    record, signed = _signed_runtime_record()
    tampered = {**record, "reason_code": "policy_denied"}

    verification = verify_signed_govengine_record(
        tampered,
        signed,
        verifier=DemoDigestVerifier(allowed_signer_ids=("owner-demo",)),
    )

    assert verification.status == "failed"
    assert verification.trust_status == "denied"
    assert verification.reason_code == "signed_record_digest_mismatch"


def test_verify_signed_govengine_record_rejects_tampered_record() -> None:
    record = {"status": "allowed", "reason_code": "ok"}
    signed = demo_sign_govengine_record(
        record,
        record_type="govengine.admission.RuntimeAdmissionResult",
        payload_ref="artifact://admission/runtime-1",
        signer_id="owner-demo",
    )

    verification = verify_signed_govengine_record(
        {"status": "blocked", "reason_code": "policy_denied"},
        signed,
        verifier=DemoDigestVerifier(allowed_signer_ids=("owner-demo",)),
    )

    assert verification.status == "failed"
    assert verification.reason_code == "signed_record_digest_mismatch"
    assert verification.metadata["payload_ref"] == "artifact://admission/runtime-1"


def test_verify_signed_govengine_record_rejects_wrong_signer() -> None:
    record, signed = _signed_runtime_record()

    verification = verify_signed_govengine_record(
        record,
        signed,
        verifier=DemoDigestVerifier(allowed_signer_ids=("another-owner",)),
    )

    assert verification.status == "failed"
    assert verification.trust_status == "denied"
    assert verification.reason_code == "signer_not_allowed"


def test_verify_signed_govengine_record_rejects_tampered_signature_value() -> None:
    record, signed = _signed_runtime_record()
    payload = signed.as_dict()
    payload["signature"]["signature"] = "demo:not-the-original-signature"

    verification = verify_signed_govengine_record(
        record,
        SignedArtifact.from_mapping(payload),
        verifier=DemoDigestVerifier(allowed_signer_ids=("owner-demo",)),
    )

    assert verification.status == "failed"
    assert verification.trust_status == "denied"
    assert verification.reason_code == "signature_value_mismatch"


def test_signature_transition_blocks_unknown_signer_trust_decision() -> None:
    decision = signature_transition_decision(
        _descriptor(),
        signature=SignatureEnvelope(
            mode="detached_signature",
            signer_id="unknown",
            signature="sig",
            binds_digest="sha256:ticket",
        ),
        verification=VerificationResult(status="failed", trust_status="unknown", reason_code="unknown_signer"),
        signing_policy=SigningPolicy(require_signature=True),
        trust_policy=TrustPolicy(allowed_trust_statuses=("trusted",)),
    )

    assert decision.allowed is False
    assert "trust_status_not_allowed" in decision.blockers
    assert decision.context.trust_decision["reason_code"] == "unknown_signer"


def test_key_resolution_wrong_key_status_is_not_resolved() -> None:
    result = KeyResolutionResult.from_mapping({
        "status": "wrong_key",
        "signer_id": "owner-demo",
        "key_ref": "host-key://owner-demo/old",
        "reason_code": "wrong_key",
    })

    assert result.resolved is False
    assert result.reason_code == "wrong_key"


def test_signed_artifact_from_record_requires_payload_ref() -> None:
    record = {"status": "allowed", "reason_code": "ok"}
    signed = demo_sign_govengine_record(
        record,
        record_type="govengine.admission.RuntimeAdmissionResult",
        payload_ref="artifact://admission/runtime-1",
        signer_id="owner-demo",
    )

    with pytest.raises(GovApiError, match="missing_signed_payload_ref"):
        signed_artifact_from_record(
            record,
            record_type="govengine.admission.RuntimeAdmissionResult",
            payload_ref="",
            signature=signed.signature,
        )


def test_signed_artifact_rejects_unsigned_signature() -> None:
    record = {"status": "allowed", "reason_code": "ok"}

    with pytest.raises(GovApiError, match="missing_signed_record_signature"):
        SignedArtifact(
            record_type="govengine.admission.RuntimeAdmissionResult",
            record_digest=govengine_record_digest(record, record_type="govengine.admission.RuntimeAdmissionResult"),
            payload_ref="artifact://admission/runtime-1",
            signature=SignatureEnvelope(),
        )


def test_signed_artifact_from_record_rejects_mismatched_signature_digest() -> None:
    record = {"status": "allowed", "reason_code": "ok"}

    with pytest.raises(GovApiError, match="signed_record_digest_mismatch"):
        signed_artifact_from_record(
            record,
            record_type="govengine.admission.RuntimeAdmissionResult",
            payload_ref="artifact://admission/runtime-1",
            signature=SignatureEnvelope(
                mode="detached_signature",
                signer_id="owner-demo",
                signature="sig",
                binds_digest="sha256:" + ("0" * 64),
            ),
        )


def test_signed_artifact_rejects_invalid_digest() -> None:
    with pytest.raises(GovApiError, match="invalid_signed_record_digest"):
        SignedArtifact(
            record_type="govengine.admission.RuntimeAdmissionResult",
            record_digest="sha256:not-a-real-digest",
            payload_ref="artifact://admission/runtime-1",
            signature=SignatureEnvelope(),
        )
