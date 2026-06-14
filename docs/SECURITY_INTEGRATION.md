# Security Integration Boundary

GovEngine composes bounded runtime security records. It does not replace
SCLite lifecycle authority, host policy authority, production identity, or live
execution infrastructure.

## Required Order

Runtime-consuming hosts should evaluate the security path in this order:

1. SCLite secure verification for strict lifecycle and Kernel Guard status.
2. GovEngine replay freshness for the guarded root or guarded payload.
3. Host trust decision for signer, signature, and trust-anchor status.
4. Execution ticket gate for ticket status and scope binding.
5. Runtime admission composition through `RuntimeAdmissionResult`.
6. Runner request creation from an approved execution spec.
7. Runner receipt binding for admission, ticket, request, and receipt refs.
8. Evidence and review records bounded by receipt status.
9. Audit record and audit ledger verification over bounded records.

This order is a safety precondition checklist, not a scheduler.
`RuntimeAdmissionResult` is not proof and not execution authority. It is a
bounded decision record showing which earlier gates were present, allowed, or
blocked. `validate_runtime_admission_proof_inputs()` checks that an allowed
admission carries the expected proof input summaries and references; it does
not verify SCLite artifacts, validate signatures, choose policy meaning, or
authorize execution.

## Production Non-Claims

GovEngine does not provide:

- live execution, live subprocess runners, target access, or scanner control;
- PKI, KMS, CA, HSM, private key storage, credential storage, or trust-anchor
  administration;
- production replay persistence, locking, retention, or multi-process
  concurrency;
- production audit database, retention, deletion, or concurrency semantics;
- raw evidence storage, raw stdout/stderr publication, raw prompt storage, or
  redaction pipelines;
- SCLite schema ownership, canonicalization, lifecycle verification,
  guarded-strict verification, execution-ticket semantics, or review-bundle
  verdict authority.

Hosts own domain policy, operator approval, production storage, live runner
adapters, network access, secrets, release authorization, public evidence
publication, and incident response.

## Development Helpers

The following helpers are safe for tests, examples, and local smoke evidence,
but are not production security backends:

- `DemoDigestSigner` and `DemoDigestVerifier` are deterministic demo helpers,
  not cryptographic identity proof.
- `InMemoryReplayClaimStore` is a development claim-once adapter, not durable
  atomic storage.
- `record_guard_replay_file()` is a local JSON helper, not a production replay
  database.
- `JsonlAuditLedgerAdapter` is a development JSONL hash-chain adapter, not a
  production audit ledger.
- `runner_receipt_public_summary()`, `runtime_admission_public_summary()`,
  `audit_record_public_summary()`, and review public-summary helpers are
  public-safe projections, not raw evidence publication.

## Public Projection Rule

Public records may carry ids, statuses, reason codes, counts, bounded refs, and
`sha256:` digests. They must not carry raw targets, credentials, prompts,
commands, carrier payloads, raw evidence, raw stdout, raw stderr, or private
storage paths.

The public-safe chain is:

```text
RuntimeAdmissionResult
-> GovRunnerReceipt binding
-> GovEvidenceClaim / GovReviewResult summary
-> GovAuditRecord / AuditLedgerVerificationResult summary
```

Each step is review evidence only. It is not permission to execute live work.
