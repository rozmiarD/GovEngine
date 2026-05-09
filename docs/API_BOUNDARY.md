# GovEngine API Boundary

GovEngine owns reusable governed-execution services. Its public surface should stay carrier-neutral and SCLite-aware.

## Owns

GovEngine owns:

- `govengine.core` — portable artifact descriptors/envelopes/state, governance context, transition decisions, reason codes, and execution-prerequisite guardrails.
- `govengine.deconfliction` / `govengine.state_index` — digest/state conflict, change-order, and lightweight artifact state summary helpers.
- `govengine.lifecycle` — lightweight artifact lifecycle transition policy/gate/controller helpers.
- `govengine.signing` — signature envelopes, signing/trust policy objects, host-provided signer/verifier ports, and signature transition decisions without PKI/key ownership.
- `govengine.action_schema` — action type/capability constants and limits.
- `govengine.action_validators` — action/probe shape validation.
- `govengine.action_compiler` — action spec lowering into execution plans.
- `govengine.capability_recipes` — capability and recipe resolution.
- `govengine.semantic_loss_policy` — semantic-loss classification/gates.
- `govengine.policy.*` — policy core and gateway helpers.
- `govengine.contracts.*` — execution-contract shaping/redaction helpers plus signal, analysis, and confirmation-evidence policy contracts.
- `govengine.execution.*` — approved-spec, ticket, command-shape, dry-run helpers, and controlled execution gates that keep live backends disabled by default.
- `govengine.scope` — neutral scope helpers and `GovScopePort`.
- `govengine.state_store` — neutral JSON state helper primitives.
- `govengine.sclite_*` — explicit integration seams with SCLite, including descriptor/status/transition mapping that delegates lifecycle verification to SCLite.

## Consumes

GovEngine consumes:

- SCLite schemas, lifecycle helpers, and verification surfaces;
- host-provided filesystem/context paths;
- host-provided policy/scope/tool registry data.

## Does not own

GovEngine must not own Ravenclaw-specific runtime/application concerns:

- Logdash UI/API routes;
- Ravenclaw public snapshot assembly/publishing scripts;
- OpenClaw session wiring;
- BRAIN/AUDITOR/ANALYSIS/LIGHT prompts/personas;
- LLM provider configuration;
- PKI, CA, KMS, key storage, or trust-store ownership;
- protocol adapters such as MCP/A2A;
- live target campaign orchestration UX;
- public demo branding/docs owned by Ravenclaw.

## Execution backend rule

Live subprocess execution is intentionally absent from this scaffold and remains disabled by default for future live backends.

GovEngine must never execute directly from raw intent. Execution requires all of the following boundary inputs:

1. prepared execution contract;
2. valid policy decision;
3. approved execution ticket;
4. valid signature/trust decision;
5. allowed runner profile.

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
