# GovEngine

[![CI: pytest](https://github.com/rozmiarD/GovEngine/actions/workflows/pytest.yml/badge.svg)](https://github.com/rozmiarD/GovEngine/actions/workflows/pytest.yml)
[![Package: govengine 0.11.0a0](https://img.shields.io/badge/package-govengine%200.11.0a0-blueviolet.svg)](https://pypi.org/project/govengine/0.11.0a0/)
[![Python: 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)
[![Dependency: SCLite >=0.8.0a0](https://img.shields.io/badge/dependency-SCLite%20%3E%3D0.8.0a0-informational.svg)](https://github.com/rozmiarD/SCLite)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

GovEngine is a carrier-agnostic deterministic governed-runtime kernel for portable artifact governance and policy-gated controlled execution.

It consumes **SCLite** as its contract lifecycle layer and provides reusable services around artifact state/transition boundaries, policy decisions, execution-contract shaping, execution-ticket checks, command-shape normalization, dry-run result assembly, and neutral runtime/control projections. Security-oriented action/tool/scope/signal helpers remain available as optional Ravenclaw-derived compatibility helpers, not as the neutral core itself.


## Why it exists

AI-assisted security workflows need a hard boundary between:

1. what an agent or caller wants;
2. what policy allows;
3. what execution shape was prepared;
4. what was approved;
5. what was dry-run or executed;
6. what evidence can be reviewed.

SCLite defines the auditable contract artifacts for that lifecycle. GovEngine is the reusable Python service layer that consumes those contracts and helps a host runtime enforce them without relying on prompt text alone.

## Dependency direction

```text
Ravenclaw -> GovEngine -> SCLite
```

- **SCLite** owns schema-backed lifecycle artifacts and validation.
- **GovEngine** owns reusable governed-execution helpers that consume SCLite artifacts.
- **Ravenclaw** remains the reference security runtime/control plane and concrete integration host.
- **Tecrax** is reserved as a future infrastructure-operations runtime/profile on the same foundation.

GovEngine is **not** Ravenclaw, Tecrax, Logdash, an LLM agent loop, a scanner, or a protocol adapter.

## What GovEngine includes now

- a public surface registry that separates neutral artifact-governance core, controlled-execution core, and optional security-profile helpers;
- an explicit `govengine.security_profile` compatibility facade for optional Ravenclaw-derived helper discovery;
- serializable kernel/profile/runtime/SCLite boundary contracts and a machine-readable boundary report;
- execution-contract shaping/redaction helpers;
- artifact descriptor/state/transition boundary helpers;
- SCLite lifecycle status bridge and lightweight lifecycle transition gate/controller;
- artifact deconfliction/change-order helpers and lightweight state-index summaries;
- signature/trust policy bridge helpers with host-provided signer/verifier ports and deterministic demo ports for fixtures;
- approved-spec and execution-ticket validation helpers;
- controlled execution gate helpers with dry-run as the default runner path;
- command-shape helpers;
- dry-run result assembly helpers;
- deterministic orchestration handoff, governance event envelope, run-state, and between-step control-decision contracts;
- neutral runtime-shell contracts for host control actions, queue snapshots, runtime snapshots, and scheduler-tick metadata;
- neutral planning contracts for task, plan-intent, and planner-port handoffs;
- neutral admission, policy, approval, and audit contracts for host runtime gates;
- optional compatibility helpers for action schema/validation/compilation, capability recipes, tool registry, semantic-loss policy, scope checks, policy gateway, and signal/analysis/evidence-confirmation contracts;
- explicit SCLite integration seams;
- focused standalone pytest coverage and GitHub Actions CI.

## What it intentionally does not include yet

- live subprocess execution backend;
- raw artifact storage/writes;
- Logdash UI/API routes;
- OpenClaw, MCP, A2A, or other protocol adapters;
- LLM provider integrations;
- Ravenclaw-specific personas, workspace state, or campaign UX;
- production-readiness claims;
- PKI, CA, KMS, key storage, or production identity proof.

## Current status

GovEngine is an **alpha 0.11.0a0 (`0.11.0-alpha`) kernel package candidate**. The package is importable, tested, package-buildable, and validated against the Ravenclaw public downstream contract surface. The active dependency line is `sclite-core>=0.8.0a0,<0.9`. The `0.11.x` line contains neutral artifact governance, planning, admission/policy, controlled-execution, runner-supervision, runtime-shell, evidence-review contracts, a minimal contract-only Domain Profile SDK, and runtime contract proof fixtures plus optional security-profile helpers. It removes the Ravenclaw-shaped lifecycle assembly module: SCLite retains artifact/review ownership and Ravenclaw owns its lifecycle projection and public proof. Historical lines through `0.10.2-alpha` are documented in `CHANGELOG.md`; current status docs should treat `0.11.0a0` as the source candidate until release gates and publication complete.

## Installation

Install the current public alpha package from PyPI with an exact version pin:

```bash
python -m pip install govengine==0.11.0a0
```

GovEngine depends on the PyPI distribution `sclite-core` while preserving the Python import package `sclite`.

For local development:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
python -m pytest -q
```

## Minimal smoke example

```python
from govengine import public_surface_index, security_profile_index
from govengine.action_compiler import compile_action_spec
from govengine.execution.runner import legacy_action_spec_dry_run_result

assert [surface.name for surface in public_surface_index()] == [
    "artifact_governance_core",
    "planning_contracts_core",
    "admission_policy_core",
    "evidence_review_core",
    "domain_profile_sdk",
    "runtime_contract_proofs",
    "controlled_execution_core",
    "security_profile_helpers",
]
assert security_profile_index()["entrypoint"] == "govengine.security_profile"

compiled = compile_action_spec({
    "action_type": "single_probe",
    "capability": "http_probe",
    "tool": "curl",
    "args": ["https://example.com"],
})

receipt = legacy_action_spec_dry_run_result(
    compiled_action=compiled,
    planned_commands=[["curl", "https://example.com"]],
)
assert receipt["status"] == "dry-run"
```

## Documentation

- [`PUBLIC_STATUS.md`](PUBLIC_STATUS.md) — current maturity and non-claims.
- [`CHANGELOG.md`](CHANGELOG.md) — notable public changes.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — contribution and boundary rules.
- [`SECURITY.md`](SECURITY.md) — security reporting and package safety boundaries.
- [`PUBLISHING.md`](PUBLISHING.md) — publishing/PyPI readiness checklist.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — package shape and dependency boundaries.
- [`docs/SCLITE_INTEGRATION.md`](docs/SCLITE_INTEGRATION.md) — how GovEngine consumes SCLite.
- [`docs/API_BOUNDARY.md`](docs/API_BOUNDARY.md) — owned vs excluded surfaces.
- [`docs/GOVENGINE_KERNEL_BOUNDARY.md`](docs/GOVENGINE_KERNEL_BOUNDARY.md) — kernel/profile/runtime/SCLite ownership split.
- [`docs/DOMAIN_PROFILE_CONTRACT.md`](docs/DOMAIN_PROFILE_CONTRACT.md) — domain profile contract and conformance rules.
- [`docs/ORCHESTRATOR_MODEL.md`](docs/ORCHESTRATOR_MODEL.md) — deterministic orchestration boundary and runtime non-claims.
- [`docs/EVENT_MODEL.md`](docs/EVENT_MODEL.md) — neutral governance event metadata and payload boundaries.
- [`docs/STATE_MACHINE.md`](docs/STATE_MACHINE.md) — neutral run-state and transition contract.
- [`docs/CONTROL_MODEL.md`](docs/CONTROL_MODEL.md) — between-step control decisions and state-machine delegation.
- [`docs/RUNTIME_SHELL.md`](docs/RUNTIME_SHELL.md) — neutral host runtime/control projection contracts.
- [`docs/VALIDATION.md`](docs/VALIDATION.md) — local checks and non-claims.
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — staged extraction roadmap.

## Safety boundary

GovEngine should preserve deterministic governance over prompt-only behavior. GovEngine must never execute directly from raw intent: execution requires a prepared execution contract, valid policy decision, approved execution ticket, valid signature/trust decision, and allowed runner profile.

`DryRunRunner`/dry-run behavior remains the default. Live execution backends are disabled by default; any future `LocalSubprocessRunner` must be optional, policy-enabled, negative-tested, and never the default. Controlled execution depends on lifecycle gates and signing/trust gates, with Ravenclaw retaining the concrete runtime adapter until reviewed. Demo signing helpers are fixture ports only: they bind a deterministic signature to an artifact digest for tests/reviewer demos and must not be presented as cryptographic identity, PKI, CA, KMS, or trust-store support.
