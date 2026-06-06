# Documentation Hygiene Audit

This audit classifies the tracked Markdown documentation present during the
GE-036A side task. It separates public GovEngine documentation from
Signposter roadmap artifacts and local-only scratch material.

## Decision

No tracked documentation is removed in this task.

The `docs/roadmaps/` files are workflow artifacts, not package API
documentation. They remain tracked because the active Signposter planner uses
`docs/roadmaps/ge-governed-runtime-kernel-mvp-seed-manifest.json` to continue
the current DAG. Removing those files mid-roadmap would break the current
Signposter-controlled lifecycle.

Future local-only roadmap notes must go under ignored scratch locations such as
`.signposter-local/` or `docs/roadmaps/local/`, or use ignored suffixes such as
`.local.md`, `.scratch.md`, or `.private.md`.

## Audited Root Documents

These files are public project documentation and remain tracked:

- `CHANGELOG.md`
- `CONTRIBUTING.md`
- `PUBLIC_STATUS.md`
- `PUBLISHING.md`
- `README.md`
- `SECURITY.md`

## Audited GovEngine Documentation

These files describe the alpha GovEngine kernel, boundaries, validation,
runtime admission, SCLite integration, runner supervision, evidence/review, and
public API truth. They remain tracked:

- `docs/ADMISSION_POLICY.md`
- `docs/API_BOUNDARY.md`
- `docs/API_STABILITY_MATRIX.md`
- `docs/ARCHITECTURE.md`
- `docs/CONTROL_MODEL.md`
- `docs/DOCUMENTATION_HYGIENE.md`
- `docs/DOMAIN_PROFILE_CONTRACT.md`
- `docs/EVENT_MODEL.md`
- `docs/EVIDENCE_REVIEW.md`
- `docs/GOVENGINE_KERNEL_BOUNDARY.md`
- `docs/GUARDED_FRESH_RUNTIME_ADMISSION_EXAMPLE.md`
- `docs/INSPECT_ONLY_ADMISSION_WORKFLOW.md`
- `docs/LOCAL_SUBPROCESS_RUNNER_DECISION.md`
- `docs/OODA_RECEIPT_EVIDENCE.md`
- `docs/ORCHESTRATOR_MODEL.md`
- `docs/PLANNING_CONTRACTS.md`
- `docs/RECEIPT_BINDING.md`
- `docs/ROADMAP.md`
- `docs/RUNNER_SUPERVISION.md`
- `docs/RUNTIME_ADMISSION.md`
- `docs/RUNTIME_SHELL.md`
- `docs/SCLITE_INTEGRATION.md`
- `docs/STATE_MACHINE.md`
- `docs/VALIDATION.md`

## Audited Roadmap Artifacts

These files are not GovEngine API documentation. They are tracked Signposter
control-plane artifacts for the current roadmap and remain tracked until the
stage is complete:

- `docs/roadmaps/GE-TASK-CONTRACT.md`
- `docs/roadmaps/ge-001-repository-signposter-audit.md`
- `docs/roadmaps/ge-governed-runtime-kernel-mvp-plan.json`
- `docs/roadmaps/ge-governed-runtime-kernel-mvp-seed-manifest.json`
- `docs/roadmaps/ge-issue-bodies/GE-001.md`
- `docs/roadmaps/ge-issue-bodies/GE-002.md`
- `docs/roadmaps/ge-issue-bodies/GE-003.md`
- `docs/roadmaps/ge-issue-bodies/GE-004.md`
- `docs/roadmaps/ge-issue-bodies/GE-005.md`
- `docs/roadmaps/ge-issue-bodies/GE-006.md`
- `docs/roadmaps/ge-issue-bodies/GE-007.md`
- `docs/roadmaps/ge-issue-bodies/GE-008.md`
- `docs/roadmaps/ge-issue-bodies/GE-009.md`
- `docs/roadmaps/ge-issue-bodies/GE-010.md`
- `docs/roadmaps/ge-issue-bodies/GE-011.md`
- `docs/roadmaps/ge-issue-bodies/GE-012.md`
- `docs/roadmaps/ge-issue-bodies/GE-013.md`
- `docs/roadmaps/ge-issue-bodies/GE-014.md`
- `docs/roadmaps/ge-issue-bodies/GE-015.md`
- `docs/roadmaps/ge-issue-bodies/GE-016.md`
- `docs/roadmaps/ge-issue-bodies/GE-017.md`
- `docs/roadmaps/ge-issue-bodies/GE-018.md`
- `docs/roadmaps/ge-issue-bodies/GE-019.md`
- `docs/roadmaps/ge-issue-bodies/GE-020.md`
- `docs/roadmaps/ge-issue-bodies/GE-021.md`
- `docs/roadmaps/ge-issue-bodies/GE-022.md`
- `docs/roadmaps/ge-issue-bodies/GE-023.md`
- `docs/roadmaps/ge-issue-bodies/GE-024.md`
- `docs/roadmaps/ge-issue-bodies/GE-025.md`
- `docs/roadmaps/ge-issue-bodies/GE-026.md`
- `docs/roadmaps/ge-issue-bodies/GE-027.md`
- `docs/roadmaps/ge-issue-bodies/GE-028.md`
- `docs/roadmaps/ge-issue-bodies/GE-029.md`
- `docs/roadmaps/ge-issue-bodies/GE-030.md`
- `docs/roadmaps/ge-issue-bodies/GE-031.md`
- `docs/roadmaps/ge-issue-bodies/GE-031A.md`
- `docs/roadmaps/ge-issue-bodies/GE-032.md`
- `docs/roadmaps/ge-issue-bodies/GE-033.md`
- `docs/roadmaps/ge-issue-bodies/GE-034.md`
- `docs/roadmaps/ge-issue-bodies/GE-035.md`
- `docs/roadmaps/ge-issue-bodies/GE-036.md`
- `docs/roadmaps/ge-issue-bodies/GE-037.md`
- `docs/roadmaps/ge-issue-bodies/GE-038.md`
- `docs/roadmaps/ge-issue-bodies/GE-039.md`
- `docs/roadmaps/ge-issue-bodies/GE-040.md`
- `docs/roadmaps/ge-issue-bodies/GE-041.md`
- `docs/roadmaps/ge-issue-bodies/GE-042.md`
- `docs/roadmaps/ge-issue-bodies/GE-043.md`
- `docs/roadmaps/ge-issue-bodies/GE-044.md`
- `docs/roadmaps/ge-issue-bodies/GE-045.md`

## Local-Only Boundary

The following locations and suffixes are reserved for untracked local work:

- `.signposter-local/`
- `docs/roadmaps/local/`
- `*.local.md`
- `*.scratch.md`
- `*.private.md`

Those files are local operator scratch space and must not be pushed.

Returning to mainline: next task is GE-039 after this side task is integrated
and cleaned up.
