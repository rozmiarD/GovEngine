# GovEngine publishing

This is the operator procedure for release candidates and stable GovEngine
releases. It describes the repository as it exists; release history belongs in
[CHANGELOG.md](CHANGELOG.md).

## Current state

- Current source version: `1.0.0rc3`, source A; external review is pending.
- Published immutable candidate: `govengine==1.0.0rc2` from `v1.0.0rc2`.
- Published and source dependency: `sclite-core==2.0.1`.
- Published `rc2` external review: approved with no open P0/P1 findings.
- Authentic review-record child B: merged and named by `v1.0.0rc2`.
- Publication: tag-bound GitHub OIDC workflow, run
  [31254483143](https://github.com/rozmiarD/GovEngine/actions/runs/31254483143).
- RC observation window: elapsed_unclosed after `2026-08-15T11:15:02.258488Z`;
  the frozen record has no closure evidence.

Current `main` is rc3 source A. Its review form and candidate record are
explicitly pending and contain no authentic artifact hashes, approval verdict
or publication evidence. Stable promotion remains `publishable=false`; the rc2
observation is elapsed_unclosed and rc3 has not completed external review.

The immutable PyPI description comes from `PYPI_LONG_DESCRIPTION.md`. The
uploaded wheel/sdist, dependency metadata and recorded hashes match the
external review and workflow artifact; never recreate or move the tag.

The relevant commits have different roles and must not be conflated:

- `bd7ac496006bd8447f6722fb346e0033815aac64` is the independently reviewed
  contract baseline;
- `0b5d483f1259aef681521a185e0cdfb19a538314` is the frozen RC-window baseline;
- `33aefcd386351be622794e10cf5c43c8e812d6bc` is the immutable `v1.0.0rc1`
  release-tag commit;
- `f4845c1076df848c1be2df7aa7817450472e6e11` is reviewed rc2 source A;
- `e65ad22ec25d74bbbb4969bd614981a8ed5e47c8` is authentic record child B and
  the immutable `v1.0.0rc2` tag target;
- later `main` commits may change documentation or non-frozen fixes, but may not
  silently change the frozen facade, schemas, corpus, or reason registry.

## Release train

The v2 manifest keeps immutable `published_artifacts` separate from current
`source_candidates`; source metadata never rewrites published history.
The immutable published artifact identities are:

```text
sclite-core 2.0.1     truth/contracts; published and frozen
govengine 1.0.0rc2    governance; published RC, observation elapsed_unclosed

sclite-core 2.0.0 -> govengine 1.0.0rc1 -> rexecop 1.0.0rc1
```

The exact current source candidates are:

```text
sclite-core 2.0.1 -> govengine 1.0.0rc3
govengine 1.0.0rc3 governance; source A, external review pending

rexecop 1.0.0rc3.dev0: govengine 1.0.0rc2 (pending_realignment)

tecrax 0.4.0rc3: govengine 1.0.0rc2, sclite-core 2.0.1,
                 rexecop 1.0.0rc2 (pending_realignment)
```

Published RExecOp `1.0.0rc1` remains immutable and pinned to the published rc1
dependency pair. The current RExecOp source candidate `1.0.0rc3.dev0` consumes
GovEngine `1.0.0rc2` and SCLite `2.0.1`; it is pending realignment to rc3 and does not replace that artifact
history. Tecrax `0.4.0rc3` remains `pending_realignment` and pins
`rexecop==1.0.0rc2`, so the four source candidates are not an aligned install
graph. Hosted qualification installs only the aligned SCLite/GovEngine source
pair and checks it with `pip check`; it validates RExecOp and Tecrax separately
as exact, pending-realignment API consumers.

Ravenclaw is a legacy/external consumer, not the next package in the current
release train. A downstream release must consume the exact already-published
upstream versions; neither source qualification nor this manifest authorizes a
release or changes component ownership. The same facts are recorded in
machine-readable form in `docs/release-train.json`.

## External configuration

`.github/workflows/publish.yml` is the only repository workflow allowed to
upload GovEngine. PyPI Trusted Publishing must bind:

- owner `rozmiarD`;
- repository `GovEngine`;
- workflow `publish.yml`;
- environment `pypi`;
- project `govengine`.

The GitHub `pypi` environment must exist. Repository reviewers or branch rules
are optional policy, not an OIDC protocol requirement. Do not add a `PYPI_API_TOKEN` secret. The workflow requests a short-lived token with
`id-token: write`, rebuilds the reviewed source deterministically, and publishes
only the byte-identical reviewed artifacts without `skip-existing`.

## Prepare the release commit

1. Work on the intended `main` commit with a clean tree and synchronized
   `origin/main`.
2. Use the maintainer identity
   `Krzysztof Probola <32790662+rozmiarD@users.noreply.github.com>` for
   maintainer releases. External contributors keep their own GitHub identity.
3. Never force-push, rewrite published history, rewrite dates, or move an
   existing release tag. Use a corrective commit and a new version.
4. Align version and status in `pyproject.toml`, `govengine/__init__.py`,
   `CHANGELOG.md`, `README.md`, `PUBLIC_STATUS.md`, this file,
   `docs/ROADMAP.md`, `docs/VALIDATION.md`, validators, tests, and the RC-window
   record when applicable.
5. Keep dependency pins exact. A coordinated dependency change must update and
   validate SCLite, GovEngine, RExecOp, and Tecrax in dependency order.
6. Confirm the independent review record and zero open P0/P1 findings. Tests do
   not replace release approval.

Build artifacts must come from a clean release commit. Generated `build/`,
`dist/`, `*.egg-info`, caches, private state, and external workspaces are not
release source.

## Required gates

Run the source parity gate:

```bash
bash scripts/run_ci_parity_checks.sh
```

Then run the release-only gates:

```bash
.venv/bin/python scripts/validate_v1_freeze.py
.venv/bin/python scripts/validate_release_train_truth.py --cross-repo \
  --sclite-root /path/to/sclite \
  --rexecop-root /path/to/rexecop \
  --tecrax-root /path/to/tecrax
.venv/bin/python scripts/generate_conformance_corpus.py --check
.venv/bin/python scripts/validate_workflow_security.py
.venv/bin/python scripts/validate_v1_security_review.py --require-independent
.venv/bin/python scripts/validate_api_stability.py \
  --cross-repo \
  --consumer-root /path/to/rexecop \
  --consumer-root /path/to/tecrax
.venv/bin/python scripts/validate_clean_package_install.py \
  --venv /tmp/govengine-clean-release \
  --dev \
  --sclite-source /path/to/sclite \
  --no-editable
git diff --check
```

On current rc3 source A, `validate_release_readiness.py` intentionally reports
stable promotion as `publishable=false` while external review is pending, the
rc2 observation is elapsed_unclosed and downstream qualification is incomplete.

For an RC, the candidate-specific RC-window validator must pass.
RC-window status must be `prepared` before first publication.
`scripts/validate_rc_window.py` validates immutable rc1/rc2 history against the
recorded Git sources and validates the rc3 v2 source-A record against current
inputs. `pending_review` never qualifies as prepared or published. The frozen
rc2 active record is now elapsed_unclosed; `--history-mode` verifies immutable
history and reports that state. A distinct `govengine.rc_window_closure.v1` record must bind
the frozen record SHA-256, the original lifecycle timestamps, a non-future
`completed_at` no earlier than the window end, and an existing local evidence
file by SHA-256. Pass it with `--closure-record`; never rewrite the frozen rc2
JSON.

The clean-install script is the dependency-consistency gate. Do not use
`pip check` from a broad system interpreter as release evidence.
Passing these gates does not create whole-stack production-readiness claims.

## Build and inspect distributions

```bash
 .venv/bin/python -m pip install -r .github/release-build-requirements.txt
PYTHON=.venv/bin/python bash scripts/build_release_artifacts.sh --outdir /tmp/govengine-dist
PYTHON=.venv/bin/python bash scripts/reproducible_build_gate.sh
PYTHON=.venv/bin/python bash scripts/package_smoke.sh
```

The helper sets a deterministic environment and umask, normalizes the sdist,
requires exactly one wheel and sdist, runs `twine check`, and validates exact
name, version, `sclite-core==2.0.1`, Markdown content type and publication
description bytes. Package smoke is an explicit disposable `/tmp` check for
both wheel and sdist; it is deliberately outside normal unit tests.

## Completed rc2 review child

The immutable `v1.0.0rc2` tag names B, a single-parent child of reviewed source
A. Source A contains a valid-JSON, explicitly pending external-review form at
`docs/security-review/rc2-external-review.json` and no rc2 window. The authentic
reviewer edited that existing form through GitHub Web. B modifies the seeded
external security-review JSON and adds the prepared RC-window JSON. Those must
be the only two changed paths, as enforced by
`validate_release_record_commit.py`. The completed external security record
binds A, the official GitHub-hosted-runner wheel and normalized-sdist SHA-256
values, the confidential report hash, reviewer, review date, approved verdict,
and zero unresolved P0/P1 findings. The prepared window binds A and frozen-input
hashes and cryptographically references that review record without copying its
fields.

The publish workflow rebuilt A and B, required artifact equality before OIDC,
and never creates or fills authentic records itself. The seeded form is not
approval, identity proof or publication authority and contains no confidential
report content. On pending source A, `scripts/release_ab_repro_gate.sh` modifies
the seeded form and adds only a temporary synthetic window to prove the
mechanism; neither is rc2 evidence. Once authentic record child B exists, the
same gate requires full history, resolves exactly one valid record child in the
checked commit's ancestry, validates the current window/review binding, rebuilds
source A and B, and requires byte-identical artifacts. Post-release descendants
therefore retain the authentic A/B proof without being misclassified as source
A. For a prepared record-only PR aggregate before B exists, the gate constructs
a disposable exact-squash candidate with A as its sole parent, requires exactly
the two record changes, and applies the same authentic binding and artifact
checks; this fallback is forbidden after the window becomes active.

## Pending rc3 source A

`docs/security-review/rc3-external-review.json` is an exact pending form and
`docs/rc-window/1.0.0rc3.json` has status `pending_review`. Neither contains
reviewed artifact hashes, approval or publication evidence. An authentic
single-parent record child must modify only those two paths, bind the committed
source A and reviewed wheel/sdist, and move the window to `prepared`. The
candidate-aware A/B gate exercises that topology with synthetic data only in a
disposable clone; synthetic output never becomes release evidence.

## Tag and publish

Tagging and publication require explicit operator approval. Set the intended
version and verify that it matches `pyproject.toml`:

```bash
VERSION=1.0.0rc2
TAG="v${VERSION}"
test "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)"
test -z "$(git status --porcelain)"
git tag -a "$TAG" -m "GovEngine ${VERSION}"
git push origin "$TAG"
gh workflow run publish.yml \
  --ref "$TAG" \
  -f confirm_release="publish-${TAG}"
gh run watch --exit-status
```

Never recreate `v1.0.0rc1` or `v1.0.0rc2`; the commands above show the completed
rc2 procedure. A later release uses its own new version and immutable tag.

## Post-publish verification

The current GovEngine workflow publishes and attests but does not run an
automatic public-index install job. Until that workflow gains a post-publish
gate, the following verification is mandatory and manual:

```bash
VERSION=1.0.0rc2
python -m venv /tmp/govengine-public-release
/tmp/govengine-public-release/bin/python -m pip install --upgrade pip
/tmp/govengine-public-release/bin/python -m pip install \
  --index-url https://pypi.org/simple \
  --no-cache-dir \
  "sclite-core==2.0.1" \
  "govengine==${VERSION}"
/tmp/govengine-public-release/bin/python -m pip check
/tmp/govengine-public-release/bin/python -c \
  "import importlib.metadata as m, govengine, sclite; print(m.version('govengine'), govengine.__version__, sclite.__version__)"
```

Record the tag, commit, workflow run, PyPI URL, wheel/sdist SHA-256 values,
provenance reference, clean-install result, and exact downstream RExecOp commit.
RExecOp must resolve GovEngine and SCLite from the public index and pass the
shared governance conformance/G6 gate. Tecrax evidence is required only when
the coordinated profile release is in scope.

For an RC, set the checked-in RC record to `active` using PyPI's first artifact
timestamp, an observation end exactly seven days later, and a public evidence
reference. Then require:

```bash
python scripts/validate_rc_window.py --require-published
```

Evidence discovered after tagging belongs in a normal follow-up commit; never
move the release tag to include it.

## Stable promotion

Stable `1.0.0` remains blocked on completion of the published `1.0.0rc2`
candidate observation. The existing elapsed_unclosed `rc1` history is
insufficient for the rc2 changes. At least seven complete days must elapse from
rc2 `published_at`, and all of the following must remain true:

- a forward-only closure record reports `completed` with an aware `completed_at`
  and passes local evidence/digest verification;
- frozen facade/schema/corpus/reason inputs have not drifted;
- the review covering the `rc2` release commit reports zero open P0/P1
  findings;
- public-index installation and RExecOp consumption remain reproducible;
- source truth, changelog, version metadata, and release evidence are aligned.

After the `rc2`-specific
`python scripts/validate_rc_window.py --require-completed --closure-record
PATH` passes, prepare and
review a separate `1.0.0` release commit, rerun every gate, and use the same
tag-confirmed OIDC workflow with `v1.0.0`.

## Failure handling

- Before upload: fix forward, rerun gates, and create the tag only after the
  release commit is final.
- After tag but before upload: do not move the tag; use a new version/tag.
- After upload: PyPI artifacts are immutable. Document the issue, yank only
  when justified, fix forward, and publish a new version.
- A contract, schema, corpus, reason-registry or security-relevant code change
  after an RC tag requires a new RC and observation record before stable
  promotion.

Publishing does not certify production safety of the whole stack and does not
grant legal or operational authorization.
