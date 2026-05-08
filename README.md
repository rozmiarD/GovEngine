# GovEngine

[![pytest](https://github.com/rozmiarD/GovEngine/actions/workflows/pytest.yml/badge.svg)](https://github.com/rozmiarD/GovEngine/actions/workflows/pytest.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)
[![Package: govengine 0.0.0](https://img.shields.io/badge/package-govengine%200.0.0-blueviolet.svg)](pyproject.toml)
[![SCLite](https://img.shields.io/badge/SCLite-contract%20lifecycle-informational.svg)](https://github.com/rozmiarD/SCLite)

GovEngine is the carrier-agnostic governed-execution core being extracted from Ravenclaw.

Project owner: **Krzysztof Probola**.

It is intended to own reusable, policy-bound execution services:

- action schema, validation, and compiler helpers;
- policy gates and tool registry evaluation;
- execution-contract shaping and redaction helpers;
- approved-spec and execution-ticket validation helpers;
- command-shape, scope, and dry-run result assembly helpers;
- SCLite lifecycle verification integration.

Dependency direction:

```text
Ravenclaw -> GovEngine -> SCLite
```

GovEngine is **not** Ravenclaw, Logdash, an LLM agent loop, or a protocol adapter. Ravenclaw remains the reference runtime, public demo/snapshot publisher, operator control plane, and owner of Ravenclaw-specific defaults/personas/UI.

## Current status

This repository scaffold is pre-alpha extraction work. It validates the package boundary before public repo creation or live execution migration.

Currently included:

- importable `govengine` package;
- package-local YAML data for capability recipes and tool registry defaults;
- focused standalone tests;
- GitHub Actions pytest workflow.

Not included yet:

- live subprocess execution backend;
- artifact writes;
- Logdash or Ravenclaw UI routes;
- OpenClaw/MCP/A2A/protocol adapters;
- LLM provider integrations;
- production deployment promises.

## Install for local development

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
python -m pytest -q
```

## Minimal smoke example

```python
from govengine.action_compiler import compile_action_spec
from govengine.execution.runner import legacy_action_spec_dry_run_result

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

## Safety boundary

GovEngine should preserve deterministic governance over prompt-only behavior. Any future execution backend must be introduced behind explicit interfaces and tests, with Ravenclaw retaining the concrete runtime adapter until reviewed.
