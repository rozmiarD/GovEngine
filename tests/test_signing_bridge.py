from __future__ import annotations

import json
from hashlib import sha256
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
    return ArtifactDescriptor("execution_ticket", "v0.2", "sha256:" + ("a" * 64))


def _runtime_admission_inputs(**overrides):
    values = {
        "admission_id": "runtime-admission-signing-1",
        "subject_ref": "sha256:prepared-contract",
        "prepared_execution_contract": {"status": "prepared", "digest": "sha256:" + ("b" * 64)},
        "policy_decision": {"decision": "allow", "policy_id": "policy-1"},
        "execution_ticket": {"status": "passed", "ticket_id": "ticket-1", "digest": "sha256:" + ("c" * 64)},
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
        binds_digest="sha256:" + ("a" * 64),
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
        binds_digest="sha256:" + ("a" * 64),
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


def test_signature_gate_rejects_failed_verification_even_with_trusted_status() -> None:
    signature = SignatureEnvelope(
        mode="detached_signature",
        signer_id="owner",
        signature="sig",
        binds_digest="sha256:" + ("a" * 64),
    )
    verification = VerificationResult(status="failed", trust_status="trusted", verifier_id="fixture")
    decision = signature_transition_decision(
        _descriptor(),
        signature=signature,
        verification=verification,
        signing_policy=SigningPolicy(require_signature=True),
        trust_policy=TrustPolicy(allowed_trust_statuses=("trusted",)),
    )

    assert decision.allowed is False
    assert decision.reason_code == "trust_denied"
    assert "verification_status_not_passed" in decision.blockers


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
    other = ArtifactDescriptor("execution_ticket", "v0.2", "sha256:" + ("d" * 64))
    signing, _verification = demo_sign_and_verify(descriptor, purpose="execution_ticket", signer_id="owner-demo")

    verification = DemoDigestVerifier(allowed_signer_ids=("owner-demo",)).verify(other, signing.signature)

    assert verification.status == "failed"
    assert verification.reason_code == "signature_digest_mismatch"


def test_demo_digest_verifier_uses_compare_digest_for_computed_signature(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    descriptor = _descriptor()
    signing = DemoDigestSigner(signer_id="owner-demo").sign(
        SigningRequest(descriptor=descriptor, purpose="execution_ticket")
    )
    comparisons: list[tuple[str, str]] = []

    def _compare_digest(actual: str, expected: str) -> bool:
        comparisons.append((actual, expected))
        return actual == expected if actual.startswith("sha256:") else False

    monkeypatch.setattr("govengine.signing.compare_digest", _compare_digest)

    verification = DemoDigestVerifier(allowed_signer_ids=("owner-demo",)).verify(
        descriptor,
        signing.signature,
    )

    assert verification.reason_code == "signature_value_mismatch"
    assert comparisons == [
        (signing.signature.binds_digest, descriptor.digest),
        (
            signing.signature.signature,
            "demo:" + sha256(
                f"{descriptor.digest}|owner-demo|execution_ticket".encode("utf-8")
            ).hexdigest(),
        ),
    ]


def test_demo_digest_verifier_rejects_unsupported_signature_mode() -> None:
    verification = DemoDigestVerifier(allowed_signer_ids=("owner-demo",)).verify(
        _descriptor(),
        SignatureEnvelope(
            mode="detached_signature",
            signer_id="owner-demo",
            signature="host-signature",
            binds_digest="sha256:" + ("a" * 64),
        ),
    )

    assert verification.status == "failed"
    assert verification.trust_status == "denied"
    assert verification.reason_code == "unsupported_signature_mode"


def test_runtime_admission_blocks_digest_mismatch_verification_result() -> None:
    descriptor = _descriptor()
    other = ArtifactDescriptor("execution_ticket", "v0.2", "sha256:" + ("d" * 64))
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


@pytest.mark.parametrize(
    ("factory", "expected"),
    [
        (
            lambda reference: KeyResolutionResult(
                status="resolved",
                signer_id="owner-demo",
                key_ref=reference,
            ),
            "host-key://owner/current",
        ),
        (
            lambda reference: KeyResolutionResult.from_mapping({
                "status": "resolved",
                "signer_id": "owner-demo",
                "key_ref": reference,
            }),
            "host-key://owner/current",
        ),
        (
            lambda reference: TrustStoreDecision(
                status="trusted",
                signer_id="owner-demo",
                trust_anchor_ref=reference,
            ),
            "host-trust://anchors/demo",
        ),
        (
            lambda reference: TrustStoreDecision.from_mapping({
                "status": "trusted",
                "signer_id": "owner-demo",
                "trust_anchor_ref": reference,
            }),
            "host-trust://anchors/demo",
        ),
    ],
    ids=["key-direct", "key-mapping", "trust-direct", "trust-mapping"],
)
def test_trust_references_preserve_known_valid_forms(factory, expected: str) -> None:
    record = factory(expected)

    assert expected in record.as_dict().values()


@pytest.mark.parametrize(
    ("factory", "reference"),
    [
        (
            lambda reference: KeyResolutionResult(
                status="resolved",
                signer_id="owner-demo",
                key_ref=reference,
            ),
            "host-key:begin-private-key-rotation-v2",
        ),
        (
            lambda reference: KeyResolutionResult.from_mapping({
                "status": "resolved",
                "signer_id": "owner-demo",
                "key_ref": reference,
            }),
            "host-key:begin-private-key-rotation-v2",
        ),
        (
            lambda reference: TrustStoreDecision(
                status="trusted",
                signer_id="owner-demo",
                trust_anchor_ref=reference,
            ),
            "host-cert:end-user-certificate-2026",
        ),
        (
            lambda reference: TrustStoreDecision.from_mapping({
                "status": "trusted",
                "signer_id": "owner-demo",
                "trust_anchor_ref": reference,
            }),
            "host-cert:end-user-certificate-2026",
        ),
        (
            lambda reference: KeyResolutionResult.from_mapping({
                "status": "resolved",
                "signer_id": "owner-demo",
                "key_ref": reference,
            }),
            "host-key:QUJDREVGR0g=",
        ),
        (
            lambda reference: KeyResolutionResult(
                status="resolved",
                signer_id="owner-demo",
                key_ref=reference,
            ),
            "host-key:-----endpoint-current-----",
        ),
        (
            lambda reference: KeyResolutionResult.from_mapping({
                "status": "resolved",
                "signer_id": "owner-demo",
                "key_ref": reference,
            }),
            "host-key:-----BEGINENDPOINT-----",
        ),
    ],
    ids=[
        "begin-words-direct",
        "begin-words-mapping",
        "end-words-direct",
        "end-words-mapping",
        "headerless-base64-residual",
        "non-material-five-dash-label",
        "begin-non-material-five-dash-label",
    ],
)
def test_trust_reference_material_words_require_structural_armor(
    factory,
    reference: str,
) -> None:
    record = factory(reference)

    assert reference in record.as_dict().values()


@pytest.mark.parametrize(
    ("factory", "reference"),
    [
        (
            lambda reference: KeyResolutionResult(
                status="resolved",
                signer_id="owner-demo",
                key_ref=reference,
            ),
            "host-key://owner/current",
        ),
        (
            lambda reference: KeyResolutionResult.from_mapping({
                "status": "resolved",
                "signer_id": "owner-demo",
                "key_ref": reference,
            }),
            "host-key://owner/current",
        ),
        (
            lambda reference: TrustStoreDecision(
                status="trusted",
                signer_id="owner-demo",
                trust_anchor_ref=reference,
            ),
            "host-trust://anchors/demo",
        ),
        (
            lambda reference: TrustStoreDecision.from_mapping({
                "status": "trusted",
                "signer_id": "owner-demo",
                "trust_anchor_ref": reference,
            }),
            "host-trust://anchors/demo",
        ),
    ],
    ids=["key-direct", "key-mapping", "trust-direct", "trust-mapping"],
)
def test_trust_reference_normalizes_ordinary_surrounding_spaces(
    factory,
    reference: str,
) -> None:
    record = factory(f"  {reference}  ")

    assert reference in record.as_dict().values()


@pytest.mark.parametrize(
    ("factory", "reason_code"),
    [
        (
            lambda reference: KeyResolutionResult(
                status="resolved",
                signer_id="owner-demo",
                key_ref=reference,
            ),
            "invalid_key_ref",
        ),
        (
            lambda reference: KeyResolutionResult.from_mapping({
                "status": "resolved",
                "signer_id": "owner-demo",
                "key_ref": reference,
            }),
            "invalid_key_ref",
        ),
        (
            lambda reference: TrustStoreDecision(
                status="trusted",
                signer_id="owner-demo",
                trust_anchor_ref=reference,
            ),
            "invalid_trust_anchor_ref",
        ),
        (
            lambda reference: TrustStoreDecision.from_mapping({
                "status": "trusted",
                "signer_id": "owner-demo",
                "trust_anchor_ref": reference,
            }),
            "invalid_trust_anchor_ref",
        ),
    ],
    ids=["key-direct", "key-mapping", "trust-direct", "trust-mapping"],
)
@pytest.mark.parametrize(
    "reference",
    [
        "host-key://owner/\x00current",
        "host-key://owner/\x1fcurrent",
        "host-key://owner/\ncurrent",
        "\nhost-key://owner/current",
        "\u2028host-key://owner/current",
        "host-key://owner/current\u2029",
        "host-key:-----PRIVATEKEY-----",
        "host-key:-----ENDCERTIFICATE-----",
        "host-key:-----benign-----PRIVATEKEY-----",
        "host-key:-----PRIVATE-----KEY-----",
        "host-key:-----PUB-----LICKEY-----",
        "host-key:-----CERT-----IFICATE-----",
        "host-key:-----" + ("x" * 129) + "PRIVATEKEY-----",
        "host-key://-----bEgInRsAPrIvAtEkEy-----",
        "host-key://-----BEGIN   OPENSSH   PRIVATE   KEY-----",
        "pem:opaque-id",
        "data:application/pkcs8;base64,QUJD",
        "pkcs8:QUJDREVGR0g=",
        "pkcs-8:QUJDREVGR0g=",
        "private-key-material:opaque-id",
        "private_key_material:opaque-id",
        "raw-private-material",
        "host-key:",
        ":owner/current",
        "1host-key:owner/current",
        "host-key:////",
        "host-key:owner current",
        "host-key:" + ("x" * 2_040),
    ],
    ids=[
        "nul",
        "control",
        "newline",
        "leading-newline",
        "leading-unicode-line-separator",
        "trailing-unicode-paragraph-separator",
        "bare-private-key-armor",
        "end-certificate-armor",
        "adjacent-delimiter-private-key-armor",
        "split-private-key-armor",
        "split-public-key-armor",
        "split-certificate-armor",
        "long-armored-private-key-bypass",
        "compact-pem-marker",
        "spaced-pem-marker",
        "pem-namespace",
        "data-namespace",
        "pkcs8-namespace",
        "punctuated-pkcs8-namespace",
        "private-key-material-namespace",
        "punctuated-private-key-material-namespace",
        "missing-namespace",
        "missing-opaque-id",
        "missing-namespace-name",
        "invalid-namespace",
        "punctuation-only-id",
        "embedded-space",
        "over-limit",
    ],
)
def test_trust_references_reject_material_and_non_reference_shapes_without_echo(
    factory,
    reason_code: str,
    reference: str,
) -> None:
    with pytest.raises(GovApiError, match=reason_code) as exc_info:
        factory(reference)

    assert reference not in str(exc_info.value)
    assert reference not in json.dumps(exc_info.value.as_dict())


@pytest.mark.parametrize(
    ("factory", "namespace"),
    [
        (
            lambda reference: KeyResolutionResult(
                status="resolved",
                signer_id="owner-demo",
                key_ref=reference,
            ),
            "host-key:",
        ),
        (
            lambda reference: KeyResolutionResult.from_mapping({
                "status": "resolved",
                "signer_id": "owner-demo",
                "key_ref": reference,
            }),
            "host-key:",
        ),
        (
            lambda reference: TrustStoreDecision(
                status="trusted",
                signer_id="owner-demo",
                trust_anchor_ref=reference,
            ),
            "host-trust:",
        ),
        (
            lambda reference: TrustStoreDecision.from_mapping({
                "status": "trusted",
                "signer_id": "owner-demo",
                "trust_anchor_ref": reference,
            }),
            "host-trust:",
        ),
    ],
    ids=["key-direct", "key-mapping", "trust-direct", "trust-mapping"],
)
def test_trust_reference_length_boundary(factory, namespace: str) -> None:
    maximum = namespace + ("x" * (2_048 - len(namespace)))

    factory(maximum)
    with pytest.raises(GovApiError):
        factory(maximum + "x")


@pytest.mark.parametrize(
    ("factory", "primary_key", "alias_key", "reason_code"),
    [
        (
            lambda value: KeyResolutionResult.from_mapping({
                "status": "resolved",
                "signer_id": "owner-demo",
                **value,
            }),
            "key_ref",
            "public_key_ref",
            "invalid_key_ref",
        ),
        (
            lambda value: TrustStoreDecision.from_mapping({
                "status": "trusted",
                "signer_id": "owner-demo",
                **value,
            }),
            "trust_anchor_ref",
            "anchor_ref",
            "invalid_trust_anchor_ref",
        ),
    ],
    ids=["key", "trust-anchor"],
)
@pytest.mark.parametrize("field_kind", ["primary", "alias"])
@pytest.mark.parametrize(
    "invalid_value",
    [False, 0, [], {}],
    ids=["false", "zero", "empty-list", "empty-mapping"],
)
def test_trust_reference_mapping_rejects_falsey_non_strings(
    factory,
    primary_key: str,
    alias_key: str,
    reason_code: str,
    field_kind: str,
    invalid_value,
) -> None:
    value = {primary_key: "host-key://owner/current"}
    value[primary_key if field_kind == "primary" else alias_key] = invalid_value

    with pytest.raises(GovApiError, match=reason_code) as exc_info:
        factory(value)

    assert exc_info.value.message == ""
    assert exc_info.value.context == {}


@pytest.mark.parametrize(
    ("factory", "primary_key", "alias_key", "primary_reference", "alias_reference"),
    [
        (
            lambda value: KeyResolutionResult.from_mapping({
                "status": "resolved",
                "signer_id": "owner-demo",
                **value,
            }),
            "key_ref",
            "public_key_ref",
            "host-key://owner/primary",
            "host-key://owner/alias",
        ),
        (
            lambda value: TrustStoreDecision.from_mapping({
                "status": "trusted",
                "signer_id": "owner-demo",
                **value,
            }),
            "trust_anchor_ref",
            "anchor_ref",
            "host-trust://anchors/primary",
            "host-trust://anchors/alias",
        ),
    ],
    ids=["key", "trust-anchor"],
)
def test_trust_reference_mapping_validates_alias_before_primary_precedence(
    factory,
    primary_key: str,
    alias_key: str,
    primary_reference: str,
    alias_reference: str,
) -> None:
    selected = factory({
        primary_key: primary_reference,
        alias_key: alias_reference,
    })
    assert primary_reference in selected.as_dict().values()

    malicious_alias = "pem:synthetic-private-material"
    with pytest.raises(GovApiError) as exc_info:
        factory({
            primary_key: primary_reference,
            alias_key: malicious_alias,
        })
    assert malicious_alias not in str(exc_info.value)
    assert malicious_alias not in repr(exc_info.value.as_dict())


@pytest.mark.parametrize(
    ("factory", "primary_key", "alias_key", "alias_reference"),
    [
        (
            lambda value: KeyResolutionResult.from_mapping({
                "status": "resolved",
                "signer_id": "owner-demo",
                **value,
            }),
            "key_ref",
            "public_key_ref",
            "host-key://owner/alias",
        ),
        (
            lambda value: TrustStoreDecision.from_mapping({
                "status": "trusted",
                "signer_id": "owner-demo",
                **value,
            }),
            "trust_anchor_ref",
            "anchor_ref",
            "host-trust://anchors/alias",
        ),
    ],
    ids=["key", "trust-anchor"],
)
@pytest.mark.parametrize("primary_value", [None, ""], ids=["none", "empty"])
def test_trust_reference_mapping_falls_back_only_for_empty_primary(
    factory,
    primary_key: str,
    alias_key: str,
    alias_reference: str,
    primary_value,
) -> None:
    selected = factory({
        primary_key: primary_value,
        alias_key: alias_reference,
    })

    assert alias_reference in selected.as_dict().values()


def test_trust_reference_mapping_falls_back_when_primary_is_absent() -> None:
    result = KeyResolutionResult.from_mapping({
        "status": "resolved",
        "signer_id": "owner-demo",
        "public_key_ref": "host-key://owner/alias",
    })

    assert result.key_ref == "host-key://owner/alias"


def test_trust_reference_mapping_does_not_fallback_from_space_only_primary() -> None:
    result = KeyResolutionResult.from_mapping({
        "status": "resolved",
        "signer_id": "owner-demo",
        "key_ref": "   ",
        "public_key_ref": "host-key://owner/alias",
    })

    assert result.key_ref == ""
    assert result.resolved is False


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


@pytest.mark.parametrize(
    "record",
    [
        lambda metadata: KeyResolutionRequest(
            signer_id="owner-demo",
            metadata=metadata,
        ),
        lambda metadata: KeyResolutionResult.from_mapping({
            "status": "resolved",
            "signer_id": "owner-demo",
            "key_ref": "host-key://owner-demo/current",
            "metadata": metadata,
        }),
        lambda metadata: TrustStoreDecision.from_mapping({
            "status": "trusted",
            "signer_id": "owner-demo",
            "trust_anchor_ref": "host-trust://anchors/demo",
            "metadata": metadata,
        }),
    ],
)
def test_trust_records_reject_forbidden_keys_inside_nested_collections(record) -> None:
    with pytest.raises(GovApiError, match="forbidden_trust_material"):
        record({"items": [{"nested": ({"password": "must-not-cross-boundary"},)}]})


def test_trust_records_normalize_forbidden_key_spelling() -> None:
    with pytest.raises(GovApiError, match="forbidden_trust_material"):
        TrustStoreDecision.from_mapping({
            "status": "trusted",
            "signer_id": "owner-demo",
            "trust_anchor_ref": "host-trust://anchors/demo",
            "metadata": {"nested": {" PASSWORD ": "must-not-cross-boundary"}},
        })


def test_trust_metadata_uses_shared_json_depth_limit() -> None:
    metadata = {}
    cursor = metadata
    for _ in range(34):
        cursor["nested"] = {}
        cursor = cursor["nested"]

    with pytest.raises(GovApiError, match="json_boundary_max_depth"):
        KeyResolutionRequest(signer_id="owner-demo", metadata=metadata)


def test_trust_metadata_rejects_non_finite_numbers() -> None:
    with pytest.raises(GovApiError, match="json_boundary_non_finite_number"):
        KeyResolutionResult.from_mapping({
            "status": "resolved",
            "signer_id": "owner-demo",
            "key_ref": "host-key://owner-demo/current",
            "metadata": {"confidence": nan},
        })


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


def test_v1_canonical_record_bytes_and_digest_remain_frozen() -> None:
    record = {
        "status": "allowed",
        "blockers": [],
        "subject": {"b": 2, "a": 1},
        "score": 1.0,
        "negative_zero": -0.0,
        "small": 1e-7,
    }
    record_type = "govengine.admission.RuntimeAdmissionResult"

    assert canonical_govengine_record(record, record_type=record_type) == (
        '{"owner":"govengine","record":{"blockers":[],"negative_zero":-0.0,'
        '"score":1.0,"small":1e-07,"status":"allowed","subject":{"a":1,"b":2}},'
        '"record_type":"govengine.admission.RuntimeAdmissionResult","schema_version":"v1"}'
    )
    assert govengine_record_digest(record, record_type=record_type) == (
        "sha256:5b7cadc6e8dc15afc8d07655776ead2bcbaaad5016a65ebe1351bf2f36cd5105"
    )


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
            binds_digest="sha256:" + ("a" * 64),
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


def test_signed_artifact_rejects_uppercase_digest_without_normalizing() -> None:
    with pytest.raises(GovApiError, match="invalid_signed_record_digest"):
        SignedArtifact(
            record_type="govengine.admission.RuntimeAdmissionResult",
            record_digest="sha256:" + ("A" * 64),
            payload_ref="artifact://admission/runtime-1",
            signature=SignatureEnvelope(),
        )
