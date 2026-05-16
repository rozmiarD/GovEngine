# GovEngine Architecture

GovEngine is a deterministic governed-runtime kernel in pre-alpha form. It is designed to sit between a host/domain runtime and the SCLite contract lifecycle.

```text
host runtime -> GovEngine -> SCLite
```

For the current extraction, the host/domain runtime is Ravenclaw. A future infrastructure-operations runtime/profile is reserved as Tecrax. Later carriers may include OpenClaw, MCP/A2A-style transports, or other local harnesses, but GovEngine should not become a carrier-specific adapter or a domain product shell.

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

### 0. Kernel/profile boundary layer

Module:

- `govengine.boundary`

Purpose:

- make the kernel/profile/runtime/SCLite ownership split serializable;
- let hosts declare domain-profile ownership without claiming GovEngine core, SCLite authority, live execution authority, credentials, or carrier adapter ownership;
- provide a tested Ravenclaw profile contract as the current host-profile example.

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

### 4. Execution helper / runner protocol layer

Modules:

- `govengine.api`
- `govengine.execution.approved_spec`
- `govengine.execution.ticket_gate`
- `govengine.execution.command_shape`
- `govengine.execution.runner`
- `govengine.execution.runner_protocol`
- `govengine.execution_backend`

Purpose:

- expose stable API result/error envelopes for hard boundaries;
- validate approved execution specs;
- check execution-ticket presence/shape;
- normalize command shape and target observations;
- assemble dry-run result envelopes;
- define the carrier-neutral runner request/receipt protocol a host adapter can honor.

Important: live subprocess execution is not owned by GovEngine yet. The runner protocol prepares and records bounded execution shape; host adapters still own concrete IO/subprocess behavior.

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

Module:

- `govengine.ooda`

Purpose:

- observe normalized execution telemetry and operator-control events;
- orient observations against approved specs, execution tickets, policy decisions, scope, budgets, and host state;
- decide whether the next step should continue, pause, abort, cooldown, degrade to dry-run, or require owner review;
- act by returning deterministic control decisions to the host runner/adapter.

This layer converts Ravenclaw's existing scattered controls — stop/pause, host health gates, cooldowns, runtime decisions, and anomaly/replay checks — into a reusable GovEngine contract. It is policy-first, deterministic by default, and carrier-neutral.

## Boundary rule

GovEngine can consume SCLite and host-supplied context. It should not import Ravenclaw `engine/*`, Logdash, OpenClaw session wiring, or protocol adapters.

```text
allowed:   Ravenclaw -> GovEngine -> SCLite
forbidden: GovEngine -> Ravenclaw engine/*
forbidden: GovEngine -> Logdash/OpenClaw/MCP/A2A adapters
```

## Current maturity

The package currently covers dry-run-safe helpers and contract/policy seams. It is not yet a complete orchestrator/scheduler/supervisor stack and does not claim production execution safety on its own. The roadmap moves toward that kernel through neutral contracts, profile adapters, and negative-tested execution gates rather than mechanical migration of Ravenclaw files.
