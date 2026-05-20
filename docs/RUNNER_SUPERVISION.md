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
