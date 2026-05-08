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
- Consume GovEngine from the public git dependency.
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

## Stage 6 — carrier adapters

Deferred.

Potential hosts/carriers such as OpenClaw, MCP, or A2A should come after the core API, runner protocol, OODA safety loop, and package/publication discipline are stable. GovEngine should not become protocol-first.

Before adapter implementation resumes, finish the repository-publication hygiene wave: changelog/status/security/publishing docs, versioning decision, SCLite package dependency path, and release validation gates.
