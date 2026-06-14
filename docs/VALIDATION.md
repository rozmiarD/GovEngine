# GovEngine Validation

GovEngine validation is local and public-safe. It does not run live targets.

## CI vs local gates

GitHub Actions (`.github/workflows/pytest.yml`) runs public-truth validation,
alpha readiness, full pytest across supported Python versions, package dry-run
build, `twine check`, wheel install, and isolated `pip check`. Treat branch or
PR CI as required merge evidence.

Local-only gates that CI does not fully replace:

- `ruff check .`
- `git diff --check`
- `scripts/validate_clean_package_install.py` with a disposable venv and
  coordinated SCLite source when validating release readiness

## Local package gate

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
python scripts/validate_public_truth.py
python scripts/validate_alpha_readiness.py
```

GitHub Actions source validation may install the current SCLite source line before the editable GovEngine test dependency set during coordinated prerelease waves. For this release line, clean wheel and PyPI install gates validate the published dependency chain.

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

## Next alpha release readiness gate

The next alpha release gate is a decision checklist, not a publication action.
It must pass before any tag or package upload is considered:

```bash
env PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_public_truth.py
env PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_alpha_readiness.py
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
  `sclite-core` package range and run public truth, alpha readiness, full
  pytest, clean install, and package smoke. This is required for release
  approval.
- SCLite main smoke: optional CI or manual pre-release gate during coordinated
  SCLite/GovEngine waves. It may run against
  `sclite-core @ git+https://github.com/rozmiarD/SCLite.git@main`, but failures
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

Expected result for the current `0.12.2a0` package line (`0.12.2-alpha`):

- full pytest passes in the source tree;
- `scripts/validate_clean_package_install.py` passes, rejects retired module paths from the installed artifact, and runs `pip check` inside its newly created virtual environment;
- `python scripts/validate_public_truth.py` passes;
- `python scripts/validate_alpha_readiness.py` passes;
- import smoke checks include `govengine.contract_proofs`, `govengine.profiles`, `govengine.review`, `govengine.replay`, `govengine.execution.supervision`, `govengine.admission`, `govengine.planning`, `govengine.runtime_shell`, and `govengine.scope_ports`;
- the public surface registry and `docs/API_BOUNDARY.md` agree on the exact public surfaces;
- profile SDK fixture conformance passes for Ravenclaw and Tecrax without adapter, credential, product UX, or live-execution claims;
- runtime contract proof fixtures pass for Ravenclaw and Tecrax without adapter, credential, scheduler, storage, live-execution, or new OODA claims;
- package build and clean wheel-install smoke checks pass before any tag or upload;
- Ravenclaw public downstream validation passes against the local alpha package line, using explicit runtime paths such as `RAVENCLAW_REPORTS_DIR`, `RAVENCLAW_TMP_DIR`, `RAVENCLAW_LOGDASH_DB`, and `RAVENCLAW_PIPELINE_CONFIG` when the checkout should remain clean/read-only;
- retired security facade/module paths are absent and cannot re-enter the neutral public surface index;
- public surface status markers are alpha-labelled and
  `govengine.sclite_adapter` is absent because Ravenclaw owns projection from
  its runtime payloads to public SCLite lifecycle artifacts;
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
- no queue persistence, scheduler loop, carrier adapter, credential store, runtime storage, live command, or live execution authority is introduced.

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
python scripts/validate_alpha_readiness.py
python -m pytest tests/ -q
ruff check .
git diff --check
```

## Historical validation records

Historical expected result for the published `0.1.7` source line:

- standalone pytest suite passes (`72 passed` in the `0.1.7` source tree);
- package dependencies are consistent;
- `python -m build` creates `govengine-0.1.7` sdist/wheel artifacts;
- `python -m twine check dist/*` passes for the release artifacts;
- clean wheel install reports `govengine.__version__ == 0.1.7`, distribution version `0.1.7`, import checks for the artifact-governance, surface-registry, security-profile facade, and SCLite review-bundle bridge modules pass, and `pip check` is clean;
- clean install from PyPI with `govengine==0.1.7` reports `govengine.__version__ == 0.1.7`, distribution version `0.1.7`, `sclite-core==0.5.1`, SCLite review-bundle bridge checks pass, and `pip check` is clean;
- no Ravenclaw runtime or Logdash process is started;
- demo signer/verifier tests prove deterministic descriptor-digest binding and tamper rejection, not production identity or PKI readiness; scoped-ticket use-gate tests prove SCLite receipt/evidence bounds delegation, and review-bundle tests prove GovEngine delegates pass/fail verdicts to SCLite `0.5.1`, not live runtime enforcement.

Historical expected result for the 0.2 kernel-boundary line:

- full pytest passes in the source tree;
- `python -m pip check` is clean;
- import smoke checks for `govengine.boundary`, `govengine.orchestration`, `govengine.events`, `govengine.state_machine`, and `govengine.control` pass;
- the public surface registry and `kernel_boundary_report()` agree that boundary, orchestration, event, state-machine, and control helpers are metadata/contracts only;
- no queue, scheduler, carrier adapter, credential store, runtime persistence, live command, or live execution authority is introduced.

Historical expected result for the `0.2.0` release line:

- `python -m build` creates `govengine-0.2.0` sdist/wheel artifacts;
- `python -m twine check dist/*` passes;
- clean wheel install reports `govengine.__version__ == 0.2.0`, distribution version `0.2.0`, import checks for the 0.2 boundary modules pass, and `pip check` is clean;
- clean install from PyPI with `govengine==0.2.0` reports `govengine.__version__ == 0.2.0`, distribution version `0.2.0`, and `sclite-core==0.5.1`.

Historical expected result for the 0.3 runtime-shell line:

- full pytest passes in the source tree;
- `python -m pip check` is clean;
- import smoke checks include `govengine.runtime_shell`;
- runtime-shell tests validate host control actions, queue snapshots, runtime snapshots, and scheduler-tick metadata;
- negative tests reject raw intent, commands, schedules, storage, credentials, carrier payloads, and live-execution claims;
- no queue persistence, scheduler loop, carrier adapter, credential store, runtime storage, live command, or live execution authority is introduced.

Historical expected result for the `0.3.0` release line before upload:

- `python -m build` creates `govengine-0.3.0` sdist/wheel artifacts;
- `python -m twine check dist/*` passes;
- clean wheel install reports `govengine.__version__ == 0.3.0`, distribution version `0.3.0`, `sclite-core==0.5.1`, import checks for `govengine.runtime_shell` pass, and `pip check` is clean;
- Ravenclaw validates against the 0.3 wheel/package line with `scripts/validate_public_install.py` and focused state/control projection tests;
- clean install from PyPI with `govengine==0.3.0` is required only after the operator-approved upload completes.

Historical expected result for the 0.4 planning-contract line:

- full pytest passes in the source tree;
- `python -m pip check` is clean;
- import smoke checks include `govengine.planning`;
- planning-contract tests validate `GovTaskContract`, `GovPlanIntentContract`, and `PlannerPort` shapes;
- negative tests reject raw targets, raw prompts, commands, credentials, storage/scheduler/live-execution claims, and duplicate task-contract IDs;
- no planner implementation, Ravenclaw security semantics, queue persistence, scheduler loop, adapter, credential store, runtime storage, live command, or live execution authority is introduced.

Historical expected result for the 0.5 admission-policy line:

- full pytest passes in the source tree;
- `python -m pip check` is clean;
- import smoke checks include `govengine.admission`;
- admission-policy tests validate `GovAdmissionDecision`, `GovPolicyDecision`, `GovApprovalRequest`, and `GovAuditRecord` shapes;
- negative tests reject raw targets, raw prompts, commands, credentials, carrier payloads, storage/scheduler/live-execution claims, and mismatched admission outcomes;
- no profile policy engine, operator approval workflow, audit storage/retention, adapter, credential store, runtime storage, live command, or live execution authority is introduced.

Historical expected result for the `0.5.0` release line:

- `python -m build` creates `govengine-0.5.0` sdist/wheel artifacts;
- `python -m twine check dist/*` passes;
- clean wheel install reports `govengine.__version__ == 0.5.0`, distribution version `0.5.0`, `sclite-core==0.5.1`, import checks for `govengine.admission` pass, and `pip check` is clean;
- clean install from PyPI with `govengine==0.5.0` reports `govengine.__version__ == 0.5.0`, distribution version `0.5.0`, `sclite-core==0.5.1`, `admission_policy_core` in the public surface index, and `pip check` is clean.

Historical expected result for the 0.6 runner-supervision line:

- full pytest passes in the source tree;
- `python -m pip check` is clean;
- import smoke checks include `govengine.execution.supervision`;
- runner-supervision tests validate `GovRunnerLease`, `GovSupervisionPlan`, `GovSupervisionDecision`, supervised runner requests, and runner receipts;
- negative tests reject raw-intent runner requests, missing approved specs, missing receipts, live backend use without explicit enablement, and forbidden metadata claims;
- no live subprocess backend, lease persistence, scheduler loop, carrier adapter, credential store, runtime storage, or live execution authority is introduced.

Historical expected result for the `0.6.0` release line:

- `python -m build` creates `govengine-0.6.0` sdist/wheel artifacts;
- `python -m twine check dist/*` passes;
- clean wheel install reports `govengine.__version__ == 0.6.0`, distribution version `0.6.0`, `sclite-core==0.5.1`, import checks for `govengine.execution.supervision` pass, and `pip check` is clean;
- clean install from PyPI with `govengine==0.6.0` reports `govengine.__version__ == 0.6.0`, distribution version `0.6.0`, `sclite-core==0.5.1`, `GovSupervisionPlan` import/use succeeds, and `pip check` is clean.

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

Historical expected result for the `0.7.0` release line:

- `python -m build` creates `govengine-0.7.0` sdist/wheel artifacts;
- `python -m twine check dist/*` passes;
- clean wheel install reports `govengine.__version__ == 0.7.0`, distribution version `0.7.0`, `sclite-core==0.5.1`, import checks for `govengine.review` pass, and `pip check` is clean;
- clean install from PyPI with `govengine==0.7.0` reports `govengine.__version__ == 0.7.0`, distribution version `0.7.0`, `sclite-core==0.5.1`, `evidence_review_core` in the public surface index, and `pip check` is clean.

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
