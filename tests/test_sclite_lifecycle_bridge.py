from __future__ import annotations

import json

from govengine.sclite_contracts import (
    descriptor_from_artifact,
    lifecycle_state_from_manifest,
    lifecycle_transition_decision,
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
