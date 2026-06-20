# GovEngine Architecture

GovEngine is a deterministic governed-runtime kernel in alpha form. It is designed to sit between a host/domain runtime and the SCLite contract lifecycle.

```text
host runtime -> GovEngine -> SCLite
```

For the current extraction, the host/domain runtime is Ravenclaw. A future infrastructure-operations runtime/profile is reserved as Tecrax. Later carriers may include OpenClaw, MCP/A2A-style transports, or other local harnesses, but GovEngine should not become a carrier-specific adapter or a domain product shell.

## Governed-runtime MVP chain

The current MVP path is documented for operators in
[GOVERNED_RUNTIME_MVP_RUNBOOK.md](GOVERNED_RUNTIME_MVP_RUNBOOK.md). The full
integration order and non-claims are in
[SECURITY_INTEGRATION.md](SECURITY_INTEGRATION.md). The short form is:

```text
intent
  -> policy/admission
  -> SCLite ticket or guarded verification reference
  -> trust decision
  -> replay freshness
  -> runner profile
  -> receipt obligation
  -> RuntimeAdmissionResult
  -> GovRunnerRequest
  -> GovRunnerReceipt
  -> validate_runner_receipt_binding()
  -> validate_evidence_review_chain()
  -> bounded audit / review references
```

`compose_runtime_admission_result()` composes host-supplied gate summaries into
`RuntimeAdmissionResult`. It does not validate SCLite tickets, verify
signatures, record replay state, or execute live work. Runtime admission
composition requires an allowed runner profile and a receipt obligation;
concrete runner receipts are validated later with
`validate_runner_receipt_binding()`. Guarded/replay blockers apply during
composition only when the host sets `runtime_consumable=True`.

GovEngine owns the neutral mechanics that compose and validate this chain. It
does not own domain policy meaning, operator approval workflow, production
identity or keys, raw evidence storage, SCLite proof authority, or live backend
execution.

## Public surface map

The tested public surface registry in `govengine.surfaces` currently exposes
seven neutral surfaces. Additional alpha exports such as `govengine.api`,
`govengine.context`, `govengine.roles`, and `govengine.execution_backend` exist
outside that registry. See also [API_BOUNDARY.md](API_BOUNDARY.md) and
[API_STABILITY_MATRIX.md](API_STABILITY_MATRIX.md).

| Surface | Primary modules |
| --- | --- |
| `artifact_governance_core` | `govengine.core`, `govengine.boundary`, `govengine.sclite_contracts`, `govengine.lifecycle`, `govengine.signing`, `govengine.replay`, `govengine.deconfliction`, `govengine.state_index`, `govengine.state_machine`, `govengine.state_store` |
| `planning_contracts_core` | `govengine.planning` |
| `admission_policy_core` | `govengine.admission`, `govengine.policy` (+ compiler/model/runtime) |
| `evidence_review_core` | `govengine.review` |
| `domain_profile_sdk` | `govengine.profiles` |
| `runtime_contract_proofs` | `govengine.contract_proofs` |
| `controlled_execution_core` | `govengine.execution.*`, `govengine.ooda`, `govengine.orchestration`, `govengine.events`, `govengine.control`, `govengine.runtime_shell`, `govengine.scope_ports`, `govengine.contracts.execution` |

## Layers

### 0. Kernel/profile boundary layer

Module:

- `govengine.boundary`

Purpose:

- make the kernel/profile/runtime/SCLite ownership split serializable;
- let hosts declare domain-profile ownership without claiming GovEngine core, SCLite authority, live execution authority, credentials, or carrier adapter ownership;
- provide a tested Ravenclaw profile contract as the current host-profile example.

### 1. Admission and review contract layer

Modules:

- `govengine.admission`
- `govengine.policy` (compiler, model, runtime)
- `govengine.review`

Purpose:

- validate neutral admission, policy-decision, approval, audit, evidence, and
  review records;
- evaluate declarative policy packs through `PolicyEngine` and project
  `PolicyVerdict` into `GovPolicyDecision` via
  `policy_verdict_to_gov_policy_decision()`;
- compose and validate `RuntimeAdmissionResult` through
  `compose_runtime_admission_result()`, `validate_runtime_admission_result()`,
  `validate_runtime_admission_proof_inputs()`, and bounded public summaries;
- expose `AuditLedgerPort` and a development-only `JsonlAuditLedgerAdapter` for
  hash-chained audit append/read/verify without production database ownership;
- validate receipt-bounded evidence and review reference chains through
  `validate_evidence_review_chain()`;
- keep security-domain policy meaning and evidence taxonomy in the host runtime.

`validate_runtime_admission_result()` checks record shape and consistency; it
does not by itself enforce receipt obligation on arbitrary stored records the way
`compose_runtime_admission_result()` does.

See [RUNTIME_ADMISSION.md](RUNTIME_ADMISSION.md), [POLICY_ENGINE.md](POLICY_ENGINE.md),
and [EVIDENCE_REVIEW.md](EVIDENCE_REVIEW.md).

### 2. Contract layer

Modules:

- `govengine.contracts.execution`
- `govengine.sclite_contracts`

Purpose:

- shape execution contracts and approval payloads;
- redact prepared execution specs for auditor/reviewer surfaces;
- map SCLite lifecycle/review results into neutral GovEngine state and transition decisions.

Lifecycle artifact projection from a host runtime payload is host-owned;
Ravenclaw implements its projection outside this kernel.

See [SCLITE_INTEGRATION.md](SCLITE_INTEGRATION.md).

### 3. Replay, signing, and trust bridge layer

Modules:

- `govengine.replay`
- `govengine.signing`

Purpose:

- record guarded SCLite root freshness through host-supplied JSON state,
  `ReplayClaimStore`, or development-only in-memory adapters;
- compose SCLite guarded-strict verification with replay recording through
  `verify_guard_and_record_replay()`;
- provide GovEngine-owned record digests, signed-record envelopes, and
  host-provided signer/verifier/trust ports, plus deterministic demo ports for
  fixtures only.

GovEngine does not own SCLite Kernel Guard HMAC verification, PKI, KMS, key
storage, or production replay persistence.

### 4. Execution helper / runner protocol layer

Modules:

- `govengine.api`
- `govengine.execution.approved_spec`
- `govengine.execution.ticket_gate`
- `govengine.execution.command_shape`
- `govengine.execution.runner`
- `govengine.execution.runner_protocol`
- `govengine.execution.gate`
- `govengine.execution.supervision`
- `govengine.execution_backend`

Purpose:

- expose stable API result/error envelopes for hard boundaries;
- validate approved execution specs;
- check execution-ticket presence/shape through host-facing ticket-gate helpers;
- normalize command shape and target observations;
- assemble dry-run result envelopes;
- define the carrier-neutral runner request/receipt protocol a host adapter can honor;
- gate controlled execution through `ExecutionGate` and default `DryRunRunner`;
- validate supervised runner requests, receipts, and receipt bindings through
  `validate_runner_receipt_binding()`;
- evaluate optional local subprocess runner readiness through
  `LocalSubprocessRunnerReadiness` while keeping the local runner at
  `not_applicable` by default.

`govengine.execution_backend` is a port-only contract with no shipped live
backend. Important: live subprocess execution is not owned by GovEngine. The
runner protocol prepares and records bounded execution shape; host adapters
still own concrete IO/subprocess behavior. See
[RUNNER_SUPERVISION.md](RUNNER_SUPERVISION.md) and
[LOCAL_SUBPROCESS_RUNNER_DECISION.md](LOCAL_SUBPROCESS_RUNNER_DECISION.md).

### 5. Host context and scope-port layer

Modules:

- `govengine.context`
- `govengine.scope_ports`
- `govengine.state_store`

Purpose:

- let a host runtime provide paths, neutral scope-port behavior, and state surfaces explicitly;
- retain `host_compat_context()` for package-in-place context injection while
  hosts migrate independently of retired security-domain helpers;
- avoid hard dependencies on Ravenclaw internals;
- support standalone import and package testing.

### 6. Planning, profile, and proof contract layer

Modules:

- `govengine.planning`
- `govengine.profiles`
- `govengine.contract_proofs`

Purpose:

- validate neutral planner-to-runtime handoff contracts without owning a planner
  implementation;
- declare contract-only domain profiles and conformance reports for Ravenclaw and
  Tecrax fixture paths;
- provide public-safe multi-profile proof fixtures over existing GovEngine
  contracts.

These surfaces are metadata and validation only. They do not add scheduling,
carrier adapters, credentials, or live execution authority.

### 7. OODA, orchestration, and runtime-shell control layer

Modules:

- `govengine.ooda`
- `govengine.orchestration`
- `govengine.events`
- `govengine.control`
- `govengine.runtime_shell`

Purpose:

- observe normalized execution telemetry and operator-control events;
- orient observations against approved specs, execution tickets, policy decisions, scope, budgets, and host state;
- decide whether the next step should continue, pause, abort, cooldown, degrade to dry-run, or require owner review;
- expose deterministic orchestration handoff records, governance event envelopes, run-state transitions, between-step control decisions, and host runtime-shell projections without owning schedulers, queues, storage, credentials, or live execution.

GovEngine provides reusable deterministic contracts here. Host runtimes such as
Ravenclaw still own wiring those contracts into live control loops.

## Operator surfaces

GovEngine also ships read-only operator helpers that validate bounded records
without executing work:

- `scripts/inspect_runtime_admission.py` — inspect `RuntimeAdmissionResult`
  records;
- `scripts/verify_runner_receipt_binding.py` — verify admission/ticket/request/
  receipt binding references;
- `scripts/verify_audit_ledger.py` — verify development JSONL audit-ledger
  chains.

These scripts are inspection and verification tools, not execution backends.

## Boundary rule

GovEngine can consume SCLite and host-supplied context. It should not import Ravenclaw `engine/*`, Logdash, OpenClaw session wiring, or protocol adapters.

```text
allowed:   Ravenclaw -> GovEngine -> SCLite
forbidden: GovEngine -> Ravenclaw engine/*
forbidden: GovEngine -> Logdash/OpenClaw/MCP/A2A adapters
```

## Current maturity

The package currently covers dry-run-safe helpers and neutral contract gates as
a kernel in alpha form. The published `govengine==0.14.0` (`0.14.0`) line
includes the governed-runtime MVP and roadmap-hardening surfaces described
above. Newer work should return to `Unreleased` until the next alpha release.

Those alpha surfaces — canonical runtime admission, host-provided trust ports,
receipt/evidence binding, audit/replay ports, inspect-only admission review,
read-only operator verifiers, and runner safety documentation — are not
production execution claims. GovEngine is not a complete orchestrator,
scheduler, supervisor stack, subprocess runner, or product shell and does not
claim production execution safety on its own.
