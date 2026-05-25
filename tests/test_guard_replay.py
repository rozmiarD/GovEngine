from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from govengine.api import GovApiError
from govengine.replay import (
    GuardReplayRecord,
    evaluate_guard_replay,
    guard_replay_record_from_guard,
    record_guard_replay,
    record_guard_replay_file,
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
