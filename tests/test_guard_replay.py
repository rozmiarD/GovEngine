from __future__ import annotations

import json
import sys
import types
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from govengine.api import GovApiError
from govengine.replay import (
    GuardReplayRecord,
    evaluate_guard_replay,
    guard_replay_record_from_guard,
    record_guard_replay,
    record_guard_replay_file,
    verify_guard_and_record_replay,
)


@dataclass
class MemoryStore:
    values: dict[str, dict[str, Any]] = field(default_factory=dict)

    def read_json(self, key: str) -> dict[str, Any]:
        return dict(self.values.get(key) or {"records": []})

    def write_json(self, key: str, value: dict[str, Any]) -> None:
        self.values[key] = dict(value)


def _guard(root_tag: str = "tag-1") -> dict[str, str]:
    return {
        "profile": "kernel_guard_hmac_v1",
        "root_tag": root_tag,
        "chain_id": "chain-1",
        "key_id": "key-20260525",
    }


def test_guard_replay_record_from_guard_captures_runtime_ids() -> None:
    record = guard_replay_record_from_guard(
        _guard(),
        ticket_id="ticket-1",
        run_id="run-1",
        observed_at="2026-05-25T21:00:00+00:00",
    )

    assert record.root_tag == "tag-1"
    assert record.chain_id == "chain-1"
    assert record.key_id == "key-20260525"
    assert record.ticket_id == "ticket-1"
    assert record.run_id == "run-1"
    assert record.guard_profile == "kernel_guard_hmac_v1"


def test_guard_replay_record_requires_core_guard_identifiers() -> None:
    with pytest.raises(GovApiError, match="missing_root_tag"):
        guard_replay_record_from_guard({"chain_id": "chain-1", "key_id": "key-1"})


def test_evaluate_guard_replay_allows_fresh_and_blocks_repeat() -> None:
    first = guard_replay_record_from_guard(_guard("tag-1"), observed_at="2026-05-25T21:00:00+00:00")
    second = guard_replay_record_from_guard(_guard("tag-1"), observed_at="2026-05-25T21:01:00+00:00")

    fresh = evaluate_guard_replay(first, ())
    replayed = evaluate_guard_replay(second, (first,))

    assert fresh.allowed is True
    assert fresh.replay_status == "fresh"
    assert replayed.allowed is False
    assert replayed.replay_status == "replayed"
    assert replayed.first_seen == first
    assert replayed.blocker.startswith("replayed_guard_root:")


def test_record_guard_replay_persists_only_fresh_records() -> None:
    store = MemoryStore()
    first = guard_replay_record_from_guard(_guard("tag-1"), observed_at="2026-05-25T21:00:00+00:00")
    replayed = guard_replay_record_from_guard(_guard("tag-1"), observed_at="2026-05-25T21:01:00+00:00")

    first_decision = record_guard_replay(store, first)
    replay_decision = record_guard_replay(store, replayed)

    assert first_decision.allowed is True
    assert replay_decision.allowed is False
    assert len(store.values["guard_replay_store"]["records"]) == 1


def test_record_guard_replay_can_run_in_observe_only_mode() -> None:
    first = guard_replay_record_from_guard(_guard("tag-1"), observed_at="2026-05-25T21:00:00+00:00")
    second = guard_replay_record_from_guard(_guard("tag-1"), observed_at="2026-05-25T21:01:00+00:00")

    decision = evaluate_guard_replay(second, (first,), require_fresh=False)

    assert decision.allowed is True
    assert decision.replay_status == "seen"


def test_record_guard_replay_file_round_trip(tmp_path) -> None:
    path = tmp_path / "guard_replay_store.json"
    first = guard_replay_record_from_guard(_guard("tag-1"), observed_at="2026-05-25T21:00:00+00:00")
    second = guard_replay_record_from_guard(_guard("tag-1"), observed_at="2026-05-25T21:01:00+00:00")

    assert record_guard_replay_file(path, first).allowed is True
    assert record_guard_replay_file(path, second).allowed is False
    assert "tag-1" in path.read_text(encoding="utf-8")


def _install_fake_sclite_secure(monkeypatch: pytest.MonkeyPatch) -> None:
    module = types.ModuleType("sclite.secure")

    def verify_secure_bundle(manifest_path, *, guard_path, key, root, validate_schemas, strict_jsonschema):
        return {
            "status": "passed",
            "secure_profile": "guarded-strict",
            "root_chain_digest": "root-digest-1",
            "guard_root_tag": json.loads(Path(guard_path).read_text(encoding="utf-8"))["root_tag"],
            "key_id": "key-20260525",
            "replay_status": "not_checked",
        }

    module.verify_secure_bundle = verify_secure_bundle
    monkeypatch.setitem(sys.modules, "sclite.secure", module)


def _write_guarded_bundle(tmp_path: Path, *, root_tag: str = "tag-1") -> tuple[Path, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    ticket_path = tmp_path / "execution_ticket.json"
    ticket_path.write_text(json.dumps({"ticket_id": "ticket-1"}) + "\n", encoding="utf-8")
    manifest_path = tmp_path / "artifact_chain_manifest.json"
    manifest_path.write_text(
        json.dumps({
            "chain_id": "chain-1",
            "entries": [{"role": "execution_ticket", "path": "execution_ticket.json"}],
        }) + "\n",
        encoding="utf-8",
    )
    guard_path = tmp_path / "kernel_guard_manifest.json"
    guard_path.write_text(
        json.dumps({
            "profile": "kernel_guard_hmac_v1",
            "root_tag": root_tag,
            "chain_id": "chain-1",
            "key_id": "key-20260525",
        }) + "\n",
        encoding="utf-8",
    )
    return manifest_path, guard_path


def test_verify_guard_and_record_replay_allows_first_use_and_blocks_second(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_sclite_secure(monkeypatch)
    manifest_path, guard_path = _write_guarded_bundle(tmp_path)
    store = MemoryStore()

    first = verify_guard_and_record_replay(manifest_path, guard_path=guard_path, key="secret", store=store)
    second = verify_guard_and_record_replay(manifest_path, guard_path=guard_path, key="secret", store=store)

    assert first.allowed is True
    assert first.verification_status == "passed"
    assert first.replay_status == "fresh"
    assert first.ticket_id == "ticket-1"
    assert second.allowed is False
    assert second.status == "blocked"
    assert second.replay_status == "replayed"
    assert second.blocker.startswith("replayed_guarded_payload:")


def test_verify_guard_and_record_replay_blocks_reguarded_same_payload(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_sclite_secure(monkeypatch)
    first_manifest, first_guard = _write_guarded_bundle(tmp_path / "first", root_tag="tag-1")
    second_manifest, second_guard = _write_guarded_bundle(tmp_path / "second", root_tag="tag-2")
    store = MemoryStore()

    first = verify_guard_and_record_replay(first_manifest, guard_path=first_guard, key="secret", store=store)
    second = verify_guard_and_record_replay(second_manifest, guard_path=second_guard, key="secret", store=store)

    assert first.allowed is True
    assert first.replay_status == "fresh"
    assert second.allowed is False
    assert second.replay_status == "replayed"
    assert second.guard_root_tag == "tag-2"
    assert second.blocker.startswith("replayed_guarded_payload:")


def test_verify_guard_and_record_replay_requires_strict_lifecycle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_sclite_secure(monkeypatch)
    manifest_path, guard_path = _write_guarded_bundle(tmp_path)

    decision = verify_guard_and_record_replay(
        manifest_path,
        guard_path=guard_path,
        key="secret",
        store=MemoryStore(),
        strict_lifecycle=False,
    )

    assert decision.allowed is False
    assert decision.blocker == "strict_lifecycle_required_for_runtime_consumable_guard"
