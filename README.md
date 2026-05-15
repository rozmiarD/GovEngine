# GovEngine

[![CI: pytest](https://github.com/rozmiarD/GovEngine/actions/workflows/pytest.yml/badge.svg)](https://github.com/rozmiarD/GovEngine/actions/workflows/pytest.yml)
[![Package: govengine](https://img.shields.io/pypi/v/govengine?label=package%3A%20govengine&color=blueviolet)](https://pypi.org/project/govengine/)
[![Python: 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)
[![Dependency: SCLite >=0.5.1](https://img.shields.io/badge/dependency-SCLite%20%3E%3D0.5.1-informational.svg)](https://github.com/rozmiarD/SCLite)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

GovEngine is a carrier-agnostic deterministic governed-runtime kernel for portable artifact governance and policy-gated controlled execution.

It consumes **SCLite** as its contract lifecycle layer and provides reusable services around artifact state/transition boundaries, policy decisions, execution-contract shaping, execution-ticket checks, command-shape normalization, and dry-run result assembly. Security-oriented action/tool/scope/signal helpers remain available as an optional profile for hosts such as Ravenclaw, not as the neutral core itself.


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
- an explicit `govengine.security_profile` facade for optional security-profile helper discovery;
- execution-contract shaping/redaction helpers;
- artifact descriptor/state/transition boundary helpers;
- SCLite lifecycle status bridge and lightweight lifecycle transition gate/controller;
- artifact deconfliction/change-order helpers and lightweight state-index summaries;
- signature/trust policy bridge helpers with host-provided signer/verifier ports and deterministic demo ports for fixtures;
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
- production-readiness claims;
- PKI, CA, KMS, key storage, or production identity proof.

## Current status

GovEngine is a **pre-alpha 0.1.x helper package**. The package is importable, tested, and published through `0.1.7`. The `0.1.3` line added artifact-governance control gates while keeping live execution disabled by default. The `0.1.4` line added a surface registry that separates the neutral core from optional security-profile helpers. The `0.1.5` line adds a security-profile facade for one-entrypoint helper discovery. The `0.1.6` line consumes `sclite-core>=0.3.5,<0.4`, includes thin scoped-ticket / receipt-bounded-evidence gates, and contains deterministic demo signer/verifier ports for host proof fixtures; those ports exercise signing/trust seams without claiming PKI/key ownership. The `0.1.7` line consumes `sclite-core>=0.5.1,<0.6` and adds a thin SCLite review-bundle bridge for the packaged GovEngine integration fixtures. Ravenclaw has a host adapter for the control gates and still owns concrete runtime execution.

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

`DryRunRunner`/dry-run behavior remains the default. Live execution backends are disabled by default; any future `LocalSubprocessRunner` must be optional, policy-enabled, negative-tested, and never the default. Controlled execution depends on lifecycle gates and signing/trust gates, with Ravenclaw retaining the concrete runtime adapter until reviewed. Demo signing helpers are fixture ports only: they bind a deterministic signature to an artifact digest for tests/reviewer demos and must not be presented as cryptographic identity, PKI, CA, KMS, or trust-store support.
