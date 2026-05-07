# GovEngine API Boundary

## Owns

GovEngine owns carrier-neutral governed-execution services:

- `govengine.action_schema` — action type/capability constants and limits.
- `govengine.action_validators` — action/probe shape validation.
- `govengine.action_compiler` — action spec lowering into execution plans.
- `govengine.capability_recipes` — capability and recipe resolution.
- `govengine.semantic_loss_policy` — semantic-loss classification/gates.
- `govengine.policy.*` — policy core and gateway helpers.
- `govengine.contracts.*` — execution-contract shaping/redaction helpers.
- `govengine.execution.*` — approved-spec/ticket/command-shape/dry-run helpers.
- `govengine.scope` — neutral scope helpers and `GovScopePort`.
- `govengine.state_store` — neutral JSON state helper primitives.
- `govengine.sclite_*` — explicit integration seams with SCLite.

## Does not own

GovEngine must not own Ravenclaw-specific runtime/application concerns:

- Logdash UI/API routes;
- Ravenclaw public snapshot assembly/publishing scripts;
- OpenClaw session wiring;
- BRAIN/AUDITOR/ANALYSIS/LIGHT prompts/personas;
- LLM provider configuration;
- protocol adapters such as MCP/A2A;
- live target campaign orchestration UX;
- public demo branding/docs owned by Ravenclaw.

## Execution backend rule

Live subprocess execution is intentionally absent from this scaffold.

Before any execution backend moves into GovEngine:

1. define a small runner protocol/result object;
2. keep Ravenclaw's subprocess runner as the first concrete adapter;
3. validate dry-run and scope enforcement parity;
4. add failure/redaction/artifact tests;
5. require operator review before making GovEngine own live execution mechanics.

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
