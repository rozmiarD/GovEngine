# GovEngine Public Status

GovEngine is a **pre-alpha governed-runtime kernel package** extracted from Ravenclaw in contract-first stages.

## Current maturity

- Package import: working.
- Standalone tests: present.
- GitHub Actions: pytest on supported Python versions.
- Version: `0.1.7` in source; PyPI remains published through `0.1.6` until an explicit release.
- SCLite integration: present through helper seams via `sclite-core>=0.5.1,<0.6`.
- Runner protocol: dry-run/control-plane shape only.
- OODA safety loop: deterministic between-step decision contract.
- Core artifact governance boundaries: initial portable dataclasses for artifact descriptors/envelopes/state, governance context, transition decisions, and execution prerequisites.
- SCLite lifecycle/review bridge: descriptor/state/transition mapping and review-bundle verdict mapping that delegate verification and review semantics to SCLite.
- Artifact lifecycle controller: initial transition policy/gate/controller for ordered lifecycle transitions and blocker/next-action reporting.
- Signing/trust bridge: initial signature envelope, policy, trust result, signer/verifier port, transition-decision helpers, and unreleased deterministic demo signer/verifier ports without PKI/key ownership.
- Controlled execution gate: initial dry-run-only execution gate and default `DryRunRunner`; live requests are blocked by default.
- Public surface registry: tested `govengine.surfaces` metadata separates neutral artifact-governance core, controlled-execution core, and optional security-profile helpers.
- Security profile: action/tool/scope/policy/signal helpers are available through the optional `govengine.security_profile` facade for host-facing discovery, not as the neutral core.
- Deconfliction/state index: initial conflict/change-order helpers and lightweight artifact state summaries.
- Live subprocess execution: not owned by GovEngine and disabled by default for future live backends.
- Carrier adapters: deferred.
- PyPI publication: completed through `0.1.6`; `0.1.7` is source-prepared but not tagged or uploaded. Each new release still requires the standard release checklist and operator approval before upload.

## What is public-safe today

GovEngine can be reviewed as a small Python package for:

- portable artifact descriptor/envelope/state and transition-decision boundary objects;
- lightweight artifact lifecycle transition gate/controller helpers;
- signature/trust policy bridge helpers that require host-provided verification, plus deterministic demo ports for public-safe fixture/reviewer examples;
- dry-run-only controlled execution gate helpers and default dry-run runner;
- artifact deconfliction/change-order and state-index summaries;
- public surface metadata for current pre-alpha API boundary review;
- a security-profile facade that groups optional action/tooling, policy/scope, and review-contract helpers behind one tested entrypoint;
- governed action/spec validation helpers as optional security-profile helpers;
- policy and scope helper seams as optional security-profile helpers;
- execution-ticket and approved-spec validation helpers;
- runner request/receipt shapes;
- OODA decision objects;
- signal, analysis, and evidence-confirmation contracts extracted from Ravenclaw;
- SCLite lifecycle/review integration boundaries and status/verdict mapping into portable GovEngine state/transition objects.

## What is not claimed

GovEngine does not currently claim:

- production runtime readiness;
- direct execution from raw intent;
- live exploit or scanner capability;
- authorization to run tools against targets;
- bug-bounty campaign orchestration ownership;
- protocol adapter correctness;
- complete API stability;
- production/stable PyPI API readiness;
- PKI, CA, KMS, trust-store, or key-management ownership;
- a full replacement for Ravenclaw Runtime;
- Tecrax infrastructure-domain semantics, credentials, or product UX.

## Controlled execution posture

Controlled execution is a later capability, not the current default. Execution must be gated by a prepared execution contract, valid policy decision, approved execution ticket, valid signature/trust decision, and allowed runner profile. Dry-run behavior is the default; live backends are optional future work and must stay disabled by default.

## Release posture

Keep GovEngine in `0.y.z` until:

1. GovEngine's public API boundary remains documented and tested enough for external users;
2. changelog, security, contribution, validation, and publishing docs stay complete;
3. release artifacts can be built and checked reproducibly;
4. Ravenclaw consumes the released package without Git URL pin drift.
