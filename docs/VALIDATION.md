# GovEngine validation

GovEngine validation is deterministic, local and public-safe. It does not
contact live targets or grant execution authority.

## CI

`.github/workflows/pytest.yml` runs on Python 3.11, 3.12 and 3.13 with exact
`sclite-core==2.0.1`. It checks public truth, the machine-readable release
train, API stability, v1 freeze, the RC window, generated conformance, workflow
security, review structure, release readiness, Ruff, mypy, strict facade typing
and full pytest.

Separate jobs:

- test the SCLite edge integration at immutable commit
  `66dff5cf7d75059e13db92b553c192caf67c0338`;
- clean and build wheel/sdist;
- use the canonical deterministic release helper, including `twine check` and
  exact distribution metadata validation;
- run reproducibility and lifecycle-aware record-only A/B gates: synthetic for
  pending source A, authentic for record child B and its descendants;
- install wheel and sdist in explicit disposable `/tmp` smoke environments.

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
.venv/bin/python scripts/validate_distribution_metadata.py --wheel WHEEL --sdist SDIST
.venv/bin/python scripts/validate_rc2_release_records.py --help
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
PYTHON=.venv/bin/python bash scripts/build_release_artifacts.sh --outdir /tmp/govengine-dist
PYTHON=.venv/bin/python bash scripts/reproducible_build_gate.sh
PYTHON=.venv/bin/python bash scripts/release_ab_repro_gate.sh
PYTHON=.venv/bin/python bash scripts/package_smoke.sh
```

For the immutable published `rc1`, completion is checked with:

```bash
.venv/bin/python scripts/validate_rc_window.py --require-completed
```

The default command targets immutable rc1 history. Current rc2 evidence uses
`--record docs/rc-window/1.0.0rc2.json --expected-version 1.0.0rc2
--require-published`; stable promotion later requires `--require-completed`.

Tagging, publishing and public-index verification follow
[PUBLISHING.md](../PUBLISHING.md). Validation never creates a tag or uploads a
package by itself.

## Current package evidence

Expected result for the current `1.0.0rc2` package line: published release
candidate with an active observation window and stable promotion still
`publishable=false`. Reviewed source A is
`f4845c1076df848c1be2df7aa7817450472e6e11`; tagged record child B is
`e65ad22ec25d74bbbb4969bd614981a8ed5e47c8`. B contains one modified seeded
review form plus one added prepared rc2 window and was published only after the
workflow proved package-byte equality.

Tag `v1.0.0rc2` and publish run
[31254483143](https://github.com/rozmiarD/GovEngine/actions/runs/31254483143)
produced public wheel
`e9da63696c58ad3f096a856ff75716918e3f0b397050212c13487573921d7676`
and normalized sdist
`ea214948896ef5850bb3f536f20fa40bbacbae1a3221dba94bb7ff051276c9cd`.
Both match the external review and pass clean public-index installation with
`sclite-core==2.0.1`. Observation is active through
`2026-08-15T11:15:02.258488Z`.

## Immutable published rc1 evidence

Expected result for the immutable `1.0.0rc1` package line:

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
That stale rc1 metadata and its successful RC evidence are retained as
immutable history; they do not supersede or qualify the published rc2 candidate
for stable promotion.

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
