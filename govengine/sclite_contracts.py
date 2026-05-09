from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Protocol

from govengine.core import ArtifactDescriptor, ArtifactState, ReasonCode, TransitionDecision
from sclite.integrity import artifact_descriptor, verify_artifact_chain_manifest
from sclite.integrity.chain import ChainVerificationError


class GovSCLiteLifecycleVerifier(Protocol):
    """Port around SCLite lifecycle verification."""

    def verify(self, manifest: Mapping[str, Any], *, root: Path) -> dict[str, Any]:
        ...


def verify_lifecycle_manifest(manifest: Mapping[str, Any], *, root: Path) -> dict[str, Any]:
    """Verify a v0.2 SCLite lifecycle manifest through the GovEngine seam."""

    return verify_artifact_chain_manifest(manifest, root=root)


def descriptor_from_artifact(
    artifact: Mapping[str, Any],
    *,
    role: str = "",
    path: str = "",
) -> ArtifactDescriptor:
    """Build a GovEngine descriptor from SCLite's descriptor helper.

    SCLite still owns canonical JSON, hash algorithms, and descriptor shape.
    GovEngine only maps the resulting descriptor into its portable core type.
    """

    descriptor = artifact_descriptor(dict(artifact))
    metadata = {
        "schema_ref": str(descriptor.get("schema_ref") or ""),
        "canonicalization": str(descriptor.get("canonicalization") or ""),
        "algorithm": str(descriptor.get("algorithm") or ""),
        "canonical_bytes": descriptor.get("canonical_bytes", 0),
    }
    return ArtifactDescriptor(
        artifact_type=str(descriptor.get("artifact_type") or ""),
        schema_version=str(descriptor.get("schema_version") or ""),
        digest=str(descriptor.get("digest") or ""),
        role=role,
        path=path,
        metadata=metadata,
    )


def lifecycle_state_from_manifest(
    manifest: Mapping[str, Any],
    *,
    root: Path,
    path: str = "artifact_chain_manifest.json",
    validate_schemas: bool = True,
) -> ArtifactState:
    """Verify a SCLite chain manifest and map the result into `ArtifactState`.

    This is a status bridge, not a replacement for SCLite verification. All
    chain/hash/schema/lifecycle checks are delegated to SCLite.
    """

    descriptor = descriptor_from_artifact(manifest, role="artifact_chain_manifest", path=path)
    try:
        result = verify_artifact_chain_manifest(manifest, root=root, validate_schemas=validate_schemas)
    except ChainVerificationError as exc:
        return ArtifactState(
            descriptor=descriptor,
            lifecycle_state="blocked",
            chain_status="failed",
            signature_status=_signature_status(manifest),
            policy_status="unknown",
            blocked_reasons=(str(exc),),
            next_actions=("repair_artifact_chain", "rerun_sclite_lifecycle_verification"),
        )
    semantic_checks = result.get("semantic_checks") if isinstance(result.get("semantic_checks"), list) else []
    lifecycle_state = "verified_lifecycle" if semantic_checks else "verified_chain"
    return ArtifactState(
        descriptor=descriptor,
        lifecycle_state=lifecycle_state,
        chain_status=str(result.get("status") or "passed"),
        signature_status=_signature_status(manifest),
        policy_status="unknown",
        blocked_reasons=(),
        next_actions=(),
    )


def lifecycle_transition_decision(
    manifest: Mapping[str, Any],
    *,
    root: Path,
    from_state: str = "unverified",
    to_state: str = "verified_lifecycle",
    path: str = "artifact_chain_manifest.json",
    validate_schemas: bool = True,
) -> TransitionDecision:
    """Return a portable transition decision for SCLite lifecycle status."""

    state = lifecycle_state_from_manifest(
        manifest,
        root=root,
        path=path,
        validate_schemas=validate_schemas,
    )
    if state.blocked:
        return TransitionDecision(
            status="blocked",
            reason_code=ReasonCode.LIFECYCLE_BLOCKED.value,
            from_state=from_state,
            to_state=to_state,
            artifacts=(state.descriptor,),
            blockers=state.blocked_reasons,
            next_actions=state.next_actions,
        )
    return TransitionDecision(
        status="allowed",
        reason_code=ReasonCode.OK.value,
        from_state=from_state,
        to_state=to_state,
        artifacts=(state.descriptor,),
    )


def _signature_status(manifest: Mapping[str, Any]) -> str:
    signature_policy = manifest.get("signature_policy")
    if not isinstance(signature_policy, Mapping):
        return "not_required"
    mode = str(signature_policy.get("mode") or "").strip()
    if not mode:
        return "not_required"
    if mode in {"integrity_only", "not_signed_integrity_only"}:
        return mode
    return "requires_trust_decision"
