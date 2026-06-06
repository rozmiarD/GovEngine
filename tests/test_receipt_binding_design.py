from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECEIPT_BINDING = ROOT / "docs" / "RECEIPT_BINDING.md"
RUNTIME_ADMISSION = ROOT / "docs" / "RUNTIME_ADMISSION.md"
RUNNER_SUPERVISION = ROOT / "docs" / "RUNNER_SUPERVISION.md"


def test_receipt_binding_design_names_required_references() -> None:
    text = RECEIPT_BINDING.read_text(encoding="utf-8")

    for required in (
        "RuntimeAdmissionResult",
        "GovRunnerRequest",
        "GovRunnerReceipt",
        "admission_id",
        "admission_digest",
        "ticket_id",
        "ticket_digest",
        "request_id",
        "request_digest",
        "receipt_id",
        "receipt_digest",
        "status",
        "reason_code",
        "output_digests",
        "evidence_refs",
    ):
        assert required in text


def test_receipt_binding_design_preserves_boundaries() -> None:
    text = RECEIPT_BINDING.read_text(encoding="utf-8")
    lower_text = text.lower()
    normalized_lower_text = " ".join(lower_text.split())

    for required in (
        "never raw output",
        "GovEngine owns the neutral binding mechanics",
        "SCLite owns ticket schema",
        "Hosts own raw evidence",
    ):
        assert required in text
    assert "does not add live execution authority" in normalized_lower_text
    assert "must not duplicate sclite" in lower_text
    assert "verification" in lower_text


def test_receipt_binding_design_is_linked_from_runtime_docs() -> None:
    runtime_text = RUNTIME_ADMISSION.read_text(encoding="utf-8")
    supervision_text = RUNNER_SUPERVISION.read_text(encoding="utf-8")

    assert "RECEIPT_BINDING.md" in runtime_text
    assert "RECEIPT_BINDING.md" in supervision_text
