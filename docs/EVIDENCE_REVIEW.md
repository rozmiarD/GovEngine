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
claim. The requirement `evidence_kind` is enforced as a bounded contract field:
`execution_receipt` is satisfied by receipt references, and non-default kinds
must appear in the claim type or bounded claim metadata such as
`evidence_kind` / `evidence_kinds`. GovEngine does not parse raw evidence or
define a Ravenclaw/Tecrax taxonomy. SCLite remains the proof/review artifact
authority; GovEngine only validates neutral review mechanics.

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

## OODA decisions in receipts and evidence

GovEngine's OODA controller is a safety/control contract, not a raw telemetry
publication channel. Hosts may record compact OODA decision summaries in runner
receipts only after the governed receipt chain is bounded.

### What may be recorded

A host runner may append summary-level fields such as decision, reason code,
interrupting flag, step index, observation kinds, and orientation booleans/enums
(scope, policy, ticket, spec, host-health, output-shape, operator-control,
budget state). Link approved specs, tickets, and artifact descriptors by
reference — not raw output.

### What must not be recorded

OODA receipt/evidence surfaces must not include raw stdout/stderr, command logs,
request/response bodies, credentials, private paths, unredacted live targets, full
telemetry dumps, or LLM prompts/reasoning.

### Receipt and evidence behavior

Interrupting decisions (`pause`, `abort`, `cooldown`, `degrade_to_dry_run`,
`require_owner_review`) should stop scheduling the next step. Evidence summaries
may claim that control decisions were evaluated; they must not claim live
vulnerability evidence, successful exploitation, or authorization beyond approved
bounds.

### Verification order

Before treating OODA summaries as runtime evidence, verify:

```text
RuntimeAdmissionResult
  -> GovRunnerRequest
  -> GovRunnerReceipt
  -> GovEvidenceClaim
  -> GovReviewResult
```

`validate_runner_receipt_binding()` runs first; `validate_evidence_review_chain()`
validates receipt/evidence/review references afterward. Neither helper stores raw
evidence, evaluates SCLite review-bundle verdicts, or grants execution authority.

Hosts remain responsible for redaction, persistence choices, honoring interrupting
decisions, and linking decisions into SCLite lifecycle receipts when available.
