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

Next recommended work.

- Reduce implicit host-context assumptions.
- Convert remaining dictionary-heavy boundaries into explicit typed structures where useful.
- Add more tests around policy gateway and execution-ticket failure modes.
- Clarify which helpers are stable public API vs internal extraction compatibility.

## Stage 4 — runner protocol design

Not started.

- Define a small runner protocol and result type.
- Keep Ravenclaw subprocess execution as the first adapter.
- Move dry-run-safe assembly before any live execution mechanics.
- Require operator review before moving live subprocess execution into GovEngine.

## Stage 5 — OODA safety loop

Not started. Add after the runner protocol exists, before carrier adapters.

Goal: define a carrier-neutral Observe-Orient-Decide-Act safety loop for governed execution. This is not an LLM agent loop and not a scanner. It is a runtime safety/control contract that can interrupt or reshape execution when observations diverge from the approved bounds.

Initial concepts:

- `GovObservation` — normalized execution telemetry, host health, policy signals, scope drift, transport anomalies, unexpected artifact shape, and operator-control events.
- `GovOrientation` — contextual interpretation of those observations against the approved execution spec, execution ticket, policy decision, scope, aggression/budget limits, and host state.
- `GovOodaDecision` — one of `continue`, `pause`, `abort`, `cooldown`, `degrade_to_dry_run`, `require_owner_review`, or `replan_after_step`.
- `GovOodaController` — deterministic policy-first controller that evaluates observations before, between, and eventually during runner steps.

Required safety behavior:

- detect out-of-scope drift and abort before the next action;
- detect repeated transport/host-health anomalies and apply cooldowns;
- detect policy/ticket/spec mismatch and require owner review;
- detect execution output shape anomalies before evidence is trusted;
- preserve an auditable decision record that can be linked into SCLite evidence/receipt artifacts;
- keep host-specific telemetry interpretation outside protocol/carrier adapters.

Ravenclaw has partial precursors today: Logdash pause/stop controls, host execution gates, host-health cooldowns, runtime decision records, and replay anomaly checks. GovEngine should turn those scattered mechanisms into an explicit reusable contract.

Non-goals for this stage:

- no autonomous escalation beyond approved bounds;
- no live subprocess execution ownership unless Stage 4 runner protocol explicitly allows the adapter;
- no protocol-specific OpenClaw/MCP/A2A behavior;
- no LLM-dependent safety decision as the default path.

Gate:

- unit tests for each decision outcome;
- Ravenclaw adapter test proving pause/abort/cooldown can be honored between runner steps;
- receipt/evidence note showing how OODA decisions are recorded without leaking raw output;
- public docs state non-claims clearly.

## Stage 6 — carrier adapters

Not started.

Potential hosts/carriers such as OpenClaw, MCP, or A2A should come after the core API, runner protocol, and OODA safety loop are stable. GovEngine should not become protocol-first.
