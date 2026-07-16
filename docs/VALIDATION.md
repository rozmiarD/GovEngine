# GovEngine Validation

GovEngine validation is local and public-safe. It does not run live targets.

## CI vs local gates

GitHub Actions (`.github/workflows/pytest.yml`) runs public-truth validation,
v1 facade/schema freeze, generated corpus drift validation, release readiness,
strict facade typing, full pytest across supported Python versions, package
dry-run build, `twine check`, wheel install, and isolated `pip check`. Treat
branch or PR CI as required merge evidence.

Local-only gates that CI does not fully replace:

- `ruff check .`
- `git diff --check`
- `scripts/validate_clean_package_install.py` with a disposable venv and
  coordinated SCLite source when validating release readiness

## Local package gate

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
python -m mypy govengine
python scripts/validate_public_truth.py
python scripts/validate_release_readiness.py
python scripts/validate_digest_ownership.py
python scripts/validate_api_stability.py
python scripts/validate_v1_freeze.py
python scripts/validate_rc_window.py
python scripts/generate_conformance_corpus.py --check
python scripts/validate_workflow_security.py
python scripts/validate_v1_security_review.py
python -m mypy --strict --disable-error-code=import-untyped \
  govengine/v1.py govengine/api.py govengine/approvals.py \
  govengine/governance.py govengine/governance_decision.py \
  govengine/governance_trace.py govengine/policy
```

GitHub Actions source validation may install the current SCLite source line before the editable GovEngine test dependency set. The active supported stack line is exact-pinned for package consumers, and clean wheel/PyPI install gates validate that published dependency chain.

## Clean installed-package gate

Use a new virtual environment for dependency-consistency and local package-readiness evidence:

```bash
python scripts/validate_clean_package_install.py \
  --venv /tmp/govengine-clean-source \
  --dev \
  --sclite-source /path/to/SCLite \
  --no-editable
```

This is the canonical local `pip check` gate: the script installs GovEngine
and the selected SCLite source into a disposable virtual environment, performs
an isolated installed-package smoke that rejects the retired security modules,
then runs validators, tests, and `pip check`. A broad system interpreter is not
a release-readiness environment because unrelated installed tools can make
its dependency set inconsistent.

## Digest ownership gate

```bash
python scripts/validate_digest_ownership.py
```

The gate validates the reviewed digest-boundary inventory in
[`DIGEST_OWNERSHIP.md`](DIGEST_OWNERSHIP.md). It distinguishes full
GovEngine-owned payloads that must be recomputed from SCLite/host-owned
delegated digests, reference-only bindings, and digests produced by GovEngine.
It runs as part of release readiness and fails if an entry has an invalid mode,
duplicate binding id, or claims GovEngine recomputation of a SCLite-owned
payload.

## API classification and consumer gate

```bash
python scripts/validate_api_stability.py \
  --consumer-root /path/to/rexecop \
  --consumer-root /path/to/tecrax
```

The gate proves that all 308 root exports have exactly one classification and
that the 3 compatibility callables outside `__all__` remain inventoried. It
also requires the 40-symbol `govengine.v1` facade to match the `v1-candidate`
set and remain at the 40-symbol ceiling. Consumer scanning ignores virtual
environments and build/cache directories. The reviewed downstream snapshot is
documented in [`DOWNSTREAM_IMPORT_MAP.md`](DOWNSTREAM_IMPORT_MAP.md).

## V1 freeze and conformance gates

`scripts/validate_v1_freeze.py` compares the wheel-shipped compatibility
manifest with the exact facade exports and every locally declared v1 schema
constant. `scripts/generate_conformance_corpus.py --check` verifies all 33
checked-in JSON cases are reproducible. `tests/test_conformance_corpus.py`
executes GovEngine-owned cases; RExecOp's
`scripts/validate_governance_conformance.py` consumes the same installed
corpus and executes runtime-owned atomic claim cases.

`tests/test_security_properties.py` adds bounded property coverage. It is not
unbounded fuzzing or an availability benchmark.

`scripts/validate_workflow_security.py` rejects any action not pinned to a full
commit SHA and verifies the dependency-audit, CodeQL and manual OIDC/attested
PyPI workflow invariants.

`scripts/validate_v1_security_review.py` validates the independent review
record structurally in normal CI. Release/publish mode adds
`--require-independent`, which fails until an external reviewer records an
immutable reviewed commit and zero open P0/P1 findings.

`scripts/validate_rc_window.py` binds `1.0.0rc1` to the frozen v1 manifest,
conformance manifest and policy reason-code registry source. Drift requires a
new RC version and record; the gate cannot be refreshed silently under rc1.

## Read-only operator verifier gates

These scripts are local verification helpers. They never execute work, contact
targets, append audit records, rewrite ledgers, create runner requests, or
validate SCLite canonicalization. They summarize already-bounded GovEngine
records only.

Runner receipt binding verification:

```bash
python scripts/verify_runner_receipt_binding.py \
  --request /path/to/runner-request.json \
  --receipt /path/to/runner-receipt.json \
  --admission /path/to/runtime-admission.json \
  --ticket-id ticket-1 \
  --ticket-digest sha256:<ticket-digest>
```

Inputs are JSON mappings for `GovRunnerRequest`, `GovRunnerReceipt`, and
optionally `RuntimeAdmissionResult`. If no admission file is supplied, use
`--admission-id` and `--admission-digest`. The script rejects missing or
mismatched admission, ticket, request, receipt, status, and digest bindings
through `validate_runner_receipt_binding()`. It does not accept raw target,
prompt, command, credential, stdout/stderr payload, or raw evidence fields in
the binding. Output is bounded to status, reason code, blockers, request id,
receipt status, admission id, ticket id, and the fixed `execution: not
performed` non-claim.

Development audit ledger verification:

```bash
python scripts/verify_audit_ledger.py /path/to/audit-ledger.jsonl
```

Input is a JSONL file containing `AuditLedgerEntry` records created by the
development `JsonlAuditLedgerAdapter` or an equivalent bounded local fixture.
The script reads and verifies sequence, previous-entry digest, and entry digest
continuity. Malformed JSONL, tamper, deleted-line, restarted-chain, empty, or
invalid-limit cases fail closed. Output omits raw records and reports only
status, reason code, blockers, checked entry count, last entry id, and the
fixed `writes: none` non-claim.

Stable exit codes for both helpers:

- `0`: verified.
- `1`: verification failed or failed closed on invalid/tampered input.
- `2`: CLI/input handling error such as unreadable JSON or invalid read limit.

## 1.0 release-candidate readiness gate

The release-candidate gate is a decision checklist, not a publication action.
It must pass before any tag or package upload is considered:

```bash
env PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_public_truth.py
env PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_release_readiness.py
env PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_digest_ownership.py
env PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_v1_freeze.py
env PYTHONDONTWRITEBYTECODE=1 python3 scripts/generate_conformance_corpus.py --check
env PYTHONDONTWRITEBYTECODE=1 python3 -m mypy govengine
env PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider
ruff check .
git diff --check
python scripts/validate_clean_package_install.py \
  --venv /tmp/govengine-clean-release \
  --dev \
  --sclite-source /path/to/SCLite \
  --no-editable
```

Release reviewers should also run a clean build and wheel install smoke where
build tooling is available:

```bash
python -m build
python -m twine check dist/*
python -m venv /tmp/govengine-wheel-smoke
/tmp/govengine-wheel-smoke/bin/python -m pip install --upgrade pip
/tmp/govengine-wheel-smoke/bin/python -m pip install dist/*.whl
/tmp/govengine-wheel-smoke/bin/python -m pip check
```

No tag, PyPI upload, release artifact publication, or production-readiness
claim is part of this gate. A maintainer must explicitly confirm that there
are no open P0/P1 security findings in the tracked issue/security-review
source before approving a release. If any P0/P1 finding is open, the release
gate is blocked even when tests pass.

## Downstream compatibility smoke design

Downstream compatibility is release engineering evidence, not a runtime import
path. GovEngine production code must not import Ravenclaw, Tecrax, or other
host runtimes.

- SCLite released-line smoke: local or CI gate. Install the currently supported
  `sclite-core` package range and run public truth, release readiness, full
  pytest, clean install, and package smoke. This is required for release
  approval.
- SCLite edge smoke: optional CI or manual pre-release gate during coordinated
  SCLite/GovEngine waves. It must run against an immutable full commit SHA, but failures
  should block only coordinated dependency updates, not ordinary patch releases
  unless the release target explicitly consumes main.
- Ravenclaw or other host contract smoke: external/manual gate owned by the
  host runtime. It should validate package consumption and contract adapters
  outside GovEngine production imports. Host failures become release risk
  evidence, not justification to add host semantics to GovEngine core.

## Current package-line gate

Only this section states current validation expectations. The versioned
sections under **Historical validation records** are retained release evidence,
not the active gate.

Expected result for the current `1.0.0rc1` package line (`1.0.0rc1`):

- full pytest passes in the source tree;
- `python -m mypy govengine` passes for the package surface;
- `scripts/validate_clean_package_install.py` passes, rejects retired module paths from the installed artifact, and runs `pip check` inside its newly created virtual environment;
- `python scripts/validate_public_truth.py` passes;
- `python scripts/validate_api_stability.py` passes; consumer-aware review may add `--consumer-root /path/to/rexecop`;
- `python scripts/validate_release_readiness.py` passes;
- import smoke checks include `govengine.contract_proofs`, `govengine.profiles`, `govengine.review`, `govengine.replay`, `govengine.execution.supervision`, `govengine.admission`, `govengine.planning`, `govengine.runtime_shell`, and `govengine.scope_ports`;
- the public surface registry and `docs/API_BOUNDARY.md` agree on the exact public surfaces;
- profile SDK fixture conformance passes for Ravenclaw and Tecrax without adapter, credential, product UX, or live-execution claims;
- runtime contract proof fixtures pass for Ravenclaw and Tecrax without adapter, credential, scheduler, storage, live-execution, or new OODA claims;
- package build and clean wheel-install smoke checks pass before any tag or upload;
- downstream host validation, when used, passes against the local candidate
  without moving host semantics into GovEngine;
- retired security facade/module paths are absent and cannot re-enter the neutral public surface index;
- public surface status markers are alpha-labelled and
  `govengine.sclite_adapter` is absent because host runtimes own projection
  from runtime payloads to public SCLite lifecycle artifacts;
- guarded-bundle runtime flow tests prove first use of a verified SCLite guard
  can be recorded as fresh and a second use of the same `root_tag` is blocked;
- replay claim-store tests prove the development claim-once port records the
  first fresh claim and rejects or observes repeated claims without claiming
  production persistence or concurrency ownership;
- replay documentation distinguishes host-owned atomic production stores from
  `InMemoryReplayClaimStore` and `record_guard_replay_file()` development
  helpers;
- runtime-consumable execution-gate tests require guarded-strict verification
  plus replay-fresh status before a bundle can be consumed for execution;
- runtime-consumable guard failures report `kernel_guard_required`, while replay
  freshness failures report `replay_detected`;
- lifecycle tests require canonical `verified_chain` and `verified_lifecycle`
  vocabulary and keep old `chain_verified` / `lifecycle_verified` names as
  explicit migration aliases only;
- signature tests require successful verification status as well as allowed
  trust status;
- evidence-review tests enforce `evidence_kind` as a bounded requirement field;
- runtime-admission proof-input tests require guarded root digest, execution
  ticket id, execution ticket digest or ticket digest reference, and
  admission/ticket receipt binding;
- runner receipt binding tests require admission, ticket, request, receipt,
  and digest references before a receipt can be treated as runtime evidence;
- evidence-review chain tests require the evidence claim and optional review
  result to reference the expected receipt, admission, qualification, and
  receipt-status bounds without storing raw evidence or replacing SCLite
  review-bundle verdict authority;
- audit-ledger tests require append/read/verify contracts, GovEngine-owned
  digest binding, and JSONL development hash-chain continuity without
  production persistence claims;
- inspect-only admission workflow tests must validate and summarize
  `RuntimeAdmissionResult` records without creating runner requests, receipts,
  replay claims, audit entries, target contact, or live execution authority;
- no queue persistence, scheduler loop, carrier adapter, credential store, runtime storage, live command, or live execution authority is introduced;
- PolicyEngine MVP tests pass for `govengine.policy` compile/evaluate paths and `policy_verdict_to_gov_policy_decision()` projection.

## Operator/runbook docs gate

Docs that change the governed-runtime MVP operator path should preserve the
truth in [GOVERNED_RUNTIME_MVP_RUNBOOK.md](GOVERNED_RUNTIME_MVP_RUNBOOK.md):
admission is a decision record, SCLite owns proof/review authority, trust and
keys are host-owned ports, replay/audit persistence is host-owned beyond local
adapters, dry-run remains the default runner path, and live execution remains
disabled unless a future host adapter satisfies the runner safety spec.

Use these checks for operator/runbook-only updates:

```bash
python scripts/validate_public_truth.py
python scripts/validate_release_readiness.py
python -m mypy govengine
python -m pytest tests/ -q
ruff check .
git diff --check
```

## What the focused tests cover

Current tests cover:

- public module imports;
- dry-run result assembly;
- neutral scope helpers;
- approved execution spec and ticket helper shapes;
- OODA decision outcomes and runner-control receipt shape;
- SCLite lifecycle verifier seam availability;
- current scoped-ticket lifecycle construction and SCLite review-bundle materialization compatibility;
- SCLite review-bundle bridge pass/fail mapping for packaged GovEngine integration fixtures;
- artifact descriptor/envelope/state and transition-decision boundary objects;
- lifecycle transition gates and blocker/next-action reporting;
- signing/trust bridge decisions and deterministic demo signer/verifier ports without PKI/key ownership;
- dry-run-only execution gates and default `DryRunRunner` behavior;
- guarded runtime decision assembly and replay freshness for already verified
  SCLite Kernel Guard roots;
- deconfliction/change-order and artifact state-index summaries;
- public surface registry containing only the neutral artifact-governance, planning, admission-policy, evidence-review, profile, proof, and controlled-execution groups;
- negative regression checks rejecting the retired `govengine.security_profile` facade and Ravenclaw-derived security module paths;
- kernel/profile/runtime/SCLite boundary contracts, boundary report, and domain-profile conformance checks;
- deterministic orchestration handoff records without scheduler, UI, adapter, credential, or live-execution authority;
- transport-neutral governance event metadata without raw prompt, credential, live-command, carrier-delivery, or schedule payloads;
- neutral run-state transitions and between-step control decisions without runtime storage, queue, scheduler, command, delivery, credential, or live-execution claims.
- runtime-shell host control actions, queue snapshots, runtime snapshots, and scheduler-tick metadata without storage, scheduler, command, delivery, credential, carrier, or live-execution claims.
- planning/task-contract validators without planner implementation, raw target/prompt, queue, scheduler, storage, command, carrier, credential, or live-execution claims.
- admission/policy/approval/audit validators without profile policy meaning, approval workflow, audit storage/retention, raw target/prompt, queue, scheduler, storage, command, carrier, credential, or live-execution claims.
- runner-supervision validators without live backend ownership, lease persistence, raw intent, scheduler, storage, carrier, credential, or concrete execution claims.
- evidence-review validators without SCLite review verdict ownership, Ravenclaw finding taxonomy, raw output/evidence storage, target/prompt, command, carrier, credential, or live-execution claims.
- receipt/evidence chain validators over admission, runner request, receipt,
  evidence claim, and optional review-result references without raw evidence
  storage, SCLite canonicalization ownership, or live execution authority.
- JSONL hash-chain development audit adapter without production storage,
  locking, retention, concurrency, raw evidence, or live execution authority.

## Ravenclaw consumption gate

Ravenclaw should validate that it can consume GovEngine as the external PyPI package `govengine` instead of using an in-tree `govengine/` copy or a Git URL pin.

The important checks are:

```bash
python -m pytest -q \
  engine/tests/test_govengine_dependency_isolation.py \
  engine/tests/test_govengine_stage2b_seams.py \
  engine/tests/test_govengine_policy_seam.py \
  engine/tests/test_govengine_command_shape_seam.py \
  engine/tests/test_govengine_runner_seam.py \
  engine/tests/test_signal_contract.py \
  engine/tests/test_analysis_contract.py \
  engine/tests/test_executor_v2.py \
  engine/tests/test_govengine_control_gate_adapter.py
```

and Ravenclaw's Security Contract validation receipt:

```bash
python scripts/run_security_contract_validation.py --include-pytest --format markdown
```

## Public-safety checks

For any Ravenclaw publication that consumes GovEngine:

- assemble the Ravenclaw public snapshot;
- run Ravenclaw residue audit;
- confirm the snapshot does not include an in-tree `govengine/` directory;
- confirm `pyproject.toml` consumes GovEngine from the intended package range, not a Git URL pin.

## Non-claims

These checks do not prove:

- live subprocess execution safety;
- authorization to test live targets;
- production deployment readiness;
- protocol adapter correctness;
- Logdash UI behavior;
- that compact OODA receipt summaries are a substitute for raw forensic logs;
- that demo digest signatures are production signatures, identity proof, or PKI validation.

GovEngine is currently a reusable governed-execution helper layer, not a full autonomous runtime.
The kernel ships **no live subprocess backend** by default; optional live backends remain
host-owned and policy-gated.

## Historical validation records

Release-line validation evidence before the current gate is archived in
[archive/VALIDATION_HISTORY.md](archive/VALIDATION_HISTORY.md). Those records are
retained release evidence, **not the active gate**.

The archive retains anchors for the `0.2 kernel-boundary line`, `0.2.0`,
`govengine.boundary`, `govengine.orchestration`, `govengine.events`,
`govengine.state_machine`, `govengine.control`,
`no queue, scheduler, carrier adapter, credential store`, and
`live execution authority is introduced`.
