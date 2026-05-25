from __future__ import annotations

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
        "guard_profile": raw.get("profile") or "kernel_guard_hmac_v1",
        "ticket_id": ticket_id,
        "run_id": run_id,
        "observed_at": observed_at or _utc_now(),
        "metadata": dict(metadata or {}),
    })


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
    """Evaluate whether a guarded root tag has already been observed."""

    for prior in prior_records:
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
