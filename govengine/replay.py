from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from govengine.api import GovApiError, require_mapping
from govengine.state_store import GovStateStore, atomic_write_json, safe_load_json_object

GUARD_REPLAY_STORE_ARTIFACT_TYPE = "guard_replay_store"
GUARD_REPLAY_STORE_SCHEMA_VERSION = "v0.1"
DEFAULT_GUARD_REPLAY_STORE_KEY = "guard_replay_store"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class GuardReplayRecord:
    """One observed SCLite Kernel Guard root.

    GovEngine records replay state for guarded SCLite bundles. SCLite verifies
    the guard; GovEngine decides whether the guarded root is fresh for a host
    domain. This is not key storage and does not verify HMAC tags.
    """

    root_tag: str
    chain_id: str
    key_id: str
    root_chain_digest: str = ""
    ticket_id: str = ""
    run_id: str = ""
    guard_profile: str = "kernel_guard_hmac_v1"
    observed_at: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "GuardReplayRecord":
        raw = require_mapping(value, reason_code="invalid_guard_replay_record")
        root_tag = str(raw.get("root_tag") or "").strip()
        chain_id = str(raw.get("chain_id") or "").strip()
        key_id = str(raw.get("key_id") or "").strip()
        if not root_tag:
            raise GovApiError("missing_root_tag")
        if not chain_id:
            raise GovApiError("missing_chain_id")
        if not key_id:
            raise GovApiError("missing_key_id")
        metadata = raw.get("metadata") if isinstance(raw.get("metadata"), Mapping) else {}
        return cls(
            root_tag=root_tag,
            chain_id=chain_id,
            key_id=key_id,
            root_chain_digest=str(raw.get("root_chain_digest") or ""),
            ticket_id=str(raw.get("ticket_id") or ""),
            run_id=str(raw.get("run_id") or ""),
            guard_profile=str(raw.get("guard_profile") or raw.get("profile") or "kernel_guard_hmac_v1"),
            observed_at=str(raw.get("observed_at") or ""),
            metadata=dict(metadata),
        )

    def as_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["metadata"] = dict(self.metadata)
        return out


@dataclass(frozen=True)
class GuardReplayDecision:
    """Fresh/replayed decision for a guarded SCLite root."""

    status: str
    replay_status: str
    record: GuardReplayRecord
    first_seen: GuardReplayRecord | None = None
    blocker: str = ""
    next_action: str = ""

    @property
    def allowed(self) -> bool:
        return self.status == "allowed" and self.replay_status in {"fresh", "seen"}

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "allowed": self.allowed,
            "replay_status": self.replay_status,
            "record": self.record.as_dict(),
            "first_seen": self.first_seen.as_dict() if self.first_seen else None,
            "blocker": self.blocker,
            "next_action": self.next_action,
        }


@dataclass(frozen=True)
class GuardedBundleRuntimeDecision:
    """Combined guarded verification plus replay-freshness runtime decision."""

    status: str
    verification_status: str
    replay_status: str
    root_chain_digest: str = ""
    guard_root_tag: str = ""
    chain_id: str = ""
    key_id: str = ""
    ticket_id: str = ""
    run_id: str = ""
    blocker: str = ""
    next_action: str = ""
    verification: Mapping[str, Any] = field(default_factory=dict)
    replay_decision: GuardReplayDecision | None = None

    @property
    def allowed(self) -> bool:
        return self.status == "allowed" and self.verification_status == "passed" and self.replay_status == "fresh"

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "allowed": self.allowed,
            "verification_status": self.verification_status,
            "replay_status": self.replay_status,
            "root_chain_digest": self.root_chain_digest,
            "guard_root_tag": self.guard_root_tag,
            "chain_id": self.chain_id,
            "key_id": self.key_id,
            "ticket_id": self.ticket_id,
            "run_id": self.run_id,
            "blocker": self.blocker,
            "next_action": self.next_action,
            "verification": dict(self.verification),
            "replay_decision": self.replay_decision.as_dict() if self.replay_decision else None,
        }


def guard_replay_record_from_guard(
    guard: Mapping[str, Any],
    *,
    ticket_id: str = "",
    run_id: str = "",
    observed_at: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> GuardReplayRecord:
    """Create a replay-store record from a SCLite kernel guard sidecar."""

    raw = require_mapping(guard, reason_code="invalid_kernel_guard")
    return GuardReplayRecord.from_mapping({
        "root_tag": raw.get("root_tag"),
        "chain_id": raw.get("chain_id"),
        "key_id": raw.get("key_id"),
        "root_chain_digest": raw.get("root_chain_digest") or (metadata or {}).get("root_chain_digest") or "",
        "guard_profile": raw.get("profile") or "kernel_guard_hmac_v1",
        "ticket_id": ticket_id,
        "run_id": run_id,
        "observed_at": observed_at or _utc_now(),
        "metadata": dict(metadata or {}),
    })


def _load_json_object(path: Path, *, label: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise GovApiError(f"invalid_{label}_json_root")
    return value


def _ticket_id_from_manifest(manifest_path: Path, manifest: Mapping[str, Any]) -> str:
    base = manifest_path.parent
    entries = manifest.get("entries")
    if not isinstance(entries, list):
        return ""
    for entry in entries:
        if not isinstance(entry, Mapping) or entry.get("role") != "execution_ticket":
            continue
        rel_path = str(entry.get("path") or "")
        if not rel_path:
            return ""
        ticket_path = (base / rel_path).resolve()
        try:
            ticket_path.relative_to(base.resolve())
        except ValueError:
            return ""
        try:
            ticket = _load_json_object(ticket_path, label="execution_ticket")
        except Exception:
            return ""
        return str(ticket.get("ticket_id") or "")
    return ""


def verify_guard_and_record_replay(
    manifest_path: Path | str,
    *,
    guard_path: Path | str,
    key: str | bytes,
    store: GovStateStore,
    require_fresh: bool = True,
    strict_lifecycle: bool = True,
    strict_jsonschema: bool = False,
    ticket_id: str = "",
    run_id: str = "",
    observed_at: str | None = None,
    replay_store_key: str = DEFAULT_GUARD_REPLAY_STORE_KEY,
    metadata: Mapping[str, Any] | None = None,
) -> GuardedBundleRuntimeDecision:
    """Verify a guarded SCLite bundle and record replay freshness.

    Runtime-consumable bundles must use the fail-closed SCLite secure profile:
    strict lifecycle, artifact-chain verification, and kernel_guard_hmac_v1.
    GovEngine records freshness; SCLite verifies the guard. This function does
    not own keys, perform PKI, or store raw artifacts.
    """

    if not strict_lifecycle:
        return GuardedBundleRuntimeDecision(
            status="blocked",
            verification_status="failed",
            replay_status="not_checked",
            blocker="strict_lifecycle_required_for_runtime_consumable_guard",
            next_action="rerun_with_strict_lifecycle",
        )

    manifest = Path(manifest_path).resolve()
    guard = Path(guard_path).resolve()
    try:
        from sclite.secure import verify_secure_bundle
    except Exception as exc:  # pragma: no cover - depends on installed SCLite line
        return GuardedBundleRuntimeDecision(
            status="blocked",
            verification_status="failed",
            replay_status="not_checked",
            blocker="sclite_secure_profile_unavailable",
            next_action="install_sclite_with_kernel_guard_secure_profile",
            verification={"error": str(exc)},
        )

    try:
        verification = verify_secure_bundle(
            manifest,
            guard_path=guard,
            key=key,
            root=manifest.parent,
            validate_schemas=True,
            strict_jsonschema=strict_jsonschema,
        )
        guard_payload = _load_json_object(guard, label="kernel_guard")
        manifest_payload = _load_json_object(manifest, label="artifact_chain_manifest")
    except Exception as exc:
        return GuardedBundleRuntimeDecision(
            status="blocked",
            verification_status="failed",
            replay_status="not_checked",
            blocker=f"guard_verification_failed:{exc}",
            next_action="reject_or_review_unguarded_bundle",
        )

    resolved_ticket_id = ticket_id or _ticket_id_from_manifest(manifest, manifest_payload)
    record = guard_replay_record_from_guard(
        guard_payload,
        ticket_id=resolved_ticket_id,
        run_id=run_id,
        observed_at=observed_at,
        metadata={
            "root_chain_digest": verification.get("root_chain_digest", ""),
            "secure_profile": verification.get("secure_profile", ""),
            **dict(metadata or {}),
        },
    )
    replay = record_guard_replay(
        store,
        record,
        key=replay_store_key,
        require_fresh=require_fresh,
    )
    if not replay.allowed or replay.replay_status != "fresh":
        return GuardedBundleRuntimeDecision(
            status="blocked",
            verification_status="passed",
            replay_status=replay.replay_status,
            root_chain_digest=str(verification.get("root_chain_digest") or ""),
            guard_root_tag=record.root_tag,
            chain_id=record.chain_id,
            key_id=record.key_id,
            ticket_id=record.ticket_id,
            run_id=record.run_id,
            blocker=replay.blocker or "guarded_root_not_fresh",
            next_action=replay.next_action or "reject_or_review_replayed_guarded_bundle",
            verification=verification,
            replay_decision=replay,
        )
    return GuardedBundleRuntimeDecision(
        status="allowed",
        verification_status="passed",
        replay_status="fresh",
        root_chain_digest=str(verification.get("root_chain_digest") or ""),
        guard_root_tag=record.root_tag,
        chain_id=record.chain_id,
        key_id=record.key_id,
        ticket_id=record.ticket_id,
        run_id=record.run_id,
        verification=verification,
        replay_decision=replay,
    )


def _empty_store() -> dict[str, Any]:
    return {
        "artifact_type": GUARD_REPLAY_STORE_ARTIFACT_TYPE,
        "schema_version": GUARD_REPLAY_STORE_SCHEMA_VERSION,
        "records": [],
    }


def _records_from_store(value: Mapping[str, Any]) -> list[GuardReplayRecord]:
    records = value.get("records")
    if not isinstance(records, list):
        return []
    result: list[GuardReplayRecord] = []
    for item in records:
        if isinstance(item, Mapping):
            result.append(GuardReplayRecord.from_mapping(item))
    return result


def _store_from_records(records: Iterable[GuardReplayRecord]) -> dict[str, Any]:
    return {
        "artifact_type": GUARD_REPLAY_STORE_ARTIFACT_TYPE,
        "schema_version": GUARD_REPLAY_STORE_SCHEMA_VERSION,
        "records": [record.as_dict() for record in records],
    }


def evaluate_guard_replay(
    record: GuardReplayRecord,
    prior_records: Iterable[GuardReplayRecord],
    *,
    require_fresh: bool = True,
) -> GuardReplayDecision:
    """Evaluate whether a guarded bundle has already been observed.

    `root_tag` alone is not enough freshness for runtime use: the same
    artifact-chain payload can be re-guarded with new nonces, producing a new
    root tag. When available, GovEngine therefore keys replay on the semantic
    payload binding `(root_chain_digest, ticket_id|chain_id, key_id)` and keeps
    root-tag matching as a compatibility fallback for older records.
    """

    for prior in prior_records:
        semantic_scope = record.ticket_id or record.chain_id
        prior_semantic_scope = prior.ticket_id or prior.chain_id
        semantic_replay = (
            bool(record.root_chain_digest)
            and bool(prior.root_chain_digest)
            and record.root_chain_digest == prior.root_chain_digest
            and semantic_scope == prior_semantic_scope
            and record.key_id == prior.key_id
        )
        if semantic_replay:
            if require_fresh:
                return GuardReplayDecision(
                    status="blocked",
                    replay_status="replayed",
                    record=record,
                    first_seen=prior,
                    blocker=f"replayed_guarded_payload:{record.root_chain_digest}",
                    next_action="reject_or_review_replayed_guarded_bundle",
                )
            return GuardReplayDecision(
                status="allowed",
                replay_status="seen",
                record=record,
                first_seen=prior,
            )
        if prior.root_tag == record.root_tag:
            if require_fresh:
                return GuardReplayDecision(
                    status="blocked",
                    replay_status="replayed",
                    record=record,
                    first_seen=prior,
                    blocker=f"replayed_guard_root:{record.root_tag}",
                    next_action="reject_or_review_replayed_guarded_bundle",
                )
            return GuardReplayDecision(
                status="allowed",
                replay_status="seen",
                record=record,
                first_seen=prior,
            )
    return GuardReplayDecision(status="allowed", replay_status="fresh", record=record)


def record_guard_replay(
    store: GovStateStore,
    record: GuardReplayRecord,
    *,
    key: str = DEFAULT_GUARD_REPLAY_STORE_KEY,
    require_fresh: bool = True,
) -> GuardReplayDecision:
    """Check and persist a guarded root through a host-supplied state store."""

    current = store.read_json(key)
    records = _records_from_store(current if isinstance(current, Mapping) else {})
    decision = evaluate_guard_replay(record, records, require_fresh=require_fresh)
    if decision.replay_status == "fresh":
        store.write_json(key, _store_from_records((*records, record)))
    return decision


def record_guard_replay_file(
    path: Path | str,
    record: GuardReplayRecord,
    *,
    require_fresh: bool = True,
) -> GuardReplayDecision:
    """Check and persist a guarded root in a local JSON replay-store file."""

    store_path = Path(path)
    current, _meta = safe_load_json_object(store_path, _empty_store(), description="guard_replay_store")
    records = _records_from_store(current)
    decision = evaluate_guard_replay(record, records, require_fresh=require_fresh)
    if decision.replay_status == "fresh":
        atomic_write_json(store_path, _store_from_records((*records, record)), sort_keys=True)
    return decision
