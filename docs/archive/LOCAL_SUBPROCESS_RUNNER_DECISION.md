# Local Subprocess Runner Decision

> Archived GE-032 decision evidence. The active boundary and current
> `not_applicable` readiness result are maintained in
> [`../RUNNER_SUPERVISION.md`](../RUNNER_SUPERVISION.md).

This is the GE-032 not-applicable evidence artifact for the optional
`LocalSubprocessRunner` roadmap task.

Decision: `not_applicable`

Reason code: `local_subprocess_runner_prerequisites_incomplete`

GovEngine must not add an in-core live subprocess runner in this stage. The
readiness gate added in GE-031 reports that the current kernel is not ready for
a GovEngine-owned local live backend.

## Evidence

- `evaluate_local_subprocess_runner_readiness()` returns `ready=False` and
  `status=not_applicable` by default.
- `DryRunRunner` remains the only GovEngine-owned runner behavior.
- `ExecutionGate` and runtime admission continue to block live backend use
  unless a host explicitly enables a live runner profile.
- `GovSupervisionPlan` expresses neutral timeout, cwd, env, stdin, and receipt
  policy shape, but the live-runner safety specification is stricter than the
  current neutral record.
- Runner receipts can bind admission, ticket, request, status, and digests, but
  GovEngine still does not own raw evidence storage or concrete subprocess IO.

## Missing Prerequisites

- host-owned live runner profile authorization policy;
- enforced cwd allowlist semantics beyond the neutral `cwd_policy` shape;
- enforced environment allowlist semantics beyond the neutral `env_policy`
  shape;
- maximum output enforcement for live outcomes;
- output digest contract for live stdout/stderr outcomes;
- redaction policy or hook before any output excerpt can be emitted.

## Consequence

GE-032 does not implement `LocalSubprocessRunner`.

GE-033 should treat unsafe local runner tests as not-applicable or test the
absence of a live runner unless a later, explicitly reviewed task first closes
the missing prerequisites above. The safe runtime path remains dry-run,
host-neutral, SCLite-aware, and receipt-bound.

## GE-033 Unsafe Runner Negative-Test Disposition

The unsafe live runner cases are not applicable as live-runner behavior because
GovEngine does not provide `LocalSubprocessRunner`.

The regression coverage for this stage must therefore prove:

- shell-string execution remains absent;
- out-of-scope cwd handling remains absent from GovEngine-owned live behavior;
- unallowlisted environment inheritance remains absent;
- missing timeout live execution remains absent;
- maximum-output enforcement is still a missing prerequisite, not a bypassed
  behavior;
- redaction policy is still a missing prerequisite, not an optional live-output
  publication step;
- receipt emission remains covered only by `DryRunRunner` and runner receipt
  binding helpers until a future host-owned live adapter is explicitly reviewed.

## Non-Claims

- no live execution authority;
- no subprocess backend;
- no shell execution;
- no credential, secret, PKI, KMS, or key-store ownership;
- no SCLite canonicalization or artifact-chain ownership;
- no raw evidence storage ownership.
