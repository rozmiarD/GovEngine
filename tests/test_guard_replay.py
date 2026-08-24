from __future__ import annotations

import json
import sys
import types
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from govengine import compose_runtime_admission_result
from govengine.api import GovApiError
from govengine.replay import (
    evaluate_guard_replay,
    GuardReplayRecord,
    guard_replay_record_from_guard,
    guard_replay_record_from_verification,
    InMemoryReplayClaimStore,
    ReplayClaimStore,
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


def _guard(
    root_tag: str = "tag-1",
    *,
    chain_id: str = "chain-1",
    key_id: str = "key-20260525",
) -> dict[str, str]:
    return {
        "profile": "kernel_guard_hmac_v1",
        "root_tag": root_tag,
        "chain_id": chain_id,
        "key_id": key_id,
    }


def _runtime_admission_inputs(**overrides):
    values = {
        "admission_id": "runtime-admission-guard-1",
        "subject_ref": "sha256:prepared-contract",
        "prepared_execution_contract": {
            "status": "prepared",
            "digest": "sha256:" + ("a" * 64),
        },
        "policy_decision": {"decision": "allow", "policy_id": "policy-1"},
        "execution_ticket": {
            "status": "passed",
            "ticket_id": "ticket-1",
            "digest": "sha256:" + ("b" * 64),
        },
        "trust_decision": {
            "status": "passed",
            "trust_status": "trusted",
            "verifier_id": "fixture",
        },
        "runner_profile": {"name": "dry-run", "allowed": True, "live_backend_enabled": False},
        "receipt_obligation": {"required": True, "binds": ["admission", "ticket"]},
    }
    values.update(overrides)
    return values


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
    assert record.schema_version == "v0.1"


def test_guard_replay_record_from_verified_sclite_handoff_needs_no_sidecar_payload() -> None:
    record = guard_replay_record_from_verification(
        {
            "guard_root_tag": "verified-root-tag",
            "chain_id": "verified-chain",
            "key_id": "key-20260710",
            "root_chain_digest": "verified-root-digest",
            "guard_profile": "kernel_guard_hmac_v1",
            "ticket_id": "verified-ticket",
        },
        run_id="run-1",
        observed_at="2026-07-10T10:00:00+00:00",
    )

    assert record.root_tag == "verified-root-tag"
    assert record.chain_id == "verified-chain"
    assert record.ticket_id == "verified-ticket"
    assert record.root_chain_digest == "verified-root-digest"


def test_guard_replay_record_accepts_legacy_mapping_without_schema_version() -> None:
    record = GuardReplayRecord.from_mapping({
        "root_tag": "tag-legacy",
        "chain_id": "chain-1",
        "key_id": "key-1",
    })

    assert record.schema_version == "v0.1"


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


def test_replay_claim_store_claim_once_records_fresh_record() -> None:
    store = InMemoryReplayClaimStore()
    record = guard_replay_record_from_guard(_guard("tag-1"), observed_at="2026-05-25T21:00:00+00:00")

    port: ReplayClaimStore = store
    decision = port.claim_once(record)

    assert decision.allowed is True
    assert decision.replay_status == "fresh"
    assert store.records == (record,)


def test_replay_claim_store_claim_once_blocks_replayed_record() -> None:
    store = InMemoryReplayClaimStore()
    first = guard_replay_record_from_guard(_guard("tag-1"), observed_at="2026-05-25T21:00:00+00:00")
    replayed = guard_replay_record_from_guard(_guard("tag-1"), observed_at="2026-05-25T21:01:00+00:00")

    first_decision = store.claim_once(first)
    replay_decision = store.claim_once(replayed)

    assert first_decision.replay_status == "fresh"
    assert replay_decision.allowed is False
    assert replay_decision.replay_status == "replayed"
    assert replay_decision.first_seen == first
    assert len(store.records) == 1


def test_replay_claim_store_observe_only_does_not_append_seen_record() -> None:
    first = guard_replay_record_from_guard(_guard("tag-1"), observed_at="2026-05-25T21:00:00+00:00")
    replayed = guard_replay_record_from_guard(_guard("tag-1"), observed_at="2026-05-25T21:01:00+00:00")
    store = InMemoryReplayClaimStore((first,))

    decision = store.claim_once(replayed, require_fresh=False)

    assert decision.allowed is True
    assert decision.replay_status == "seen"
    assert store.records == (first,)


def test_replay_claim_store_blocks_same_payload_claim_once() -> None:
    store = InMemoryReplayClaimStore()
    first = guard_replay_record_from_guard(
        _guard("tag-1"),
        ticket_id="ticket-1",
        observed_at="2026-05-25T21:00:00+00:00",
        metadata={"root_chain_digest": "sha256:payload"},
    )
    reguarded = guard_replay_record_from_guard(
        _guard("tag-2"),
        ticket_id="ticket-1",
        observed_at="2026-05-25T21:01:00+00:00",
        metadata={"root_chain_digest": "sha256:payload"},
    )

    first_decision = store.claim_once(first)
    replay_decision = store.claim_once(reguarded)

    assert first_decision.replay_status == "fresh"
    assert replay_decision.allowed is False
    assert replay_decision.replay_status == "replayed"
    assert replay_decision.blocker == "replayed_guarded_payload:sha256:payload"
    assert store.records == (first,)


def test_replay_claim_store_keeps_chain_and_key_namespaces_separate() -> None:
    store = InMemoryReplayClaimStore()
    first = guard_replay_record_from_guard(
        _guard("tag-1", chain_id="chain-1", key_id="key-a"),
        observed_at="2026-05-25T21:00:00+00:00",
    )
    different_chain = guard_replay_record_from_guard(
        _guard("tag-1", chain_id="chain-2", key_id="key-a"),
        observed_at="2026-05-25T21:01:00+00:00",
    )
    different_key = guard_replay_record_from_guard(
        _guard("tag-1", chain_id="chain-1", key_id="key-b"),
        observed_at="2026-05-25T21:02:00+00:00",
    )

    assert store.claim_once(first).replay_status == "fresh"
    assert store.claim_once(different_chain).replay_status == "fresh"
    assert store.claim_once(different_key).replay_status == "fresh"
    assert store.records == (first, different_chain, different_key)


def test_replay_claim_store_reports_invalid_mapping() -> None:
    store = InMemoryReplayClaimStore()

    with pytest.raises(GovApiError, match="missing_root_tag"):
        store.claim_once({"chain_id": "chain-1", "key_id": "key-1"})

    assert store.records == ()


def test_record_guard_replay_file_round_trip(tmp_path) -> None:
    path = tmp_path / "guard_replay_store.json"
    first = guard_replay_record_from_guard(_guard("tag-1"), observed_at="2026-05-25T21:00:00+00:00")
    second = guard_replay_record_from_guard(_guard("tag-1"), observed_at="2026-05-25T21:01:00+00:00")

    assert record_guard_replay_file(path, first).allowed is True
    assert record_guard_replay_file(path, second).allowed is False
    assert "tag-1" in path.read_text(encoding="utf-8")


def test_record_guard_replay_file_blocks_corrupt_store_without_overwriting_bytes(tmp_path: Path) -> None:
    path = tmp_path / "guard_replay_store.json"
    fresh = guard_replay_record_from_guard(_guard("tag-1"), observed_at="2026-05-25T21:00:00+00:00")
    replayed = guard_replay_record_from_guard(_guard("tag-1"), observed_at="2026-05-25T21:01:00+00:00")
    after_corruption = guard_replay_record_from_guard(
        _guard("tag-2"), observed_at="2026-05-25T21:02:00+00:00"
    )

    assert record_guard_replay_file(path, fresh).replay_status == "fresh"
    assert record_guard_replay_file(path, replayed).replay_status == "replayed"

    corrupt_bytes = b'{"records": '
    path.write_bytes(corrupt_bytes)
    blocked = record_guard_replay_file(path, after_corruption)

    assert blocked.status == "blocked"
    assert blocked.allowed is False
    assert blocked.replay_status == "blocked"
    assert blocked.blocker == "guard_replay_store_invalid_json"
    assert blocked.next_action == "repair_or_replace_local_guard_replay_store"
    assert path.read_bytes() == corrupt_bytes


@pytest.mark.parametrize(
    ("corrupt_bytes", "expected_blocker"),
    (
        (b'{"records": ', "guard_replay_store_invalid_json"),
        (b'{"artifact_type": "guard_replay_store", "schema_version": "v0.1", "records": {}}', "guard_replay_store_invalid_shape"),
    ),
)
def test_record_guard_replay_file_returns_typed_blocker_for_invalid_store_shape(
    tmp_path: Path,
    corrupt_bytes: bytes,
    expected_blocker: str,
) -> None:
    path = tmp_path / "guard_replay_store.json"
    record = guard_replay_record_from_guard(_guard(), observed_at="2026-05-25T21:00:00+00:00")
    path.write_bytes(corrupt_bytes)

    blocked = record_guard_replay_file(path, record)

    assert blocked.status == "blocked"
    assert blocked.replay_status == "blocked"
    assert blocked.blocker == expected_blocker
    assert path.read_bytes() == corrupt_bytes


def _install_fake_sclite_secure(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    module = types.ModuleType("sclite.secure")
    calls: list[dict[str, Any]] = []

    def verify_secure_bundle(manifest_path, *, guard_path, key, root, validate_schemas, strict_jsonschema):
        calls.append({
            "manifest_path": manifest_path,
            "guard_path": guard_path,
            "key": key,
            "root": root,
            "validate_schemas": validate_schemas,
            "strict_jsonschema": strict_jsonschema,
        })
        return {
            "status": "passed",
            "secure_profile": "guarded-strict",
            "root_chain_digest": "sha256:" + ("d" * 64),
            "guard_root_tag": json.loads(Path(guard_path).read_text(encoding="utf-8"))["root_tag"],
            "chain_id": "chain-1",
            "key_id": "key-20260525",
            "ticket_id": "ticket-1",
            "replay_status": "not_checked",
        }

    module.verify_secure_bundle = verify_secure_bundle
    monkeypatch.setitem(sys.modules, "sclite.secure", module)
    return calls


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
    calls = _install_fake_sclite_secure(monkeypatch)
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
    assert len(calls) == 2
    assert calls[0]["manifest_path"] == manifest_path.resolve()
    assert calls[0]["guard_path"] == guard_path.resolve()
    assert calls[0]["root"] == tmp_path.resolve()
    assert calls[0]["validate_schemas"] is True


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


def test_verify_guard_and_record_replay_does_not_reread_verified_bundle_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = types.ModuleType("sclite.secure")

    def verify_secure_bundle(*_args, **_kwargs):
        return {
            "status": "passed",
            "secure_profile": "guarded-strict",
            "root_chain_digest": "verified-root-digest",
            "guard_root_tag": "verified-root-tag",
            "chain_id": "verified-chain",
            "key_id": "verified-key",
            "ticket_id": "verified-ticket",
            "replay_status": "not_checked",
        }

    module.verify_secure_bundle = verify_secure_bundle
    monkeypatch.setitem(sys.modules, "sclite.secure", module)
    manifest_path, guard_path = _write_guarded_bundle(tmp_path)
    selected = {manifest_path.resolve(), guard_path.resolve(), (tmp_path / "execution_ticket.json").resolve()}
    original_read_text = Path.read_text

    def fail_if_govengine_rereads(path: Path, *args, **kwargs):
        if path.resolve() in selected:
            raise AssertionError(f"GovEngine reread verified bundle file: {path}")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fail_if_govengine_rereads)
    decision = verify_guard_and_record_replay(
        manifest_path,
        guard_path=guard_path,
        key="secret",
        store=MemoryStore(),
    )

    assert decision.allowed is True
    assert decision.chain_id == "verified-chain"
    assert decision.ticket_id == "verified-ticket"


def test_guarded_fresh_runtime_admission_example_composes_allowed_dry_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_sclite_secure(monkeypatch)
    manifest_path, guard_path = _write_guarded_bundle(tmp_path)
    guarded = verify_guard_and_record_replay(
        manifest_path,
        guard_path=guard_path,
        key="fixture-secret",
        store=MemoryStore(),
        observed_at="2026-06-06T20:00:00+00:00",
        run_id="dry-run-1",
    )

    admission = compose_runtime_admission_result(**_runtime_admission_inputs(
        admission_id="runtime-admission-guarded-fresh-example",
        runtime_consumable=True,
        sclite_guarded_strict=guarded.as_dict(),
        replay_freshness=guarded.as_dict(),
        runner_profile={"name": "dry-run", "allowed": True, "live_backend_enabled": False},
        receipt_obligation={"required": True, "binds": ["admission", "ticket"]},
        artifact_refs={
            "sclite_guarded_strict": {
                "guard_root_tag": guarded.guard_root_tag,
                "root_chain_digest": guarded.root_chain_digest,
            },
            "execution_ticket": {
                "ticket_id": guarded.ticket_id,
                "ticket_digest": "sha256:" + ("c" * 64),
            },
        },
    ))

    assert guarded.allowed is True
    assert guarded.verification_status == "passed"
    assert guarded.replay_status == "fresh"
    assert admission.allowed is True
    assert admission.status == "allowed"
    assert admission.reason_code == "all_required_gates_passed"
    assert admission.sclite_guarded_strict["verification_status"] == "passed"
    assert admission.replay_freshness["replay_status"] == "fresh"
    assert admission.runner_profile == {
        "allowed": True,
        "live_backend_enabled": False,
        "metadata": {},
        "name": "dry-run",
    }
    assert admission.receipt_obligation == {"binds": ["admission", "ticket"], "required": True}
    assert admission.sclite_guarded_strict["guard_root_tag"] == "tag-1"
    assert admission.artifact_refs["sclite_guarded_strict"]["root_chain_digest"] == guarded.root_chain_digest
    assert admission.artifact_refs["execution_ticket"]["ticket_id"] == "ticket-1"
    assert admission.artifact_refs["execution_ticket"]["digest"] == "sha256:" + ("b" * 64)


@pytest.mark.parametrize(
    "guarded_decision",
    (
        None,
        {"status": "passed", "verification_status": "passed", "guarded": False},
        {"status": "passed", "verification_status": "passed", "strict": False},
        {"status": "blocked", "verification_status": "failed"},
    ),
)
def test_runtime_admission_blocks_missing_or_non_strict_guarded_bundle(
    guarded_decision,
) -> None:
    result = compose_runtime_admission_result(**_runtime_admission_inputs(
        runtime_consumable=True,
        sclite_guarded_strict=guarded_decision,
        replay_freshness={"status": "allowed", "replay_status": "fresh"},
    ))

    assert result.allowed is False
    assert result.reason_code == "kernel_guard_required"
    assert "missing_or_invalid_kernel_guard" in result.blockers


@pytest.mark.parametrize("replay_status", ("replayed", "stale", "expired"))
def test_runtime_admission_blocks_replayed_or_stale_guarded_bundle(
    replay_status: str,
) -> None:
    result = compose_runtime_admission_result(**_runtime_admission_inputs(
        runtime_consumable=True,
        sclite_guarded_strict={"status": "allowed", "verification_status": "passed"},
        replay_freshness={"status": "blocked", "replay_status": replay_status},
    ))

    assert result.allowed is False
    assert result.reason_code == "replay_detected"
    assert "missing_or_replayed_guarded_root" in result.blockers


def test_runtime_admission_keeps_review_only_bundle_posture_distinct() -> None:
    result = compose_runtime_admission_result(**_runtime_admission_inputs(
        runtime_consumable=False,
        sclite_guarded_strict={"status": "blocked", "verification_status": "failed"},
        replay_freshness={"status": "blocked", "replay_status": "stale"},
    ))

    assert result.allowed is True
    assert result.status == "allowed"
    assert result.reason_code == "all_required_gates_passed"


def test_runtime_admission_blocks_decoupled_replay_freshness_override() -> None:
    result = compose_runtime_admission_result(**_runtime_admission_inputs(
        runtime_consumable=True,
        sclite_guarded_strict={
            "status": "blocked",
            "verification_status": "passed",
            "replay_status": "replayed",
        },
        replay_freshness={"status": "allowed", "replay_status": "fresh"},
    ))

    assert result.allowed is False
    assert "missing_or_replayed_guarded_root" in result.blockers


def test_runtime_admission_blocks_guarded_blocked_decision_with_passed_verification() -> None:
    result = compose_runtime_admission_result(**_runtime_admission_inputs(
        runtime_consumable=True,
        sclite_guarded_strict={"status": "blocked", "verification_status": "passed"},
        replay_freshness={"replay_status": "fresh"},
    ))

    assert result.allowed is False
    assert "missing_or_invalid_kernel_guard" in result.blockers


def test_runtime_admission_blocks_replay_freshness_without_guarded_replay_signal() -> None:
    result = compose_runtime_admission_result(**_runtime_admission_inputs(
        runtime_consumable=True,
        sclite_guarded_strict={"verification_status": "passed"},
        replay_freshness={"replay_status": "fresh"},
    ))

    assert result.allowed is False
    assert "missing_or_replayed_guarded_root" in result.blockers
