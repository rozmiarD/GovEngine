# GovEngine Architecture

GovEngine is a deterministic governed-runtime kernel in alpha form. It is designed to sit between a host/domain runtime and the SCLite contract lifecycle.

```text
host runtime -> GovEngine -> SCLite
```

For the current extraction, the host/domain runtime is Ravenclaw. A future infrastructure-operations runtime/profile is reserved as Tecrax. Later carriers may include OpenClaw, MCP/A2A-style transports, or other local harnesses, but GovEngine should not become a carrier-specific adapter or a domain product shell.

## Layers

### 0. Kernel/profile boundary layer

Module:

- `govengine.boundary`

Purpose:

- make the kernel/profile/runtime/SCLite ownership split serializable;
- let hosts declare domain-profile ownership without claiming GovEngine core, SCLite authority, live execution authority, credentials, or carrier adapter ownership;
- provide a tested Ravenclaw profile contract as the current host-profile example.

### 1. Admission and review contract layer

Modules:

- `govengine.admission`
- `govengine.review`

Purpose:

- validate neutral admission, policy-decision, approval, audit, evidence, and
  review records;
- keep security-domain policy meaning and evidence taxonomy in the host runtime.

### 2. Contract layer

Modules:

- `govengine.contracts.execution`
- `govengine.sclite_contracts`

Purpose:

- shape execution contracts and approval payloads;
- redact prepared execution specs for auditor/reviewer surfaces;
- map SCLite lifecycle/review results into neutral GovEngine state and transition decisions.

Lifecycle artifact projection from a host runtime payload is host-owned;
Ravenclaw implements its projection outside this kernel.

### 3. Execution helper / runner protocol layer

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

### 4. Host context and scope-port layer

Modules:

- `govengine.context`
- `govengine.scope_ports`
- `govengine.state_store`

Purpose:

- let a host runtime provide paths, neutral scope-port behavior, and state surfaces explicitly;
- retain `host_compat_context()` for package-in-place context injection while
  hosts migrate independently of retired security-domain helpers;
- avoid hard dependencies on Ravenclaw internals;
- support standalone import and package testing.

### 5. OODA safety/control layer

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

The package currently covers dry-run-safe helpers and neutral contract gates. The `0.12.0-alpha` candidate removes former Ravenclaw-derived security helper modules rather than treating them as kernel capabilities. GovEngine is not yet a complete orchestrator/scheduler/supervisor stack and does not claim production execution safety on its own.
