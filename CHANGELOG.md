# Changelog

All notable public GovEngine changes should be documented here.

GovEngine follows conservative pre-1.0 versioning while the API boundary is still being extracted from Ravenclaw.

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
