# GovEngine Architecture

GovEngine is a small governed-execution service layer. It is designed to sit between a host runtime and the SCLite contract lifecycle.

```text
host runtime -> GovEngine -> SCLite
```

For the current extraction, the host runtime is Ravenclaw. Later hosts may be OpenClaw, MCP/A2A-style carriers, or other local runtimes, but GovEngine should not become a carrier-specific adapter.

## Layers

### 1. Action layer

Modules:

- `govengine.action_schema`
- `govengine.action_validators`
- `govengine.action_compiler`
- `govengine.capability_recipes`
- `govengine.semantic_loss_policy`

Purpose:

- validate action shape;
- normalize action type and capability;
- resolve recipes and tool choices;
- compile caller intent into a bounded execution plan;
- classify semantic loss before execution planning drifts too far from request shape.

### 2. Policy layer

Modules:

- `govengine.policy.core`
- `govengine.policy.gateway`

Purpose:

- normalize policy decisions;
- evaluate action specs against tool/scope/aggression style constraints;
- keep policy checks structured and testable instead of prompt-only.

### 3. Contract layer

Modules:

- `govengine.contracts.execution`
- `govengine.sclite_adapter`
- `govengine.sclite_contracts`

Purpose:

- shape execution contracts and approval payloads;
- redact prepared execution specs for auditor/reviewer surfaces;
- bridge GovEngine helpers to SCLite lifecycle artifacts.

### 4. Execution helper layer

Modules:

- `govengine.execution.approved_spec`
- `govengine.execution.ticket_gate`
- `govengine.execution.command_shape`
- `govengine.execution.runner`
- `govengine.execution_backend`

Purpose:

- validate approved execution specs;
- check execution-ticket presence/shape;
- normalize command shape and target observations;
- assemble dry-run result envelopes.

Important: live subprocess execution is not owned by GovEngine yet.

### 5. Host context layer

Modules:

- `govengine.context`
- `govengine.scope`
- `govengine.state_store`
- `govengine.tool_registry`

Purpose:

- let a host runtime provide paths, scope, and state surfaces explicitly;
- avoid hard dependencies on Ravenclaw internals;
- support standalone import and package testing.

### 6. OODA safety/control layer

Planned after the runner protocol.

Purpose:

- observe normalized execution telemetry and operator-control events;
- orient observations against approved specs, execution tickets, policy decisions, scope, budgets, and host state;
- decide whether the next step should continue, pause, abort, cooldown, degrade to dry-run, or require owner review;
- act by returning deterministic control decisions to the host runner/adapter.

This layer should convert Ravenclaw's existing scattered controls — stop/pause, host health gates, cooldowns, runtime decisions, and anomaly/replay checks — into a reusable GovEngine contract. It must stay policy-first and carrier-neutral.

## Boundary rule

GovEngine can consume SCLite and host-supplied context. It should not import Ravenclaw `engine/*`, Logdash, OpenClaw session wiring, or protocol adapters.

```text
allowed:   Ravenclaw -> GovEngine -> SCLite
forbidden: GovEngine -> Ravenclaw engine/*
forbidden: GovEngine -> Logdash/OpenClaw/MCP/A2A adapters
```

## Current maturity

The package currently covers dry-run-safe helpers and contract/policy seams. It is not a full runtime and does not claim production execution safety on its own.
