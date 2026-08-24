from __future__ import annotations

from dataclasses import replace

import pytest

from govengine import govengine_record_digest
from govengine.api import GovApiError
from govengine.execution.runner_protocol import (
    GovRunnerReceiptBinding,
    dry_run_runner_receipt,
    normalize_runner_steps,
    runner_receipt_public_summary,
    runner_receipt_binding_verification_summary,
    runner_receipt_digest,
    runner_receipt_with_binding,
    runner_request_digest,
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

    assert request.schema_version == "v0.1"
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
    assert receipt.schema_version == "v0.1"
    assert receipt.reason_code == "dry_run_requested"
    assert receipt.step_results[0].status == "dry-run"
    assert receipt.as_dict()["step_results"][0]["reason_code"] == "dry_run_requested"
    assert "binding" not in receipt.as_dict()
    assert runner_receipt_public_summary(receipt)["binding_verification_status"] == "unanchored"


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
    assert binding["schema_version"] == "v0.1"
    assert binding["admission_digest"] == "sha256:admission"
    assert binding["ticket_id"] == "ticket-1"
    assert binding["ticket_digest"] == "sha256:ticket"
    assert binding["request_id"] == "r-bound"
    assert binding["receipt_id"] == "receipt-1"
    assert binding["runner_profile"] == "dry-run"
    assert binding["output_digests"] == {"stdout": "sha256:stdout"}
    assert binding["evidence_refs"] == {"review": "artifact://review/1"}


def test_runner_receipt_public_summary_excludes_raw_step_output() -> None:
    request = runner_request_from_approved_spec(_approved_spec(), request_id="r-public")
    receipt = runner_receipt_with_binding(
        dry_run_runner_receipt(request),
        admission_id="admission-1",
        admission_digest="sha256:" + "a" * 64,
        ticket_id="ticket-1",
        ticket_digest="sha256:" + "b" * 64,
        request_digest=runner_request_digest(request),
        receipt_id="receipt-1",
        output_digests={"stdout": "sha256:stdout"},
        evidence_refs={"review": "artifact://review/1"},
    )

    summary = runner_receipt_public_summary(receipt)

    assert summary == {
        "schema_version": "v0.1",
        "receipt_id": "receipt-1",
        "request_id": "r-public",
        "status": "dry-run",
        "reason_code": "dry_run_requested",
        "step_count": 1,
        "admission_id": "admission-1",
        "ticket_id": "ticket-1",
        "request_digest": runner_request_digest(request),
        "receipt_digest": receipt.binding.receipt_digest,
        "binding_verification_status": "present_unverified",
        "output_digest_count": 1,
        "evidence_ref_count": 1,
    }
    assert "stdout" not in summary
    assert "stderr" not in summary


def test_runner_receipt_binding_auto_digest_changes_when_receipt_mutates() -> None:
    request = runner_request_from_approved_spec(_approved_spec(), request_id="r-digest")
    receipt = runner_receipt_with_binding(
        dry_run_runner_receipt(request),
        admission_id="admission-1",
        admission_digest="sha256:" + "a" * 64,
        ticket_id="ticket-1",
        ticket_digest="sha256:" + "b" * 64,
        request_digest=runner_request_digest(request),
        receipt_id="receipt-1",
    )

    assert receipt.binding.status == "dry-run"
    assert receipt.binding.reason_code == "dry_run_requested"
    assert receipt.binding.receipt_digest == runner_receipt_digest(receipt)
    assert receipt.binding.receipt_digest.startswith("sha256:")
    assert runner_receipt_digest(replace(receipt, reason_code="tampered")) != receipt.binding.receipt_digest


def test_public_summary_does_not_claim_consistency_for_a_tampered_binding() -> None:
    request = runner_request_from_approved_spec(_approved_spec(), request_id="r-public-tampered")
    receipt = runner_receipt_with_binding(
        dry_run_runner_receipt(request),
        admission_id="admission-1",
        admission_digest="sha256:" + "a" * 64,
        ticket_id="ticket-1",
        ticket_digest="sha256:" + "b" * 64,
        request_digest=runner_request_digest(request),
        receipt_id="receipt-1",
    )

    summary = runner_receipt_public_summary(replace(receipt, reason_code="tampered"))

    assert summary["binding_verification_status"] == "present_unverified"


def test_runner_receipt_binding_rejects_raw_output_fields() -> None:
    with pytest.raises(GovApiError, match="forbidden_runner_receipt_binding:raw_stdout"):
        GovRunnerReceiptBinding.from_mapping({
            "admission_id": "admission-1",
            "ticket_id": "ticket-1",
            "raw_stdout": "must-not-cross-boundary",
        })


@pytest.mark.parametrize("argv", [[True], [7]])
def test_runner_step_normalization_rejects_coerced_argv(argv) -> None:
    with pytest.raises(GovApiError, match="invalid_runner_step_args"):
        normalize_runner_steps([{"tool": "curl", "args": argv}])


@pytest.mark.parametrize("argv", [False, 0, "", None])
def test_runner_step_normalization_rejects_supplied_falsey_non_sequences(argv) -> None:
    with pytest.raises(GovApiError, match="invalid_runner_step_args"):
        normalize_runner_steps([{"tool": "curl", "args": argv}])


def test_runner_step_normalization_allows_missing_optional_args() -> None:
    steps = normalize_runner_steps([{"tool": "curl"}])

    assert steps[0].args == ()


def test_runner_receipt_binding_status_is_self_consistent_without_external_anchors() -> None:
    request = runner_request_from_approved_spec(_approved_spec(), request_id="run-self-consistent")
    receipt = runner_receipt_with_binding(
        dry_run_runner_receipt(request),
        admission_id="admission-1",
        admission_digest="sha256:" + "a" * 64,
        ticket_id="ticket-1",
        ticket_digest="sha256:" + "b" * 64,
        request_digest=runner_request_digest(request),
        receipt_id="receipt-1",
    )

    summary = runner_receipt_binding_verification_summary(request, receipt)

    assert summary == {"status": "self_consistent", "verified": False, "external_anchors": ()}


def test_runner_receipt_binding_status_is_verified_with_external_anchors() -> None:
    request = runner_request_from_approved_spec(_approved_spec(), request_id="run-anchored")
    receipt = runner_receipt_with_binding(
        dry_run_runner_receipt(request),
        admission_id="admission-1",
        admission_digest="sha256:" + "a" * 64,
        ticket_id="ticket-1",
        ticket_digest="sha256:" + "b" * 64,
        request_digest=runner_request_digest(request),
        receipt_id="receipt-1",
    )

    summary = runner_receipt_binding_verification_summary(
        request,
        receipt,
        admission_id="admission-1",
        admission_digest="sha256:" + "a" * 64,
        ticket_id="ticket-1",
        ticket_digest="sha256:" + "b" * 64,
    )

    assert summary == {"status": "verified", "verified": True, "external_anchors": ("admission", "ticket")}


def test_runner_receipt_binding_rejects_conflicting_explicit_admission_identity() -> None:
    request = runner_request_from_approved_spec(_approved_spec(), request_id="run-conflicting-admission-id")
    admission = {"admission_id": "admission-record", "status": "allowed"}
    admission_digest = govengine_record_digest(
        admission,
        record_type="govengine.admission.RuntimeAdmissionResult",
    )
    receipt = runner_receipt_with_binding(
        dry_run_runner_receipt(request),
        admission_id="admission-override",
        admission_digest=admission_digest,
        ticket_id="ticket-1",
        ticket_digest="sha256:" + "b" * 64,
        request_digest=runner_request_digest(request),
        receipt_id="receipt-1",
    )

    with pytest.raises(GovApiError, match="runtime_admission_id_mismatch"):
        runner_receipt_binding_verification_summary(
            request,
            receipt,
            admission=admission,
            admission_id="admission-override",
            admission_digest=admission_digest,
            ticket_id="ticket-1",
            ticket_digest="sha256:" + "b" * 64,
        )


@pytest.mark.parametrize("conflicting_key", ["ticket_digest", "digest", "artifact_digest"])
def test_runner_receipt_binding_rejects_conflicting_explicit_ticket_digest(conflicting_key: str) -> None:
    request = runner_request_from_approved_spec(_approved_spec(), request_id="run-conflicting-ticket-digest")
    admission_digest = "sha256:" + "a" * 64
    ticket_digest = "sha256:" + "b" * 64
    receipt = runner_receipt_with_binding(
        dry_run_runner_receipt(request),
        admission_id="admission-1",
        admission_digest=admission_digest,
        ticket_id="ticket-1",
        ticket_digest=ticket_digest,
        request_digest=runner_request_digest(request),
        receipt_id="receipt-1",
    )

    with pytest.raises(GovApiError, match="execution_ticket_digest_mismatch"):
        runner_receipt_binding_verification_summary(
            request,
            receipt,
            admission_id="admission-1",
            admission_digest=admission_digest,
            ticket={"ticket_id": "ticket-1", conflicting_key: "sha256:" + "c" * 64},
            ticket_id="ticket-1",
            ticket_digest=ticket_digest,
        )


def test_runner_step_normalization_rejects_missing_tool() -> None:
    with pytest.raises(GovApiError, match="missing_runner_step_tool"):
        normalize_runner_steps([{"args": ["https://example.com"]}])
