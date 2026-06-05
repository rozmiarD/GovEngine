# GovEngine Public Status

GovEngine is an **alpha governed-runtime kernel package** extracted from Ravenclaw in contract-first stages.

## Current maturity

- Package import: working.
- Standalone tests: present.
- GitHub Actions: pytest on supported Python versions.
- Source/package version: `0.12.2a0`.
- Release label: `0.12.2-alpha`.
- PyPI package: `govengine==0.12.1a1` is the published current alpha package.
- SCLite integration: present through helper seams via source dependency `sclite-core>=1.0.1,<1.1`.
- Kernel/profile boundary: initial serializable `govengine.boundary` contracts, machine-readable boundary report, domain-profile conformance checks, and public boundary docs for kernel, profile, runtime, and SCLite ownership separation.
- Orchestrator model: initial `govengine.orchestration` handoff contracts define deterministic control metadata without scheduler, UI, adapter, credential, or live-execution authority.
- Event model: initial `govengine.events` envelopes define transport-neutral governance metadata without raw prompts, credentials, live commands, carrier payloads, or scheduling claims.
- State machine: initial `govengine.state_machine` contracts define neutral run-state transitions without persistence, queue, scheduler, credential, command, or live-execution authority.
- Control model: initial `govengine.control` decisions define deterministic between-step control and validated state-machine delegation without storage, scheduler, delivery, command, credential, or live-execution authority.
- Runtime shell: `govengine.runtime_shell` defines neutral host control actions, queue snapshots, runtime snapshots, and scheduler-tick metadata without storage, queue persistence, scheduler ownership, delivery, command, credential, or live-execution authority.
- Planning contracts: `govengine.planning` defines neutral task-contract, plan-intent, and planner-port validators without planner implementation ownership, raw target/prompt ownership, Ravenclaw security semantics ownership, queue/scheduler/storage ownership, commands, adapters, or live execution.
- Admission/policy contracts: `govengine.admission` defines neutral admission, policy-decision, approval-request, and audit-record validators without domain policy meaning, approval workflow, audit storage, adapter, command, or live-execution ownership.
- Evidence review contracts: `govengine.review` defines neutral evidence requirements, claims, qualifications, and review results without SCLite verdict ownership, Ravenclaw finding taxonomy ownership, raw evidence storage, adapter, command, or live-execution ownership.
- Domain profile SDK: `govengine.profiles` defines contract-only domain profile declarations, registries, fixture profiles, and conformance reports without domain taxonomy ownership, adapters, credentials, live execution, or product UX.
- Runtime contract proofs: `govengine.contract_proofs` defines public-safe Ravenclaw/Tecrax proof fixtures and neutral governance vocabulary over existing GovEngine contracts without adapters, credentials, live execution, schedulers, storage, or new OODA surface.
- Public truth gate: `scripts/validate_public_truth.py` checks version/dependency/status/surface consistency across package metadata and public docs.
- Alpha readiness gate: `scripts/validate_alpha_readiness.py` checks package metadata, alpha classifier, runtime proof fixtures, neutral vocabulary, and public-surface non-claims before alpha releases.
- Runner protocol: dry-run/control-plane shape only.
- OODA safety loop: deterministic between-step decision contract.
- Core artifact governance boundaries: initial portable dataclasses for artifact descriptors/envelopes/state, governance context, transition decisions, and execution prerequisites.
- SCLite lifecycle/review bridge: neutral descriptor/state/transition and review-bundle verdict mapping delegate verification and review semantics to SCLite. Ravenclaw owns lifecycle artifact projection from its runtime payloads and its public proof generation.
- Guard replay helper: `govengine.replay` records observed SCLite Kernel Guard
  roots through host-supplied JSON state so runtimes can reject repeated
  `root_tag` values in require-fresh mode without moving HMAC verification,
  key storage, or runtime storage into GovEngine.
- Guarded runtime adapter: `verify_guard_and_record_replay()` composes SCLite
  guarded-strict verification with GovEngine replay freshness and returns one
  runtime-consumable decision.
- Artifact lifecycle controller: initial transition policy/gate/controller for ordered lifecycle transitions and blocker/next-action reporting.
- Signing/trust bridge: initial signature envelope, policy, trust result, signer/verifier port, transition-decision helpers, and published deterministic demo signer/verifier fixture ports without PKI/key ownership.
- Controlled execution gate: initial dry-run-only execution gate and default `DryRunRunner`; live requests are blocked by default.
- Public surface registry: tested `govengine.surfaces` metadata contains only neutral artifact-governance core, planning-contracts core, admission-policy core, evidence-review core, domain-profile SDK, runtime contract proofs, and controlled-execution core surfaces.
- Security profile retirement: the published `0.12.0a0` alpha package removes the former optional Ravenclaw-derived facade and helper modules; security-domain behavior remains host-owned.
- Deconfliction/state index: initial conflict/change-order helpers and lightweight artifact state summaries.
- Live subprocess execution: not owned by GovEngine and disabled by default for future live backends.
- Carrier adapters: deferred.
- PyPI publication: completed through `govengine==0.12.1a1`; source `0.12.2a0` is not uploaded yet.

## What is public-safe today

GovEngine can be reviewed as a small Python package for:

- portable artifact descriptor/envelope/state and transition-decision boundary objects;
- serializable kernel/profile/runtime/SCLite ownership contracts, boundary report, and domain-profile boundary/conformance validation;
- lightweight artifact lifecycle transition gate/controller helpers;
- signature/trust policy bridge helpers that require host-provided verification, plus deterministic demo ports for public-safe fixture/reviewer examples;
- dry-run-only controlled execution gate helpers and default dry-run runner;
- artifact deconfliction/change-order and state-index summaries;
- public surface metadata for current alpha API boundary review;
- neutral planning/task contract validators for hosts that need a planner-to-runtime handoff without moving domain planning semantics into GovEngine;
- contract-only domain profile declarations and conformance reports for Ravenclaw and a Tecrax dry-run/local-fixture skeleton;
- public-safe runtime contract proof fixtures that show Ravenclaw and Tecrax using the same neutral GovEngine/SCLite contract flow;
- execution-ticket and approved-spec validation helpers;
- runner request/receipt shapes;
- OODA decision objects;
- SCLite lifecycle/review integration boundaries and status/verdict mapping into portable GovEngine state/transition objects.
- guarded-root replay decisions for already-verified SCLite Kernel Guard
  sidecars, using host-supplied state.
- guarded-strict plus replay-fresh gating inputs for runtime-consumable
  bundles.
- runtime-shell control/queue/snapshot projection objects for hosts that need to map their own state/control UI into a neutral reviewable shape.

## What is not claimed

GovEngine does not currently claim:

- production runtime readiness;
- direct execution from raw intent;
- live exploit or scanner capability;
- authorization to run tools against targets;
- bug-bounty campaign orchestration ownership;
- protocol adapter correctness;
- complete API stability;
- production/stable PyPI API readiness;
- PKI, CA, KMS, trust-store, or key-management ownership;
- a full replacement for Ravenclaw Runtime;
- Tecrax infrastructure-domain semantics, credentials, or product UX.
- runtime state storage, queue persistence, or scheduler ownership.

## Controlled execution posture

Controlled execution is a later capability, not the current default. Execution must be gated by a prepared execution contract, valid policy decision, approved execution ticket, valid signature/trust decision, and allowed runner profile. Runtime-consumable SCLite bundles additionally require guarded-strict verification plus replay-fresh status. Dry-run behavior is the default; live backends are optional future work and must stay disabled by default.

## Release posture

Keep GovEngine in `0.y.z` until:

1. GovEngine's public API boundary remains documented and tested enough for external users;
2. changelog, security, contribution, validation, and publishing docs stay complete;
3. release artifacts can be built and checked reproducibly;
4. Ravenclaw consumes the released package without Git URL pin drift.
