# GovEngine and SCLite Integration

GovEngine consumes [SCLite](https://github.com/rozmiarD/SCLite) as its contract lifecycle layer.

SCLite answers: **what artifacts prove the governed lifecycle?**
GovEngine answers: **how does a runtime prepare, check, and consume those artifacts safely?**

## Dependency

`pyproject.toml` depends on the published SCLite package distribution:

```toml
sclite-core>=1.0.2,<1.1
```

The PyPI distribution name is `sclite-core`; the Python import package remains `sclite`.

This keeps the dependency direction explicit:

```text
GovEngine -> SCLite
```

## Lifecycle relationship

SCLite models the lifecycle as schema-backed artifacts and review bundles:

```text
intent_contract
-> policy_decision
-> execution_contract
-> execution_ticket
-> execution_receipt
-> evidence_contract
-> artifact_chain_manifest
-> review_record / review bundle
```

GovEngine currently provides helpers around the runtime-facing parts of that lifecycle:

- approved-spec and execution-ticket validation helpers;
- execution-contract shaping and redaction through `govengine.contracts.execution`;
- dry-run result assembly;
- host-provided policy and trust decision shape validation through `govengine.admission` and `govengine.signing` (GovEngine does not own domain policy meaning);
- integration seams for SCLite lifecycle/review verification;
- guarded-root replay checks for optional SCLite `kernel_guard_hmac_v1`
  sidecars after SCLite has verified the HMAC guard;
- `ReplayClaimStore`, a host-neutral claim-once replay freshness port, plus an
  in-memory development adapter for deterministic local smoke tests;
- `verify_guard_and_record_replay()`, a high-level adapter that verifies the
  SCLite guarded-strict profile and then records replay freshness for one
  runtime-consumable decision;
- review-bundle verdict mapping through the current `sclite-core>=1.0.2,<1.1` review and guarded-strict surfaces, preserving the review-bundle contract.

Host-owned artifact projection is outside GovEngine. A runtime such as
Ravenclaw constructs its domain-shaped lifecycle artifacts before consuming
neutral GovEngine gates and SCLite review/verification services.

## What GovEngine does not replace

GovEngine does not replace SCLite schemas, lifecycle verification, artifact
integrity checks, Kernel Guard HMAC verification, Scope Fidelity checks, or
review-bundle verdict semantics. Those stay in SCLite.

GovEngine's replay helper records observed guarded roots (`root_tag`,
`chain_id`, ticket/run id, and `key_id`) through a host-supplied state store so
a runtime can reject reuse in require-fresh mode. It does not store HMAC keys,
verify tags, or make public PKI claims.

Production replay freshness should be exposed to GovEngine through a
claim-once adapter: the first claim for a guarded root or guarded payload can be
accepted, and later claims for the same replay key must be rejected by the
host-owned atomic store. `InMemoryReplayClaimStore` is deterministic but
development-only. `record_guard_replay_file()` remains a local JSON helper and
is not a production atomic store, database, or concurrency boundary.
Replay matching prefers the guarded payload digest plus ticket or chain scope
and key id. The root-tag compatibility fallback is scoped by `chain_id` and
`key_id` so unrelated domains or key namespaces do not collide.

Replay-store responsibilities are split deliberately:

- GovEngine owns the bounded replay record, decision, and claim-once port
  shapes.
- SCLite owns guarded bundle and Kernel Guard verification before replay is
  considered.
- `InMemoryReplayClaimStore` and `record_guard_replay_file()` are local
  development helpers for tests and smoke evidence only.
- Hosts own atomic production persistence, locking, transaction isolation,
  multi-process concurrency, retention, deletion policy, and recovery.

Runtime-consumable artifacts should use this posture with
`runtime_consumable=True` on the admission composition inputs:

```text
strict lifecycle pass
kernel_guard_hmac_v1 pass in SCLite
replay fresh in GovEngine
policy/ticket/trust gates pass
runtime_consumable=True for guarded/replay blockers
```

`compose_runtime_admission_result()` consumes bounded gate summaries. It does
not call SCLite verification or record replay state itself. Hosts should obtain
guarded-strict and replay summaries first — for example through
`verify_guard_and_record_replay()` — and then pass those summaries into
admission composition.

GovEngine exposes two replay models:

- `ReplayClaimStore` — host-owned claim-once replay freshness port with a
  development-only in-memory adapter;
- `verify_guard_and_record_replay()` — calls SCLite guarded-strict verification,
  then records replay freshness through a host `GovStateStore` or compatible
  adapter and returns one runtime decision.

These are complementary: SCLite verifies guarded bundles; GovEngine records
whether a guarded root or payload has already been consumed for runtime work.

A deterministic dry-run example for this path is documented in
[GUARDED_FRESH_RUNTIME_ADMISSION_EXAMPLE.md](GUARDED_FRESH_RUNTIME_ADMISSION_EXAMPLE.md).
The operator sequence that combines those checks with trust ports, runner
profile selection, receipt obligation, and evidence/review binding is
documented in [GOVERNED_RUNTIME_MVP_RUNBOOK.md](GOVERNED_RUNTIME_MVP_RUNBOOK.md).

GovEngine then keeps the runtime-consumption evidence chain bounded:

```text
RuntimeAdmissionResult
  -> SCLite execution ticket / guarded verification reference
  -> GovRunnerRequest
  -> GovRunnerReceipt
  -> GovEvidenceClaim / GovReviewResult references
```

`validate_runner_receipt_binding()` checks the GovEngine-owned admission,
request, and receipt references plus SCLite/host ticket references. It compares
SCLite ticket ids or digests only as bounded references; SCLite still owns
ticket schema, canonicalization, guarded verification, artifact-chain
verification, and review-bundle authority. `validate_evidence_review_chain()`
then checks receipt/evidence/review references and receipt status bounds
without storing raw evidence or re-deciding SCLite review verdicts.

Review-only bundles may remain `integrity_only` or `strict_lifecycle`, but a
runtime-consumable execution ticket must not be accepted from `validate-chain`
alone.

GovEngine also does not execute live targets by itself. A host runtime such as Ravenclaw remains responsible for concrete execution adapters, artifact persistence, operator approval UX, and public snapshot/demo publishing.

## Why this split matters

The split keeps responsibilities reviewable:

- SCLite is the small auditable contract and integrity layer.
- GovEngine is the reusable governance service layer that consumes those contracts.
- Ravenclaw is the full reference runtime/control plane that wires the pieces into an operator workflow.

This avoids turning one repository into a mixed contract/runtime/UI/protocol bundle and makes each layer easier to validate independently.
