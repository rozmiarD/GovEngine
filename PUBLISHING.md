# GovEngine Publishing Checklist

GovEngine is published to PyPI as a pre-alpha package. Use this checklist for future releases without overstating maturity.

## Preflight

- [ ] For maintainer releases from the operator-controlled publish tree, effective git identity is `0x505badc0de <32790662+rozmiarD@users.noreply.github.com>`; external contributors use their own GitHub-associated identity.
- [ ] Published Git history is preserved: no force-push, history rewrite, date rewrite, or tag rewrite to fix authorship/contribution graphs. Use corrective commits instead.
- [ ] `CHANGELOG.md`, `PUBLIC_STATUS.md`, `README.md`, `docs/VALIDATION.md`, `docs/ROADMAP.md`, `docs/API_BOUNDARY.md`, and `pyproject.toml` agree on version/status and claim only tested behavior.
- [ ] `python -m pytest -q` passes.
- [ ] `python -m pip check` passes.
- [ ] Build artifacts are generated from a clean tree.
- [ ] No generated `build/`, `dist/`, `*.egg-info`, caches, private state, or Ravenclaw workspace files are committed unless intentionally package metadata.

## PyPI release notes

- SCLite is published as the PyPI distribution `sclite-core`; GovEngine `0.4.0` depends on `sclite-core>=0.5.1,<0.6`; the previous published `0.3.0`, `0.2.0`, and `0.1.7` releases also depended on `sclite-core>=0.5.1,<0.6`.
- Initial public GovEngine version was `0.1.0` because the API/runner/OODA surface was documented but still pre-alpha.
- `0.1.3` is the artifact-governance control-gate line: core artifact state/transition objects, lifecycle status bridge, signing/trust bridge, dry-run execution gate, deconfliction, and state index. It still does not claim live execution backend ownership.
- `0.1.4` is the API surface registry/security-profile separation line: it names neutral core surfaces separately from optional Ravenclaw-style security helpers and still does not claim adapter or live execution ownership.
- `0.1.6` consumes `sclite-core>=0.3.5,<0.4`, keeps the security-profile facade boundary, and adds thin SCLite v0.3 scoped-ticket / receipt-bounded-evidence gate delegation while keeping adapters/live execution out of scope.
- `0.1.7` consumes `sclite-core>=0.5.1,<0.6` and adds thin SCLite review-bundle delegation for GovEngine integration fixtures while keeping adapters/live execution out of scope.
- `0.2.0` is the kernel-boundary freeze line: boundary reports, domain-profile conformance, orchestration handoffs, governance events, run-state transitions, and between-step control decisions. It does not add live execution, queue/scheduler ownership, carrier adapters, runtime persistence, or credential handling.
- `0.3.0` is the runtime-shell line: neutral host control actions, queue snapshots, runtime snapshots, and scheduler-tick metadata. It does not add queue persistence, scheduler ownership, Logdash/UI ownership, carrier adapters, credentials, live commands, or live execution.
- `0.4.0` is the planning-contracts line: neutral task-contract, plan-intent, and planner-port validators. It does not add planner implementation ownership, Ravenclaw security planning semantics, raw target/prompt ownership, queues, schedulers, storage, adapters, credentials, commands, or live execution.
- API stability and non-claims should remain explicit because this is pre-1.0.

## Release order

1. SCLite: published as `sclite-core`.
2. GovEngine: published as `govengine` after SCLite became installable as a package dependency.
3. Ravenclaw: later, and possibly not as a PyPI runtime package until public delivery boundaries are clearer.

## Validation before a tag

```bash
python -m pytest -q
python -m pip check
```

Optional build check once build tooling is installed:

```bash
python -m pip install build twine
python -m build
python -m twine check dist/*
python -m pip install dist/*.whl
python -m pip check
```

Do not upload to PyPI or create public tags until the operator explicitly approves the release action.
