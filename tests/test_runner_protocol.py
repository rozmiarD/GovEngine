from __future__ import annotations

import pytest

from govengine.api import GovApiError
from govengine.execution.runner_protocol import (
    GovRunnerReceiptBinding,
    dry_run_runner_receipt,
    normalize_runner_steps,
    runner_receipt_with_binding,
    runner_request_from_approved_spec,
)


def _approved_spec() -> dict:
    return {
        "spec_version": "2026-03-18.approved.v1",
        "action_type": "single_probe",
        "capability": "http_probe",
        "resolved_tool": "curl",
        "execution_mode": "normalized",
        "compiler": {"semantic_loss_policy": {"loss_class": "none", "policy_response": "proceed"}},
        "approval": {"decision": "approve", "reason": "ok"},
        "execution_truth": {
            "artifact_type": "approved_execution_spec",
            "execution_plan": [{"tool": "curl", "args": ["https://example.com"], "stdin": ""}],
        },
    }


def test_runner_request_from_approved_spec_is_carrier_neutral() -> None:
    request = runner_request_from_approved_spec(_approved_spec(), request_id="r1")

    assert request.request_id == "r1"
    assert request.source == "approved_execution_spec"
    assert request.dry_run is True
    assert request.steps[0].tool == "curl"
    assert request.steps[0].args == ("https://example.com",)
    assert request.as_dict()["steps"] == [{"index": 0, "tool": "curl", "args": ["https://example.com"], "stdin": ""}]


def test_dry_run_runner_receipt_records_each_step() -> None:
    request = runner_request_from_approved_spec(_approved_spec(), request_id="r2")
    receipt = dry_run_runner_receipt(request)

    assert receipt.status == "dry-run"
    assert receipt.reason_code == "dry_run_requested"
    assert receipt.step_results[0].status == "dry-run"
    assert receipt.as_dict()["step_results"][0]["reason_code"] == "dry_run_requested"
    assert "binding" not in receipt.as_dict()


def test_runner_receipt_with_binding_adds_bounded_references() -> None:
    request = runner_request_from_approved_spec(_approved_spec(), request_id="r-bound")
    receipt = runner_receipt_with_binding(
        dry_run_runner_receipt(request),
        admission_id="admission-1",
        admission_digest="sha256:admission",
        ticket_id="ticket-1",
        ticket_digest="sha256:ticket",
        request_digest="sha256:request",
        receipt_id="receipt-1",
        receipt_digest="sha256:receipt",
        runner_profile="dry-run",
        output_digests={"stdout": "sha256:stdout"},
        evidence_refs={"review": "artifact://review/1"},
    )
    binding = receipt.as_dict()["binding"]

    assert binding["admission_id"] == "admission-1"
    assert binding["admission_digest"] == "sha256:admission"
    assert binding["ticket_id"] == "ticket-1"
    assert binding["ticket_digest"] == "sha256:ticket"
    assert binding["request_id"] == "r-bound"
    assert binding["receipt_id"] == "receipt-1"
    assert binding["runner_profile"] == "dry-run"
    assert binding["output_digests"] == {"stdout": "sha256:stdout"}
    assert binding["evidence_refs"] == {"review": "artifact://review/1"}


def test_runner_receipt_binding_rejects_raw_output_fields() -> None:
    with pytest.raises(GovApiError, match="forbidden_runner_receipt_binding:raw_stdout"):
        GovRunnerReceiptBinding.from_mapping({
            "admission_id": "admission-1",
            "ticket_id": "ticket-1",
            "raw_stdout": "must-not-cross-boundary",
        })


def test_runner_step_normalization_rejects_missing_tool() -> None:
    with pytest.raises(GovApiError, match="missing_runner_step_tool"):
        normalize_runner_steps([{"args": ["https://example.com"]}])
