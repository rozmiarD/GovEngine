# Admission Policy Contracts

`govengine.admission` defines neutral admission, policy, approval, and audit
record contracts for host runtimes.

`govengine.policy` adds a deterministic **PolicyEngine MVP** (request/verdict
contracts, declarative pack compiler, fail-closed runtime). See
[POLICY_ENGINE.md](POLICY_ENGINE.md). Admission record validators remain
separate from domain policy meaning: hosts map verdicts into `GovPolicyDecision`
via `policy_verdict_to_gov_policy_decision()`.

GovEngine does not run operator approval workflows, store audit logs, deliver
carrier messages, hold credentials, or execute tools.

## Objects

- `GovAdmissionDecision` validates one host-provided go/no-go decision over a
  redacted `subject_ref`.
- `GovPolicyDecision` validates the policy result attached to a host subject.
- `policy_verdict_to_gov_policy_decision()` projects a `PolicyVerdict` from
  `govengine.policy` into `GovPolicyDecision` for admission composition.
- `GovApprovalRequest` validates approval-request state without owning the
  approval workflow.
- `GovAuditRecord` validates an append-only audit record shape without owning
  storage or retention.
- `AuditLedgerEntry`, `AuditLedgerAppendResult`, and
  `AuditLedgerVerificationResult` define the bounded append/read/verify records
  for a host-owned audit ledger.
- `AuditLedgerPort` defines the neutral append/read/verify adapter contract
  without providing production persistence.
- `JsonlAuditLedgerAdapter` is a development-only JSONL hash-chain adapter for
  local smoke validation.

## Boundary

Admission metadata must not contain raw targets, raw prompts, credentials,
commands, subprocesses, shell payloads, live-backend claims, runtime storage
paths, carrier payloads, or schedules.

Hosts such as Ravenclaw may map their own runtime admission and execution-gate
semantics into these objects. GovEngine validates the neutral representation;
the host still owns security meaning, target selection, budget logic, cooldown
logic, operator approval, queue mutation, process control, audit persistence,
and concrete execution.

The canonical runtime admission contract lives in
[RUNTIME_ADMISSION.md](RUNTIME_ADMISSION.md). The initial
`RuntimeAdmissionResult` record is the bounded admission decision surface. The
`compose_runtime_admission_result()` helper populates it from host-supplied
policy, ticket, trust, SCLite guarded verification, replay freshness,
runner-profile, and receipt-obligation summaries without making intent an
execution authority. The helper composes summaries only; it does not verify
SCLite tickets or record replay state. Guarded/replay blockers apply when the
host sets `runtime_consumable=True`.

## Audit ledger port

`GovAuditRecord` is the event shape. `AuditLedgerPort` is the storage boundary.
The port separates record validation from persistence by requiring adapters to:

- append one bounded `GovAuditRecord` plus a `record_digest` and optional
  `event_digest`;
- return `AuditLedgerAppendResult` with the assigned entry id, sequence, and
  entry digest;
- read bounded `AuditLedgerEntry` records without exposing storage paths;
- verify a sequence and return `AuditLedgerVerificationResult`.

GovEngine validates ids, sequence numbers, digest references, append outcomes,
verification outcomes, blockers, and forbidden metadata. `audit_ledger_entry_digest()`
clears the self-referential `entry_digest` field before computing a GovEngine-owned
record digest. `JsonlAuditLedgerAdapter` writes one canonical JSON object per
line, links each entry to the previous entry digest, and verifies sequence,
previous-digest, and entry-digest continuity.

GovEngine does not choose a production database, lock, clock, transaction
isolation level, retention policy, concurrency model, or deletion policy. The
JSONL adapter is development-only and should not be treated as production
persistence. Its verification is intentionally limited to local smoke evidence:
one-field tamper, missing lines, malformed JSONL, and chain restarts are
detected as failed or invalid local chains, but recovery, retention,
concurrency, and trusted reconstruction remain host-owned.
