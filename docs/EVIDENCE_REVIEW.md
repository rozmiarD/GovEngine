# Evidence Review Contracts

`govengine.review` defines neutral evidence requirement, claim,
qualification, and review-result contracts for host runtimes.

It is a shape and validation layer only. It does not own SCLite review-bundle
verdicts, Ravenclaw finding taxonomy, raw evidence storage, credentials,
carrier messages, or live execution.

## Objects

- `GovEvidenceRequirement` validates a receipt-bounded evidence requirement.
- `GovEvidenceClaim` validates a host-provided claim with receipt/evidence refs.
- `GovEvidenceQualification` records whether receipt bounds support a claim.
- `GovReviewResult` records the host review verdict shape.

## Boundary

Claims must carry receipt references. Raw targets, prompts, commands, raw
stdout/stderr, credentials, runtime storage, carrier payloads, and live backend
claims are rejected in metadata.

`qualify_evidence_claim()` is deliberately conservative: a dry-run receipt can
support execution-truth review, but it cannot support a live-vulnerability
claim. SCLite remains the proof/review artifact authority; GovEngine only
validates neutral review mechanics.

`validate_evidence_review_chain()` verifies the bounded
admission -> receipt -> evidence -> review references before a claim is treated
as supported. It requires the evidence claim to reference the expected receipt,
match the requirement subject, match the expected admission id or digest when
provided, and stay within the receipt status bounds. When a neutral
`GovReviewResult` is provided, the review must reference the computed or
provided qualification. The helper does not store raw evidence and does not
evaluate SCLite review-bundle verdicts.

In the full runtime path, this helper runs after runner receipt binding:

```text
RuntimeAdmissionResult
  -> GovRunnerRequest
  -> GovRunnerReceipt
  -> GovEvidenceClaim
  -> GovReviewResult
```

`validate_runner_receipt_binding()` owns the admission/ticket/request/receipt
reference check. `validate_evidence_review_chain()` owns the later
receipt/evidence/review reference check. It does not evaluate SCLite
review-bundle verdicts. Neither helper evaluates domain vulnerability meaning,
stores raw evidence, or grants live execution authority.
