# Security Integration Boundary

GovEngine composes bounded runtime security records. It does not replace
SCLite lifecycle authority, host policy authority, production identity, or live
execution infrastructure.

## Canonical v1 order

Runtime-consuming hosts should evaluate the security path in this order:

1. RExecOp projects one bounded, attempt/lease/fencing/inventory-bound
   `GovernanceRequest v1`.
2. GovEngine verifies every complete GovEngine-owned digest and the current
   host-provided `PolicyActivationBinding`.
3. PolicyEngine evaluates typed policy and projects enforceable controls.
4. GovEngine validates exact approval trust, validity, revocation and host
   signature verification when required.
5. Independent scope and capability decisions are evaluated.
6. GovEngine emits and the host signs one short-lived `GovernanceDecision v1`.
7. RExecOp verifies signature, decision digest, runtime bindings and expiry,
   then atomically claims decision digest and nonce.
8. RExecOp issues and rechecks its immutable runtime permit immediately before
   connector I/O.
9. RExecOp emits `RuntimeReceiptBinding v1`; GovEngine validates receipt
   bindings and postconditions.
10. RExecOp projects the final receipt/evidence bundle for SCLite secure verification
    of lifecycle and proof.

This order is a safety precondition checklist, not a scheduler. See
[THREAT_MODEL.md](THREAT_MODEL.md) and
[SECURITY_GUARANTEES.md](SECURITY_GUARANTEES.md).

## Legacy compatibility order

`RuntimeAdmissionResult` is not proof and not execution authority. It is a
bounded decision record showing which earlier gates were present, allowed, or
blocked. `validate_runtime_admission_proof_inputs()` checks that an allowed
admission carries the expected proof input summaries and references; it does
not verify SCLite artifacts, validate signatures, choose policy meaning, or
authorize execution.

The legacy review chain still names these stages for compatibility: SCLite
secure verification, GovEngine replay freshness, Host trust decision,
Execution ticket gate, Runtime admission composition, and Runner receipt binding.
They are not a second authorization protocol.

Legacy guarded SCLite/replay/ticket/admission/runner receipt helpers remain
available for compatibility and review flows. They do not replace the
canonical `GovernanceRequest -> GovernanceDecision -> RExecOp claim ->
RuntimeReceiptBinding` path for controlled connector attempts.

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

Because GovEngine is an in-process library, a compromised host can bypass these
steps or fabricate bounded facts. No malicious-host resistance is claimed.

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
