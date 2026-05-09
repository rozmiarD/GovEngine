from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Mapping

from govengine.api import GovApiError, require_mapping


class ReasonCode(str, Enum):
    """Portable reason codes for GovEngine boundary decisions."""

    OK = "ok"
    MISSING_ARTIFACT = "missing_artifact"
    INVALID_ARTIFACT = "invalid_artifact"
    LIFECYCLE_BLOCKED = "lifecycle_blocked"
    POLICY_DENIED = "policy_denied"
    SIGNATURE_REQUIRED = "signature_required"
    TRUST_DENIED = "trust_denied"
    RUNNER_PROFILE_DENIED = "runner_profile_denied"
    EXECUTION_DISABLED = "execution_disabled"
    RAW_INTENT_REJECTED = "raw_intent_rejected"


@dataclass(frozen=True)
class ArtifactDescriptor:
    """Neutral descriptor for a governed artifact.

    SCLite owns canonicalization and digest calculation. GovEngine treats the
    descriptor as an input boundary object and does not recalculate hashes here.
    """

    artifact_type: str
    schema_version: str
    digest: str
    role: str = ""
    path: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ArtifactDescriptor":
        raw = require_mapping(value, reason_code="invalid_artifact_descriptor")
        artifact_type = str(raw.get("artifact_type") or "").strip()
        schema_version = str(raw.get("schema_version") or raw.get("version") or "").strip()
        digest = str(raw.get("digest") or raw.get("sha256") or "").strip()
        if not artifact_type:
            raise GovApiError("missing_artifact_type")
        if not schema_version:
            raise GovApiError("missing_schema_version")
        if not digest:
            raise GovApiError("missing_artifact_digest")
        metadata = raw.get("metadata") if isinstance(raw.get("metadata"), Mapping) else {}
        return cls(
            artifact_type=artifact_type,
            schema_version=schema_version,
            digest=digest,
            role=str(raw.get("role") or ""),
            path=str(raw.get("path") or ""),
            metadata=dict(metadata),
        )

    def as_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["metadata"] = dict(self.metadata)
        return out


@dataclass(frozen=True)
class ArtifactEnvelope:
    """Artifact payload plus descriptor at the GovEngine boundary."""

    descriptor: ArtifactDescriptor
    artifact: Mapping[str, Any] = field(default_factory=dict)
    source: str = ""

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ArtifactEnvelope":
        raw = require_mapping(value, reason_code="invalid_artifact_envelope")
        descriptor_value = raw.get("descriptor")
        if not isinstance(descriptor_value, Mapping):
            raise GovApiError("missing_artifact_descriptor")
        artifact_value = raw.get("artifact") if isinstance(raw.get("artifact"), Mapping) else {}
        return cls(
            descriptor=ArtifactDescriptor.from_mapping(descriptor_value),
            artifact=dict(artifact_value),
            source=str(raw.get("source") or ""),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "descriptor": self.descriptor.as_dict(),
            "artifact": dict(self.artifact),
            "source": self.source,
        }


@dataclass(frozen=True)
class GovernanceContext:
    """Portable context supplied by a host or caller.

    This is intentionally smaller than a runtime context: it carries policy,
    trust, and runner-profile decisions without requiring Ravenclaw paths.
    """

    context_id: str = "default"
    profile: str = "generic"
    policy_decision: Mapping[str, Any] = field(default_factory=dict)
    trust_decision: Mapping[str, Any] = field(default_factory=dict)
    runner_profile: str = "dry-run"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "context_id": self.context_id,
            "profile": self.profile,
            "policy_decision": dict(self.policy_decision),
            "trust_decision": dict(self.trust_decision),
            "runner_profile": self.runner_profile,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class ArtifactState:
    """Current governance state for one artifact descriptor."""

    descriptor: ArtifactDescriptor
    lifecycle_state: str = "unknown"
    chain_status: str = "unknown"
    signature_status: str = "not_required"
    policy_status: str = "unknown"
    blocked_reasons: tuple[str, ...] = ()
    next_actions: tuple[str, ...] = ()

    @property
    def blocked(self) -> bool:
        return bool(self.blocked_reasons)

    def as_dict(self) -> dict[str, Any]:
        return {
            "descriptor": self.descriptor.as_dict(),
            "lifecycle_state": self.lifecycle_state,
            "chain_status": self.chain_status,
            "signature_status": self.signature_status,
            "policy_status": self.policy_status,
            "blocked": self.blocked,
            "blocked_reasons": list(self.blocked_reasons),
            "next_actions": list(self.next_actions),
        }


@dataclass(frozen=True)
class TransitionDecision:
    """Portable lifecycle transition decision."""

    status: str
    reason_code: str = ReasonCode.OK.value
    from_state: str = ""
    to_state: str = ""
    artifacts: tuple[ArtifactDescriptor, ...] = ()
    blockers: tuple[str, ...] = ()
    next_actions: tuple[str, ...] = ()
    context: GovernanceContext = field(default_factory=GovernanceContext)

    @property
    def allowed(self) -> bool:
        return self.status in {"allowed", "ok"} and not self.blockers

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "allowed": self.allowed,
            "reason_code": self.reason_code,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "artifacts": [artifact.as_dict() for artifact in self.artifacts],
            "blockers": list(self.blockers),
            "next_actions": list(self.next_actions),
            "context": self.context.as_dict(),
        }


@dataclass(frozen=True)
class ExecutionPrerequisites:
    """Gate summary proving execution is not being requested from raw intent."""

    has_prepared_execution_contract: bool = False
    policy_decision_status: str = "missing"
    execution_ticket_status: str = "missing"
    trust_decision_status: str = "missing"
    runner_profile_allowed: bool = False
    runner_profile: str = "dry-run"
    live_backend_enabled: bool = False

    def missing_reasons(self, *, live: bool = False) -> tuple[str, ...]:
        reasons: list[str] = []
        if not self.has_prepared_execution_contract:
            reasons.append("missing_prepared_execution_contract")
        if self.policy_decision_status not in {"allow", "allowed", "passed", "ok"}:
            reasons.append("missing_or_invalid_policy_decision")
        if self.execution_ticket_status not in {"approve", "approved", "approved_for_dry_run", "passed", "ok"}:
            reasons.append("missing_or_invalid_execution_ticket")
        if self.trust_decision_status not in {"trusted", "passed", "ok"}:
            reasons.append("missing_or_invalid_trust_decision")
        if not self.runner_profile_allowed:
            reasons.append("runner_profile_not_allowed")
        if live and not self.live_backend_enabled:
            reasons.append("live_backend_disabled")
        return tuple(reasons)

    def transition_decision(self, *, live: bool = False) -> TransitionDecision:
        reasons = self.missing_reasons(live=live)
        if reasons:
            return TransitionDecision(
                status="blocked",
                reason_code=ReasonCode.EXECUTION_DISABLED.value if live and "live_backend_disabled" in reasons else ReasonCode.RAW_INTENT_REJECTED.value,
                blockers=reasons,
                next_actions=("prepare_execution_contract", "obtain_policy_decision", "approve_execution_ticket", "verify_trust_decision", "select_allowed_runner_profile"),
                context=GovernanceContext(runner_profile=self.runner_profile),
            )
        return TransitionDecision(
            status="allowed",
            reason_code=ReasonCode.OK.value,
            context=GovernanceContext(runner_profile=self.runner_profile),
        )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
