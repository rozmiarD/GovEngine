# GovEngine Publishing Checklist

GovEngine is not ready for PyPI publication yet. Use this checklist to prepare without overstating maturity.

## Preflight

- [ ] Effective git identity is `0x505badc0de <0x505badc0de@proton.me>`.
- [ ] `CHANGELOG.md`, `PUBLIC_STATUS.md`, `README.md`, and `pyproject.toml` agree on version/status.
- [ ] `python -m pytest -q` passes.
- [ ] `python -m pip check` passes.
- [ ] Build artifacts are generated from a clean tree.
- [ ] No generated `build/`, `dist/`, `*.egg-info`, caches, private state, or Ravenclaw workspace files are committed unless intentionally package metadata.

## PyPI blockers today

- SCLite should be published first, so GovEngine can depend on a normal version range such as `sclite>=0.2,<0.3` instead of a Git URL pin.
- GovEngine should choose an initial public version (`0.1.0` is likely more honest than `0.0.0` once the current API/runner/OODA surface is documented).
- API stability and non-claims should remain explicit because this is pre-1.0.

## Recommended release order

1. SCLite: package-first candidate because it has no runtime dependencies and already has a CLI/version/changelog.
2. GovEngine: after SCLite is installable as a package dependency.
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
```

Do not upload to PyPI or create public tags until the operator explicitly approves the release action.
