# Contributing to GovEngine

GovEngine source tracks the published `1.0.0rc2` candidate for the stable v1
governance facade while its observation window is active. Legacy top-level
surfaces retain their documented compatibility/alpha posture. Contributions
should preserve the package boundary:

```text
domain profile -> host runtime -> GovEngine -> SCLite
```

## Development setup

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
python -m pytest -q
python scripts/validate_public_truth.py
```

For dependency-consistency and readiness validation, run the clean installed-package gate from a new virtual environment path:

```bash
python scripts/validate_clean_package_install.py \
  --venv /tmp/govengine-clean-source \
  --dev \
  --sclite-source /path/to/SCLite \
  --no-editable
```

Do not treat `pip check` from a broad system interpreter as GovEngine release evidence; it reports every unrelated package installed in that interpreter.

## Change rules

- Keep GovEngine carrier-neutral.
- Do not import Ravenclaw runtime, Logdash, OpenClaw, MCP, or A2A code.
- Do not add live subprocess execution without an explicit reviewed design.
- Prefer typed/result envelopes for new public boundaries.
- Preserve public-safe redaction and non-claims in receipts/evidence docs.
- Update `CHANGELOG.md` for meaningful user-visible or API-boundary changes.
- Update docs/tests with contract changes.

## Release discipline

Before release-oriented work:

1. confirm tests pass;
2. confirm package metadata is accurate;
3. confirm dependency direction remains `GovEngine -> SCLite` only;
4. confirm no private Ravenclaw workspace state or generated artifacts are included;
5. confirm version/changelog/public-status docs agree.
