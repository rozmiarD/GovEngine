from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Protocol

from govengine.api import GovApiError, require_mapping
from govengine.core import ArtifactDescriptor, GovernanceContext, ReasonCode, TransitionDecision

INTEGRITY_ONLY_SIGNATURE_MODES = {"", "integrity_only", "not_signed_integrity_only"}


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


class SignerPort(Protocol):
    """Host-provided signing port. GovEngine core must not store keys."""

    def sign(self, request: SigningRequest) -> SigningResult:
        ...


class VerifierPort(Protocol):
    """Host-provided verifier port. GovEngine core must not own PKI."""

    def verify(self, descriptor: ArtifactDescriptor, signature: SignatureEnvelope) -> VerificationResult:
        ...


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
