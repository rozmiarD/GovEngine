# GE-041 Signposter-Managed Lifecycle Smoke

Date: 2026-06-06
Branch: `issue-41-ge-041-signposter-lifecycle-smoke`
Issue: GE-041 / #41

## Purpose

This bounded artifact records a completed GovEngine roadmap item moving through
the actual Signposter-managed lifecycle on the target repository and branch.

The smoke uses GE-040 / issue #40 as the completed low-risk item. It verifies
that the current GovEngine stage can pass through report, gate, PR, review,
merge, integration, cleanup, and planner advance without bypassing the
Signposter control plane.

## Lifecycle Evidence

| Step | Evidence |
| --- | --- |
| Planner selection | `signposter planner next --manifest docs/roadmaps/ge-governed-runtime-kernel-mvp-seed-manifest.json --sync-github` selected GE-040 / #40 after GE-039 advanced. |
| Claim | `signposter run --repo ExatronOmega/GovEngine --issue 40 --claim` moved #40 from `state:ready` to `state:active` and added `gate:ci`. |
| Prompt | `signposter run --repo ExatronOmega/GovEngine --issue 40 --write-prompt` wrote `artifacts/prompts/issue-40.md`. |
| Worker report | `signposter artifact write-worker-summary ... --apply` wrote `artifacts/runs/issue-40-worker.summary.md`; `signposter report --apply` posted a bounded issue report. |
| Gate | `signposter gate --repo ExatronOmega/GovEngine --issue 40 --dry-run` returned `PASS` and proposed `state:active -> state:done`. |
| Completion | `signposter complete --repo ExatronOmega/GovEngine --issue 40 --apply` moved #40 to `state:done`; the issue remained open for integration ownership. |
| PR | PR #91 was created against `work` from `issue-40-ge-040-package-clean-install-smoke` after Signposter PR plan documented the known `work/issue-*` branch-shape blocker. |
| CI | PR #91 checks passed: `pytest (3.11)`, `pytest (3.12)`, `pytest (3.13)`, and `package-dry-run` in GitHub Actions run `27076704537`. |
| Review | `signposter review gate --repo ExatronOmega/GovEngine --pr 91` passed; `signposter review submit --repo ExatronOmega/GovEngine --pr 91 --apply` submitted non-author approval from `AlphaExatron`. |
| Merge | `signposter merge plan --repo ExatronOmega/GovEngine --pr 91` returned `ready`; `signposter merge apply --repo ExatronOmega/GovEngine --pr 91 --apply` squash-merged PR #91. |
| Integration | `signposter integration apply --repo ExatronOmega/GovEngine --pr 91 --apply` removed `state:done`, added `state:merged`, and closed issue #40. |
| Cleanup | `signposter cleanup apply --repo ExatronOmega/GovEngine --pr 91 --apply` removed the local worker branch/worktree state; lifecycle status later reported cleanup complete. |
| Planner advance | `signposter planner advance --manifest docs/roadmaps/ge-governed-runtime-kernel-mvp-seed-manifest.json --issue 40 --sync-github --apply` promoted GE-041 / #41 to `state:ready`. |

## Final State Snapshot

- Issue #40: `CLOSED`
- Issue #40 workflow label: `state:merged`
- PR #91: `MERGED`
- PR #91 base/head: `work` <- `issue-40-ge-040-package-clean-install-smoke`
- PR #91 merge commit: `a9ce428a82a54ea6b68ea969519fa35896e91445`
- Review: approved by `AlphaExatron`
- Integration: complete; issue closure owned by Signposter integration
- Cleanup: complete; no local #40 worktree or branch remains
- Auto-close keywords: absent from PR body; issue closure happened via Signposter integration

## Known Workflow Recovery Evidence

Signposter worktree and PR planning currently propose branch names under
`work/issue-*` and PR base `main`, while this GovEngine stage is executed from
the `work` branch. Local Git rejects `work/issue-*` because `refs/heads/work`
already exists. The safe recovery used for GE-040 was:

1. Run Signposter worktree/PR plan first and record the blocker.
2. Create a manual isolated branch `issue-40-ge-040-package-clean-install-smoke`
   from `work`.
3. Keep claim, prompt, worker report, gate, complete, review, merge,
   integration, cleanup, and planner advance under Signposter lifecycle
   surfaces.
4. Use fallback `gh pr create --base work` only after Signposter PR plan
   documented the incompatible branch/base proposal.

This recovery did not mutate `upstream`, publish a package, create a tag, close
the issue manually, enable live execution, or bypass CI/review/merge gates.

## Current GE-041 Validation

The GE-041 artifact itself is documentation-only. Local validation was run from
the issue #41 worktree before PR:

| Command | Result |
| --- | --- |
| `/tmp/govengine-ge041-clean-source/bin/python scripts/validate_public_truth.py` | passed; `public_truth_ok:govengine==0.12.2a0:sclite-core>=1.0.1,<1.1:surfaces=7` |
| `/tmp/govengine-ge041-clean-source/bin/python scripts/validate_alpha_readiness.py` | passed; `alpha_readiness_ok:govengine==0.12.2a0:0.12.2-alpha:surfaces=7` |
| `/tmp/govengine-ge041-clean-source/bin/python -m pytest -q -o cache_dir=/tmp/govengine-ge041-clean-source/pytest-cache` | passed; full suite green with one skipped test |
| `/tmp/govengine-ge041-clean-source/bin/python -m pip check` | passed; no broken requirements |
| `ruff check .` | passed |
| `git diff --check` | passed |

An earlier full-pytest attempt used the temporary GE-040 validation venv after
the GE-040 worktree had been cleaned up. That venv contained an editable install
pointing at the removed GE-040 worktree, so subprocess tests for
`scripts/inspect_runtime_admission.py` failed with `ModuleNotFoundError:
No module named 'govengine'`. The recovery was to create
`/tmp/govengine-ge041-clean-source` from the current GE-041 worktree and rerun
the clean-install validator successfully. No code change was required for this
environment-only blocker.

## Conclusion

The GovEngine roadmap has an observed completed Signposter lifecycle smoke:
GE-040 / #40 moved through bounded report, worker gate, PR #91, green CI,
review approval, squash merge, Signposter integration, cleanup, and planner
advance back into the DAG. The remaining workflow gap is the known Signposter
branch/base mismatch for this repository's `work` branch, which was handled by
a bounded fallback without bypassing lifecycle ownership.
