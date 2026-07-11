# GovEngine Publishing Checklist

GovEngine is published to PyPI as a pre-1.0 package. Use this checklist for future releases without overstating maturity.

Current candidate line: `govengine==0.17.0rc1` with `sclite-core==2.0.0rc1`.
Current published PyPI line: `govengine==0.16.11`. Older alpha releases are archived only.

## Preflight

- [ ] For maintainer releases from the operator-controlled publish tree, effective git identity is `Krzysztof Probola <32790662+rozmiarD@users.noreply.github.com>`; external contributors use their own GitHub-associated identity.
- [ ] Published Git history is preserved after the one-time 2026-06-09 authorship normalization on `rozmiarD/GovEngine`: no further force-push, history rewrite, date rewrite, or tag rewrite to fix authorship/contribution graphs. Use corrective commits instead.
- [ ] Published Git history is preserved: no force-push, history rewrite, date rewrite, or tag rewrite to fix authorship/contribution graphs. Use corrective commits instead.
- [ ] `CHANGELOG.md`, `PUBLIC_STATUS.md`, `README.md`, `docs/VALIDATION.md`, `docs/ROADMAP.md`, `docs/API_BOUNDARY.md`, `govengine/surfaces.py`, and `pyproject.toml` agree on version/status and claim only tested behavior.
- [ ] `python scripts/validate_public_truth.py` passes.
- [ ] `python scripts/validate_alpha_readiness.py` passes for alpha release lines.
- [ ] `python -m pytest -q` passes.
- [ ] `python scripts/validate_clean_package_install.py --venv /tmp/govengine-clean-release --dev --sclite-source /path/to/SCLite --no-editable` passes from a new virtual environment path, including its isolated installed-package retirement smoke.
- [ ] `scripts/verify_runner_receipt_binding.py` and `scripts/verify_audit_ledger.py` are treated as read-only verifier smoke helpers if their records are used as release evidence; they must not generate runner requests, append ledger records, or expose raw payloads.
- [ ] Maintainer/security review confirms there are no open P0/P1 security findings. Passing tests alone is not release approval when a P0/P1 finding is open.
- [ ] Downstream smoke evidence is classified before release: SCLite released-line is required, SCLite main is optional/coordinated unless targeted, and Ravenclaw/Tecrax host contract smokes remain external host-owned checks.
- [ ] Build artifacts are generated from a clean tree.
- [ ] No generated `build/`, `dist/`, `*.egg-info`, caches, private state, or Ravenclaw workspace files are committed unless intentionally package metadata.

## PyPI release notes

- SCLite is published as the PyPI distribution `sclite-core`; the current local GovEngine candidate depends on `sclite-core==2.0.0rc1`, while published `0.16.11` remains on `sclite-core==1.0.9`.
- Initial public GovEngine version was `0.1.0` because the API/runner/OODA surface was documented but still pre-alpha.
- `0.1.3` is the artifact-governance control-gate line: core artifact state/transition objects, lifecycle status bridge, signing/trust bridge, dry-run execution gate, deconfliction, and state index. It still does not claim live execution backend ownership.
- `0.1.4` is the API surface registry/security-profile separation line: it names neutral core surfaces separately from optional Ravenclaw-style security helpers and still does not claim adapter or live execution ownership.
- `0.1.6` consumes `sclite-core>=0.3.5,<0.4`, keeps the security-profile facade boundary, and adds thin SCLite v0.3 scoped-ticket / receipt-bounded-evidence gate delegation while keeping adapters/live execution out of scope.
- `0.1.7` consumes `sclite-core>=0.5.1,<0.6` and adds thin SCLite review-bundle delegation for GovEngine integration fixtures while keeping adapters/live execution out of scope.
- `0.2.0` is the kernel-boundary freeze line: boundary reports, domain-profile conformance, orchestration handoffs, governance events, run-state transitions, and between-step control decisions. It does not add live execution, queue/scheduler ownership, carrier adapters, runtime persistence, or credential handling.
- `0.3.0` is the runtime-shell line: neutral host control actions, queue snapshots, runtime snapshots, and scheduler-tick metadata. It does not add queue persistence, scheduler ownership, Logdash/UI ownership, carrier adapters, credentials, live commands, or live execution.
- `0.4.0` is the planning-contracts line: neutral task-contract, plan-intent, and planner-port validators. It does not add planner implementation ownership, Ravenclaw security planning semantics, raw target/prompt ownership, queues, schedulers, storage, adapters, credentials, commands, or live execution.
- `0.5.0` is the admission-policy line: neutral admission decisions, policy decisions, approval requests, and audit records. It does not add profile policy meaning, approval workflow, audit storage, adapters, credentials, commands, or live execution.
- `0.6.0` is the runner-supervision line: neutral runner leases, supervision plans, supervision decisions, and approved-spec request/receipt validation. It does not add concrete runner behavior, scheduler ownership, carrier adapters, credentials, storage, or live execution.
- `0.7.0` is the evidence-review line: neutral evidence requirements, claims, qualifications, and review results. It does not add SCLite verdict ownership, Ravenclaw finding taxonomy, raw evidence storage, adapters, credentials, commands, or live execution.
- `0.7.1` is the public-truth and boundary-hardening stabilization line. It should not add broad new runtime features.
- `0.8.0` is the minimal Domain Profile SDK line: contract-only profile declarations and Ravenclaw/Tecrax fixture profiles. It does not add domain taxonomy ownership, carrier adapters, credentials, product UX, or live execution.
- `0.9.0` is the runtime contract proof line: public-safe Ravenclaw/Tecrax proof fixtures and neutral governance vocabulary over existing contracts. It does not add carrier adapters, credentials, schedulers, storage, live execution, or new OODA surfaces.
- `0.10.0-alpha` is the alpha-readiness line: package metadata, build/install validation, public truth, runtime proof fixtures, and Ravenclaw downstream compatibility checks are aligned. It does not add carrier adapters, credentials, schedulers, storage, live execution, production readiness, public tags, or PyPI upload without operator approval.
- `0.10.1-alpha` is the SCLite 0.6 alpha sync line: dependency truth, public status, validators, and downstream compatibility checks move to `sclite-core>=0.6.0a0,<0.7` without expanding GovEngine's runtime ownership.
- `0.10.2-alpha` is the SCLite 0.7 surface-collapse sync line: it adds a scoped-ticket lifecycle projection for active review-bundle consumers while SCLite retains artifact/review verdict ownership.
- `0.11.0-alpha` consumes the SCLite 0.8 retired-legacy surface and removes the Ravenclaw-shaped lifecycle projection from GovEngine after Ravenclaw takes ownership of that mapping.
- `0.12.0-alpha` is the published API-narrowing line that removes the Ravenclaw-derived optional security facade and helper modules while preserving the neutral kernel surfaces.
- `0.12.1-alpha.1` is the guarded-bundle runtime gate line: it consumes SCLite `0.8.0-beta`, composes guarded-strict verification with replay freshness, and requires guarded+fresh status for runtime-consumable execution gates.
- API stability and non-claims should remain explicit because this is pre-1.0.

## Release order

1. SCLite: published as `sclite-core`.
2. GovEngine: published as `govengine` after SCLite became installable as a package dependency.
3. Ravenclaw: publishes narrow `ravenclaw-security` helper/profile package lines while the full runtime remains source/reference-owned.

## Validation before a tag

```bash
python scripts/validate_clean_package_install.py \
  --venv /tmp/govengine-clean-release \
  --dev \
  --sclite-source /path/to/SCLite \
  --no-editable
```

This clean-install script is the local dependency-consistency gate. Do not use
`pip check` from a broad system interpreter as release evidence.

Optional wheel build/install check in another new virtual environment:

```bash
python -m venv /tmp/govengine-wheel-smoke
/tmp/govengine-wheel-smoke/bin/python -m pip install --upgrade pip build twine
/tmp/govengine-wheel-smoke/bin/python -m pip install /path/to/SCLite
/tmp/govengine-wheel-smoke/bin/python -m build
/tmp/govengine-wheel-smoke/bin/python -m twine check dist/*
/tmp/govengine-wheel-smoke/bin/python -m pip install dist/*.whl
/tmp/govengine-wheel-smoke/bin/python -m pip check
```

Do not upload to PyPI or create public tags until the operator explicitly approves the release action.

## Downstream compatibility smoke gates

GovEngine release checks may validate downstream compatibility, but production
code must stay host-neutral:

- Required: SCLite released-line smoke in a clean environment using the
  supported `sclite-core` package range.
- Optional/coordinated: SCLite main smoke during dependency waves. Treat it as
  an early warning unless the release target explicitly updates the supported
  dependency line.
- External/manual: Ravenclaw, Tecrax, or other host contract smokes. Those
  checks prove package consumption and host adapter compatibility without
  adding host imports to GovEngine.

These smokes support a release decision. They do not publish, tag, upload,
enable live execution, or make production-readiness claims.
