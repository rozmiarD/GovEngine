# GovEngine Architecture

GovEngine is a deterministic governed-runtime kernel in alpha form. It is designed to sit between a host/domain runtime and the SCLite contract lifecycle.

```text
host runtime -> GovEngine -> SCLite
```

RExecOp is the current domain-neutral host runtime and Tecrax is its infrastructure-operations profile. Ravenclaw is a legacy consumer outside the current RExecOp/Tecrax roadmap. Other host runtimes may consume the same contracts, but GovEngine must not become a carrier-specific adapter or a domain product shell.

## Governed-runtime MVP chain

Operator steps: [GOVERNED_RUNTIME_MVP_RUNBOOK.md](GOVERNED_RUNTIME_MVP_RUNBOOK.md).
Integration order and non-claims: [SECURITY_INTEGRATION.md](SECURITY_INTEGRATION.md).
Contract reference: [RUNTIME_ADMISSION.md](RUNTIME_ADMISSION.md),
[GOVERNANCE_REQUEST.md](GOVERNANCE_REQUEST.md),
[GOVERNANCE_DECISION.md](GOVERNANCE_DECISION.md),
[RECEIPT_BINDING.md](RECEIPT_BINDING.md), [EVIDENCE_REVIEW.md](EVIDENCE_REVIEW.md).

```text
intent -> policy/admission -> SCLite ticket/guard -> trust -> replay freshness
  -> runner profile -> receipt obligation -> RuntimeAdmissionResult
  -> GovRunnerRequest -> GovRunnerReceipt
  -> validate_runner_receipt_binding() -> validate_evidence_review_chain()
```

`compose_runtime_admission_result()` composes host-supplied gate summaries; it
does not verify SCLite artifacts, record replay state, or execute work. See the
linked docs for field-level contracts and operator procedures.

G2-A adds `GovernanceRequest v1` and `ApprovalAttestation v1` as the canonical
input candidates for the replacement flow. They bind one runtime-owned attempt
to GovEngine policy/scope/approval inputs. `RuntimeAdmissionResult` remains a
legacy adapter instead of being expanded into the new protocol.

G2-B adds independent `ScopePolicyBinding`,
`OperationCapabilityRequirements` and `CapabilityInventoryBinding` inputs plus
deterministic scope/compatibility decisions. They are bound into
`GovernanceRequest`; RExecOp still owns runtime inventory collection and all
pre-I/O network enforcement.

G2-C adds the canonical `GovernanceDecision v1` evaluator. It reuses the
PolicyEngine enforcement plan and governance trace, validates current policy
activation and independent approval signature verification, then composes
policy, scope and capability results. Only `allowed` embeds a short-lived
attempt-bound authorization. RExecOp owns atomic claim, runtime permits and
I/O; before claim it must verify decision authenticity through the existing
signed GovEngine record boundary. SCLite is unchanged.

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

Module: `govengine.boundary`. Serializable kernel/profile/runtime/SCLite ownership
split and domain-profile conformance. See
[GOVENGINE_KERNEL_BOUNDARY.md](GOVENGINE_KERNEL_BOUNDARY.md).

### 1. Admission and review contract layer

Modules: `govengine.admission`, `govengine.approvals`, `govengine.governance`,
`govengine.governance_decision`, `govengine.policy`, `govengine.review`.

Validates admission/policy/audit records, evaluates declarative policy packs,
validates the canonical governance request and independently bound approval,
produces the canonical fail-closed governance decision,
composes legacy `RuntimeAdmissionResult`, and checks receipt-bounded evidence
chains. Policy meaning and evidence taxonomy stay host-owned.

See [RUNTIME_ADMISSION.md](RUNTIME_ADMISSION.md), [POLICY_ENGINE.md](POLICY_ENGINE.md),
[GOVERNANCE_DECISION.md](GOVERNANCE_DECISION.md),
[ADMISSION_POLICY.md](ADMISSION_POLICY.md), and [EVIDENCE_REVIEW.md](EVIDENCE_REVIEW.md).

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

Modules: `govengine.planning`, `govengine.profiles`, `govengine.contract_proofs`.
Neutral planner handoff, profile declarations, and public-safe proof fixtures.
Planning objects and boundaries are documented under **Planning-contracts core**
in [API_BOUNDARY.md](API_BOUNDARY.md#planning-contracts-core). Profile SDK:
[DOMAIN_PROFILE_CONTRACT.md](DOMAIN_PROFILE_CONTRACT.md).

### 7. OODA, orchestration, and runtime-shell control layer

Modules: `govengine.ooda`, `govengine.orchestration`, `govengine.events`,
`govengine.control`, `govengine.runtime_shell`. Deterministic control and
projection records without schedulers, storage, or live execution. OODA receipt
bounds: [EVIDENCE_REVIEW.md](EVIDENCE_REVIEW.md#ooda-decisions-in-receipts-and-evidence).
Model docs: [ORCHESTRATOR_MODEL.md](ORCHESTRATOR_MODEL.md), [EVENT_MODEL.md](EVENT_MODEL.md),
[STATE_MACHINE.md](STATE_MACHINE.md), [CONTROL_MODEL.md](CONTROL_MODEL.md),
[RUNTIME_SHELL.md](RUNTIME_SHELL.md).

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
a kernel in alpha form. The published `govengine==0.16.0` line
includes the PolicyEngine MVP, the governed-runtime MVP from `0.14.0`, and
roadmap-hardening surfaces described above. Newer work should return to
`Unreleased` until the next alpha release.

Those alpha surfaces — canonical runtime admission, host-provided trust ports,
receipt/evidence binding, audit/replay ports, inspect-only admission review,
read-only operator verifiers, and runner safety documentation — are not
production execution claims. GovEngine is not a complete orchestrator,
scheduler, supervisor stack, subprocess runner, or product shell and does not
claim production execution safety on its own.
