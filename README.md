# GovEngine

[![CI: pytest](https://github.com/rozmiarD/GovEngine/actions/workflows/pytest.yml/badge.svg)](https://github.com/rozmiarD/GovEngine/actions/workflows/pytest.yml)
[![Package: govengine 0.16.0](https://img.shields.io/badge/package-govengine%200.16.0-blueviolet.svg)](https://pypi.org/project/govengine/0.16.0/)
[![Python: 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)
[![Dependency: SCLite >=1.0.3](https://img.shields.io/badge/dependency-SCLite%20%3E%3D1.0.3-informational.svg)](https://github.com/rozmiarD/SCLite)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

GovEngine is an alpha package 0.16.0 (`0.16.0`) release line for deterministic governance-kernel contracts.

It consumes **SCLite** as the lower truth layer and exposes reusable Python records, validators, and composition helpers for admission decisions, lifecycle gates, policy/trust summaries, receipt binding, evidence review, replay freshness, and profile conformance. It does not run jobs. It does not own host runtime behavior. Carrier adapters, concrete schedulers, credentials, domain semantics, and live execution remain outside the kernel.

## Dependency Direction

```text
Tecrax profile -> RExecOp runtime -> GovEngine governance -> SCLite truth
Other host runtimes ----------------> GovEngine governance -> SCLite truth
```

- **SCLite** owns artifact lifecycle schemas, canonical descriptors, ordered hash-chain verification, guarded verification, tickets, receipts, and evidence truth records.
- **GovEngine** owns deterministic governance contracts over those truth records: admission envelopes, policy/trust/replay decisions, lifecycle state mapping, receipt/evidence binding, review qualification, profile conformance, and public-safe contract fixtures.
- **RExecOp** owns domain-neutral workflow interpretation, lifecycle, connector dispatch, execution mechanics, deterministic reaction mechanics, and runtime receipts.
- **Tecrax** owns infrastructure intent, connector semantics, observations, findings, normalization, validation, and runbooks. GovEngine retains a synthetic Tecrax conformance fixture; the operational profile itself lives in Tecrax.
- **Ravenclaw** is a legacy consumer outside the current RExecOp/Tecrax roadmap.

GovEngine is not SCLite, Ravenclaw, Tecrax, Logdash, an LLM loop, a scanner, a scheduler, a credential manager, a replay database, a PKI/KMS layer, or a subprocess runner.

## What GovEngine Includes Now

The public surface registry is `govengine.surfaces.public_surface_index()`. It currently reports seven alpha surfaces:

- `artifact_governance_core` for artifact descriptors, lifecycle state mapping, transition decisions, signing/trust records, guarded-root replay decisions, state-index helpers, deconfliction, and the SCLite bridge.
- `planning_contracts_core` for neutral task, plan-intent, and planner-port handoff records. These are handoff contracts, not a planner.
- `admission_policy_core` for `RuntimeAdmissionResult`, policy/admission/approval/audit records, **PolicyEngine MVP** (`govengine.policy`), proof-input validation, public summaries, bounded artifact references, and the development-only JSONL audit-ledger adapter.
- `evidence_review_core` for receipt-bounded evidence requirements, claims, qualifications, review results, and evidence-review-chain validation.
- `domain_profile_sdk` for contract-only domain profile declarations and conformance reports, including Ravenclaw and Tecrax fixture profiles.
- `runtime_contract_proofs` for public-safe conformance artifacts over Ravenclaw and Tecrax contract shapes. They are fixtures, not runtime authorization.
- `controlled_execution_core` for approved-spec checks, execution-ticket gates, command-shape normalization, runner request/receipt boundaries, supervision records, dry-run helpers, runtime-shell projections, event/control records, OODA records, and orchestration handoff records.

The published `0.15.0` line added:

- **PolicyEngine MVP** (`govengine.policy`): declarative policy packs, fail-closed
  `PolicyEngine.evaluate()`, verdict projection via `policy_verdict_to_gov_policy_decision()`,
  JSON Schema authoring helpers, baseline policy scaffolds, and the `govengine-policy`
  validation/scaffold CLI.

The published `0.16.0` line adds:

- **policy enforcement plan**: deterministic pack/verdict/plan digest binding,
  an existing `GovAdmissionDecision` reference, and fail-closed projection of a
  small neutral control set for host runners; GovEngine does not execute or claim
  host enforcement;
- retains the `0.14.0` governed-runtime MVP (`RuntimeAdmissionResult`, receipt/evidence
  binding, audit ledger port, inspect-only workflow) without changing its contract shape.

## Current Status

Current source line: `0.16.0`. Latest published PyPI line: `govengine==0.16.0`.
The package dependency remains `sclite-core>=1.0.3,<1.1`, and the Python import
package remains `sclite`. The published wheel contains the digest-bound
enforcement-plan API used by coordinated B2 consumers.

The current kernel is useful for deterministic review of prepared governance records. It is not production runtime readiness and it is not an execution authority. `RuntimeAdmissionResult` is the single canonical admission envelope; `compose_runtime_admission_result()` composes host-supplied gate summaries into that envelope, and `validate_runtime_admission_result()` checks the envelope shape. These helpers do not verify SCLite artifacts, persist replay claims, approve operators, or execute commands by themselves.

When hosts need a runtime-consumable path, the intended chain is:

1. SCLite verifies the artifact lifecycle and guarded truth records.
2. GovEngine maps the lifecycle status and validates proof-input summaries.
3. GovEngine composes policy, ticket, trust, replay freshness, runner profile, receipt obligation, blockers, and next actions into `RuntimeAdmissionResult`.
4. Host runtime code decides what to do with that result under its own operator, credential, storage, scheduler, and execution controls.

Dry-run remains the default local execution posture. Any live backend belongs outside this package until a separate host/runtime boundary explicitly owns and tests it.

## Explicit Non-Claims

GovEngine does not provide:

- live subprocess execution;
- raw-intent execution;
- scanner, exploit, campaign, or target authorization;
- scheduler, queue persistence, long-running worker, or LLM agent loop;
- credential handling, private key storage, CA, PKI, KMS, HSM, trust-anchor management, rotation, or revocation;
- production replay database or production audit database;
- raw artifact store or raw evidence store;
- SCLite schema authority, SCLite canonicalization, SCLite hash-chain verification, or SCLite Kernel Guard HMAC verification;
- Ravenclaw security taxonomy, target semantics, campaign UX, public proof projection, or runtime adapters;
- Tecrax infrastructure semantics, infrastructure credentials, or runtime adapters;
- carrier adapters such as OpenClaw, MCP, A2A, HTTP APIs, or UI routes;
- stable 1.0 API guarantees.

## Installation

Install the latest published package from PyPI:

```bash
python -m pip install govengine
```

That installs `0.16.0`, including the PolicyEngine MVP and B2 enforcement-plan
contracts.

For local development:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
python -m pytest -q
python -m mypy govengine
python -m ruff check .
python scripts/validate_public_truth.py
python scripts/validate_alpha_readiness.py
```

## Minimal Smoke Example

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

## Validation

The current package-line gate is intentionally local and deterministic:

```bash
python -m pytest -q
python -m mypy govengine
python -m ruff check .
python scripts/validate_public_truth.py
python scripts/validate_alpha_readiness.py
python scripts/validate_clean_package_install.py --no-editable
```

`scripts/validate_public_truth.py` keeps package metadata, public docs, dependency truth, public surface names, and release labels aligned. `scripts/validate_alpha_readiness.py` checks the alpha package posture before publication. `scripts/validate_clean_package_install.py --no-editable` validates an installed wheel in isolation and uses scoped `pip check` instead of a broad system interpreter.

## Documentation

Navigation hub: [`docs/README.md`](docs/README.md).

- [`PUBLIC_STATUS.md`](PUBLIC_STATUS.md) records the active package status and non-claims.
- [`CHANGELOG.md`](CHANGELOG.md) records release changes.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) records contribution and boundary rules.
- [`SECURITY.md`](SECURITY.md) records security reporting and package safety boundaries.
- [`PUBLISHING.md`](PUBLISHING.md) records PyPI release checks.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) explains package shape and dependency boundaries.
- [`docs/API_BOUNDARY.md`](docs/API_BOUNDARY.md) maps owned and excluded surfaces.
- [`docs/API_STABILITY_MATRIX.md`](docs/API_STABILITY_MATRIX.md) classifies public exports.
- [`docs/GOVENGINE_KERNEL_BOUNDARY.md`](docs/GOVENGINE_KERNEL_BOUNDARY.md) defines kernel/profile/runtime/SCLite ownership.
- [`docs/GOVERNED_RUNTIME_MVP_RUNBOOK.md`](docs/GOVERNED_RUNTIME_MVP_RUNBOOK.md) is the operator runbook for the governed-runtime MVP chain.
- [`docs/SECURITY_INTEGRATION.md`](docs/SECURITY_INTEGRATION.md) records the required security integration order and non-claims.
- [`docs/SCLITE_INTEGRATION.md`](docs/SCLITE_INTEGRATION.md) explains how GovEngine consumes SCLite.
- [`docs/RUNTIME_ADMISSION.md`](docs/RUNTIME_ADMISSION.md) describes the canonical runtime admission envelope.
- [`docs/INSPECT_ONLY_ADMISSION_WORKFLOW.md`](docs/INSPECT_ONLY_ADMISSION_WORKFLOW.md) documents read-only admission inspection.
- [`docs/GUARDED_FRESH_RUNTIME_ADMISSION_EXAMPLE.md`](docs/GUARDED_FRESH_RUNTIME_ADMISSION_EXAMPLE.md) shows guarded-strict plus replay-fresh admission input.
- [`docs/RECEIPT_BINDING.md`](docs/RECEIPT_BINDING.md) documents admission/ticket/request/receipt binding.
- [`docs/EVIDENCE_REVIEW.md`](docs/EVIDENCE_REVIEW.md) documents receipt-bounded evidence review and OODA receipt bounds.
- [`docs/ADMISSION_POLICY.md`](docs/ADMISSION_POLICY.md) documents admission, policy, approval, audit, and audit-ledger contracts.
- [`docs/POLICY_ENGINE.md`](docs/POLICY_ENGINE.md) documents the PolicyEngine MVP (request/verdict, compiler, runtime, admission projection).
- [`docs/RUNNER_SUPERVISION.md`](docs/RUNNER_SUPERVISION.md) documents runner request, receipt, supervision, and live-runner safety boundaries.
- [`docs/LOCAL_SUBPROCESS_RUNNER_DECISION.md`](docs/LOCAL_SUBPROCESS_RUNNER_DECISION.md) records why no live subprocess runner ships now.
- [`docs/DOMAIN_PROFILE_CONTRACT.md`](docs/DOMAIN_PROFILE_CONTRACT.md) documents profile contracts and conformance.
- [`docs/ORCHESTRATOR_MODEL.md`](docs/ORCHESTRATOR_MODEL.md), [`docs/EVENT_MODEL.md`](docs/EVENT_MODEL.md), [`docs/STATE_MACHINE.md`](docs/STATE_MACHINE.md), [`docs/CONTROL_MODEL.md`](docs/CONTROL_MODEL.md), and [`docs/RUNTIME_SHELL.md`](docs/RUNTIME_SHELL.md) separate deterministic handoff/projection records from host runtime execution.
- [`docs/VALIDATION.md`](docs/VALIDATION.md) records the **current** validation gate; historical release evidence is in [`docs/archive/VALIDATION_HISTORY.md`](docs/archive/VALIDATION_HISTORY.md).
- [`docs/ROADMAP.md`](docs/ROADMAP.md) records the current roadmap; delivered version milestones are in [`docs/archive/ROADMAP_VERSION_HISTORY.md`](docs/archive/ROADMAP_VERSION_HISTORY.md).

## License and provenance

GovEngine is MIT-licensed. It was extracted from Ravenclaw in contract-first stages, so [`LICENSE`](LICENSE) preserves the copyright notice for the originating Ravenclaw contribution lineage. The author metadata in `pyproject.toml` identifies the GovEngine package maintainer; it does not replace or reassign the originating copyright notice.

## Safety Boundary

GovEngine should preserve deterministic governance over prompt-only behavior. It must not execute directly from raw intent. Execution by a host runtime requires a prepared execution contract, valid policy decision, approved execution ticket, valid signature/trust decision, allowed runner profile, receipt obligation, and, for runtime-consumable SCLite bundles, guarded-strict verification plus replay-fresh status.

The published `0.16.0` line provides records and validators for that boundary. It does not provide the runtime that acts on them.
