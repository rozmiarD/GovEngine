# Runner Supervision

`govengine.execution.supervision` defines neutral runner-supervision contracts
for bounded host runner requests.

It is a shape and validation layer only. It does not run subprocesses, own live
backends, persist leases, hold credentials, deliver carrier messages, or write
runtime storage.

## Objects

- `GovSupervisionPlan` validates bounded runner requirements: runner profile,
  dry-run/live posture, timeout, cwd, env, stdin, and receipt requirement.
- `GovRunnerLease` validates a storage-neutral lease record for a runner
  request. Hosts own persistence, clocks, and cleanup.
- `GovSupervisionDecision` validates a supervisor decision over a request,
  lease, or receipt boundary.

## Boundary

Supervised runner requests must come from approved execution specs, not raw
intent. Receipts are required for attempted work. Dry-run remains the default;
live backend requests are blocked unless the host provides an explicit
supervision plan with live backend enabled and bounded timeout/cwd/env/stdin
policies.

Hosts such as Ravenclaw may map their own approved execution and runner
semantics into these objects. GovEngine validates the neutral representation;
the host still owns concrete tool adapters, subprocess behavior, artifact
storage, operator authorization, live execution authority, and audit retention.

Receipt binding across admission, execution ticket, runner request, receipt, and
evidence references is defined in [RECEIPT_BINDING.md](RECEIPT_BINDING.md).
`validate_runner_receipt_binding()` verifies the bounded binding before a
receipt is treated as runtime evidence. It compares GovEngine-owned request and
receipt digests, can compare an admission digest when a GovEngine admission
record or digest is supplied, and treats ticket digests as SCLite/host-provided
references. The verifier is not live execution authority and does not store raw
evidence.

## Live Runner Safety Specification

GovEngine does not provide a live subprocess runner in this stage. This section
is the prerequisite safety contract for any future optional host adapter; it is
not implementation permission and it does not make live execution the default.

A future live runner must be rejected unless all of these conditions are true:

- Runtime admission is allowed and references a valid policy decision,
  approved execution ticket, guarded-strict SCLite verification when the action
  is runtime-consumable, fresh replay state, valid trust decision, an allowed
  runner profile, and an explicit receipt obligation.
- The runner profile explicitly enables a live backend for the host and task;
  dry-run remains the default profile and `live_backend_enabled` remains false
  unless the host provides an approved supervision plan.
- Commands are derived from approved execution specs as argv-only step shapes.
  Shell strings, implicit shell execution, command interpolation, and raw
  intent prompts are rejected by default.
- The working directory is restricted by an allowlist policy. A live runner must
  not accept arbitrary cwd values, home-directory expansion, or unreviewed
  runtime storage paths from task metadata.
- The environment is restricted by an allowlist policy. A live runner must not
  inherit the ambient process environment wholesale and must reject credential,
  token, password, private-key, and secret material at the GovEngine boundary.
- A positive timeout is required for every attempted step. Unbounded execution
  is invalid.
- Bounded stdout/stderr capture is required. Raw output is not stored in
  GovEngine-owned records; receipts carry digests, statuses, reason codes, and
  bounded excerpts only when a host redaction policy permits them.
- A redaction hook or equivalent host policy is required before any output
  excerpt is emitted. Redaction failures must block publication of excerpts.
- A receipt is always emitted for attempted work, including blocked, timed out,
  interrupted, failed, and dry-run outcomes. The receipt must bind admission,
  ticket, request, runner profile, status, and output digests where available.
- SCLite remains the proof/review artifact authority. GovEngine may bind
  references and digests, but it must not duplicate SCLite artifact-chain
  verification, review-bundle verdicts, or canonicalization.
- Production identity, credentials, key management, operator approval workflow,
  raw evidence storage, audit retention, and live backend implementation remain
  host-owned.

These requirements are deliberately stricter than the current
`GovSupervisionPlan` record. The record expresses the neutral plan shape; the
host live adapter must satisfy the full checklist before it can run anything.
