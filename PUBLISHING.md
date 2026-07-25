# GovEngine publishing

This is the operator procedure for release candidates and stable GovEngine
releases. It describes the repository as it exists; release history belongs in
[CHANGELOG.md](CHANGELOG.md).

## Current state

- Source and published candidate: `govengine==1.0.0rc1`.
- Exact dependency: `sclite-core==2.0.0`.
- Review status: independently reviewed, with no open P0/P1 findings.
- Publication: tag-bound GitHub OIDC workflow, run
  [29764475143](https://github.com/rozmiarD/GovEngine/actions/runs/29764475143).
- RC observation window: active until `2026-07-27T17:39:58.058090Z`.

The relevant commits have different roles and must not be conflated:

- `bd7ac496006bd8447f6722fb346e0033815aac64` is the independently reviewed
  contract baseline;
- `0b5d483f1259aef681521a185e0cdfb19a538314` is the frozen RC-window baseline;
- `33aefcd386351be622794e10cf5c43c8e812d6bc` is the immutable `v1.0.0rc1`
  release-tag commit;
- later `main` commits may change documentation or non-frozen fixes, but may not
  silently change the frozen facade, schemas, corpus, or reason registry.

## Release train

Publish in dependency order:

```text
sclite-core 2.0.0     truth/contracts; published and frozen
        |
        v
govengine 1.0.0rc1    governance; published RC
        |
        v
rexecop 1.0.0rc1      reference runtime; published RC

tecrax 0.4.0rc3       profile source candidate; pending realignment
```

Ravenclaw is a legacy/external consumer, not the next package in the current
release train. Tecrax is not currently aligned with the published train because
its source candidate still pins `rexecop==0.3.0rc3`; it must be repinned and
requalified before it is presented as a matching downstream release. A
downstream release must consume the exact already-published upstream versions;
it does not authorize changing upstream ownership.
The same facts are recorded in machine-readable form in
`docs/release-train.json`.

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
`id-token: write`, builds once, attests those distributions, and publishes the
same artifacts without `skip-existing`.

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
.venv/bin/python scripts/validate_release_train_truth.py --cross-repo
.venv/bin/python scripts/generate_conformance_corpus.py --check
.venv/bin/python scripts/validate_workflow_security.py
.venv/bin/python scripts/validate_v1_security_review.py --require-independent
.venv/bin/python scripts/validate_api_stability.py \
  --consumer-root /path/to/rexecop \
  --consumer-root /path/to/tecrax
.venv/bin/python scripts/validate_clean_package_install.py \
  --venv /tmp/govengine-clean-release \
  --dev \
  --sclite-source /path/to/sclite \
  --no-editable
git diff --check
```

For an RC, `python scripts/validate_rc_window.py` must pass. RC-window status must be `prepared` before first publication. For stable promotion,
`python scripts/validate_rc_window.py --require-completed` must pass.

The clean-install script is the dependency-consistency gate. Do not use
`pip check` from a broad system interpreter as release evidence.
Passing these gates does not create whole-stack production-readiness claims.

## Build and inspect distributions

```bash
rm -rf dist build *.egg-info
.venv/bin/python -m build
.venv/bin/python -m twine check dist/*
python -m venv /tmp/govengine-wheel-smoke
/tmp/govengine-wheel-smoke/bin/python -m pip install --upgrade pip
/tmp/govengine-wheel-smoke/bin/python -m pip install dist/*.whl
/tmp/govengine-wheel-smoke/bin/python -m pip check
/tmp/govengine-wheel-smoke/bin/python -c \
  "import importlib.metadata as m, govengine; print(m.version('govengine'), govengine.__version__)"
sha256sum dist/*
```

Confirm that wheel and sdist contain the compatibility manifest and conformance
corpus and contain no repository-only, private, cached, or secret material.

## Tag and publish

Tagging and publication require explicit operator approval. Set the intended
version and verify that it matches `pyproject.toml`:

```bash
VERSION=1.0.0rc1
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

Never recreate `v1.0.0rc1`; the commands above show the completed RC procedure.
A later release uses its own new version and immutable tag.

## Post-publish verification

The current GovEngine workflow publishes and attests but does not run an
automatic public-index install job. Until that workflow gains a post-publish
gate, the following verification is mandatory and manual:

```bash
VERSION=1.0.0rc1
python -m venv /tmp/govengine-public-release
/tmp/govengine-public-release/bin/python -m pip install --upgrade pip
/tmp/govengine-public-release/bin/python -m pip install \
  --index-url https://pypi.org/simple \
  --no-cache-dir \
  "sclite-core==2.0.0" \
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

Stable `1.0.0` remains blocked until at least seven complete days have elapsed
from the RC `published_at` time and all of the following remain true:

- the RC record is `completed` with an aware `completed_at`;
- frozen facade/schema/corpus/reason inputs have not drifted;
- the independent review still reports zero open P0/P1 findings;
- public-index installation and RExecOp consumption remain reproducible;
- source truth, changelog, version metadata, and release evidence are aligned.

After `python scripts/validate_rc_window.py --require-completed` passes, prepare
and review a separate `1.0.0` release commit, rerun every gate, and use the same
tag-confirmed OIDC workflow with `v1.0.0`.

## Failure handling

- Before upload: fix forward, rerun gates, and create the tag only after the
  release commit is final.
- After tag but before upload: do not move the tag; use a new version/tag.
- After upload: PyPI artifacts are immutable. Document the issue, yank only
  when justified, fix forward, and publish a new version.
- A contract, schema, corpus, or reason-registry change during an RC window
  requires a new RC and a new observation record.

Publishing does not certify production safety of the whole stack and does not
grant legal or operational authorization.
