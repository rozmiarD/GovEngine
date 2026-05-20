# GovEngine Roadmap

GovEngine is evolving from a Ravenclaw-extracted helper package into a deterministic governed-runtime kernel. It consumes SCLite for lifecycle/proof artifacts and exposes host/profile-facing mechanisms for planning, admission, audit, approval, runner gating, supervision, and evidence review.

Current source baseline: `govengine==0.6.0`, depending on `sclite-core>=0.5.1,<0.6`.
The latest public PyPI publication remains `0.5.0` until the standard release
checklist, operator approval, and upload are completed for `0.6.0`.

## Architecture thesis

```text
LLM intent is not execution authority.
```

GovEngine exists to keep intent, permission, execution, receipt, and review as separate runtime states. A model, agent, UI, or carrier may propose an action, but execution must pass through deterministic governance boundaries:

```text
intent
  -> policy decision
  -> execution contract
  -> execution ticket
  -> trust decision
  -> runner gate
  -> execution or dry-run
  -> receipt
  -> evidence contract
  -> review bundle
```

SCLite owns the contract/proof/review artifact layer. GovEngine owns the runtime mechanics that consume those artifacts. Domain runtimes such as Ravenclaw and Tecrax own domain semantics, UX, tools, and operator workflows.

## Responsibility boundary

GovEngine owns reusable mechanics:

- event/state/control envelopes;
- reason-code and transition-decision registries;
- task and planning contracts;
- audit, policy, admission, approval, and ticket-control boundaries;
- trust/signer/verifier ports without PKI or key-store ownership;
- runner request/receipt/gate/supervisor contracts;
- OODA-style pause/abort/cooldown/replan decisions;
- deconfliction and common operational picture summaries;
- evidence qualification and review-controller contracts;
- domain-profile SDK and conformance tests.

GovEngine does **not** own:

- SCLite schemas, canonicalization, chain verification, or review-bundle CLI;
- Ravenclaw campaign semantics, finding taxonomy, Logdash, or security toolchains;
- Tecrax infrastructure UX, service inventories, change-management policy, or host credentials;
- OpenClaw/MCP/A2A carrier adapters as core;
- live subprocess execution by default;
- PKI, CA, KMS, trust-store, or key storage;
- legal authorization, organizational approval, or operator accountability.

Rule of thumb:

```text
GovEngine owns mechanics.
Profiles own meaning.
Runtimes own UX/integration.
SCLite owns proof/review artifacts.
```

## Current implemented baseline: 0.1.x

The `0.1.x` line already proves the first useful slice of the model:

- stable-ish API result/error envelopes;
- SCLite lifecycle integration seams;
- SCLite review-bundle bridge delegated to SCLite `0.5.1`;
- artifact descriptor/state/transition boundary objects;
- lifecycle transition gates;
- signing/trust policy bridge with host-provided ports;
- dry-run controlled-execution gate and default `DryRunRunner`;
- execution-ticket and receipt-bounded-evidence checks delegated to SCLite v0.3;
- OODA safety-loop decisions;
- deconfliction and artifact state index;
- public surface registry;
- optional `govengine.security_profile` helper facade for Ravenclaw-derived security helpers.

This is still pre-alpha. The next roadmap should not be a file move from Ravenclaw into GovEngine. It should be contract-first extraction: define neutral contracts, add GovEngine tests, add Ravenclaw compatibility wrappers, then thin Ravenclaw only after behavior is preserved.

## Version roadmap

### 0.2.x — Kernel boundary freeze and stable envelopes

Goal: make the kernel/profile split explicit before extracting more runtime mechanics.

Delivered in 0.2.0: `govengine.boundary` adds serializable kernel/profile/runtime/SCLite ownership contracts, a Ravenclaw profile contract, a machine-readable boundary report, domain-profile conformance checks, deterministic orchestration handoff contracts, neutral governance event envelopes, neutral run-state transitions, deterministic control decisions, and negative tests that prevent domain profiles, orchestration steps, events, run-state metadata, or control decisions from claiming GovEngine core ownership, SCLite authority, live execution authority, credentials, carrier adapters, scheduler ownership, runtime storage, command authority, or unknown consumed surfaces. The initial kernel-boundary, domain-profile contract, orchestrator-model, event-model, state-machine, and control-model docs are now present.

Planned work:

1. Add/settle architecture docs:
   - `docs/GOVENGINE_KERNEL_BOUNDARY.md` (initial doc present)
   - `docs/DOMAIN_PROFILE_CONTRACT.md` (initial doc present)
   - `docs/ORCHESTRATOR_MODEL.md` (initial doc present)
   - `docs/EVENT_MODEL.md` (initial doc present)
   - `docs/STATE_MACHINE.md` (initial doc present)
   - `docs/RUNNER_SUPERVISION.md`
2. Promote portable envelopes:
   - `KernelBoundary`
   - `DomainProfileContract`
   - `ReasonCode`
   - `TransitionDecision`
   - `PolicyDecision`
   - `TrustDecision`
   - `RunnerProfile`
   - `ExecutionPrerequisites`
3. Add compatibility notes for Ravenclaw and future Tecrax profiles.
4. Keep live execution disabled by default.

Definition of done:

- public docs explain kernel vs profile vs runtime vs SCLite;
- standalone tests cover envelope serialization and negative boundary cases;
- Ravenclaw can still consume the package without behavior drift.

### 0.3.x — Event, state, queue, scheduler, and control shell

Status: implemented in `0.3.0` as the initial `govengine.runtime_shell`
surface. The implementation adds neutral control actions, queue snapshots,
runtime snapshots, and scheduler-tick metadata while leaving persistence,
queue mutation, scheduler loops, carrier delivery, credentials, UI, and live
execution to host runtimes.

Goal: introduce a deterministic orchestration shell without making GovEngine an LLM agent loop.

Planned work:

- `GovEvent`, `EventEnvelope`, `EventStore` protocol;
- `GovState`, `GovRunState`, `StateStore` protocol;
- `GovControlAction` values: `start`, `pause`, `resume`, `stop`, `cancel`, `replan`, `degrade_to_dry_run`, `cooldown`, `retry`, `archive`;
- `WorkQueue`, `PriorityQueue`, `DelayedQueue`, `RetryQueue`, `CooldownQueue`, `ApprovalQueue`, `DeadLetterQueue`;
- `QueueSnapshot`, `RetryPolicy`, `CooldownPolicy`, `HeartbeatPolicy`;
- `SchedulerTick`, `HeartbeatMonitor`, `LeaseManager`, `StaleRunDetector`, `RecoveryPolicy`.

Definition of done:

- the orchestrator shell reacts to events/state/control actions deterministically;
- storage is protocol/interface-driven and host-provided;
- no Ravenclaw paths, Logdash assumptions, or carrier adapters enter core;
- Ravenclaw state/control files can be represented through GovEngine-compatible adapters.

### 0.4.x — Planning kernel

Goal: extract neutral planning contracts while leaving domain planning semantics in profiles.

Planned work:

- `GovTaskContract`;
- `PlanRequest`;
- `PlanCandidate`;
- `PlanIntentContract`;
- `PlanningLadder`;
- `PlanNormalizer`;
- `PlanValidator`;
- `PlannerPort`;
- deterministic `StaticPlanner` fixtures;
- optional host-provided `LLMPlannerPort` interface, not a default dependency.

Definition of done:

- Ravenclaw `RuntimeTaskContract` v2 and planner intent compatibility can route through GovEngine contracts;
- security planning stages remain in Ravenclaw profile;
- Tecrax can define infrastructure planning stages without changing the kernel.

### 0.5.x — Audit, policy, admission, and approval kernel

Status: implemented in `0.5.0` as the initial `govengine.admission` surface.
The implementation adds neutral admission decisions, policy decisions, approval
requests, and audit records while leaving profile policy meaning, approval
workflows, audit storage/retention, carrier delivery, credentials, UI, and live
execution to host runtimes.

Goal: make go/no-go decisions, escalation, and positive-control boundaries reusable.

Planned work:

- `AuditCase`, `AuditChecklist`, `AuditFinding`, `AuditDecision`;
- `ApprovalRequest` and approval/ticket-controller interfaces;
- `PolicyDecision`, `PDP`, `PEP` boundaries;
- `AdmissionContext`, `AdmissionDecision`, `AdmissionController`;
- `SignalGate`, `DepthGate`, `BudgetGate`, `CooldownGate`, `ResourceHealthGate`.

Definition of done:

- hosts can ask GovEngine whether a task may proceed, must dry-run, requires approval/replan, or is blocked;
- profile-specific policy remains outside neutral core;
- deterministic negative tests cover raw-intent execution, missing ticket, policy drift, budget exceedance, and cooldown behavior.

### 0.6.x — Execution supervisor and runner kernel

Status: implemented in `0.6.0` as the initial
`govengine.execution.supervision` surface. The implementation adds neutral
runner leases, supervision plans, supervision decisions, and request/receipt
validators while leaving concrete runner behavior, lease persistence, operator
authorization, artifact storage, carrier delivery, credentials, and live backend
ownership to host runtimes.

Goal: provide the reusable supervision layer for bounded execution while preserving dry-run as default.

Planned work:

- `RunnerGate`;
- `RunnerRequest`;
- `RunnerReceipt`;
- `RunnerLease`;
- `ExecutionSupervisor`;
- `DryRunRunner` as default;
- optional `LocalSubprocessRunner`, disabled by default and policy-enabled only.

Required guardrails:

- no execution from raw intent;
- valid execution contract required;
- valid policy decision required;
- approved scoped ticket required;
- trust decision required;
- runner profile required;
- timeout/env/cwd/stdin policy required for local subprocess backends;
- receipt required for every attempted step;
- live backend must be negative-tested as blocked by default.

Definition of done:

- Ravenclaw approved execution can pass through GovEngine runner gate/supervisor;
- legacy direct execution remains marked as compatibility/dev path until retired;
- no scanner/campaign execution semantics move into GovEngine.

### 0.7.x — Evidence and review kernel

Goal: make post-execution qualification reusable while SCLite remains the proof/review authority.

Planned work:

- `EvidenceRequirement`;
- `EvidenceClaim`;
- `EvidenceQualification`;
- `ConfirmationPolicy`;
- `FalsePositiveGuard`;
- `ControlComparison`;
- `ReproductionRequirement`;
- `ReviewResult`;
- `AnalysisContract`;
- `EvidenceReviewController`;
- SCLite review-bundle bridge. The `0.1.7` source line now includes the first thin review-bundle bridge delegated to SCLite `0.5.1`.

Definition of done:

- Ravenclaw finding/evidence qualification can use GovEngine review contracts;
- SCLite still validates lifecycle/proof boundaries and review bundles;
- overclaims are rejected when receipt bounds do not support evidence claims.

### 0.8.x — Domain Profile SDK

Goal: prove portability across more than one domain without turning GovEngine into a domain monolith.

Planned work:

- `DomainProfile` metadata and conformance contracts;
- resource-type registry;
- task-family registry;
- planning-stage registry;
- capability and runner-profile declarations;
- policy/evidence/audit checklist hooks;
- profile conformance tests;
- `SecurityResearchProfile` extracted/normalized from Ravenclaw-facing helpers;
- `TecraxProfile` skeleton for governed infrastructure operations.

Definition of done:

- Ravenclaw can identify as a security-research runtime/profile;
- Tecrax can exist as a second profile skeleton without live infrastructure authority;
- profile conformance proves generic kernel portability.

### 0.9.x — Multi-runtime integration proofs

Goal: demonstrate that the same kernel supports multiple domain runtimes without expanding authority.

Planned work:

- Ravenclaw profile integration proof;
- Tecrax dry-run infrastructure-change proof;
- profile-to-SCLite review-bundle examples;
- readiness packet for first carrier adapter, likely OpenClaw, if boundaries are stable.

Definition of done:

- at least two public-safe domain proofs use the same GovEngine/SCLite lifecycle;
- carrier adapter work remains gated and does not bypass GovEngine.

## Domain profiles

### Ravenclaw Security Research Profile

Ravenclaw supplies security meaning:

- resource types: `host`, `url`, `endpoint`, `web_app`;
- task families: `recon`, `authz`, `idor`, `workflow`, `content_discovery`, `tls_assessment`;
- planning stages: `discovery`, `validation`, `control_boundary_confirmation`, `state_transition_confirmation`, `bounded_exploit_proof`, `report_artifact_capture`;
- security-specific audit checklists, policy rules, tools, and evidence rules.

### Tecrax Infrastructure Operations Profile

Tecrax is the reserved name for the future governed infrastructure-operations runtime/profile. Avoid inherited working-name/product framing until public language is deliberately chosen.

Tecrax should supply infrastructure meaning:

- resource types: `server`, `service`, `container`, `firewall`, `switch`, `vm`, `backup_job`;
- task families: `inspect`, `diagnose`, `propose_change`, `dry_run_change`, `apply_change`, `verify`, `rollback`;
- planning stages: `observe`, `diagnose`, `plan_change`, `validate_dry_run`, `approve`, `execute`, `verify`, `rollback_if_needed`.

Initial Tecrax work should be dry-run/local-fixture only until GovEngine runner supervision and SCLite review bundles are mature.

## Carrier adapters

Carrier adapters remain deferred. OpenClaw should be evaluated first because it is the natural operator/carrier environment. MCP should come later. A2A should stay last and example-first.

Correct model:

```text
carrier or harness proposes
  -> domain runtime maps to workflow/profile semantics
  -> GovEngine gates and supervises
  -> SCLite artifacts bind lifecycle and review
  -> operator approves where required
  -> runner performs bounded step or dry-run
  -> receipt/evidence returns to carrier
```

Incorrect model:

```text
agent says execute -> runner executes
```

## Refactor rule

Do not move files mechanically from Ravenclaw into GovEngine. For each extraction:

1. identify the reusable concept;
2. name it neutrally;
3. define the GovEngine contract;
4. add GovEngine tests;
5. add Ravenclaw compatibility wrappers/adapters;
6. route Ravenclaw seam tests through the new contract;
7. remove or thin old code only after parity is proven.

## Research documentation backlog

Later, after the boundaries are implemented enough to support claims, add:

- `docs/RESEARCH_THESIS.md`;
- `docs/RESEARCH_EVALUATION_MATRIX.md`;
- `docs/BASELINE_COMPARISON.md`;
- `examples/research-scenarios/`.

Candidate scenarios:

- raw intent rejected;
- ticket digest drift rejected;
- policy changed after ticket;
- receipt overclaim rejected;
- evidence overclaim rejected;
- signature digest mismatch rejected;
- OODA scope drift abort;
- live runner disabled by default;
- common operational picture shows blocked state.
