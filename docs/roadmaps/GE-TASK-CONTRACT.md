# GE Task Contract v1

This contract applies to GovEngine roadmap task bodies that reference
`GE-TASK-CONTRACT v1`.

## Purpose

The contract removes repeated boilerplate from individual roadmap tasks while
preserving the same Signposter lifecycle, safety, validation, and reporting
requirements.

## Control Plane

- Use Signposter as the workflow control plane.
- Prefer Signposter-native commands over direct GitHub mutation.
- Run dry-run or plan commands before every guarded mutation.
- Use `--apply` only after the matching plan says ready.
- Do not use OpenClaw execution.
- Do not invoke an execution backend unless the existing Signposter permission
  model explicitly allows it.
- Do not manually close issues; issue closure belongs to Signposter integration.
- Do not bypass gates.

## Repository Boundary

- Work in `ExatronOmega/GovEngine` on the `work` branch unless repository policy
  proves another branch is required.
- Do not mutate `upstream`.
- Do not publish packages, create releases, create tags, force-push, rotate
  secrets, change credentials, or change repository settings.
- Do not import Ravenclaw internals, replace SCLite, or add platform/product
  shell scope to GovEngine core.
- Preserve dry-run/default-safe behavior.

## Standard Lifecycle

For each task:

1. Select or confirm the next dependency-ready issue through Signposter.
2. Inspect issue state, dependencies, route, gate, risk, PRs, branches, and
   artifacts before changing files.
3. Run the Signposter dry-run/plan surface first.
4. Use an isolated worktree when practical.
5. Implement only the scoped task.
6. Run targeted validation for the changed surface.
7. Run `ruff check .` when available.
8. Run `python -m pytest tests/ -q` before push for code or test changes.
9. Run public truth / alpha validators when docs, package truth, surfaces, or
   roadmap claims are touched.
10. Commit only intended changes.
11. Push to `origin`, open/update one PR for the issue, and avoid auto-close
    keywords in PR text.
12. Wait for remote CI to pass.
13. Run review and merge gates; use explicit risk/scope overrides only when the
    plan requires them and evidence supports the override.
14. Merge only when Signposter merge plan is ready and CI is green.
15. Run Signposter integration, then cleanup, then planner advance.
16. Return to the DAG next task after side-task completion.

## Common Mutation Boundary

- GitHub mutation must be explicit and guarded.
- Issue creation/sync should use Signposter planner surfaces where available.
- If Signposter lacks a safe update surface, document the gap, show the planned
  mutation, keep it bounded, and avoid raw logs or secrets.
- PR bodies and comments must not use auto-close keywords.
- Raw logs stay local unless explicitly bounded and safe.

## Common Validation

Use the task-specific validation first. Then run the smallest additional set
needed by the changed files:

- `ruff check .`
- changed-surface pytest
- `python -m pytest tests/ -q`
- `python scripts/validate_public_truth.py`
- `python scripts/validate_alpha_readiness.py`
- `python -m pip check`
- `git diff --check`

If a command is not available or not relevant, report the exact reason instead
of claiming it passed.

## Common Stop Conditions

Stop and report a blocked state when:

- targeted validation fails;
- full pytest fails;
- public truth validation fails;
- CI fails;
- a mutation is requested without a ready plan/apply guard;
- merge or integration plan is not ready;
- a PR body would introduce auto-close keywords;
- live subprocess execution would be enabled before documented prerequisites;
- the task would cross GovEngine/SCLite/host ownership boundaries.

## Common Report Evidence

Every worker summary, review, PR, or issue comment should be compact,
deterministic, honest, bounded, and explicit about:

- files changed;
- behavior implemented or verified;
- validation commands and results;
- safety notes;
- whether GitHub mutation happened;
- whether issue closure/integration/cleanup is still pending;
- whether the task returns to mainline after a side-task.

## Per-Task Body Requirements

Each lightweight task body must still include:

- task ID and title;
- contract version reference;
- purpose;
- concrete scope;
- non-goals;
- dependencies;
- route / gate / risk / model tier;
- mutation boundary;
- acceptance criteria;
- validation commands;
- done criteria;
- task-specific stop conditions when stricter than this contract.
