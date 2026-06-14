# GovEngine

[![CI: pytest](https://github.com/rozmiarD/GovEngine/actions/workflows/pytest.yml/badge.svg)](https://github.com/rozmiarD/GovEngine/actions/workflows/pytest.yml)
[![Package: govengine 0.13.0](https://img.shields.io/badge/package-govengine%200.13.0-blueviolet.svg)](https://pypi.org/project/govengine/0.13.0/)
[![Python: 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)
[![Dependency: SCLite >=1.0.2](https://img.shields.io/badge/dependency-SCLite%20%3E%3D1.0.2-informational.svg)](https://github.com/rozmiarD/SCLite)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

GovEngine is a carrier-agnostic deterministic governed-runtime kernel for portable artifact governance and policy-gated controlled execution.

It consumes **SCLite** as its contract lifecycle layer and provides reusable services around artifact state/transition boundaries, policy decisions, execution-contract shaping, execution-ticket checks, command-shape normalization, dry-run result assembly, and neutral runtime/control projections. Security-domain action, tool, scope, and signal behavior is host-owned; the published `0.12` alpha line removes the former Ravenclaw-derived compatibility helpers.


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

- a public surface registry covering neutral artifact-governance, planning, admission/policy, evidence-review, domain-profile, runtime-proof, and controlled-execution surfaces;
- serializable kernel/profile/runtime/SCLite boundary contracts and a machine-readable boundary report;
- execution-contract shaping/redaction helpers;
- artifact descriptor/state/transition boundary helpers;
- SCLite lifecycle status bridge and lightweight lifecycle transition gate/controller;
- guarded-root replay checks for already-verified SCLite Kernel Guard sidecars;
- high-level guarded-strict verification plus replay-fresh runtime decisions;
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
- explicit SCLite integration seams;
- focused standalone pytest coverage and GitHub Actions CI.

The `0.13.0` line also adds:

- **one admission decision you can actually read** — a single `RuntimeAdmissionResult` record that summarizes whether a prepared request may proceed, what blocked it, and what to fix next; helpers compose and validate that record from separate policy, ticket, trust, guard, replay, runner, and receipt signals without running live work themselves;
- **replay freshness** — remember which verified SCLite guarded roots were already used, so the same protected bundle cannot silently count as “fresh” twice;
- **receipt and evidence chain checks** — confirm that a runner receipt still points at the right admission and ticket, and that later evidence or review references stay within the bounds of that receipt;
- **GovEngine-owned record signing for fixtures** — deterministic digests and signed-record helpers for tests and reviewer demos, not production PKI;
- **a development-only audit trail adapter** — append and verify a local hash-chained audit log during development, without claiming a production database;
- **runner safety posture** — supervision helpers that keep dry-run as the default and treat an optional local subprocess runner as not ready until explicit host safety gates exist;
- **operator inspect without executing** — `scripts/inspect_runtime_admission.py` lets you read and summarize an admission record read-only, with no runner request, replay claim, audit write, or live execution.

## What it intentionally does not include yet

- live subprocess execution backend;
- raw artifact storage/writes;
- Logdash UI/API routes;
- OpenClaw, MCP, A2A, or other protocol adapters;
- LLM provider integrations;
- Ravenclaw-specific personas, workspace state, or campaign UX;
- production-readiness claims;
- PKI, CA, KMS, key storage, or production identity proof;
- a shipped `LocalSubprocessRunner` implementation (`LocalSubprocessRunnerReadiness` is a gating contract only);
- production replay or audit persistence (`ReplayClaimStore` and `JsonlAuditLedgerAdapter` are host-owned or development-only adapters).

## Current status

GovEngine is an **alpha package 0.13.0 (`0.13.0`)**. It keeps the neutral artifact-governance, planning, admission/policy, controlled-execution, runner-supervision, runtime-shell, evidence-review, profile, and proof surfaces while removing the former optional security-profile facade and Ravenclaw-derived helper modules. The published dependency line is `sclite-core>=1.0.2,<1.1`.

## Current roadmap direction

The governed-runtime MVP on `main` includes a canonical `RuntimeAdmissionResult`
record as the bounded admission decision surface and
`compose_runtime_admission_result()` as the neutral gate-summary composition
helper. The helper composes prepared execution contract status, policy
decision, execution ticket status, trust decision, guarded-strict SCLite
verification when runtime-consumable, GovEngine replay freshness, runner
profile, receipt obligation, blockers, next actions, and bounded artifact
references into that record. `normalize_admission_artifact_refs()` is an alpha
helper for bounded review references and existing digest strings; it does not
compute content digests or claim SCLite canonicalization.

`compose_runtime_admission_result()` composes host-supplied gate summaries; it does not validate SCLite tickets, verify signatures, record replay state, or execute live work.

The operator-facing MVP flow is documented in
[`docs/GOVERNED_RUNTIME_MVP_RUNBOOK.md`](docs/GOVERNED_RUNTIME_MVP_RUNBOOK.md).
It ties admission, trust ports, guarded SCLite verification, replay freshness,
runner profile, receipt obligation, and evidence/review binding into one
inspectable dry-run/default-safe chain.

This roadmap does not make intent execution authority. It keeps profile/domain
policy meaning, production identity, key management, operator authorization,
raw evidence storage, and live backend behavior host-owned until explicit
ports, negative tests, and safety gates justify any additional kernel surface.

## Installation

Install the latest published package from PyPI:

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
python scripts/validate_public_truth.py
```

## Minimal smoke example

```python
from govengine import public_surface_index
from govengine.execution.runner import approved_spec_dry_run_result

assert [surface.name for surface in public_surface_index()] == [
    "artifact_governance_core",
    "planning_contracts_core",
    "admission_policy_core",
    "evidence_review_core",
    "domain_profile_sdk",
    "runtime_contract_proofs",
    "controlled_execution_core",
]

receipt = approved_spec_dry_run_result(
    approved_execution_spec={
        "action_type": "bounded_request",
        "capability": "fixture_review",
        "resolved_tool": "fixture",
        "execution_mode": "dry_run",
    },
    planned_commands=[["fixture", "review"]],
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
- [`docs/API_STABILITY_MATRIX.md`](docs/API_STABILITY_MATRIX.md) — alpha vs fixture export classification.
- [`docs/RUNTIME_ADMISSION.md`](docs/RUNTIME_ADMISSION.md) — canonical runtime admission contract direction.
- [`docs/GOVERNED_RUNTIME_MVP_RUNBOOK.md`](docs/GOVERNED_RUNTIME_MVP_RUNBOOK.md) — operator-facing governed-runtime MVP chain.
- [`docs/INSPECT_ONLY_ADMISSION_WORKFLOW.md`](docs/INSPECT_ONLY_ADMISSION_WORKFLOW.md) — read-only admission inspect workflow.
- [`docs/GUARDED_FRESH_RUNTIME_ADMISSION_EXAMPLE.md`](docs/GUARDED_FRESH_RUNTIME_ADMISSION_EXAMPLE.md) — guarded-strict plus replay-fresh example.
- [`docs/ADMISSION_POLICY.md`](docs/ADMISSION_POLICY.md) — neutral admission, policy, approval, audit, and audit-ledger contracts.
- [`docs/RECEIPT_BINDING.md`](docs/RECEIPT_BINDING.md) — admission/ticket/request/receipt binding design.
- [`docs/EVIDENCE_REVIEW.md`](docs/EVIDENCE_REVIEW.md) — receipt-bounded evidence/review contract.
- [`docs/RUNNER_SUPERVISION.md`](docs/RUNNER_SUPERVISION.md) — runner request, receipt, supervision, and live-runner safety boundaries.
- [`docs/LOCAL_SUBPROCESS_RUNNER_DECISION.md`](docs/LOCAL_SUBPROCESS_RUNNER_DECISION.md) — local subprocess runner decision record.
- [`docs/GOVENGINE_KERNEL_BOUNDARY.md`](docs/GOVENGINE_KERNEL_BOUNDARY.md) — kernel/profile/runtime/SCLite ownership split.
- [`docs/DOMAIN_PROFILE_CONTRACT.md`](docs/DOMAIN_PROFILE_CONTRACT.md) — domain profile contract and conformance rules.
- [`docs/ORCHESTRATOR_MODEL.md`](docs/ORCHESTRATOR_MODEL.md) — deterministic orchestration boundary and runtime non-claims.
- [`docs/EVENT_MODEL.md`](docs/EVENT_MODEL.md) — neutral governance event metadata and payload boundaries.
- [`docs/STATE_MACHINE.md`](docs/STATE_MACHINE.md) — neutral run-state and transition contract.
- [`docs/CONTROL_MODEL.md`](docs/CONTROL_MODEL.md) — between-step control decisions and state-machine delegation.
- [`docs/RUNTIME_SHELL.md`](docs/RUNTIME_SHELL.md) — neutral host runtime/control projection contracts.
- [`docs/VALIDATION.md`](docs/VALIDATION.md) — local checks and non-claims.
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — staged extraction roadmap.

## License and provenance

GovEngine is MIT-licensed. It was extracted from Ravenclaw in contract-first
stages, so [`LICENSE`](LICENSE) preserves the copyright notice for the
originating Ravenclaw contribution lineage. The author metadata in
`pyproject.toml` identifies the GovEngine package maintainer; it does not
replace or reassign the originating copyright notice.

## Safety boundary

GovEngine should preserve deterministic governance over prompt-only behavior. GovEngine must never execute directly from raw intent: execution requires a prepared execution contract, valid policy decision, approved execution ticket, valid signature/trust decision, and allowed runner profile. When a SCLite bundle is runtime-consumable, the execution gate also requires a guarded-strict SCLite verification result and replay-fresh GovEngine decision; review-only bundles can remain on weaker review/integrity postures without becoming execution authority.

`DryRunRunner`/dry-run behavior remains the default. Live execution backends are disabled by default; any future `LocalSubprocessRunner` must be optional, policy-enabled, negative-tested, and never the default. Controlled execution depends on lifecycle gates and signing/trust gates, with Ravenclaw retaining the concrete runtime adapter until reviewed. Demo signing helpers are fixture ports only: they bind a deterministic signature to an artifact digest for tests/reviewer demos and must not be presented as cryptographic identity, PKI, CA, KMS, or trust-store support.
