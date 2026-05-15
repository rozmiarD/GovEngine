from __future__ import annotations

import json
from importlib.resources import as_file, files

from govengine.sclite_contracts import (
    descriptor_from_artifact,
    lifecycle_state_from_manifest,
    lifecycle_transition_decision,
    review_bundle_state,
    review_bundle_transition_decision,
    review_sclite_bundle,
)
from sclite.integrity import build_artifact_chain_manifest


def _write_json(path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True))


def test_descriptor_from_artifact_uses_sclite_descriptor_boundary() -> None:
    artifact = {"artifact_type": "intent_contract", "schema_version": "v0.2", "intent_id": "i1"}
    descriptor = descriptor_from_artifact(artifact, role="intent_contract", path="intent_contract.json")

    assert descriptor.artifact_type == "intent_contract"
    assert descriptor.schema_version == "v0.2"
    assert descriptor.digest
    assert descriptor.role == "intent_contract"
    assert descriptor.path == "intent_contract.json"
    assert descriptor.metadata["algorithm"] == "sha256"


def test_lifecycle_state_from_manifest_maps_verified_chain(tmp_path) -> None:
    artifact = {"artifact_type": "intent_contract", "schema_version": "v0.2", "intent_id": "i1"}
    _write_json(tmp_path / "intent_contract.json", artifact)
    manifest = build_artifact_chain_manifest([
        {"role": "intent_contract", "path": "intent_contract.json", "value": artifact},
    ], chain_id="fixture-chain", created_at="2026-05-09T00:00:00+00:00")

    state = lifecycle_state_from_manifest(manifest, root=tmp_path, validate_schemas=False)

    assert state.blocked is False
    assert state.lifecycle_state == "verified_chain"
    assert state.chain_status == "passed"
    assert state.descriptor.artifact_type == "artifact_chain_manifest"


def test_lifecycle_transition_decision_blocks_invalid_chain(tmp_path) -> None:
    artifact = {"artifact_type": "intent_contract", "schema_version": "v0.2", "intent_id": "i1"}
    _write_json(tmp_path / "intent_contract.json", artifact)
    manifest = build_artifact_chain_manifest([
        {"role": "intent_contract", "path": "intent_contract.json", "value": artifact},
    ], chain_id="fixture-chain", created_at="2026-05-09T00:00:00+00:00")
    _write_json(tmp_path / "intent_contract.json", {**artifact, "intent_id": "changed"})

    decision = lifecycle_transition_decision(manifest, root=tmp_path, validate_schemas=False)

    assert decision.allowed is False
    assert decision.reason_code == "lifecycle_blocked"
    assert decision.blockers
    assert "repair_artifact_chain" in decision.next_actions


def _sclite_example_dir(name: str):
    return as_file(files("sclite.examples").joinpath(name))


def test_review_sclite_bundle_delegates_govengine_integration_bundle_to_sclite() -> None:
    with _sclite_example_dir("govengine-integration") as bundle_dir:
        record = review_sclite_bundle(bundle_dir)
        state = review_bundle_state(bundle_dir)
        decision = review_bundle_transition_decision(bundle_dir)

    assert record["artifact_type"] == "review_record"
    assert record["schema_version"] == "v0.1"
    assert record["verdict"] == "pass"
    assert state.blocked is False
    assert state.lifecycle_state == "review_bundle_passed"
    assert state.descriptor.artifact_type == "review_record"
    assert decision.allowed is True
    assert decision.reason_code == "ok"


def test_review_bundle_transition_blocks_cross_host_bundle() -> None:
    with _sclite_example_dir("bad-review-bundle-cross-host") as bundle_dir:
        state = review_bundle_state(bundle_dir)
        decision = review_bundle_transition_decision(bundle_dir)

    assert state.blocked is True
    assert state.lifecycle_state == "blocked"
    assert state.blocked_reasons
    assert "review_sclite_bundle" in state.next_actions
    assert decision.allowed is False
    assert decision.reason_code == "lifecycle_blocked"
    assert decision.blockers
