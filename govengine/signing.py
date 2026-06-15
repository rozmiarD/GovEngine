from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, is_dataclass
from hashlib import sha256
from math import isfinite
from string import hexdigits
from typing import Any, Mapping, Protocol

from govengine.api import GovApiError, require_mapping
from govengine.core import ArtifactDescriptor, GovernanceContext, ReasonCode, TransitionDecision

INTEGRITY_ONLY_SIGNATURE_MODES = {"", "integrity_only", "not_signed_integrity_only"}
FORBIDDEN_TRUST_MATERIAL_KEYS = {
    "api_key",
    "credential",
    "credentials",
    "key_material",
    "passphrase",
    "password",
    "pem",
    "private_key",
    "secret",
    "token",
}


@dataclass(frozen=True)
class SignatureEnvelope:
    """Portable signature metadata at a GovEngine boundary.

    GovEngine does not implement PKI, key storage, or cryptographic signing in
    core. This envelope only carries signature metadata and the digest binding
    that a host-provided verifier can evaluate.
    """

    mode: str = "not_signed_integrity_only"
    signer_id: str = ""
    signature: str = ""
    binds_digest: str = ""
    algorithm: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any] | None) -> "SignatureEnvelope":
        if value is None:
            return cls()
        raw = require_mapping(value, reason_code="invalid_signature_envelope")
        metadata = raw.get("metadata") if isinstance(raw.get("metadata"), Mapping) else {}
        return cls(
            mode=str(raw.get("mode") or "not_signed_integrity_only"),
            signer_id=str(raw.get("signer_id") or raw.get("identity") or ""),
            signature=str(raw.get("signature") or raw.get("value") or ""),
            binds_digest=str(raw.get("binds_digest") or raw.get("artifact_digest") or raw.get("chain_digest") or ""),
            algorithm=str(raw.get("algorithm") or ""),
            metadata=dict(metadata),
        )

    @property
    def signed(self) -> bool:
        return self.mode not in INTEGRITY_ONLY_SIGNATURE_MODES and bool(self.signature)

    def as_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["metadata"] = dict(self.metadata)
        out["signed"] = self.signed
        return out


@dataclass(frozen=True)
class SigningPolicy:
    """Local signing requirement for a transition/execution boundary."""

    require_signature: bool = False
    allowed_modes: tuple[str, ...] = ("not_signed_integrity_only", "integrity_only", "detached_signature")
    required_signer_ids: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "require_signature": self.require_signature,
            "allowed_modes": list(self.allowed_modes),
            "required_signer_ids": list(self.required_signer_ids),
        }


@dataclass(frozen=True)
class TrustPolicy:
    """Trust-policy summary evaluated from host-provided verification."""

    allowed_trust_statuses: tuple[str, ...] = ("trusted", "passed", "ok")

    def as_dict(self) -> dict[str, Any]:
        return {"allowed_trust_statuses": list(self.allowed_trust_statuses)}


@dataclass(frozen=True)
class KeyResolutionRequest:
    """Host-neutral request to resolve a signer key reference.

    GovEngine only asks for a reference. Key storage, key material, KMS, CA,
    rotation, and revocation remain host-owned.
    """

    signer_id: str
    purpose: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        signer_id = str(self.signer_id or "").strip()
        if not signer_id:
            raise GovApiError("missing_signer_id")
        metadata = _bounded_trust_metadata(self.metadata)
        object.__setattr__(self, "signer_id", signer_id)
        object.__setattr__(self, "purpose", str(self.purpose or ""))
        object.__setattr__(self, "metadata", metadata)

    def as_dict(self) -> dict[str, Any]:
        return {
            "signer_id": self.signer_id,
            "purpose": self.purpose,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class KeyResolutionResult:
    """Host-neutral key reference result without key material."""

    status: str
    signer_id: str
    key_ref: str = ""
    reason_code: str = ReasonCode.OK.value
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        signer_id = str(self.signer_id or "").strip()
        if not signer_id:
            raise GovApiError("missing_signer_id")
        metadata = _bounded_trust_metadata(self.metadata)
        object.__setattr__(self, "status", str(self.status or "unknown"))
        object.__setattr__(self, "signer_id", signer_id)
        object.__setattr__(self, "key_ref", str(self.key_ref or ""))
        object.__setattr__(self, "reason_code", str(self.reason_code or ReasonCode.OK.value))
        object.__setattr__(self, "metadata", metadata)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "KeyResolutionResult":
        raw = require_mapping(value, reason_code="invalid_key_resolution_result")
        _reject_forbidden_trust_material(raw)
        metadata = raw.get("metadata") if isinstance(raw.get("metadata"), Mapping) else {}
        return cls(
            status=str(raw.get("status") or ""),
            signer_id=str(raw.get("signer_id") or ""),
            key_ref=str(raw.get("key_ref") or raw.get("public_key_ref") or ""),
            reason_code=str(raw.get("reason_code") or ReasonCode.OK.value),
            metadata=dict(metadata),
        )

    @property
    def resolved(self) -> bool:
        return self.status in {"resolved", "passed", "ok"} and bool(self.key_ref)

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "resolved": self.resolved,
            "signer_id": self.signer_id,
            "key_ref": self.key_ref,
            "reason_code": self.reason_code,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class TrustStoreDecision:
    """Host-neutral trust-store decision without owning the trust store."""

    status: str
    signer_id: str
    trust_anchor_ref: str = ""
    reason_code: str = ReasonCode.OK.value
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        signer_id = str(self.signer_id or "").strip()
        if not signer_id:
            raise GovApiError("missing_signer_id")
        metadata = _bounded_trust_metadata(self.metadata)
        object.__setattr__(self, "status", str(self.status or "unknown"))
        object.__setattr__(self, "signer_id", signer_id)
        object.__setattr__(self, "trust_anchor_ref", str(self.trust_anchor_ref or ""))
        object.__setattr__(self, "reason_code", str(self.reason_code or ReasonCode.OK.value))
        object.__setattr__(self, "metadata", metadata)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "TrustStoreDecision":
        raw = require_mapping(value, reason_code="invalid_trust_store_decision")
        _reject_forbidden_trust_material(raw)
        metadata = raw.get("metadata") if isinstance(raw.get("metadata"), Mapping) else {}
        return cls(
            status=str(raw.get("status") or raw.get("trust_status") or ""),
            signer_id=str(raw.get("signer_id") or ""),
            trust_anchor_ref=str(raw.get("trust_anchor_ref") or raw.get("anchor_ref") or ""),
            reason_code=str(raw.get("reason_code") or ReasonCode.OK.value),
            metadata=dict(metadata),
        )

    @property
    def trusted(self) -> bool:
        return self.status in {"trusted", "passed", "ok"} and bool(self.trust_anchor_ref)

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "trusted": self.trusted,
            "signer_id": self.signer_id,
            "trust_anchor_ref": self.trust_anchor_ref,
            "reason_code": self.reason_code,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class SigningRequest:
    """Request shape for host-provided signing ports."""

    descriptor: ArtifactDescriptor
    purpose: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "descriptor": self.descriptor.as_dict(),
            "purpose": self.purpose,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class SigningResult:
    status: str
    signature: SignatureEnvelope
    reason_code: str = ReasonCode.OK.value

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reason_code": self.reason_code,
            "signature": self.signature.as_dict(),
        }


@dataclass(frozen=True)
class VerificationResult:
    status: str
    trust_status: str = "unknown"
    reason_code: str = ReasonCode.OK.value
    verifier_id: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def trusted(self) -> bool:
        return self.status in {"passed", "ok"} and self.trust_status in {"trusted", "passed", "ok"}

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "trust_status": self.trust_status,
            "trusted": self.trusted,
            "reason_code": self.reason_code,
            "verifier_id": self.verifier_id,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class SignedArtifact:
    """Envelope for a signed GovEngine-owned record.

    The envelope binds a GovEngine-owned record digest, signer metadata, and a
    payload reference. It does not implement PKI, KMS, key storage, or SCLite
    canonicalization.
    """

    record_type: str
    record_digest: str
    payload_ref: str
    signature: SignatureEnvelope | Mapping[str, Any] = field(default_factory=SignatureEnvelope)
    schema_version: str = "v1"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        record_type = _validate_govengine_record_type(self.record_type)
        record_digest = _validate_govengine_record_digest(self.record_digest)
        payload_ref = str(self.payload_ref or "").strip()
        if not payload_ref:
            raise GovApiError("missing_signed_payload_ref")
        signature = self.signature if isinstance(self.signature, SignatureEnvelope) else SignatureEnvelope.from_mapping(self.signature)
        if not signature.signed:
            raise GovApiError("missing_signed_record_signature")
        if not signature.signer_id:
            raise GovApiError("missing_signed_record_signer")
        if signature.binds_digest != record_digest:
            raise GovApiError("signed_record_digest_mismatch")
        metadata = self.metadata if isinstance(self.metadata, Mapping) else {}
        object.__setattr__(self, "record_type", record_type)
        object.__setattr__(self, "record_digest", record_digest)
        object.__setattr__(self, "payload_ref", payload_ref)
        object.__setattr__(self, "signature", signature)
        object.__setattr__(self, "schema_version", str(self.schema_version or "v1"))
        object.__setattr__(self, "metadata", dict(metadata))

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "SignedArtifact":
        raw = require_mapping(value, reason_code="invalid_signed_artifact")
        signature = raw.get("signature") if isinstance(raw.get("signature"), Mapping) else {}
        signature_payload = dict(signature)
        if raw.get("signer_id") and not signature_payload.get("signer_id"):
            signature_payload["signer_id"] = raw.get("signer_id")
        metadata = raw.get("metadata") if isinstance(raw.get("metadata"), Mapping) else {}
        return cls(
            record_type=str(raw.get("record_type") or ""),
            record_digest=str(raw.get("record_digest") or raw.get("digest") or ""),
            payload_ref=str(raw.get("payload_ref") or raw.get("payload_reference") or ""),
            signature=SignatureEnvelope.from_mapping(signature_payload),
            schema_version=str(raw.get("schema_version") or "v1"),
            metadata=dict(metadata),
        )

    @property
    def signer_id(self) -> str:
        return self.signature.signer_id

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "record_type": self.record_type,
            "record_digest": self.record_digest,
            "payload_ref": self.payload_ref,
            "signer_id": self.signer_id,
            "signature": self.signature.as_dict(),
            "metadata": dict(self.metadata),
        }


def canonical_govengine_record(
    record: Mapping[str, Any] | Any,
    *,
    record_type: str = "",
    schema_version: str = "v1",
) -> str:
    """Serialize a GovEngine-owned record deterministically.

    This helper is scoped to GovEngine-owned records only. It is not SCLite
    canonicalization, artifact-chain verification, PKI, KMS, or a raw evidence
    storage format.
    """

    resolved_type = _resolve_govengine_record_type(record, record_type=record_type)
    envelope = {
        "owner": "govengine",
        "record_type": resolved_type,
        "schema_version": str(schema_version or "v1"),
        "record": _canonical_record_value(record),
    }
    return json.dumps(envelope, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def govengine_record_digest(
    record: Mapping[str, Any] | Any,
    *,
    record_type: str = "",
    schema_version: str = "v1",
    algorithm: str = "sha256",
) -> str:
    """Return a deterministic digest for a GovEngine-owned record."""

    if algorithm != "sha256":
        raise GovApiError("unsupported_govengine_record_digest_algorithm", algorithm)
    payload = canonical_govengine_record(record, record_type=record_type, schema_version=schema_version)
    return f"sha256:{sha256(payload.encode('utf-8')).hexdigest()}"


def signed_artifact_from_record(
    record: Mapping[str, Any] | Any,
    *,
    record_type: str,
    payload_ref: str,
    signature: SignatureEnvelope | Mapping[str, Any],
    schema_version: str = "v1",
    metadata: Mapping[str, Any] | None = None,
) -> SignedArtifact:
    """Create a signed-artifact envelope for a GovEngine-owned record."""

    return SignedArtifact(
        record_type=record_type,
        record_digest=govengine_record_digest(record, record_type=record_type, schema_version=schema_version),
        payload_ref=payload_ref,
        signature=signature,
        schema_version=schema_version,
        metadata=metadata or {},
    )


def _resolve_govengine_record_type(record: Any, *, record_type: str) -> str:
    explicit = str(record_type or "").strip()
    if explicit:
        return _validate_govengine_record_type(explicit)
    if is_dataclass(record) and not isinstance(record, type):
        cls = record.__class__
        module = str(cls.__module__)
        if module.startswith("govengine."):
            return f"{module}.{cls.__name__}"
    raise GovApiError("missing_govengine_record_type", "mapping records require an explicit govengine.* record_type")


def _validate_govengine_record_type(record_type: str) -> str:
    resolved = str(record_type or "").strip()
    if not resolved:
        raise GovApiError("missing_govengine_record_type")
    if not resolved.startswith("govengine."):
        raise GovApiError("invalid_govengine_record_type", "record_type must start with govengine.")
    return resolved


def _validate_govengine_record_digest(record_digest: str) -> str:
    digest = str(record_digest or "").strip().lower()
    prefix = "sha256:"
    value = digest.removeprefix(prefix)
    if not digest.startswith(prefix) or len(value) != 64 or any(char not in hexdigits for char in value):
        raise GovApiError("invalid_signed_record_digest")
    return digest


def _bounded_trust_metadata(value: Mapping[str, Any] | None) -> dict[str, Any]:
    metadata = value if isinstance(value, Mapping) else {}
    _reject_forbidden_trust_material(metadata)
    return dict(metadata)


def _reject_forbidden_trust_material(value: Mapping[str, Any]) -> None:
    for key in value:
        if str(key).lower() in FORBIDDEN_TRUST_MATERIAL_KEYS:
            raise GovApiError("forbidden_trust_material")


def _canonical_record_value(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return _canonical_record_value(asdict(value))
    if isinstance(value, Mapping):
        for key in value:
            if not isinstance(key, str):
                raise GovApiError("unsupported_govengine_record_key", type(key).__name__)
        return {key: _canonical_record_value(value[key]) for key in sorted(value)}
    if isinstance(value, (tuple, list)):
        return [_canonical_record_value(item) for item in value]
    if isinstance(value, float) and not isfinite(value):
        raise GovApiError("unsupported_govengine_record_value", "non_finite_float")
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    raise GovApiError("unsupported_govengine_record_value", type(value).__name__)




@dataclass(frozen=True)
class DemoDigestSigner:
    """Deterministic host-demo signer for fixtures and tests.

    This is deliberately not PKI and not a production signing backend. It keeps
    no keys and produces a reproducible detached demo signature bound to the
    descriptor digest, signer id, and request purpose so hosts can exercise the
    signing/trust ports without claiming cryptographic identity.
    """

    signer_id: str = "demo-signer"
    algorithm: str = "demo-sha256-digest-binding"

    def sign(self, request: SigningRequest) -> SigningResult:
        payload = f"{request.descriptor.digest}|{self.signer_id}|{request.purpose}".encode("utf-8")
        digest = sha256(payload).hexdigest()
        envelope = SignatureEnvelope(
            mode="detached_demo_digest",
            signer_id=self.signer_id,
            signature=f"demo:{digest}",
            binds_digest=request.descriptor.digest,
            algorithm=self.algorithm,
            metadata={"purpose": request.purpose, "demo_only": True},
        )
        return SigningResult(status="signed", signature=envelope, reason_code=ReasonCode.OK.value)


@dataclass(frozen=True)
class DemoDigestVerifier:
    """Verifier companion for :class:`DemoDigestSigner`.

    The verifier checks deterministic digest binding and optional signer ids. It
    returns a trust decision for demo/test purposes only; it is not a CA, KMS,
    key store, certificate verifier, or production identity proof.
    """

    verifier_id: str = "demo-verifier"
    allowed_signer_ids: tuple[str, ...] = ()
    trusted_status: str = "trusted"

    def verify(self, descriptor: ArtifactDescriptor, signature: SignatureEnvelope) -> VerificationResult:
        if signature.mode != "detached_demo_digest":
            return VerificationResult(status="failed", trust_status="denied", reason_code="unsupported_signature_mode", verifier_id=self.verifier_id)
        if signature.binds_digest != descriptor.digest:
            return VerificationResult(status="failed", trust_status="denied", reason_code="signature_digest_mismatch", verifier_id=self.verifier_id)
        if self.allowed_signer_ids and signature.signer_id not in self.allowed_signer_ids:
            return VerificationResult(status="failed", trust_status="denied", reason_code="signer_not_allowed", verifier_id=self.verifier_id)
        purpose = str(signature.metadata.get("purpose") or "") if isinstance(signature.metadata, Mapping) else ""
        expected = "demo:" + sha256(f"{descriptor.digest}|{signature.signer_id}|{purpose}".encode("utf-8")).hexdigest()
        if signature.signature != expected:
            return VerificationResult(status="failed", trust_status="denied", reason_code="signature_value_mismatch", verifier_id=self.verifier_id)
        return VerificationResult(
            status="passed",
            trust_status=self.trusted_status,
            reason_code=ReasonCode.OK.value,
            verifier_id=self.verifier_id,
            metadata={"demo_only": True, "signer_id": signature.signer_id, "purpose": purpose},
        )


def demo_sign_and_verify(
    descriptor: ArtifactDescriptor,
    *,
    purpose: str = "artifact_transition",
    signer_id: str = "demo-signer",
    verifier_id: str = "demo-verifier",
) -> tuple[SigningResult, VerificationResult]:
    """Exercise the host signing/verifier ports with deterministic demo objects."""

    signer = DemoDigestSigner(signer_id=signer_id)
    signing = signer.sign(SigningRequest(descriptor=descriptor, purpose=purpose, metadata={"demo_only": True}))
    verifier = DemoDigestVerifier(verifier_id=verifier_id, allowed_signer_ids=(signer_id,))
    verification = verifier.verify(descriptor, signing.signature)
    return signing, verification


def demo_sign_govengine_record(
    record: Mapping[str, Any] | Any,
    *,
    record_type: str,
    payload_ref: str,
    signer_id: str = "demo-signer",
    purpose: str = "govengine_record",
    schema_version: str = "v1",
) -> SignedArtifact:
    """Create a demo-only signed envelope for a GovEngine-owned record."""

    record_digest = govengine_record_digest(record, record_type=record_type, schema_version=schema_version)
    descriptor = ArtifactDescriptor(
        "govengine_record",
        schema_version,
        record_digest,
        role=record_type,
        path=payload_ref,
        metadata={"demo_only": True},
    )
    signing = DemoDigestSigner(signer_id=signer_id).sign(
        SigningRequest(descriptor=descriptor, purpose=purpose, metadata={"demo_only": True, "record_type": record_type})
    )
    signature = SignatureEnvelope(
        mode=signing.signature.mode,
        signer_id=signing.signature.signer_id,
        signature=signing.signature.signature,
        binds_digest=signing.signature.binds_digest,
        algorithm=signing.signature.algorithm,
        metadata={**dict(signing.signature.metadata), "record_type": record_type, "payload_ref": payload_ref},
    )
    return SignedArtifact(
        record_type=record_type,
        record_digest=record_digest,
        payload_ref=payload_ref,
        signature=signature,
        schema_version=schema_version,
        metadata={"demo_only": True, "purpose": purpose},
    )


class SignerPort(Protocol):
    """Host-provided signing port. GovEngine core must not store keys."""

    def sign(self, request: SigningRequest) -> SigningResult:
        ...


class VerifierPort(Protocol):
    """Host-provided verifier port. GovEngine core must not own PKI."""

    def verify(self, descriptor: ArtifactDescriptor, signature: SignatureEnvelope) -> VerificationResult:
        ...


class KeyResolverPort(Protocol):
    """Host-provided key resolver. GovEngine receives references, not keys."""

    def resolve_key(self, request: KeyResolutionRequest) -> KeyResolutionResult:
        ...


class TrustStorePort(Protocol):
    """Host-provided trust store. GovEngine does not store trust anchors."""

    def lookup_signer(self, signer_id: str, *, purpose: str = "") -> TrustStoreDecision:
        ...


def verify_signed_govengine_record(
    record: Mapping[str, Any] | Any,
    signed_artifact: SignedArtifact | Mapping[str, Any],
    *,
    verifier: VerifierPort,
) -> VerificationResult:
    """Verify a signed GovEngine-owned record envelope with a host verifier."""

    artifact = signed_artifact if isinstance(signed_artifact, SignedArtifact) else SignedArtifact.from_mapping(signed_artifact)
    computed_digest = govengine_record_digest(
        record,
        record_type=artifact.record_type,
        schema_version=artifact.schema_version,
    )
    if computed_digest != artifact.record_digest:
        return VerificationResult(
            status="failed",
            trust_status="denied",
            reason_code="signed_record_digest_mismatch",
            verifier_id=str(getattr(verifier, "verifier_id", "")),
            metadata={"record_type": artifact.record_type, "payload_ref": artifact.payload_ref},
        )
    descriptor = ArtifactDescriptor(
        "govengine_record",
        artifact.schema_version,
        artifact.record_digest,
        role=artifact.record_type,
        path=artifact.payload_ref,
    )
    return verifier.verify(descriptor, artifact.signature)


def signature_transition_decision(
    descriptor: ArtifactDescriptor,
    *,
    signature: SignatureEnvelope | Mapping[str, Any] | None = None,
    verification: VerificationResult | None = None,
    signing_policy: SigningPolicy | None = None,
    trust_policy: TrustPolicy | None = None,
    from_state: str = "unsigned",
    to_state: str = "trusted",
) -> TransitionDecision:
    """Evaluate signature/trust readiness for an artifact transition."""

    signing_policy = signing_policy or SigningPolicy()
    trust_policy = trust_policy or TrustPolicy()
    envelope = signature if isinstance(signature, SignatureEnvelope) else SignatureEnvelope.from_mapping(signature)
    blockers: list[str] = []
    next_actions: list[str] = []

    if envelope.mode not in signing_policy.allowed_modes:
        blockers.append("signature_mode_not_allowed")
        next_actions.append("use_allowed_signature_mode")

    if signing_policy.require_signature and not envelope.signed:
        blockers.append("signature_required")
        next_actions.append("obtain_signature")

    if signing_policy.required_signer_ids and envelope.signer_id not in signing_policy.required_signer_ids:
        blockers.append("signer_not_allowed")
        next_actions.append("obtain_signature_from_allowed_signer")

    if envelope.binds_digest and envelope.binds_digest != descriptor.digest:
        blockers.append("signature_digest_mismatch")
        next_actions.append("resign_current_descriptor")

    if signing_policy.require_signature and envelope.signed and not envelope.binds_digest:
        blockers.append("signature_missing_digest_binding")
        next_actions.append("bind_signature_to_descriptor_digest")

    if signing_policy.require_signature and envelope.signed and verification is None:
        blockers.append("trust_decision_required")
        next_actions.append("verify_signature_trust")

    if verification is not None and verification.status not in {"passed", "ok"}:
        blockers.append("verification_status_not_passed")
        next_actions.append("obtain_valid_trust_decision")

    if verification is not None and verification.trust_status not in trust_policy.allowed_trust_statuses:
        blockers.append("trust_status_not_allowed")
        next_actions.append("obtain_valid_trust_decision")

    if blockers:
        reason = ReasonCode.SIGNATURE_REQUIRED.value if "signature_required" in blockers else ReasonCode.TRUST_DENIED.value
        return TransitionDecision(
            status="blocked",
            reason_code=reason,
            from_state=from_state,
            to_state=to_state,
            artifacts=(descriptor,),
            blockers=tuple(dict.fromkeys(blockers)),
            next_actions=tuple(dict.fromkeys(next_actions)),
            context=GovernanceContext(
                trust_decision=verification.as_dict() if verification else {},
                metadata={"signing_policy": signing_policy.as_dict(), "signature": envelope.as_dict()},
            ),
        )

    return TransitionDecision(
        status="allowed",
        reason_code=ReasonCode.OK.value,
        from_state=from_state,
        to_state=to_state,
        artifacts=(descriptor,),
        context=GovernanceContext(
            trust_decision=verification.as_dict() if verification else {"status": "not_required"},
            metadata={"signing_policy": signing_policy.as_dict(), "signature": envelope.as_dict()},
        ),
    )


def signature_envelope_from_artifact(artifact: Mapping[str, Any]) -> SignatureEnvelope:
    raw = require_mapping(artifact, reason_code="invalid_signed_artifact")
    signature = raw.get("signature")
    if signature is None:
        return SignatureEnvelope()
    if not isinstance(signature, Mapping):
        raise GovApiError("invalid_signature_envelope")
    return SignatureEnvelope.from_mapping(signature)
