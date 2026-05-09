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

- SCLite is published as the PyPI distribution `sclite-core`; GovEngine depends on `sclite-core>=0.2.1,<0.3`.
- Initial public GovEngine version was `0.1.0` because the API/runner/OODA surface was documented but still pre-alpha.
- `0.1.3` is the artifact-governance control-gate line: core artifact state/transition objects, lifecycle status bridge, signing/trust bridge, dry-run execution gate, deconfliction, and state index. It still does not claim live execution backend ownership.
- `0.1.4` is the API surface registry/security-profile separation line: it names neutral core surfaces separately from optional Ravenclaw-style security helpers and still does not claim adapter or live execution ownership.
- `0.1.5` is the security-profile facade candidate: it gives hosts one explicit optional-profile entrypoint for action/tooling, policy/scope, and review-contract helper discovery while keeping neutral core and adapter/live-execution claims separate.
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
