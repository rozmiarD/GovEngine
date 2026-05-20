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
