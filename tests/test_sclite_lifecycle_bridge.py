from __future__ import annotations

import json
import shutil
from importlib.resources import as_file, files

import pytest

from govengine.sclite_contracts import (
    descriptor_from_artifact,
    lifecycle_state_from_manifest,
    lifecycle_transition_decision,
    review_bundle_state,
    review_bundle_transition_decision,
    review_sclite_bundle,
    verify_lifecycle_manifest,
)
from sclite.integrity import ChainVerificationError, artifact_descriptor, build_artifact_chain_manifest


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


def test_lifecycle_state_from_manifest_blocks_generic_integrity_chain(tmp_path) -> None:
    artifact = {"artifact_type": "intent_contract", "schema_version": "v0.2", "intent_id": "i1"}
    _write_json(tmp_path / "intent_contract.json", artifact)
    manifest = build_artifact_chain_manifest([
        {"role": "intent_contract", "path": "intent_contract.json", "value": artifact},
    ], chain_id="fixture-chain", created_at="2026-05-09T00:00:00+00:00")

    state = lifecycle_state_from_manifest(manifest, root=tmp_path, validate_schemas=False)

    assert state.blocked is True
    assert state.lifecycle_state == "blocked"
    assert state.chain_status == "failed"
    assert "lifecycle roles mismatch" in state.blocked_reasons[0]
    assert state.descriptor.artifact_type == "artifact_chain_manifest"

    with pytest.raises(ChainVerificationError, match="lifecycle roles mismatch"):
        verify_lifecycle_manifest(manifest, root=tmp_path)


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


LIFECYCLE_FILES = (
    ("intent_contract", "intent_contract.json"),
    ("policy_decision", "policy_decision.json"),
    ("execution_contract", "execution_contract.json"),
    ("execution_ticket", "execution_ticket.json"),
    ("execution_receipt", "execution_receipt.json"),
    ("evidence_contract", "evidence_contract.json"),
)


def _copy_lifecycle_bundle(tmp_path) -> tuple[object, dict[str, dict]]:
    bundle = tmp_path / "bundle"
    with _sclite_example_dir("contract-lifecycle-v0.2") as source:
        shutil.copytree(source, bundle)
    artifacts = {
        role: json.loads((bundle / filename).read_text(encoding="utf-8"))
        for role, filename in LIFECYCLE_FILES
    }
    return bundle, artifacts


def _rebind_lifecycle_artifacts(artifacts: dict[str, dict]) -> None:
    intent = artifacts["intent_contract"]
    policy = artifacts["policy_decision"]
    contract = artifacts["execution_contract"]
    ticket = artifacts["execution_ticket"]
    receipt = artifacts["execution_receipt"]
    evidence = artifacts["evidence_contract"]
    intent_descriptor = artifact_descriptor(intent)
    policy["links"]["intent"]["descriptor"] = intent_descriptor
    policy_descriptor = artifact_descriptor(policy)
    contract["links"]["intent"]["descriptor"] = intent_descriptor
    contract["links"]["policy_decision"]["descriptor"] = policy_descriptor
    contract_descriptor = artifact_descriptor(contract)
    ticket["links"]["intent"]["descriptor"] = intent_descriptor
    ticket["links"]["policy_decision"]["descriptor"] = policy_descriptor
    ticket["links"]["execution_contract"]["descriptor"] = contract_descriptor
    ticket["integrity"]["ticket_binds_execution_contract_digest"] = contract_descriptor["digest"]
    ticket_descriptor = artifact_descriptor(ticket)
    receipt["links"]["execution_contract"]["descriptor"] = contract_descriptor
    receipt["links"]["execution_ticket"]["descriptor"] = ticket_descriptor
    receipt_descriptor = artifact_descriptor(receipt)
    evidence["links"]["execution_ticket"]["descriptor"] = ticket_descriptor
    evidence["links"]["execution_receipt"]["descriptor"] = receipt_descriptor


def _write_lifecycle_bundle(bundle, artifacts: dict[str, dict]) -> dict:
    for role, filename in LIFECYCLE_FILES:
        _write_json(bundle / filename, artifacts[role])
    manifest = build_artifact_chain_manifest(
        [
            {"role": role, "path": filename, "value": artifacts[role]}
            for role, filename in LIFECYCLE_FILES
        ],
        chain_id="govengine-lifecycle-bridge-test",
        created_at="2026-07-10T10:00:00+00:00",
    )
    _write_json(bundle / "artifact_chain_manifest.json", manifest)
    return manifest


def test_lifecycle_state_from_manifest_allows_complete_strict_lifecycle(tmp_path) -> None:
    bundle, artifacts = _copy_lifecycle_bundle(tmp_path)
    manifest = _write_lifecycle_bundle(bundle, artifacts)

    state = lifecycle_state_from_manifest(manifest, root=bundle)
    decision = lifecycle_transition_decision(manifest, root=bundle)

    assert state.blocked is False
    assert state.lifecycle_state == "verified_lifecycle"
    assert decision.allowed is True


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (
            lambda artifacts: artifacts["policy_decision"]["scope"].__setitem__("target_in_scope", False),
            "target_in_scope is explicitly false",
        ),
        (
            lambda artifacts: artifacts["execution_ticket"].__setitem__(
                "validity",
                {
                    "not_before": "1970-01-01T00:00:00+00:00",
                    "not_after": "1970-01-01T00:01:00+00:00",
                },
            ),
            "outside ticket validity window",
        ),
    ],
)
def test_lifecycle_transition_blocks_false_scope_and_expired_ticket(
    tmp_path,
    mutate,
    expected: str,
) -> None:
    bundle, artifacts = _copy_lifecycle_bundle(tmp_path)
    mutate(artifacts)
    _rebind_lifecycle_artifacts(artifacts)
    manifest = _write_lifecycle_bundle(bundle, artifacts)

    decision = lifecycle_transition_decision(manifest, root=bundle)

    assert decision.allowed is False
    assert decision.reason_code == "lifecycle_blocked"
    assert any(expected in blocker for blocker in decision.blockers)


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
