# GovEngine API Boundary

GovEngine owns reusable governed-execution services. Its public surface should stay carrier-neutral and SCLite-aware.

`govengine.surfaces.public_surface_index()` is the tested machine-readable map of the current pre-alpha public surfaces. It separates the neutral artifact-governance core, the controlled-execution core, and optional security-profile helpers. `govengine.security_profile.security_profile_index()` is the tested convenience facade for hosts that want to discover the optional security-profile helpers through one entrypoint without treating them as neutral core.
`govengine.boundary.kernel_boundary_report()` is the tested machine-readable 0.2 boundary report. It combines the kernel/profile/runtime/SCLite ownership contract, known domain-profile contracts such as Ravenclaw, and the current public surface index.

## Public surface groups

### Artifact-governance core

Neutral core modules:

- `govengine.boundary`
- `govengine.core`
- `govengine.sclite_contracts`
- `govengine.lifecycle`
- `govengine.signing`
- `govengine.deconfliction`
- `govengine.state_index`
- `govengine.state_store`

Claim: portable kernel/profile boundary contracts, artifact descriptor/state/transition, lifecycle and review-bundle bridges, signing/trust decision, deconfliction, and state-index helpers. Non-claims: SCLite schema/canonicalization/review ownership, PKI/key-store ownership, raw artifact storage ownership, workflow scheduler ownership.

### Controlled-execution core

Neutral controlled-execution modules:

- `govengine.execution.*`
- `govengine.contracts.execution`
- `govengine.ooda`

Claim: approved-spec, execution-ticket, command-shape, runner receipt, OODA, and dry-run-only execution-gate helpers. Non-claims: raw-intent execution, default live subprocess execution, scanner/campaign execution ownership, protocol adapter ownership.

### Optional security-profile helpers

Security-oriented helpers are explicit optional profile modules, not the neutral artifact-governance core:

- `govengine.action_schema`
- `govengine.action_validators`
- `govengine.action_compiler`
- `govengine.capability_recipes`
- `govengine.tool_registry`
- `govengine.semantic_loss_policy`
- `govengine.policy.*`
- `govengine.scope`
- `govengine.contracts.signal`
- `govengine.contracts.analysis`
- `govengine.contracts.evidence_policy`

Claim: reusable public-safe helpers for hosts such as Ravenclaw that need bounded action/tool/scope/policy/signal behavior. The `govengine.security_profile` facade groups these helpers into `action_tooling`, `policy_scope`, and `review_contracts`, and exposes allowlisted lazy imports for those modules only. Non-claims: live exploit/scanner capability, authorization to test targets, bug-bounty campaign orchestration, Logdash/Ravenclaw runtime ownership, or OpenClaw/MCP/A2A adapter ownership.

## Owns

GovEngine owns:

- `govengine.boundary` — serializable kernel/profile/runtime/SCLite ownership contracts and profile-boundary validation helpers.
- `govengine.core` — portable artifact descriptors/envelopes/state, governance context, transition decisions, reason codes, and execution-prerequisite guardrails.
- `govengine.deconfliction` / `govengine.state_index` — digest/state conflict, change-order, and lightweight artifact state summary helpers.
- `govengine.lifecycle` — lightweight artifact lifecycle transition policy/gate/controller helpers.
- `govengine.signing` — signature envelopes, signing/trust policy objects, host-provided signer/verifier ports, deterministic demo signer/verifier fixture ports, and signature transition decisions without PKI/key ownership.
- `govengine.security_profile` — optional security-profile facade for helper discovery, grouped metadata, allowlisted lazy imports, and boundary assertions.
- `govengine.action_schema` — optional security-profile action type/capability constants and limits.
- `govengine.action_validators` — optional security-profile action/probe shape validation.
- `govengine.action_compiler` — optional security-profile action spec lowering into execution plans.
- `govengine.capability_recipes` — optional security-profile capability and recipe resolution.
- `govengine.semantic_loss_policy` — optional security-profile semantic-loss classification/gates.
- `govengine.policy.*` — optional security-profile policy core and gateway helpers.
- `govengine.contracts.*` — execution-contract shaping/redaction helpers plus optional security-profile signal, analysis, and confirmation-evidence policy contracts.
- `govengine.execution.*` — approved-spec, ticket, command-shape, dry-run helpers, and controlled execution gates that keep live backends disabled by default.
- `govengine.scope` — optional security-profile scope helpers and `GovScopePort`.
- `govengine.state_store` — neutral JSON state helper primitives.
- `govengine.sclite_*` — explicit integration seams with SCLite, including descriptor/status/transition mapping that delegates lifecycle verification and review-bundle verdicts to SCLite.

## Consumes

GovEngine consumes:

- SCLite schemas, lifecycle helpers, review-bundle helpers, and verification surfaces;
- host-provided filesystem/context paths;
- host-provided policy/scope/tool registry data.

## Does not own

GovEngine must not own Ravenclaw-specific runtime/application concerns:

- Logdash UI/API routes;
- Ravenclaw public snapshot assembly/publishing scripts;
- OpenClaw session wiring;
- BRAIN/AUDITOR/ANALYSIS/LIGHT prompts/personas;
- LLM provider configuration;
- PKI, CA, KMS, key storage, trust-store ownership, or production identity proof;
- protocol adapters such as MCP/A2A;
- live target campaign orchestration UX;
- public demo branding/docs owned by Ravenclaw.

## Demo signing fixture rule

`DemoDigestSigner`, `DemoDigestVerifier`, and `demo_sign_and_verify` are test/reviewer helpers. They create deterministic digest-bound demo signatures so hosts can exercise the `SignerPort`/`VerifierPort` contract and inspect trust decisions without bringing real keys into GovEngine. They are not cryptographic identity proof, not a CA/KMS/key-store, and not a replacement for a host-owned production verifier. Hosts that need real signatures must provide their own signer/verifier ports and trust policy.

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
