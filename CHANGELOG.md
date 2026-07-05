# Changelog

All notable public GovEngine changes should be documented here.

GovEngine follows conservative pre-1.0 versioning while the API boundary is still being extracted from Ravenclaw.

## Unreleased

- Added `govengine.automation` with `AutomationTransitionRequest` and
  `admit_automation_transition()` for child-operation planning admission over
  SCLite `automation_chain.v0.1` refs, max-depth limits, child budgets,
  allowed child intent classes, LLM proposal-only handling, and approval
  deferral without mutating runtime state.
- Added `govengine.automation_explain` with `AutomationTransitionExplanation`,
  `explain_automation_transition()`, and
  `govengine-policy automation-transition --json` for redacted operator-facing
  automation admission reasoning.

## 0.16.9 - 2026-07-05 - G8 CLI contract registry and error envelope

- Published `govengine==0.16.9` on PyPI with `sclite-core==1.0.8`.
- G8 slice 1 (`cda9a27`): `govengine.cli_contract_registry.v0.1` for `govengine-policy`
  and `govengine-supervisor` operator CLIs with format and exit-code matrices.
- G8 slice 1 (`cda9a27`): `govengine.cli_error.v0.1` envelope on `--json` failure paths for
  policy and supervisor authoring CLIs.
- G8 slice 1 (`cda9a27`): subprocess contract tests in `tests/test_cli_contracts.py` and
  `tests/test_supervisor_cli.py`; docs in `docs/POLICY_ENGINE.md`.

## 0.16.8 - 2026-07-04 - Registered plugin backend typed execution admission

- Published `govengine==0.16.8` on PyPI with `sclite-core==1.0.8`.
- Admit registered RExecOp plugin backends in typed execution governance when
  `registered_plugin_backend` metadata is present.
- Fix plugin stack compatibility to honor `declared_capability_descriptors`.

## 0.16.7 - 2026-07-04 - Typed execution governance, contract compatibility and governance trace

- Published `govengine==0.16.7` on PyPI with `sclite-core==1.0.8`.
- Added M7 `GovernanceTrace` with `project_governance_trace()` and
  `policy_request_digest()` for digest-bound truth-path consumers.
- Extended M6.5 contract catalog with `gov_admission_decision` and admission/
  runtime-control surfaces for RExecOp policy enforcement binding.
- Added M6.5 central contract compatibility with `supported_contract_report()`,
  `evaluate_contract_compatibility()`, `validate_supported_contract_version()`
  and `govengine-policy compatibility --json` for machine-readable supported
  GovEngine contract catalog and fail-closed unknown-major version checks.
- Policy-pack `output_digest_required` now projects to post-IO receipt enforcement
  overlay only; pre-IO typed execution admission no longer requires
  `output_digest_ref` before backend IO.
- Extended typed execution control catalog with policy-pack mappings:
  `TYPED_EXECUTION_CONTROL_CATALOG_ENTRIES`, `project_typed_execution_policy_overlay()`
  and `map_policy_verdict_to_typed_execution_controls()` bridge
  `PolicyVerdict`/`RuntimeControlProjection` into typed execution evidence,
  network egress and backend-class controls. Policy enforcement now projects
  `read_only_required`, `no_raw_shell`, `allowed_network_egress`,
  `allowed_backend_classes` and `mutation_requires_approval` constraints.
- Added typed execution stack compatibility with `TypedExecutionStackCompatibilityRequest`,
  `evaluate_typed_execution_stack_compatibility()`, `typed_execution_control_catalog()`
  and `govengine-policy typed-execution-compatibility|typed-execution-control-catalog`
  for RExecOp backend descriptor vs GovEngine control coverage without backend IO.
- Added G5 typed execution governance with `TypedExecutionGovernanceRequest`,
  `RuntimeCapabilityDescriptor`, `TypedExecutionCapabilityCompatibilityReport`,
  `explain_typed_execution_governance()`, `admit_typed_execution()` and
  `govengine-policy typed-execution-governance --json` for digest-bound typed
  execution admission, capability compatibility controls and fail-closed
  blockers over raw shell, unsupported backends, missing output digest refs,
  network boundary mismatch and mutation approval evidence without backend IO.

## 0.16.6 - 2026-07-04 - Supervisor action explanations for recovery/triage

- Published `govengine==0.16.6` on PyPI with `sclite-core==1.0.8`.
- Added `govengine.supervisor_explain` with `SupervisorActionExplanation` and
  `explain_supervisor_action()` for stable, redacted supervisor admission
  reasoning over retry budgets, stale-age gates, human sign-off and record-only
  health actions.
- Added `govengine-supervisor explain --json` for operator-side inspection of
  bounded `SupervisorActionRequest` payloads without executing recovery.
- Added G3 profile governance projection with `ProfileGovernanceProjection`,
  `ProfileConnectorCompatibilityReport`, `explain_profile_governance()` and
  `govengine-policy profile-governance --json` for policy-hook/evidence/runner
  posture checks and profile/connector capability compatibility without backend IO.

## 0.16.5 - Supervisor action admission source line

- Added `govengine.supervisor_actions` with `SupervisorActionRequest` and
  `admit_supervisor_action()` for bounded runtime-supervisor admission over
  watchdog record digests, retry/stale limits and affected operation/event/inbox
  references. The surface does not implement a worker, queue, scheduler,
  recovery tool, infrastructure monitor, runtime store or SCLite artifact writer.
- `block_autostart` admission now requires the stale-operation age to meet or
  exceed the declared stale-age threshold, so premature runtime blockers are
  denied fail-closed.
- Signed manual recovery requests now carry bounded `actor_ref` and `scope`
  fields. Human-signoff supervisor actions are rejected when either field is
  missing, keeping manual recovery auditable without giving GovEngine runtime
  execution authority.

## 0.16.2 - 2026-06-28

- Added `govengine.triggers` with `TriggerPlanningRequest` and
  `admit_trigger_planning()` for bounded trigger-planning admission over
  event/rule digests. The surface does not implement scheduling, event intake,
  execution, domain trigger meaning, or SCLite evidence truth.
- Published `govengine==0.16.2` as the admission-contract baseline required by
  RExecOp trigger planning while keeping execution, scheduler, profile semantics
  and SCLite truth outside GovEngine.

## 0.16.1 - 2026-06-27

- Added the PEP 561 `py.typed` marker and wired the existing `ruff`/`mypy`
  developer tooling into CI so GovEngine participates in the stack-wide quality
  baseline.
- Published `govengine==0.16.1` as a packaging and public-truth patch over
  `sclite-core==1.0.8`.
- Kept GovEngine ownership unchanged: governance, policy, admission,
  obligations, constraints, and enforcement-plan contracts only; no scheduler,
  executor, profile semantics, SCLite truth authority, or live backend was
  added.

## 0.16.0 - 2026-06-24

- Published the enforcement-plan API as the dependency baseline for RExecOp B2.

### Policy enforcement plan and existing-admission binding

- Added `PolicyEnforcementPlan` and `RuntimeControlProjection` as the GovEngine-owned
  binding between a compiled policy pack, a PolicyEngine verdict, and
  host-enforceable neutral controls. Admission uses the existing
  `GovAdmissionDecision` contract rather than introducing another envelope.
- Added deterministic GovEngine record digests for compiled policy packs,
  verdicts, enforcement plans, and admission decisions, plus drift validation.
- Supported projections are `receipt`/`receipt_required`,
  `output_digest_required`, `output_limit`, `timeout`, and `max_steps`;
  unsupported or malformed controls produce a blocked plan and matching denied admission.
- GovEngine still performs no subprocess, SSH, HTTP, SCLite canonicalization, or
  domain-specific execution. The host runner must enforce every projected control.

## 0.15.0 - 2026-06-20

### Policy engine MVP (`govengine.policy`)

- New public surface: `govengine.policy` with `PolicyRequest`, `PolicyVerdict`, `PolicyObligation`, `PolicyConstraint` (schema `v0.1`)
- `PolicyCompiler` / `compile_policy_pack`: declarative YAML/JSON policy packs → deterministic `CompiledPolicyPack`; rejects empty packs and conflicting rules on the same conditions
- `PolicyEngine` / `evaluate_policy`: fail-closed evaluation with built-in invariants (`unsafe_execution_shape`, destructive actions without approval evidence, critical mutating actions without approval)
- Rule effects: `allow`, `allow_with_obligations`, `approval_required`, `deny`; conditions match dotted paths such as `action.mode` and `resource.criticality`
- `policy_verdict_to_gov_policy_decision()` projects `PolicyVerdict` into legacy `GovPolicyDecision` for `compose_runtime_admission_result()`
- Tests: `tests/test_policy_engine.py`
- Docs: [docs/POLICY_ENGINE.md](docs/POLICY_ENGINE.md)
- `API_STABILITY_MATRIX.md`: `govengine.policy` row; alpha export count 203

## 0.14.0

- Publishes the `0.14.0` package line over `sclite-core>=1.0.3,<1.1` after
  the SCLite 1.0.3 truth-layer release.
- Canonicalizes lifecycle verified-state naming on `verified_chain` and
  `verified_lifecycle`, while keeping `chain_verified` /
  `lifecycle_verified` as explicit migration aliases.
- Hardens signature transition decisions so failed verification status cannot
  pass solely because `trust_status` is `trusted`.
- Enforces `GovEvidenceRequirement.evidence_kind` during review qualification
  using bounded claim metadata or claim type only; no raw evidence store or
  domain taxonomy is added.
- Splits runtime-consumable guard failures onto the `kernel_guard_required`
  reason code instead of reporting them as `signature_required`.
- Tightens allowed runtime-admission proof inputs to require an execution
  ticket id and ticket digest/reference plus guarded root digest and
  admission/ticket receipt binding.
- Adds mypy and documentation anti-drift gates for version truth, lifecycle
  vocabulary, runtime-shell/state-machine separation, and contract-proof
  classification.

## 0.13.0

- PyPI default install fix: publishes stable `0.13.0` so `pip install govengine` resolves above stale `0.7.0` without yanking old versions.
- Admission guarded/replay fail-closed fix: `_guarded_bundle_decision_failed` and `_replay_runtime_status` with `runtime_consumable` now fail closed consistently.

## 0.12.3-alpha - Governed-runtime MVP and SCLite 1.0.2 sync

- Publishes the `0.12.3a0` / `0.12.3-alpha` package line over
  `sclite-core>=1.0.2,<1.1` after SCLite 1.0.2 roadmap hardening and
  Ravenclaw stack-compatibility validation.

### Governed-runtime admission kernel

- Added the public runtime admission surface: `RuntimeAdmissionResult`,
  `compose_runtime_admission_result()`, `normalize_admission_artifact_refs()`,
  and `validate_runtime_admission_result()`. The composer assembles policy,
  ticket, trust, guarded replay, runner profile, receipt obligation, and bounded
  artifact-reference summaries into one host-consumable decision record.
- Added runner-profile and receipt-obligation admission gates. Runtime admission
  now requires an allowed runner profile and a receipt obligation; concrete
  runner receipts are validated separately with
  `validate_runner_receipt_binding()` against admission, ticket, request, and
  receipt digests.
- Added these admission gates before any host-owned controlled runner path may
  proceed; GovEngine still does not grant live execution authority or ship a live
  subprocess backend.
- Added inspect-only admission workflow and `scripts/inspect_runtime_admission.py`
  for read-only operator inspection of composed admission decisions without live
  execution.

### Replay, receipt, evidence, and audit

- Extended `govengine.replay` with a neutral `ReplayClaimStore` port and an
  in-memory development adapter. The port records replay claims (root tag, chain
  id, ticket/run id, key id) and can reject repeat roots in require-fresh mode
  without replacing existing guarded-root replay helpers from `0.12.1`.
- Added receipt-to-admission binding plus `validate_runner_receipt_binding()`
  and `validate_evidence_review_chain()` for bounded admission/ticket/request/
  receipt and receipt/evidence/review reference checks.
- Added `validate_evidence_review_chain()` and supporting validators for end-to-end
  evidence review chains (admission → receipt → evidence → review).
- Added `AuditLedgerPort` contracts plus `JsonlAuditLedgerAdapter`, a
  development-only hash-chained append-only JSONL adapter without choosing a
  production database.

### Signing, trust, and runner supervision

- Added signed GovEngine record support: `govengine_record_digest()`,
  `canonical_govengine_record()`, `signed_artifact_from_record()`,
  `verify_signed_govengine_record()`, and supporting trust/key-resolver ports.
- Refined trust ports and normalized admission artifact references and digests.
- Added local subprocess runner readiness gating with
  `LocalSubprocessRunnerReadiness` and
  `evaluate_local_subprocess_runner_readiness()`. The kernel keeps the optional
  local subprocess runner at `not_applicable` until explicit host safety
  prerequisites exist.

### Documentation, validation, and repository hygiene

- Added governed-runtime operator documentation:
  `docs/GOVERNED_RUNTIME_MVP_RUNBOOK.md`, `docs/RUNTIME_ADMISSION.md`,
  `docs/INSPECT_ONLY_ADMISSION_WORKFLOW.md`,
  `docs/GUARDED_FRESH_RUNTIME_ADMISSION_EXAMPLE.md`, and related updates to
  `docs/API_STABILITY_MATRIX.md`, `docs/API_BOUNDARY.md`, `PUBLIC_STATUS.md`,
  and `README.md`.
- Recorded final roadmap audits, package-validation smoke, and Signposter
  lifecycle smoke evidence in docs without expanding live-execution claims.
- Strengthened public-truth and documentation hygiene guards in
  `scripts/validate_public_truth.py` and tests.
- Added read-only operator verifier scripts for runner receipt bindings and
  development JSONL audit ledgers, with bounded outputs, stable exit codes, and
  focused CLI tests.
- Added the next-alpha release readiness gate, downstream compatibility smoke
  design, and final roadmap audit decision without publishing, tagging, or
  adding host runtime imports.
- Added governed-runtime smoke-chain coverage in standalone tests.
- Removed Signposter control-plane artifacts (`docs/roadmaps/`,
  `DOCUMENTATION_HYGIENE.md`) from the tracked public surface.

## 0.12.2-alpha - SCLite 1.0 dependency sync and guarded replay hardening

- Publishes the `0.12.2a0` / `0.12.2-alpha` package line over
  `sclite-core>=1.0.1,<1.1` after SCLite 1.0.1 audit hardening and
  downstream Ravenclaw validation.
- Tightens guarded-bundle replay freshness from root-tag-only matching to
  semantic payload matching over `root_chain_digest`, ticket/chain scope, and
  `key_id`, so re-guarding the same payload with fresh nonces does not bypass
  replay detection.
- Adds an explicit execution-gate entry point for runtime-consumable guarded
  bundle decisions produced by `verify_guard_and_record_replay()`, avoiding
  hand-mapped guarded/fresh status fields at the host boundary.

## 0.12.1-alpha.1 - Guarded-bundle replay gate

- Publishes `0.12.1a1` / `0.12.1-alpha.1` as the guarded-bundle replay gate
  line over `sclite-core>=0.8.0b2,<0.9`.
- Adds `govengine.replay`, a neutral guarded-root replay store helper for
  already-verified SCLite `kernel_guard_hmac_v1` sidecars. The helper records
  `root_tag`, `chain_id`, ticket/run id, and `key_id` through host-supplied
  JSON state and can reject repeat roots in require-fresh mode without owning
  HMAC verification, key storage, runtime storage, or public PKI semantics.
- Adds `verify_guard_and_record_replay()`, the high-level runtime-consumable
  guarded-bundle flow: SCLite guarded-strict verification first, then
  GovEngine replay-store recording. The controlled-execution gate can now
  require `guarded + replay-fresh` for runtime-consumable bundles while keeping
  review-only bundles on the existing review path.

## 0.12.0-alpha - Security facade retirement

- Publishes `0.12.0a0` / `0.12.0-alpha` as the alpha API-narrowing line.
- Removes the optional `security_profile_helpers` surface, its
  `govengine.security_profile` facade, and Ravenclaw-derived action, tool,
  policy, scope, signal, analysis, and confirmation helper modules.
- Retains neutral scope ports, review, planning, admission, runtime/control,
  supervision, profile, proof, and SCLite integration boundaries and adds
  negative tests against reintroducing the retired facade.
- Corrects roadmap current-baseline wording after the published `0.11.0-alpha`
  boundary release and adds public-truth coverage against regressing to the
  superseded `0.10` current-line claim.
- Aligns contributor maturity wording with the published alpha line, makes the
  current validation gate precede archived release evidence, and documents why
  extracted Ravenclaw copyright attribution coexists with GovEngine package
  maintainer metadata.
- Adds a clean installed-package validation gate and removes active guidance to
  use a dependency-polluted system interpreter for `pip check` evidence.
- Corrects post-publication drift that still described the published `0.12`
  alpha line as a candidate and mechanically guards that active wording.

## 0.11.0-alpha - Host projection removal and SCLite 0.8 sync

- Published the alpha package as `govengine==0.11.0a0` on PyPI.
- Promotes source/package truth to `0.11.0a0` / `0.11.0-alpha` with `sclite-core>=0.8.0a0,<0.9`.
- Removes `govengine.sclite_adapter`, the transitional Ravenclaw-shaped lifecycle assembly seam, after Ravenclaw moved public lifecycle projection into its own runtime boundary.
- Retains neutral lifecycle/review result mapping and validates that host-owned projection does not re-enter GovEngine core.

## 0.10.2-alpha - SCLite 0.7 lifecycle surface sync

- Promoted source/package truth to `0.10.2a0` / `0.10.2-alpha` with `sclite-core>=0.7.0a0,<0.8`.
- Added a current SCLite lifecycle builder using scoped `execution_ticket.v0.3` semantics and receipt-bounded evidence verification.
- Removed the legacy v0.1 descriptor from current lifecycle policy output while keeping compatibility builders available during downstream migration.
- Added an integration test that materializes and reviews the current lifecycle through SCLite, without expanding GovEngine ownership of artifact review or runtime execution.
- Added an alpha hygiene guard that rejects Ravenclaw host-context and
  `RAVENCLAW_*` assumptions inside neutral public surfaces, and removed the
  leftover Ravenclaw context import from the neutral execution-contract module.
- Narrowed the optional `security_profile_helpers` claim to compatibility
  scaffolding instead of presenting Ravenclaw-derived helpers as a neutral SDK.
- Renamed the optional tool-registry planner-profile environment default to
  `GOVENGINE_TOOL_PROFILES`, while preserving the legacy Ravenclaw variable as
  a compatibility fallback.

## 0.10.1-alpha - SCLite 0.6 alpha sync

- Promoted the source line to `0.10.1a0` / `0.10.1-alpha`.
- Updated the SCLite dependency and public truth validators to `sclite-core>=0.6.0a0,<0.7`.
- Kept this as a dependency/documentation/validation sync without adding runtime execution, adapters, storage, schedulers, credentials, or production-readiness claims.

## 0.10.0-alpha - Alpha readiness gate

- Promoted the source line to `0.10.0a0` / `0.10.0-alpha` after public truth, package-build, runtime proof, and Ravenclaw downstream compatibility validation.
- Added an alpha-readiness validator that checks package metadata, public surfaces, runtime proof fixtures, neutral governance vocabulary, and alpha non-claims.
- Kept PyPI upload, public tags, carrier adapters, credentials, schedulers, storage, live execution, and production-readiness claims out of scope pending operator approval.

## 0.9.0 - Runtime contract proofs

- Added `govengine.contract_proofs` with public-safe Ravenclaw and Tecrax runtime proof fixtures over existing planning, supervision, runtime snapshot, review, and change-order contracts.
- Added neutral governance vocabulary entries for objective, policy constraints, task plan, runner bounds, runtime snapshot, review result, and change order without changing neutral public API naming.
- Added `runtime_contract_proofs` to the public surface registry while keeping adapters, credentials, schedulers, storage, live execution, and new OODA surfaces out of scope.

## 0.8.0 - Minimal Domain Profile SDK

- Added `govengine.profiles` with contract-only `DomainProfile`, registry, capability, runner-profile, policy-hook, evidence-rule, and conformance-report declarations.
- Added Ravenclaw security and Tecrax infrastructure-ops fixture profiles to prove profile portability without moving domain taxonomy, product UX, credentials, carrier adapters, or live execution into GovEngine.
- Added `domain_profile_sdk` to the public surface registry while keeping profile conformance bounded by existing kernel/profile/SCLite ownership checks.

## 0.7.1 - Public truth and boundary hardening

- Prepared a stabilization release that aligns public status, validation, publishing, roadmap, and API-boundary docs with the `0.7.x` source baseline.
- Added a public truth validator for version/dependency/status/surface consistency across package metadata and public docs.
- Hardened neutral-core boundary tests so controlled-execution core no longer depends on optional security-profile helper modules at import time.

## 0.7.0 - Evidence review contracts

- Added `govengine.review` with neutral `GovEvidenceRequirement`, `GovEvidenceClaim`, `GovEvidenceQualification`, and `GovReviewResult` validators.
- Added receipt-bounded claim qualification that rejects live vulnerability claims when the supporting receipt is only dry-run.
- Added `evidence_review_core` to the public surface registry while keeping SCLite review-bundle verdicts, Ravenclaw finding taxonomy, raw evidence storage, adapters, commands, and live execution host-owned.

## 0.6.0 - Runner supervision contracts

- Added `govengine.execution.supervision` with neutral `GovRunnerLease`, `GovSupervisionPlan`, and `GovSupervisionDecision` validators for bounded runner supervision.
- Added request/receipt validation helpers that require approved-spec runner requests, matching receipts, and dry-run/default-deny live backend behavior.
- Added negative validation for raw-intent runner requests, missing approved specs, missing receipts, live backend use without explicit enablement, and forbidden metadata claims.

## 0.5.0 - Admission, policy, approval, and audit contracts

- Added `govengine.admission` with neutral `GovAdmissionDecision`, `GovPolicyDecision`, `GovApprovalRequest`, and `GovAuditRecord` validators for host runtime gate records.
- Added negative validation for raw targets, raw prompts, commands, credentials, carrier payloads, storage/scheduler/live-execution claims, and admission outcome mismatches.
- Added `admission_policy_core` to the public surface registry while keeping profile policy meaning, operator approval workflow, audit storage/retention, adapters, commands, and live execution host-owned.

## 0.4.0 - Planning/task contracts

- Added `govengine.planning` with neutral `GovTaskContract`, `GovPlanIntentContract`, and `PlannerPort` validators for planner-to-runtime handoff shapes.
- Added negative validation for raw targets, raw prompts, commands, credentials, storage/scheduler/live-execution claims, and duplicate task-contract IDs.
- Added `planning_contracts_core` to the public surface registry while keeping Ravenclaw security planning semantics, planner implementation, queues, schedulers, adapters, commands, and live execution host-owned.

## 0.3.0 - Runtime state/control shell

- Added `govengine.runtime_shell` with neutral control actions, queue lane/snapshot summaries, runtime snapshots, and scheduler tick metadata for host runtimes such as Ravenclaw.
- Added deterministic validation for `start`, `pause`, `resume`, `stop`, `cancel`, `replan`, `degrade_to_dry_run`, `cooldown`, `retry`, and `archive` control actions without adding command execution, runtime storage, queue persistence, scheduler ownership, or carrier adapters.
- Kept queue/runtime snapshots redaction-bounded and host-owned; GovEngine validates shape and unsafe metadata but does not store, schedule, enqueue, execute, or deliver work.

## 0.2.0 - Kernel boundary freeze

- Added `govengine.boundary`, `govengine.orchestration`, `govengine.events`, `govengine.state_machine`, and `govengine.control` with serializable kernel/profile/runtime/SCLite ownership contracts, a machine-readable boundary report, a Ravenclaw profile contract, domain-profile conformance checks, deterministic orchestration handoff contracts, neutral governance event envelopes, neutral run-state transitions, between-step control decisions, boundary docs, and negative boundary validation for forbidden profile ownership, forbidden orchestration authority, unsafe event/state/control metadata, command/live-execution claims, or unknown consumed-surface claims.
- Kept live execution, queues/schedulers, carrier adapters, credential handling, runtime persistence, and domain product UX outside GovEngine.
- Updated release validation docs and publishing notes for the 0.2 kernel-boundary freeze line.

## 0.1.7 - SCLite 0.5.1 review-bundle bridge

- Updated the SCLite dependency to `sclite-core>=0.5.1,<0.6`.
- Added thin SCLite review-bundle bridge helpers that delegate GovEngine integration bundle pass/fail verdicts to SCLite `0.5.1`.
- Added integration tests for packaged SCLite GovEngine review bundles, including the expected cross-host failure fixture.
- Updated public docs/status/validation notes for the SCLite `0.5.1` chain sync and PyPI release.

## 0.1.6 - SCLite 0.3.5 scoped-ticket bridge

- Updated the SCLite dependency to `sclite-core>=0.3.5,<0.4`.
- Added thin GovEngine gates that delegate SCLite v0.3 scoped-ticket semantics and receipt/evidence use-bounds verification to SCLite.
- Added deterministic tests for valid scoped-ticket use and rejection of unbounded execution claims.
- Added deterministic demo signing/verifier ports for host-provided signing/trust examples without adding PKI, key storage, or production identity claims.
- Cleaned README badge order, removed personal ownership copy from public-facing docs, completed package metadata fields, and updated roadmap wording for the published `0.1.5` line.
- Polished public docs to state the package boundary, security-profile boundary, and deferred adapter/live-execution non-claims more plainly.

## 0.1.5 - security profile facade

- Added `govengine.security_profile`, a tested optional-profile facade for action/tooling, policy/scope, and review-contract helpers.
- Added allowlisted lazy imports and boundary assertions so hosts can discover security-profile helpers through one entrypoint without pulling neutral core or adapter/live-execution claims into the profile.
- Released the package version for the security-profile facade line after the standard release checklist and operator approval.

## 0.1.4 - API surface registry

- Added a tested public surface registry in `govengine.surfaces` that names the artifact-governance core, controlled-execution core, and optional security-profile helper surface without moving live execution or protocol adapters into GovEngine.
- Clarified that action/tool/scope/policy/signal helpers are an optional security profile for hosts such as Ravenclaw, while artifact lifecycle/signing/trust/execution gates remain the neutral core.
- Released the package version for the API surface registry line after the standard release checklist and operator approval.

## 0.1.3 - artifact governance control gates

- Added initial portable artifact-governance boundary objects in `govengine.core`.
- Added SCLite lifecycle status mapping, lifecycle transition gates, signing/trust bridge helpers, dry-run-only controlled execution gates, deconfliction/change-order helpers, and lightweight artifact state-index summaries.
- Updated public roadmap/API/status docs to keep carrier adapters deferred and document that live execution remains disabled by default.
- Released the package version for the artifact-governance control-gate line after the standard release checklist and operator approval.

## 0.1.2 - contract extraction

- Extracted reusable signal, analysis, and confirmation-evidence policy contracts from Ravenclaw into `govengine.contracts.*`.
- Added standalone tests for signal promotion bridges, governance-blocked evidence classification, analysis success semantics, and confirmed-evidence gates.
- Prepared the package version for the signal/evidence/analysis contract extraction line. Publication requires the standard release checklist and operator approval.

## 0.1.1 - metadata calibration

- Updated the PyPI package description to describe GovEngine as carrier-agnostic governed execution services that consume SCLite contract lifecycle artifacts for policy-gated security automation.
- Calibrated validation, roadmap, publishing, and public-status docs after `govengine==0.1.0` PyPI publication.

## 0.1.0 - initial PyPI candidate

- Switched SCLite dependency from a Git URL pin to the published PyPI distribution `sclite-core>=0.2.1,<0.3`.
- Normalized package license metadata to SPDX-style `MIT`.
- Added `govengine.__version__` for package/version checks.
- Added OODA receipt/evidence guidance for recording compact governance-control decisions without publishing raw output or private telemetry.
- Added deterministic OODA safety/control primitives: `GovObservation`, `GovOrientation`, `GovOodaDecision`, and `GovOodaController`.
- Added carrier-neutral runner protocol primitives: `GovRunnerStep`, `GovRunnerRequest`, `GovRunnerStepResult`, `GovRunnerReceipt`, and `GovRunner`.
- Added public API envelopes: `GovApiResult` and `GovApiError`.
- Kept SCLite imports lazy where needed so GovEngine public surface imports cleanly in standalone checks.
- Documented that carrier adapters remain deferred until the package/release boundary is more mature.

## 0.0.0

- Initial public extraction scaffold.
- Added importable `govengine` package, standalone tests, GitHub Actions pytest workflow, and initial architecture/API-boundary documentation.
- Added reusable helpers extracted around action validation, policy gateway behavior, approved execution specs, execution-ticket checks, command-shape normalization, dry-run result assembly, scope helpers, and SCLite lifecycle integration seams.
