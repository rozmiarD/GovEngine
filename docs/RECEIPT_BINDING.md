# Receipt Binding Design

GovEngine runner receipts must be bindable to the runtime admission decision and
the execution ticket they claim to satisfy. This design defines the neutral
binding shape for later implementation. It does not add live execution
authority.

```text
Intent is not execution authority.
Admission is not a receipt.
A receipt without admission and ticket bindings is not runtime evidence.
```

## Purpose

Receipt binding makes the post-run record reviewable without moving host-owned
runner behavior, raw evidence storage, or SCLite proof authority into
GovEngine. A host runtime should be able to verify that a receipt belongs to one
approved governed chain:

```text
RuntimeAdmissionResult
  -> SCLite execution ticket / guarded verification
  -> GovRunnerRequest
  -> GovRunnerReceipt
  -> bounded evidence or review references
```

## Required Binding Fields

Future receipt-binding records should carry these bounded fields:

- `admission_id`: the `RuntimeAdmissionResult` identifier.
- `admission_digest`: the GovEngine-owned digest for the admission record when
  available.
- `admission_ref`: optional bounded path, URI, or artifact reference.
- `ticket_id`: the SCLite execution ticket identifier or host ticket id.
- `ticket_digest`: the ticket digest or bounded SCLite ticket artifact digest
  when available.
- `ticket_ref`: optional bounded ticket artifact reference.
- `request_id`: the `GovRunnerRequest` identifier.
- `request_digest`: a GovEngine-owned digest for the runner request record when
  available.
- `receipt_id`: the receipt identifier assigned by the host or runner adapter.
- `receipt_digest`: a GovEngine-owned digest for the receipt envelope when
  available.
- `status`: one of the neutral receipt outcomes such as `dry-run`, `succeeded`,
  `blocked`, `failed`, or `interrupted`.
- `reason_code`: deterministic status reason.
- `runner_profile`: the admitted runner profile, including dry-run/live posture.
- `output_digests`: bounded stdout/stderr or artifact digests, never raw output.
- `evidence_refs`: bounded downstream evidence or review artifact references.
- `control_decisions`: compact OODA/control decision summaries when present.

The binding record may carry timestamps or lease references only as
host-provided bounded metadata. Hosts own clocks, leases, persistence, raw logs,
and retention policy.

## Verification Rules

A receipt-binding verifier should fail closed when:

- the receipt omits `admission_id` or `admission_digest` after admission binding
  is required;
- the receipt omits `ticket_id` or `ticket_digest` after ticket binding is
  required;
- the `request_id` on the receipt does not match the runner request;
- the receipt status is unknown;
- an admission, ticket, request, or receipt digest does not match the referenced
  record;
- a dry-run receipt claims live execution evidence;
- evidence references are present without a receipt id or receipt digest;
- raw stdout, stderr, prompts, commands, credentials, target payloads, or noisy
  logs appear in binding metadata.

Bounded output digests may support later evidence review. They are not raw
evidence storage and do not replace SCLite review bundles.

## Compatibility With Current Receipts

`GovRunnerReceipt` currently records `status`, `request_id`, `source`,
`reason_code`, step results, and compact control decisions. That shape remains
valid for dry-run/default-safe execution helpers.

Receipt binding should be additive:

1. keep existing dry-run receipt constructors working;
2. add a future binding helper or envelope around existing receipts;
3. require `receipt_obligation.binds` from `RuntimeAdmissionResult` before a
   receipt can be treated as runtime evidence;
4. preserve bounded `step_results` and digest-only output references;
5. keep issue, ticket, admission, request, and evidence closure decisions
   outside the runner itself.

## Boundaries

GovEngine owns the neutral binding mechanics, validation shape, reason codes,
and GovEngine-owned record digests for admission, request, and receipt records.

SCLite owns ticket schema, guarded verification, artifact-chain verification,
canonicalization, lifecycle proof, and review-bundle authority. GovEngine may
store bounded SCLite ticket ids, refs, and digests but must not duplicate SCLite
verification.

Hosts own raw evidence, redaction, clocks, persistence, live runner behavior,
operator approval, legal authorization, ticket issuance policy, and production
key/trust management.

## Implementation Sequence

This design is intentionally before implementation. The next implementation
task should add the minimal receipt/admission/ticket binding helper and tests
without enabling live execution. Evidence/review helpers should then verify
admission -> request -> receipt -> evidence references without storing raw
evidence.
