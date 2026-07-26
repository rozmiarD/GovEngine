# GovEngine validation

GovEngine validation is deterministic, local and public-safe. It does not
contact live targets or grant execution authority.

## CI

`.github/workflows/pytest.yml` runs on Python 3.11, 3.12 and 3.13 with exact
`sclite-core==2.0.0`. It checks public truth, the machine-readable release
train, API stability, v1 freeze, the RC window, generated conformance, workflow
security, review structure, release readiness, Ruff, mypy, strict facade typing
and full pytest.

Separate jobs:

- test the SCLite edge integration at immutable commit
  `2470373c6384c284ab48df7ce763f0938797d155`;
- clean and build wheel/sdist;
- run `twine check`;
- install the wheel in an isolated environment and run `pip check`;
- verify that the wheel ships the v1 manifest and 33-case corpus.

The scheduled security workflow runs dependency audit and CodeQL. All GitHub
Actions are pinned to full commit SHAs.

## Local parity gate

Use the repository environment when available:

```bash
bash scripts/run_ci_parity_checks.sh
```

This runs public truth, local release-train truth, API stability, release-source
validation, G3 receipt conformance, Ruff, mypy and full pytest. Current
post-tag `main` reports `publishable=false`; this is a successful validation of
the explicitly unreleased source posture, not release authorization.
`git diff --check` remains a separate local delivery check.

## Contract gates

```bash
.venv/bin/python scripts/validate_v1_freeze.py
.venv/bin/python scripts/generate_conformance_corpus.py --check
.venv/bin/python scripts/validate_documentation_antidrift.py
.venv/bin/python scripts/validate_digest_ownership.py
.venv/bin/python scripts/validate_workflow_security.py
.venv/bin/python scripts/validate_v1_security_review.py
.venv/bin/python scripts/validate_rc_window.py
.venv/bin/python scripts/validate_release_train_truth.py
```

- `validate_v1_freeze.py` enforces 40 facade exports, 15 v1 records and five
  retained v0.1 facade schemas.
- corpus generation enforces 33 reproducible cases: five valid and 28 negative.
- documentation anti-drift scans all 42 active Markdown files for broken local
  links and anchors, missing file references, unknown CLI commands, index gaps,
  active ownership/version contradictions and inconsistent release
  disclosures. Historical CHANGELOG sections remain outside current-truth
  semantics; `Unreleased` is checked.
- digest ownership rejects GovEngine recomputation claims over SCLite- or
  RExecOp-owned payloads.
- normal review validation checks structure; release mode adds
  `--require-independent`.
- RC validation binds the facade manifest, corpus manifest and reason registry.
- release-train validation checks current GovEngine package metadata and active
  documentation against `docs/release-train.json`.

## Downstream import and protocol gates

```bash
.venv/bin/python scripts/validate_api_stability.py \
  --consumer-root /path/to/rexecop \
  --consumer-root /path/to/tecrax
```

The gate classifies every GovEngine root export, detects unlisted callables and
checks supported downstream root imports. RExecOp separately executes the
shared corpus cases it owns, including trusted signed-decision verification and
atomic decision/nonce claim semantics.

For a checked-out sibling stack, verify every package version and exact
dependency pin:

```bash
.venv/bin/python scripts/validate_release_train_truth.py --cross-repo
```

The cross-repo gate fails on version, dependency or alignment-status drift.
Historical changelog entries and immutable security-review evidence are
deliberately outside this current-truth scan.

## Clean installed-package gate

```bash
.venv/bin/python scripts/validate_clean_package_install.py \
  --venv /tmp/govengine-clean-release \
  --dev \
  --sclite-source /path/to/sclite \
  --no-editable
```

The script uses a disposable environment, installs the selected SCLite source
and a non-editable GovEngine package, rejects retired installed module paths,
runs package smoke checks and performs isolated `pip check`. A broad system
interpreter is not dependency evidence.

## Release gate

Before tagging, additionally require:

```bash
.venv/bin/python scripts/validate_v1_security_review.py --require-independent
.venv/bin/python scripts/validate_rc_window.py
.venv/bin/python scripts/validate_release_train_truth.py --cross-repo
rm -rf dist build *.egg-info
.venv/bin/python -m build
.venv/bin/python -m twine check dist/*
```

For the immutable published `rc1`, completion is checked with:

```bash
.venv/bin/python scripts/validate_rc_window.py --require-completed
```

That command currently targets the `rc1` record and is not sufficient to
qualify post-tag `main`. The `rc2` release slice must create and validate its
own record before stable promotion.

Tagging, publishing and public-index verification follow
[PUBLISHING.md](../PUBLISHING.md). Validation never creates a tag or uploads a
package by itself.

## Current package evidence

Expected result for the current `1.0.0rc1` package line:

- PyPI serves `govengine==1.0.0rc1` with exact `sclite-core==2.0.0`;
- tag `v1.0.0rc1` points to
  `33aefcd386351be622794e10cf5c43c8e812d6bc`;
- publish workflow
  [29764475143](https://github.com/rozmiarD/GovEngine/actions/runs/29764475143)
  completed through OIDC and emitted build provenance;
- wheel SHA-256 is
  `3a6575b4a430cc5b98cfe042cf86fb01371ca73a36cf3f7d00349ce7a700052f`;
- sdist SHA-256 is
  `10d08555497f15efcaa988510fdb88729331fa2e14f00144825e0e8124c3ed72`;
- clean public-index install, `pip check`, independent review and the RExecOp G6
  consumer evidence passed;
- the `rc1` record is active; stable promotion is additionally blocked on a new
  candidate containing current `main`.

These are immutable release facts, not instructions to recreate the tag.
The immutable PyPI long description for `1.0.0rc1` is stale because it contains
the pre-publication README and obsolete `0.16.11` installation guidance.
Current `main` also contains unreleased post-tag fixes while retaining the
`1.0.0rc1` version label. Therefore the successful RC evidence above does not
qualify current `main` for stable promotion; a new candidate must rebuild,
publish and repeat the relevant gates.

`validate_public_truth.py` also scans every active root/docs Markdown file. It
fails on broken repository links, missing documented files, unknown GovEngine
CLI commands, unindexed top-level docs, common ownership-boundary
contradictions and missing release-drift disclosures. Historical archive pages
remain outside current-truth semantics.

## Compatibility checks

Legacy verifier scripts and the
[inspect-only admission workflow](INSPECT_ONLY_ADMISSION_WORKFLOW.md) remain
read-only. Compatibility tests cover `RuntimeAdmissionResult`, runner receipt
bindings, audit/review records, runtime shell and other classified pre-v1
surfaces. Their presence does not make them part of `govengine.v1` and does not
grant live execution authority.

## Non-claims

Passing these gates proves the bounded package contracts tested here. It is not
a penetration test, legal authorization, production certification, malicious-
host guarantee, plugin audit, live-target test or proof that external adapters
are correct.
