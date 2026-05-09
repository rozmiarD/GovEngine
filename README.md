# GovEngine

[![pytest](https://github.com/rozmiarD/GovEngine/actions/workflows/pytest.yml/badge.svg)](https://github.com/rozmiarD/GovEngine/actions/workflows/pytest.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)
[![Package: govengine 0.1.5](https://img.shields.io/badge/package-govengine%200.1.5-blueviolet.svg)](pyproject.toml)
[![SCLite](https://img.shields.io/badge/SCLite-contract%20lifecycle-informational.svg)](https://github.com/rozmiarD/SCLite)

GovEngine is a carrier-agnostic governed-execution core for portable artifact governance and policy-gated controlled execution.

It consumes **SCLite** as its contract lifecycle layer and provides reusable services around artifact state/transition boundaries, policy decisions, execution-contract shaping, execution-ticket checks, command-shape normalization, and dry-run result assembly. Security-oriented action/tool/scope/signal helpers remain available as an optional profile for hosts such as Ravenclaw, not as the neutral core itself.

Project owner: **Krzysztof Probola**.

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
- **Ravenclaw** remains the reference runtime/control plane and concrete integration host.

GovEngine is **not** Ravenclaw, Logdash, an LLM agent loop, a scanner, or a protocol adapter.

## What GovEngine includes now

- a public surface registry that separates neutral artifact-governance core, controlled-execution core, and optional security-profile helpers;
- an explicit `govengine.security_profile` facade for optional security-profile helper discovery;
- execution-contract shaping/redaction helpers;
- artifact descriptor/state/transition boundary helpers;
- SCLite lifecycle status bridge and lightweight lifecycle transition gate/controller;
- artifact deconfliction/change-order helpers and lightweight state-index summaries;
- signature/trust policy bridge helpers with host-provided verifier ports;
- approved-spec and execution-ticket validation helpers;
- controlled execution gate helpers with dry-run as the default runner path;
- command-shape helpers;
- dry-run result assembly helpers;
- optional security-profile helpers for action schema/validation/compilation, capability recipes, tool registry, semantic-loss policy, scope checks, policy gateway, and signal/analysis/evidence-confirmation contracts;
- explicit SCLite integration seams;
- focused standalone pytest coverage and GitHub Actions CI.

## What it intentionally does not include yet

- live subprocess execution backend;
- raw artifact storage/writes;
- Logdash UI/API routes;
- OpenClaw, MCP, A2A, or other protocol adapters;
- LLM provider integrations;
- Ravenclaw-specific personas, workspace state, or campaign UX;
- production-readiness claims.

## Current status

GovEngine is **pre-alpha extraction work**. The package is importable and tested. The `0.1.3` line added initial artifact-governance control gates while keeping live execution disabled by default. The `0.1.4` line added an explicit surface registry so reviewers can distinguish the neutral core from optional security-profile helpers. The published `0.1.5` line adds a security-profile facade for one-entrypoint helper discovery. Ravenclaw has a host adapter for the control gates, and still retains concrete runtime execution ownership.

## Installation

Install the current public package from PyPI:

```bash
python -m pip install govengine
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
- [`docs/VALIDATION.md`](docs/VALIDATION.md) — local checks and non-claims.
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — staged extraction roadmap.

## Safety boundary

GovEngine should preserve deterministic governance over prompt-only behavior. GovEngine must never execute directly from raw intent: execution requires a prepared execution contract, valid policy decision, approved execution ticket, valid signature/trust decision, and allowed runner profile.

`DryRunRunner`/dry-run behavior remains the default. Live execution backends are disabled by default; any future `LocalSubprocessRunner` must be optional, policy-enabled, negative-tested, and never the default. Controlled execution depends on lifecycle gates and signing/trust gates, with Ravenclaw retaining the concrete runtime adapter until reviewed.
