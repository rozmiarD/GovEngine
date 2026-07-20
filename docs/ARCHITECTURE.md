# GovEngine architecture

GovEngine is an in-process deterministic governance kernel. It evaluates
policy, approval, scope and capability facts for one concrete runtime attempt.
It returns a decision; it does not perform or schedule the operation.

## Ownership

```text
Domain profile   meaning, intents, workflows and connector semantics
      |
      v
RExecOp          lifecycle, queues, lease/fencing, permits, retries and I/O
      |  +---- request / terminal facts -----> GovEngine
      |  <---- decision / conformance result -+  policy, approval, scope and
      |                                           capability decisions
      |
      +---- final lifecycle/evidence --------> SCLite
                                                  contracts, integrity and
                                                  verification truth
```

The projects cooperate through small contracts. None may infer ownership from
the fact that it consumes another component's record or digest.

## Canonical v1 flow

1. RExecOp constructs one bounded `GovernanceRequest` for an operation, step,
   attempt, runtime instance, lease, fencing token and inventory.
2. GovEngine recomputes every complete GovEngine-owned binding and checks the
   current host-provided policy activation.
3. PolicyEngine evaluates the typed policy. GovEngine validates independent
   approval, scope-policy and capability-inventory inputs.
4. GovEngine returns one `GovernanceDecision`. Only `allowed` carries a
   short-lived authorization contract.
5. The host signs the decision. RExecOp verifies signature, digest, expiry and
   runtime bindings, atomically claims the decision and nonce, and issues its
   immutable runtime permit.
6. RExecOp rechecks the permit immediately before connector I/O.
7. After I/O, RExecOp reports bounded terminal facts. GovEngine checks their
   binding and decision obligations; this check cannot authorize execution.
8. RExecOp projects final lifecycle, receipt and evidence artifacts for SCLite
   verification.

See [SECURITY_INTEGRATION.md](SECURITY_INTEGRATION.md) for the fail-closed
ordering and [DIGEST_OWNERSHIP.md](DIGEST_OWNERSHIP.md) for digest semantics.

## Kernel layers

### Stable-candidate facade

`govengine.v1` contains the 40-symbol 1.0 candidate surface:

- API result/error envelopes;
- approval attestation and revocation/trust ports;
- governance request and decision;
- PolicyEngine compiler, evaluator, obligations, constraints and explanations;
- governance trace and policy/enforcement projections.

The wheel-shipped compatibility manifest freezes this set and the 15
GovEngine-owned v1 records.

### Module-scoped v1 support

Scope/capability decisions, policy activation, signed-decision helpers and
terminal-runtime-fact conformance are real v1 protocol components but remain
module-scoped in the RC. They are not implicitly added to the 1.x import
promise.

### Compatibility layer

The package retains older admission, audit, review, planning, lifecycle,
runner, OODA, orchestration, event, state-machine and runtime-shell records.
They are adapter, experimental or fixture surfaces classified in
[API_STABILITY_MATRIX.md](API_STABILITY_MATRIX.md). They do not form a second
authorization protocol and do not transfer runtime or SCLite ownership to
GovEngine.

## Dependency direction

```text
GovEngine -> sclite-core
RExecOp   -> GovEngine + sclite-core
Tecrax    -> RExecOp + GovEngine + sclite-core
```

GovEngine must remain independently importable without RExecOp, Tecrax,
Ravenclaw, carrier adapters or runtime internals. SCLite 2.0 is frozen; the v1
governance protocol does not require a new SCLite schema.

## Host ports and state

GovEngine defines interfaces for policy activation, approval revocation,
signing/verification and related stateful decisions. Production storage,
locking, retention, clock authority, trust roots and atomic runtime claim
belong to host adapters and RExecOp. In-memory and JSONL helpers are development
fixtures, not production backends.

## Security boundary

The host process is part of the trusted computing base. A compromised host can
skip GovEngine, replace inputs, ignore a decision or fabricate terminal facts.
GovEngine is not a sandbox, remote authorization service, identity provider,
secret store, network proxy, scheduler, executor or truth layer.

Machine-readable ownership is exposed by
`govengine.boundary.kernel_boundary_report()`. That legacy report and the broad
root surface remain useful for migration, but `govengine.v1` is the only 1.x
compatibility boundary.
