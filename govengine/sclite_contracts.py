from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Protocol

from govengine.core import ArtifactDescriptor, ArtifactState, ReasonCode, TransitionDecision
from sclite.bundles import ReviewBundleError, review_bundle
from sclite.integrity import artifact_descriptor, verify_artifact_chain_manifest
from sclite.integrity.chain import ChainVerificationError


class GovSCLiteLifecycleVerifier(Protocol):
    """Port around SCLite lifecycle verification."""

    def verify(self, manifest: Mapping[str, Any], *, root: Path) -> dict[str, Any]:
        ...


def verify_lifecycle_manifest(manifest: Mapping[str, Any], *, root: Path) -> dict[str, Any]:
    """Verify a v0.2 SCLite lifecycle manifest through the GovEngine seam."""

    return verify_artifact_chain_manifest(manifest, root=root)


def review_sclite_bundle(
    bundle_dir: Path | str,
    *,
    strict_jsonschema: bool = False,
) -> dict[str, Any]:
    """Review a SCLite review bundle through the GovEngine seam.

    SCLite owns canonical review-bundle shape, review-record semantics, chain
    verification, Scope Fidelity, and verdict calculation. GovEngine only calls
    the published SCLite review surface so host runtimes can consume the result
    through a neutral GovEngine boundary.
    """

    return review_bundle(bundle_dir, strict_jsonschema=strict_jsonschema)


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


def review_bundle_state(
    bundle_dir: Path | str,
    *,
    strict_jsonschema: bool = False,
    path: str = "verification_receipt.json",
) -> ArtifactState:
    """Map a SCLite review-bundle verdict into portable GovEngine state.

    This bridge deliberately does not reimplement SCLite validation. SCLite
    returns the review record; GovEngine maps the verdict into its own state
    vocabulary so a host can gate transitions without owning review semantics.
    """

    try:
        record = review_sclite_bundle(bundle_dir, strict_jsonschema=strict_jsonschema)
    except ReviewBundleError as exc:
        descriptor = ArtifactDescriptor(
            artifact_type="review_record",
            schema_version="v0.1",
            digest="",
            role="review_record",
            path=path,
            metadata={"review_bundle_error": str(exc)},
        )
        return ArtifactState(
            descriptor=descriptor,
            lifecycle_state="blocked",
            chain_status="failed",
            signature_status="not_required",
            policy_status="unknown",
            blocked_reasons=(str(exc),),
            next_actions=("repair_sclite_review_bundle", "rerun_sclite_review"),
        )

    descriptor = descriptor_from_artifact(record, role="review_record", path=path)
    verdict = str(record.get("verdict") or "review")
    if verdict == "pass":
        return ArtifactState(
            descriptor=descriptor,
            lifecycle_state="review_bundle_passed",
            chain_status="passed",
            signature_status="not_required",
            policy_status="unknown",
            blocked_reasons=(),
            next_actions=(),
        )

    return ArtifactState(
        descriptor=descriptor,
        lifecycle_state="blocked" if verdict == "fail" else "review_required",
        chain_status="failed" if verdict == "fail" else "review",
        signature_status="not_required",
        policy_status="unknown",
        blocked_reasons=tuple(_review_record_blockers(record)) or (f"sclite_review_verdict:{verdict}",),
        next_actions=("review_sclite_bundle", "repair_or_accept_bundle_by_policy"),
    )


def review_bundle_transition_decision(
    bundle_dir: Path | str,
    *,
    from_state: str = "unreviewed",
    to_state: str = "review_bundle_passed",
    strict_jsonschema: bool = False,
    path: str = "verification_receipt.json",
) -> TransitionDecision:
    """Return a transition decision based on SCLite review-bundle state."""

    state = review_bundle_state(bundle_dir, strict_jsonschema=strict_jsonschema, path=path)
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


def _review_record_blockers(record: Mapping[str, Any]) -> list[str]:
    checks = record.get("checks")
    if not isinstance(checks, list):
        return []
    blockers: list[str] = []
    for check in checks:
        if not isinstance(check, Mapping):
            continue
        status = str(check.get("status") or "")
        if status in {"review", "fail"}:
            name = str(check.get("name") or "check")
            detail = str(check.get("detail") or status)
            blockers.append(f"{name}:{status}:{detail}")
    return blockers


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
