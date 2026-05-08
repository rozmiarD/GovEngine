# GovEngine Publishing Checklist

GovEngine is a pre-alpha PyPI release candidate. Use this checklist to publish without overstating maturity.

## Preflight

- [ ] Effective git identity is `0x505badc0de <0x505badc0de@proton.me>`.
- [ ] `CHANGELOG.md`, `PUBLIC_STATUS.md`, `README.md`, and `pyproject.toml` agree on version/status.
- [ ] `python -m pytest -q` passes.
- [ ] `python -m pip check` passes.
- [ ] Build artifacts are generated from a clean tree.
- [ ] No generated `build/`, `dist/`, `*.egg-info`, caches, private state, or Ravenclaw workspace files are committed unless intentionally package metadata.

## PyPI readiness notes

- SCLite is published as the PyPI distribution `sclite-core`; GovEngine should depend on `sclite-core>=0.2.1,<0.3`.
- Initial public GovEngine version is `0.1.0` because the API/runner/OODA surface is now documented but still pre-alpha.
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
python -m pip install dist/*.whl
python -m pip check
```

Do not upload to PyPI or create public tags until the operator explicitly approves the release action.
