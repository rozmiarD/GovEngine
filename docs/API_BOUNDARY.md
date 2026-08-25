# GovEngine API boundary

The public package has two different meanings of "available": a small frozen
1.0 candidate contract and a broad pre-v1 compatibility surface. Consumers must
not treat root availability as a stability promise.

## 1.x candidate facade

`govengine.v1` exports exactly 40 names from these owners:

- `govengine.api`;
- `govengine.approvals`;
- `govengine.governance`;
- `govengine.governance_decision`;
- `govengine.governance_trace`;
- `govengine.policy`.

The exact symbols and 15 GovEngine-owned v1 records are recorded in
`govengine/v1_compatibility_manifest.json`. The manifest status is
`frozen_for_1.0`; `scripts/validate_v1_freeze.py` and
`scripts/validate_api_stability.py` reject drift.

The facade owns deterministic governance records and decisions. It does not
include runtime mechanics, SCLite bridges, fixtures or compatibility adapters.

## Module-scoped v1 records

The v1 record inventory also includes module-scoped contracts for:

- policy activation and reason-code registry;
- independent scope policy and scope decision;
- operation capability requirements, inventory binding and compatibility;
- attempt-bound governance authorization;
- `RuntimeReceiptBinding` and `ReceiptConformanceResult`.

These records are part of the protocol implemented by the RC, but their module
imports are not yet part of the capped `govengine.v1` facade.

## Root compatibility surface

The machine-checked root inventory currently contains:

- 40 `v1-candidate` exports;
- 188 adapter exports;
- 61 experimental exports;
- 19 fixture exports;
- 3 module-owned compatibility callables exposed outside `__all__`.

The exact per-module classification and migration note lives in
[API_STABILITY_MATRIX.md](API_STABILITY_MATRIX.md). Legacy admission, audit,
review, planning, lifecycle, runner, OODA, orchestration, events, state machine,
runtime shell, profile fixtures and SCLite bridge helpers remain outside the
1.x promise. Contract-proof objects are conformance artifacts and proof
fixtures, not production authority.

## Optional governed-admission versions

`govengine.typed_execution_governed_admission` is a deep-module-only adapter
family. The catalog advertises `typed_execution_governed_admission:v0.1` and
`typed_execution_governed_admission:v0.2`; neither version adds a root export
or a `govengine.v1` export.

Version v0.1 remains the exact approval-attested built-in-backend projection.
The additive v0.2 names are
`TYPED_EXECUTION_GOVERNED_ADMISSION_V02_SCHEMA_VERSION`,
`TypedExecutionGovernedAdmissionV02`,
`evaluate_typed_execution_governed_admission_v02()`,
`validate_typed_execution_governed_admission_v02()` and
`typed_execution_governed_admission_v02_digest()`.

The v0.2 evaluator accepts only a non-built-in, non-raw-shell plugin descriptor
with a nonempty exact capability declaration and `no_network` or
`local_subprocess` egress. It calls the actual frozen-v1 governance evaluator
and requires the resulting decision controls to be exact singleton matches for
that backend and egress. Request metadata is not policy authority. The record
is not decision authority or an execution permit; a host still verifies and
atomically claims the separately signed decision before I/O.

## Ownership rules

GovEngine owns:

- typed policy compilation/evaluation and policy controls;
- approval requirements and attestation validation;
- bounded governance request/decision records;
- scope and capability compatibility decisions;
- stable reason codes, redacted explanations and governance traces;
- conformance of bounded terminal runtime facts to a decision.

GovEngine consumes but does not own:

- SCLite schemas, artifact canonicalization, lifecycle/evidence integrity,
  receipts, review bundles or verification verdicts;
- RExecOp execution specifications, payload bytes, fencing tokens, runtime
  permits, lifecycle state, queues, leases, retries, connectors or I/O;
- profile domain taxonomy, intents, workflow meaning or connector semantics;
- host identity, trust roots, approval workflow, storage and clocks.

`govengine_record_digest()` is limited to GovEngine-owned records. SCLite and
RExecOp digests stay delegated or reference-only according to
[DIGEST_OWNERSHIP.md](DIGEST_OWNERSHIP.md).

## Compatibility and removal

An existing root symbol may move or disappear only after its classification,
consumer scan, migration note and compatibility policy permit it. New work must
not expand the legacy root. Supported 1.x imports use `govengine.v1`; optional
module-scoped additions require an explicit API decision and conformance
evidence.

RExecOp and Tecrax import scans run with:

```bash
python scripts/validate_api_stability.py \
  --cross-repo \
  --consumer-root /path/to/rexecop \
  --consumer-root /path/to/tecrax
```

`--cross-repo` is required for this two-consumer qualification. A bare or
`--local` invocation with consumer roots fails closed and cannot be treated as
downstream API evidence.

See [API_COMPATIBILITY.md](API_COMPATIBILITY.md) and
[DOWNSTREAM_IMPORT_MAP.md](DOWNSTREAM_IMPORT_MAP.md).

## Dependency rule

Allowed package direction is `GovEngine -> SCLite`. GovEngine must not import
RExecOp runtime internals, Tecrax/Ravenclaw domain code, Logdash, or
OpenClaw/MCP/A2A adapters.
