# GovEngine API Boundary

GovEngine owns reusable governed-execution services. Its public surface should stay carrier-neutral and SCLite-aware.

The top-level export stability classification lives in [API_STABILITY_MATRIX.md](API_STABILITY_MATRIX.md). It covers the current `govengine.__all__` surface and is guarded by tests so new public exports require an explicit stability decision.

`govengine.surfaces.public_surface_index()` is the tested machine-readable map of the current alpha public surface set. It contains the neutral artifact-governance core, planning contracts, admission/policy contracts, evidence review, domain-profile SDK, runtime contract proofs, and controlled-execution core. The published `0.12.0-alpha` line removes the prior Ravenclaw-derived optional security facade; domain security behavior belongs in the host runtime.
`govengine.boundary.kernel_boundary_report()` is the tested machine-readable 0.2 boundary report. It combines the kernel/profile/runtime/SCLite ownership contract, known domain-profile contracts such as Ravenclaw, and the current public surface index.
`govengine.boundary.validate_domain_profile_conformance()` checks that a domain profile does not claim forbidden ownership and consumes only known GovEngine/SCLite surfaces.
`govengine.orchestration.validate_orchestration_step()` checks deterministic orchestration handoff records without granting agent-loop, scheduler, UI, carrier, credential, or live-execution authority.
`govengine.events.validate_event_envelope()` checks transport-neutral governance event metadata without accepting raw prompts, credentials, live commands, carrier payloads, or scheduling claims.
`govengine.state_machine.validate_state_transition()` checks neutral run-state transitions without accepting runtime storage, scheduler, credential, command, or live-execution claims.
`govengine.replay.record_guard_replay()` checks and records SCLite Kernel Guard root tags through a host-supplied state store without verifying HMAC tags, storing keys, or replacing SCLite guard verification. `govengine.replay.verify_guard_and_record_replay()` is the high-level runtime adapter: it calls SCLite's guarded-strict verification profile, then records replay freshness and returns one runtime decision.
`govengine.control.validate_control_decision()` checks deterministic between-step control decisions and delegates legal state changes to the state machine without accepting raw prompts, commands, schedulers, runtime storage, delivery, or live-execution claims.
`govengine.runtime_shell.validate_runtime_snapshot()` checks host-provided control actions, queue snapshots, runtime snapshots, and scheduler-tick metadata without accepting raw prompts, commands, storage, schedules, credentials, carrier payloads, or live-execution claims.
`govengine.planning.validate_task_contract()` and `validate_plan_intent_contract()` check neutral planner-to-runtime handoff shapes without accepting raw targets, raw prompts, commands, storage, schedules, credentials, carrier payloads, or live-execution claims.
`govengine.admission.validate_admission_decision()`, `validate_policy_decision()`, `validate_approval_request()`, `validate_audit_record()`, and `validate_runtime_admission_result()` check neutral runtime gate records without accepting raw targets, raw prompts, commands, storage, schedules, credentials, carrier payloads, or live-execution claims.
`govengine.execution.supervision.validate_supervised_runner_request()` and `validate_runner_receipt_for_request()` check approved-spec runner supervision and receipt boundaries without accepting raw intent or granting live backend ownership.
`govengine.review.qualify_evidence_claim()` checks neutral evidence claims against receipt bounds without accepting raw targets, raw output, commands, credentials, storage, carrier payloads, or live-execution claims.
`govengine.profiles.validate_profile_conformance()` checks contract-only domain profile declarations without granting domain taxonomy, carrier adapter, credential, product UX, or live-execution ownership.
`govengine.contract_proofs.validate_runtime_contract_proof()` checks public-safe multi-profile contract proof fixtures without granting adapter, credential, scheduler, storage, live-execution, or new OODA ownership.

Host-owned lifecycle projection is outside GovEngine. Ravenclaw maps its
runtime payloads into SCLite artifacts and owns its public proof projection;
GovEngine retains only neutral SCLite descriptor/state/transition and
review-bundle verdict mapping while SCLite owns lifecycle/review verification.

## Public surface groups

### Artifact-governance core

Neutral core modules:

- `govengine.boundary`
- `govengine.core`
- `govengine.sclite_contracts`
- `govengine.lifecycle`
- `govengine.signing`
- `govengine.deconfliction`
- `govengine.state_index`
- `govengine.state_store`
- `govengine.replay`

Claim: portable kernel/profile boundary contracts, artifact descriptor/state/transition, lifecycle and review-bundle bridges, signing/trust decision, guarded-root replay checks, guarded-bundle runtime decision assembly, deconfliction, and state-index helpers. Non-claims: SCLite schema/canonicalization/review ownership, SCLite Kernel Guard HMAC verification ownership, PKI/key-store ownership, raw artifact storage ownership, workflow scheduler ownership.

### Planning-contracts core

Neutral planning-contract modules:

- `govengine.planning`

Claim: neutral task-contract, plan-intent, and planner-port validators that hosts can use for planner-to-runtime handoff review. Non-claims: planner implementation ownership, Ravenclaw security planning semantics ownership, raw target/prompt ownership, queue/scheduler/storage ownership, protocol adapter ownership, command authority, or live execution.

### Admission-policy core

Neutral admission-policy modules:

- `govengine.admission`

Claim: neutral admission-decision, runtime-admission, policy-decision, approval-request, and audit-record validators that hosts can use for runtime gate review. Non-claims: domain policy meaning ownership, operator approval workflow ownership, audit storage or retention ownership, raw target/prompt ownership, queue/scheduler/storage ownership, protocol adapter ownership, command authority, or live execution.

### Evidence-review core

Neutral evidence-review modules:

- `govengine.review`

Claim: neutral evidence-requirement, evidence-claim, evidence-qualification, and review-result validators that hosts can use for receipt-bounded post-execution review. Non-claims: SCLite review-bundle verdict ownership, Ravenclaw finding taxonomy ownership, raw evidence storage ownership, raw target/output ownership, protocol adapter ownership, command authority, or live execution.

### Domain-profile SDK

Contract-only domain-profile modules:

- `govengine.profiles`

Claim: minimal domain-profile declarations, registry shapes, Ravenclaw/Tecrax fixture profiles, and conformance reports that hosts can use to bind domain meaning around GovEngine. Non-claims: domain taxonomy ownership, Ravenclaw finding taxonomy ownership, Tecrax infrastructure semantics ownership, product UX, credential/PKI/KMS/key-store ownership, protocol adapter ownership, default live subprocess execution, command authority, or live execution.

### Runtime contract proofs

Neutral runtime-proof modules:

- `govengine.contract_proofs`

Claim: public-safe Ravenclaw and Tecrax proof fixtures plus neutral governance vocabulary over existing planning, runner supervision, runtime snapshot, review-result, and artifact change-order contracts. Non-claims: carrier adapter ownership, domain runtime ownership, scheduler/queue/storage ownership, credential/PKI/KMS/key-store ownership, default live subprocess execution, command authority, live execution, or a new OODA surface.

### Controlled-execution core

Neutral controlled-execution modules:

- `govengine.execution.*`
- `govengine.scope_ports`
- `govengine.contracts.execution`
- `govengine.ooda`
- `govengine.orchestration`
- `govengine.events`
- `govengine.control`
- `govengine.runtime_shell`

Claim: approved-spec, execution-ticket, command-shape, runner receipt, runner supervision, OODA, orchestration handoff, event envelope, control-decision, runtime-shell projection, and dry-run-only execution-gate helpers. Non-claims: raw-intent execution, default live subprocess execution, live backend ownership, scanner/campaign execution ownership, protocol adapter ownership, runtime storage ownership, or scheduler ownership.

## Owns

GovEngine owns:

- `govengine.boundary` — serializable kernel/profile/runtime/SCLite ownership contracts and profile-boundary validation helpers.
- `govengine.core` — portable artifact descriptors/envelopes/state, governance context, transition decisions, reason codes, and execution-prerequisite guardrails.
- `govengine.deconfliction` / `govengine.state_index` — digest/state conflict, change-order, and lightweight artifact state summary helpers.
- `govengine.state_machine` — neutral run-state and transition validation without persistence, queue, scheduler, credential, or live-execution authority.
- `govengine.control` — deterministic between-step control decisions that can apply validated in-memory state transitions without storage, scheduler, delivery, command, or live-execution authority.
- `govengine.runtime_shell` — neutral host control actions, queue snapshots, runtime snapshots, and scheduler-tick metadata without storage, scheduler, delivery, command, credential, carrier, or live-execution authority.
- `govengine.planning` — neutral task-contract, plan-intent, and planner-port validators without planner implementation, raw target/prompt, queue/scheduler/storage, command, credential, adapter, or live-execution authority.
- `govengine.admission` — neutral admission-decision, runtime-admission, policy-decision, approval-request, and audit-record validators without domain policy meaning, approval workflow, audit storage, command, credential, adapter, or live-execution authority.
- `govengine.review` — neutral evidence-requirement, evidence-claim, evidence-qualification, and review-result validators without SCLite review verdict ownership, Ravenclaw finding taxonomy ownership, raw evidence storage, command, credential, adapter, or live-execution authority.
- `govengine.profiles` — contract-only domain profile declarations, registries, fixture profiles, and conformance reports without domain taxonomy, product UX, credential, adapter, or live-execution ownership.
- `govengine.contract_proofs` — public-safe runtime contract proof fixtures and neutral governance vocabulary over existing contracts without adapter, credential, scheduler, storage, live-execution, domain runtime, or new OODA ownership.
- `govengine.lifecycle` — lightweight artifact lifecycle transition policy/gate/controller helpers.
- `govengine.signing` — signature envelopes, signing/trust policy objects, host-provided signer/verifier ports, deterministic demo signer/verifier fixture ports, and signature transition decisions without PKI/key ownership.
- `govengine.contracts.execution` — execution-contract shaping and redaction helpers.
- `govengine.execution.*` — approved-spec, ticket, command-shape, dry-run helpers, and controlled execution gates that keep live backends disabled by default.
- `govengine.orchestration` — deterministic orchestration handoff contracts without scheduler, UI, adapter, credential, or live-execution authority.
- `govengine.events` — transport-neutral governance event metadata and envelope validation without scheduler, carrier, credential, or command payload authority.
- `govengine.scope_ports` — neutral scope-port protocol and host extraction helper used by controlled-execution contracts.
- `govengine.state_store` — neutral JSON state helper primitives.
- `govengine.replay` — guarded SCLite root replay records and fresh/replayed decisions over host-supplied JSON state without HMAC verification, key storage, runtime storage ownership, or replay policy beyond the supplied store.
- `govengine.sclite_*` — explicit integration seams with SCLite, including descriptor/status/transition mapping that delegates lifecycle verification and review-bundle verdicts to SCLite.

## Consumes

GovEngine consumes:

- SCLite schemas, lifecycle helpers, review-bundle helpers, and verification surfaces;
- host-provided filesystem/context paths;
- host-provided inputs required by neutral runtime ports and contracts.

## Does not own

GovEngine must not own Ravenclaw-specific runtime/application concerns:

- Logdash UI/API routes;
- Ravenclaw public snapshot assembly/publishing scripts;
- OpenClaw session wiring;
- BRAIN/AUDITOR/ANALYSIS/LIGHT prompts/personas;
- LLM provider configuration;
- PKI, CA, KMS, key storage, trust-store ownership, or production identity proof;
- protocol adapters such as MCP/A2A;
- live target campaign orchestration UX;
- public demo branding/docs owned by Ravenclaw.

## Demo signing fixture rule

`DemoDigestSigner`, `DemoDigestVerifier`, and `demo_sign_and_verify` are test/reviewer helpers. They create deterministic digest-bound demo signatures so hosts can exercise the `SignerPort`/`VerifierPort` contract and inspect trust decisions without bringing real keys into GovEngine. They are not cryptographic identity proof, not a CA/KMS/key-store, and not a replacement for a host-owned production verifier. Hosts that need real signatures must provide their own signer/verifier ports and trust policy.

## Execution backend rule

Live subprocess execution is intentionally absent from this scaffold and remains disabled by default for future live backends.

GovEngine must never execute directly from raw intent. Execution requires all of the following boundary inputs:

1. prepared execution contract;
2. valid policy decision;
3. approved execution ticket;
4. valid signature/trust decision;
5. allowed runner profile.

The governed-runtime MVP exposes those inputs through the canonical runtime
admission contract described in
[RUNTIME_ADMISSION.md](RUNTIME_ADMISSION.md). `RuntimeAdmissionResult` carries
bounded blockers, next actions, and artifact references.
`compose_runtime_admission_result()` populates it from bounded gate evidence for
hosts and reviewers; the record does not grant live execution authority by
itself.

Before any execution backend moves into GovEngine:

1. lifecycle gates and signing/trust gates must be explicit;
2. keep dry-run behavior as the default runner path;
3. keep Ravenclaw's subprocess runner as the first concrete host adapter;
4. validate dry-run and scope enforcement parity;
5. add negative tests for malformed ticket, stale signature/trust, profile mismatch, live-backend-disabled, failure/redaction/artifact handling;
6. require operator review before making GovEngine own live execution mechanics.

## Dependency rule

Allowed core dependency direction:

```text
GovEngine -> SCLite
```

Forbidden dependencies:

```text
GovEngine -> Ravenclaw engine/*
GovEngine -> Logdash
GovEngine -> OpenClaw/MCP/A2A adapters
```

Ravenclaw may import GovEngine. GovEngine must remain independently importable without Ravenclaw's `engine/` path.
