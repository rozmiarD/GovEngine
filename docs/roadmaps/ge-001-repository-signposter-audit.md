# GE-001 Repository and Signposter Control-Plane Audit

Date: 2026-06-06

## Repository Baseline

- Target path: `/home/probo/projects/govengine`
- GitHub repo: `ExatronOmega/GovEngine`
- Current branch: `work`
- Upstream branch: `origin/work`
- Divergence at start: `0 0`
- Initial commit: `8870f3b`
- Origin: `https://github.com/ExatronOmega/GovEngine.git`
- Upstream: `https://github.com/rozmiard/govengine.git`
- Working tree before roadmap generation: clean

Recent commits:

```text
8870f3b release: publish GovEngine 0.12.2 alpha truth
5a14dd8 release: prepare GovEngine for SCLite 1.0
9ce45ca fix: tighten guarded bundle replay admission
60be5e3 release: publish GovEngine 0.12.1 alpha
7f3f53e feat: integrate guarded bundle replay gate
6860c33 feat: add guarded root replay store
a8c82ff docs: stabilize GovEngine 0.12 public truth
687940b docs: calibrate GovEngine 0.12 release truth
22c799f refactor: retire GovEngine security profile facade
9f88451 test: isolate GovEngine pip check validation
```

## Signposter Capability Summary

The `signposter` command was not on `PATH`. The available control-plane command
is:

```text
/home/probo/projects/signposter/.venv/bin/signposter
```

Inspected command groups:

- `planner`: `draft`, `validate`, `seed`, `next`, `run`, `advance`, `impact`,
  `side-task-plan`, `step`, `mark`, `roadmap`, `regenerate`, `status`
- `lifecycle`: `status`, `next`, `watch`
- `run`: dry-run planning, claim, prompt writing, and explicit backend execution
- `worktree`: plan/apply isolated worktrees
- `review`, `merge`, `integration`, `cleanup`
- `labels`, `control-plane`, `issue-factory`, `sync`

Important execution boundary:

- `run` defaults to `codex-cli`, but execution requires explicit `--execute`.
- OpenClaw execution was not used.
- GitHub mutation was only performed after dry-run or readiness output, except
  for two recovery mutations documented below.

## GovEngine Current-State Summary

GovEngine is an alpha governed-runtime kernel package at `0.12.2a0`.

Confirmed source areas:

- admission, policy, approval, and audit record validators;
- execution gate, dry-run runner, runner protocol, supervision, approved-spec,
  command-shape, and ticket gate helpers;
- SCLite lifecycle/review bridge and guarded replay helpers;
- signing/trust bridge with demo-only signer/verifier ports;
- evidence/review contracts;
- boundary, profile, planning, event, state, control, runtime-shell, OODA, and
  public surface registry modules.

Confirmed strategic gap from repository and audit evidence:

GovEngine has real component gates, but it does not yet expose one canonical
runtime admission result that composes prepared execution contract status,
policy decision, execution ticket status, trust decision, guarded-strict
verification, replay freshness, runner profile, and receipt obligation.

## Audit Inputs

Inspected repository guidance and truth sources:

- `README.md`
- `PUBLIC_STATUS.md`
- `CONTRIBUTING.md`
- `SECURITY.md`
- `PUBLISHING.md`
- `CHANGELOG.md`
- `pyproject.toml`
- `docs/`
- `tests/`
- `scripts/`
- `.github/workflows/pytest.yml`

Inspected external audit files:

- `/home/probo/projects/audit/govengineapiboundary.txt`
- `/home/probo/projects/audit/govenginedeepaudit.txt`
- `/home/probo/projects/audit/govengineroadmap.txt`
- `/home/probo/projects/audit/govenginetargetarchitecture.txt`

## Roadmap Artifact

Created deterministic GovEngine roadmap artifacts:

- Plan: `docs/roadmaps/ge-governed-runtime-kernel-mvp-plan.json`
- Seed manifest: `docs/roadmaps/ge-governed-runtime-kernel-mvp-seed-manifest.json`
- Issue bodies: `docs/roadmaps/ge-issue-bodies/GE-001.md` through
  `docs/roadmaps/ge-issue-bodies/GE-045.md`

The roadmap contains 45 dependency-aware DAG nodes. The first task is `GE-001`.
The final task is `GE-045`.

Dependency shape:

- root task: `GE-001`
- ready after root: API truth and public truth grounding
- runtime admission chain before trust, receipt, ledger, replay, runner safety,
  inspect workflow, docs, smoke, and final audit
- final tail: `GE-043 -> GE-044 -> GE-045`

## Seed Result

Commands and results:

```text
signposter planner validate --plan docs/roadmaps/ge-governed-runtime-kernel-mvp-plan.json
-> pass

signposter planner seed --plan docs/roadmaps/ge-governed-runtime-kernel-mvp-plan.json --repo ExatronOmega/GovEngine --write-bodies --body-dir docs/roadmaps/ge-issue-bodies --write-manifest --manifest docs/roadmaps/ge-governed-runtime-kernel-mvp-seed-manifest.json --show-commands
-> ready, no GitHub mutation

signposter planner seed --plan docs/roadmaps/ge-governed-runtime-kernel-mvp-plan.json --repo ExatronOmega/GovEngine --write-bodies --body-dir docs/roadmaps/ge-issue-bodies --write-manifest --manifest docs/roadmaps/ge-governed-runtime-kernel-mvp-seed-manifest.json --apply
-> applied, created issues #1 through #45

signposter planner run --manifest docs/roadmaps/ge-governed-runtime-kernel-mvp-seed-manifest.json --sync-github --dry-run
-> ready, total=45, ready=1, waiting=44, next=GE-001/#1
```

## Recovery Notes

Two setup gaps were discovered and recovered:

1. GitHub Issues were initially disabled for `ExatronOmega/GovEngine`. After the
   repository setting was corrected externally, `control-plane status` could
   read issues normally.
2. Signposter required workflow labels, then claim required `gate:ci`. The
   `labels ensure` surface created the base workflow labels, but not `gate:ci`.
   The missing `gate:ci` label caused a partial claim failure that removed
   `state:ready` from issue #1. The smallest safe recovery was:
   - create `gate:ci`;
   - restore `state:ready` on #1;
   - rerun `signposter run --repo ExatronOmega/GovEngine --issue 1 --claim --write-prompt`.

Worktree setup also exposed a branch naming issue:

- GovEngine target branch is `work`.
- Signposter proposed worker branch `work/issue-1-ge-001-refresh-govengine-repository-and-signposter`.
- Git cannot create `refs/heads/work/...` while `refs/heads/work` exists.
- A manual local worktree was created at the Signposter-expected path
  `../signposter-work/1` using branch
  `issue-1-ge-001-refresh-govengine-repository-and-signposter`.
- The future PR base remains `work`.

## Validation Plan

GE-001 validation uses the current project truth gates:

```text
python scripts/validate_public_truth.py
python scripts/validate_alpha_readiness.py
python -m pytest tests/test_public_truth_consistency.py -q
python -m pytest tests/ -q
```

No package was published, no release was created, no tag was created, no
upstream mutation was performed, no secret or credential was changed, and no
live execution backend was invoked.
