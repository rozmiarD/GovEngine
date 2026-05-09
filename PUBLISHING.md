# GovEngine Publishing Checklist

GovEngine is published to PyPI as a pre-alpha package. Use this checklist for future releases without overstating maturity.

## Preflight

- [ ] Effective git identity is `0x505badc0de <32790662+rozmiarD@users.noreply.github.com>`.
- [ ] Published Git history is preserved: no force-push, history rewrite, date rewrite, or tag rewrite to fix authorship/contribution graphs. Use corrective commits instead.
- [ ] `CHANGELOG.md`, `PUBLIC_STATUS.md`, `README.md`, and `pyproject.toml` agree on version/status.
- [ ] `python -m pytest -q` passes.
- [ ] `python -m pip check` passes.
- [ ] Build artifacts are generated from a clean tree.
- [ ] No generated `build/`, `dist/`, `*.egg-info`, caches, private state, or Ravenclaw workspace files are committed unless intentionally package metadata.

## PyPI release notes

- SCLite is published as the PyPI distribution `sclite-core`; GovEngine depends on `sclite-core>=0.2.1,<0.3`.
- Initial public GovEngine version is `0.1.0` because the API/runner/OODA surface is now documented but still pre-alpha.
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
