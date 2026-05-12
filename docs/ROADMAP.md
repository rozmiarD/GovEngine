# GovEngine Roadmap

GovEngine is being extracted in stages from Ravenclaw. The goal is a reusable governed-execution core that consumes SCLite and remains independent of Ravenclaw UI/runtime specifics.

## Stage 0 — package boundary

Status: completed.

- Create importable `govengine` package.
- Add standalone tests and CI.
- Document owned vs excluded surfaces.
- Keep live execution out of scope.

## Stage 1 — SCLite consumption

Status: completed for initial public package.

- Pin SCLite as the contract lifecycle dependency.
- Keep schema/lifecycle ownership in SCLite.
- Expose GovEngine helpers that prepare/check execution contracts around SCLite artifacts.

## Stage 2 — Ravenclaw external consumption

Status: completed in Ravenclaw migration branch.

- Remove in-tree `govengine/` from Ravenclaw.
- Consume GovEngine from the public PyPI package dependency.
- Preserve Ravenclaw compatibility wrappers.
- Validate focused GovEngine/Ravenclaw seams and Security Contract receipt.

## Stage 3 — API hardening

Status: initial implementation complete.

- Added `govengine.api` with structured `GovApiResult` and `GovApiError` envelopes.
- Added boundary tests for stable result/error shape.
- Public API hardening is incremental: existing compatibility helpers remain available while new boundaries get typed envelopes first.

## Stage 4 — runner protocol design

Status: initial implementation complete, dry-run/control-plane only.

- Added `govengine.execution.runner_protocol` with `GovRunnerStep`, `GovRunnerRequest`, `GovRunnerStepResult`, `GovRunnerReceipt`, and `GovRunner` protocol.
- Added approved-spec-to-runner-request assembly and dry-run runner receipts.
- Ravenclaw subprocess execution remains host-owned. Moving live execution ownership into GovEngine still requires explicit operator review.

## Stage 5 — OODA safety loop

Status: initial implementation complete for deterministic between-step decisions.

Goal: define a carrier-neutral Observe-Orient-Decide-Act safety loop for governed execution. This is not an LLM agent loop and not a scanner. It is a runtime safety/control contract that can interrupt or reshape execution when observations diverge from the approved bounds.

Implemented concepts:

- `GovObservation` — normalized execution telemetry, host health, policy signals, scope drift, transport anomalies, unexpected artifact shape, and operator-control events.
- `GovOrientation` — contextual interpretation of those observations against the approved execution spec, execution ticket, policy decision, scope, aggression/budget limits, and host state.
- `GovOodaDecision` — one of `continue`, `pause`, `abort`, `cooldown`, `degrade_to_dry_run`, `require_owner_review`, or `replan_after_step`.
- `GovOodaController` — deterministic policy-first controller that evaluates observations before and between runner steps.

Required safety behavior:

- detect out-of-scope drift and abort before the next action;
- detect repeated transport/host-health anomalies and apply cooldowns;
- detect policy/ticket/spec mismatch and require owner review;
- detect execution output shape anomalies before evidence is trusted;
- preserve an auditable decision record that can be linked into SCLite evidence/receipt artifacts;
- keep host-specific telemetry interpretation outside protocol/carrier adapters.

Ravenclaw has partial precursors today: Logdash pause/stop controls, host execution gates, host-health cooldowns, runtime decision records, and replay anomaly checks. GovEngine is turning those scattered mechanisms into an explicit reusable contract.

Non-goals for this stage:

- no autonomous escalation beyond approved bounds;
- no live subprocess execution ownership unless Stage 4 runner protocol explicitly allows the adapter;
- no protocol-specific OpenClaw/MCP/A2A behavior;
- no LLM-dependent safety decision as the default path.

Gate:

- unit tests for each initial decision outcome: complete;
- Ravenclaw adapter test proving pause/abort/cooldown can be honored between runner steps: complete in Ravenclaw (`engine/tests/test_govengine_ooda_adapter.py`);
- receipt/evidence note showing how OODA decisions are recorded without leaking raw output: complete (`docs/OODA_RECEIPT_EVIDENCE.md`);
- public docs state non-claims clearly: complete.

## Stage 6 — signal/evidence/analysis contracts

Status: initial extraction complete for the pure contract helpers.

Goal: move pure decision/evidence contracts out of Ravenclaw Runtime and into GovEngine without moving UI, storage, raw artifacts, live execution, or campaign orchestration. These contracts make the reusable post-run reasoning seam explicit while preserving Ravenclaw as the reference host.

Implemented concepts:

- `govengine.contracts.signal` — signal contract builders/readers for workflow promotion, finding signal, success outcome, adaptation feedback, and legacy bridge flags.
- `govengine.contracts.analysis` — analysis contract builder that maps planner hypothesis, expected signal, evidence goal, success semantics, and semantic-loss execution fit into a compact review object.
- `govengine.contracts.evidence_policy` — confirmation gate for requiring false-positive guards, control comparison, observed control delta, and optional reproduction pass before a finding can be treated as confirmed.
- `govengine.security_profile` — optional facade that groups action/tooling, policy/scope, and review-contract helpers behind one host-facing discovery entrypoint without moving those helpers into the neutral core.

Non-goals for this stage:

- no raw evidence storage ownership;
- no Logdash projection/UI ownership;
- no live execution backend movement;
- no protocol/carrier adapters;
- no broad stable API claim beyond tested pre-alpha helpers.

Gate:

- standalone GovEngine tests for extracted contracts: complete;
- standalone GovEngine tests for the optional security-profile facade and boundary assertions: complete in the 0.1.5 line;
- Ravenclaw compatibility wrappers import the GovEngine modules: complete in the migration tree;
- Ravenclaw focused seam tests passed against the released GovEngine package line: complete;
- future package releases still require the standard release checklist and operator approval.

## Stage 7 — artifact governance core hardening

Status: initial implementation complete for neutral boundary objects.

Goal: make GovEngine portable as an artifact governance layer before any live execution backend or carrier adapter work. This stage introduces small, Ravenclaw-independent core objects that future lifecycle, signing/trust, and controlled-execution gates can share.

Implemented concepts:

- `govengine.core.ReasonCode` — stable reason-code values for portable boundary decisions.
- `govengine.core.ArtifactDescriptor` — neutral artifact descriptor object; SCLite still owns canonicalization and digest calculation.
- `govengine.core.ArtifactEnvelope` — descriptor plus artifact payload at the GovEngine boundary.
- `govengine.core.ArtifactState` — lightweight state summary with chain/signature/policy status, blockers, and next actions.
- `govengine.core.GovernanceContext` — profile, policy, trust, and runner-profile context without Ravenclaw path discovery.
- `govengine.core.TransitionDecision` — portable lifecycle transition decision envelope.
- `govengine.core.ExecutionPrerequisites` — guardrail summary that rejects raw-intent execution and keeps live backends disabled unless explicitly enabled.

Required safety behavior:

- GovEngine must never execute directly from raw intent.
- Execution requires a prepared execution contract, valid policy decision, approved execution ticket, valid signature/trust decision, and allowed runner profile.
- Dry-run behavior remains the default path.
- Live backends remain disabled by default.
- A future `LocalSubprocessRunner` must be optional, policy-enabled, negative-tested, and never default.

Non-goals for this stage:

- no schema/canonicalization/hash ownership movement out of SCLite;
- no live subprocess execution backend;
- no PKI, CA, KMS, or trust-store implementation;
- no carrier-specific OpenClaw/MCP/A2A behavior;
- no Ravenclaw campaign, Logdash, or persona ownership.

Gate:

- standalone tests prove stable descriptor/envelope/state/transition shapes;
- raw-intent execution prerequisites are rejected deterministically;
- live execution stays blocked by default even when dry-run prerequisites pass.

## Stage 8 — SCLite lifecycle verifier/status bridge

Status: initial implementation complete for descriptor/status/decision mapping.

Goal: make the existing SCLite adapter a neutral lifecycle verifier and status bridge, not a schema owner. GovEngine should build/read SCLite descriptors, call SCLite artifact/lifecycle validation helpers, and map lifecycle verification into `ArtifactState`/`TransitionDecision` objects.

Implemented concepts:

- `govengine.sclite_contracts.descriptor_from_artifact` maps SCLite descriptors into `ArtifactDescriptor` without reimplementing hashing.
- `govengine.sclite_contracts.lifecycle_state_from_manifest` delegates chain/lifecycle verification to SCLite and maps status into `ArtifactState`.
- `govengine.sclite_contracts.lifecycle_transition_decision` maps lifecycle verification into a portable `TransitionDecision`.

Non-goals:

- no duplicate schema registry, canonical JSON, digest, or chain verification implementation in GovEngine;
- no workflow engine;
- no carrier adapters.

## Stage 9 — artifact lifecycle controller and transition gates

Status: initial implementation complete for ordered transitions, missing-artifact blockers, and blocked-artifact propagation.

Goal: make artifact transitions the central governance primitive. Add a lightweight `ArtifactLifecycleController`/`TransitionGate` around SCLite lifecycle roles, blocking reasons, missing artifacts, and invalidation rules.

Implemented concepts:

- `govengine.lifecycle.TransitionPolicy` — small allow-list for lifecycle state transitions.
- `govengine.lifecycle.TransitionGate` — evaluates proposed transitions against policy, required artifact roles, and artifact blockers.
- `govengine.lifecycle.ArtifactLifecycleController` — thin controller facade for transition decisions and next actions.

This stage must precede controlled live execution.

## Stage 10 — signing/trust policy bridge

Status: initial implementation complete for signature envelopes, signing/trust policy objects, signer/verifier ports, and signature transition decisions.

Goal: define signing and verification ports plus trust-policy decisions without making SCLite or GovEngine own PKI/key management. GovEngine may verify that signatures bind to descriptor/chain/ticket digests and ask host-provided signer/verifier ports for trust decisions.

Implemented concepts:

- `govengine.signing.SignatureEnvelope` — portable signature metadata and digest binding.
- `govengine.signing.SigningPolicy` / `TrustPolicy` — local requirements and allowed trust statuses.
- `govengine.signing.SignerPort` / `VerifierPort` — host-provided interfaces; GovEngine core stores no keys.
- `govengine.signing.VerificationResult` — verifier/trust decision result shape.
- `govengine.signing.DemoDigestSigner` / `DemoDigestVerifier` — deterministic fixture/demo ports for exercising host-provided signing and verification without PKI or key storage.
- `govengine.signing.signature_transition_decision` — transition gate for required signatures, digest mismatch, signer allow-list, and trust decision status.

This stage must precede controlled live execution.

## Stage 11 — controlled execution layer

Status: initial implementation complete for dry-run-only execution gate and default `DryRunRunner`.

Goal: allow GovEngine to prepare/gate approved `RunnerRequest` execution only after lifecycle gates and signing/trust gates are explicit. `DryRunRunner` remains the default. Live backends are optional future adapters and must stay policy-enabled and never default.

Implemented concepts:

- `govengine.execution.gate.RunnerProfile` — policy-visible runner profile with live backend disabled by default.
- `govengine.execution.gate.ExecutionGateInput` — required boundary inputs before a runner request can proceed.
- `govengine.execution.gate.ExecutionGate` — rejects raw intent, missing policy/ticket/trust, disallowed profiles, and live execution when disabled.
- `govengine.execution.gate.DryRunRunner` — default runner that returns dry-run receipts and blocks live requests.

Required inputs before execution:

1. prepared execution contract;
2. valid policy decision;
3. approved execution ticket;
4. valid signature/trust decision;
5. allowed runner profile.

Non-goals:

- no execution from raw intent;
- no scanner/campaign executor ownership;
- no Ravenclaw executor moved 1:1 into GovEngine;
- no arbitrary subprocess execution by default.

## Stage 12 — deconfliction and artifact state index

Status: initial implementation complete for digest conflict detection, blocked-artifact propagation, change orders, and lightweight state summaries.

Goal: detect lifecycle conflicts and invalidated artifacts, then expose a small common operational picture without creating a workflow engine.

Implemented concepts:

- `govengine.deconfliction.ArtifactConflict` — portable conflict finding.
- `govengine.deconfliction.ArtifactChangeOrder` — required actions and invalidated downstream roles.
- `govengine.deconfliction.ConflictDetector` — digest/state conflict detection without replacing SCLite verification.
- `govengine.state_index.ArtifactStateIndex` — lightweight state summary with missing roles, blocked roles, invalidated roles, and next actions.

Non-goals:

- no event bus;
- no workflow scheduler;
- no UI ownership;
- no raw artifact storage ownership.

## Stage 12.5 — public surface registry and security-profile separation

Status: implemented and published in the `0.1.4`/`0.1.5` line.

Goal: make the pre-alpha API boundary easier to review before carrier-adapter work. GovEngine should expose a tested surface map that distinguishes neutral artifact-governance primitives from optional security-oriented helpers inherited from the Ravenclaw extraction path.

Implemented concepts:

- `govengine.surfaces.GovSurface` — compact metadata for a public surface group.
- `govengine.surfaces.public_surface_index` — tested index of current public surfaces.
- `artifact_governance_core` — neutral artifact descriptor/state/transition, lifecycle, signing/trust, deconfliction, and state-index modules.
- `controlled_execution_core` — approved-spec, execution-ticket, command-shape, runner, OODA, and dry-run execution-gate modules.
- `security_profile_helpers` — optional action/tool/scope/policy/signal helpers for hosts such as Ravenclaw.
- `govengine.security_profile` — optional facade for grouped helper discovery, JSON-safe profile indexing, allowlisted lazy imports, and boundary assertions.

Non-goals:

- no module migration or breaking import paths in this slice;
- no live scanner/exploit capability;
- no bug-bounty campaign orchestration ownership;
- no protocol adapter implementation.

Gate:

- standalone tests prove the surface names, optional-profile flag, non-claims, and strict lookup behavior;
- standalone tests prove the security-profile facade maps exactly to the public surface registry and does not import neutral core helpers through the optional profile;
- public docs state the separation without claiming stable 1.0 API maturity.

## Stage 13 — carrier adapters

Deferred.

Potential hosts/carriers such as OpenClaw, MCP, or A2A should come only after the artifact lifecycle, signing/trust, controlled-execution gates, package/publication discipline, and Ravenclaw consumption path are stable. GovEngine should not become protocol-first.

Adapter order remains: OpenClaw first later, MCP later, A2A last/example-first.
