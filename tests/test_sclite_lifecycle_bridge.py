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
from govengine.sclite_adapter import build_current_lifecycle_artifacts
from govengine.execution.ticket_gate import validate_scoped_ticket_use_gate
from sclite.bundles import REVIEW_BUNDLE_REQUIRED_FILES, materialize_review_bundle
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


def _host_pipeline_data() -> dict:
    return {
        "run_id": "govengine-current-lifecycle",
        "created_at": "2026-05-23T00:00:00+00:00",
        "settings": {"runtime_mode": "demo"},
        "policy_gate": {"pass": True, "reason": "public-safe"},
        "auditor": {"owner_gate": False, "constraints": {}},
        "prepared_execution_spec": {
            "target": "https://example.com",
            "target_host": "example.com",
            "target_in_scope": True,
            "action_type": "single_probe",
            "resolved_tool": "curl",
            "normalized_args": ["https://example.com"],
            "execution_plan": [{"tool": "curl", "args": ["https://example.com"]}],
        },
        "approved_execution_spec": {
            "target": "https://example.com",
            "target_host": "example.com",
            "target_in_scope": True,
            "resolved_tool": "curl",
            "normalized_args": ["https://example.com"],
            "execution_plan": [{"tool": "curl", "args": ["https://example.com"]}],
            "approval": {"decision": "approve", "approval_source": "auditor"},
            "execution_truth": {
                "artifact_type": "approved_execution_spec",
                "execution_plan": [{"tool": "curl", "args": ["https://example.com"]}],
            },
        },
        "engine": {
            "status": "dry-run",
            "returncode": 0,
            "execution_source": "dry_run",
            "planned_commands": [["curl", "https://example.com"]],
            "executed_commands": [],
        },
    }


def test_current_lifecycle_builds_scoped_ticket_and_receipt_bounded_evidence(tmp_path) -> None:
    artifacts = build_current_lifecycle_artifacts(_host_pipeline_data())
    ticket = artifacts["execution_ticket.json"]

    assert ticket["schema_version"] == "v0.3"
    assert ticket["ticket_profile"] == "scoped_execution_ticket"
    assert "legacy_v0_1_descriptor" not in artifacts["policy_decision.v0.2.json"]
    gate = validate_scoped_ticket_use_gate(
        execution_ticket=ticket,
        execution_contract=artifacts["execution_contract.json"],
        execution_receipt=artifacts["execution_receipt.v0.2.json"],
        evidence_contract=artifacts["evidence_contract.json"],
    )
    assert gate["status"] == "passed"

    bundle = materialize_review_bundle(
        tmp_path / "review-bundle",
        {
            "intent_contract": artifacts["intent_contract.json"],
            "policy_decision": artifacts["policy_decision.v0.2.json"],
            "execution_contract": artifacts["execution_contract.json"],
            "execution_ticket": ticket,
            "execution_receipt": artifacts["execution_receipt.v0.2.json"],
            "evidence_contract": artifacts["evidence_contract.json"],
        },
        chain_id="govengine-current-lifecycle",
        created_at="2026-05-23T00:00:00+00:00",
        generated_at="2026-05-23T00:00:00+00:00",
    )
    assert set(REVIEW_BUNDLE_REQUIRED_FILES) <= set(bundle["summary"]["review_bundle_files"])
    assert bundle["verdict"] == "pass"
