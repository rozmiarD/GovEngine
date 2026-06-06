# GE-043 Final Hardening Audit

Date: 2026-06-06
Branch: `issue-43-ge-043-hardening-audit`
Issue: GE-043 / #43

## Scope

This audit covers the governed-runtime kernel MVP state after GE-040, GE-041,
and GE-042 were integrated. It focuses on boundary correctness, dry-run safety,
SCLite delegation, trust non-overclaim, receipt/evidence chain, audit ledger,
replay semantics, runner safety, tests, package smoke, CI evidence, and
remaining risks.

This audit is bounded evidence. It does not add a live backend, publish a
package, create a release or tag, mutate upstream, claim production readiness,
or move host-owned policy/key/evidence responsibilities into GovEngine.

## Result

Status: pass with tracked residual risks.

The current GovEngine MVP is coherent as an alpha host-neutral governance
kernel. It exposes deterministic admission, trust, replay, receipt/evidence,
audit-ledger, runner-safety, inspect-only, docs, and validation surfaces without
turning intent into execution authority.

## Boundary Audit

| Area | Finding | Evidence | Status |
| --- | --- | --- | --- |
| Runtime admission | `RuntimeAdmissionResult` and `compose_runtime_admission_result()` provide the canonical bounded decision surface. Missing policy, invalid ticket, invalid trust, stale replay, live-by-default, missing runner profile, and missing receipt obligation are covered by tests. | `govengine/admission.py`; `tests/test_admission_contracts.py`; `docs/RUNTIME_ADMISSION.md` | pass |
| SCLite delegation | GovEngine consumes SCLite lifecycle/guard/review signals and does not claim SCLite schemas, canonicalization, guarded verification, artifact-chain verification, ticket semantics, or review-bundle authority. | `docs/SCLITE_INTEGRATION.md`; `tests/test_sclite_lifecycle_bridge.py`; `tests/test_guarded_bundle_source_chain_e2e.py` | pass |
| Replay freshness | `ReplayClaimStore` and `InMemoryReplayClaimStore` express claim-once semantics while documenting production atomicity as host-owned. | `govengine/replay.py`; `tests/test_guard_replay.py`; `docs/SCLITE_INTEGRATION.md` | pass |
| Trust/signing | GovEngine-owned record serialization/digest and signed envelopes are scoped to GovEngine records. Demo signer/verifier remain fixture-only; key resolver/trust store are ports, not PKI/KMS/key-store ownership. | `govengine/signing.py`; `tests/test_signing_bridge.py`; `docs/API_BOUNDARY.md`; `docs/API_STABILITY_MATRIX.md` | pass |
| Receipt/evidence binding | Runner receipt binding and evidence/review chain helpers bind admission, ticket, request, receipt, evidence, and review references without storing raw evidence or replacing SCLite review authority. | `govengine/execution/runner_protocol.py`; `govengine/review.py`; `tests/test_execution_supervision.py`; `tests/test_review_contracts.py`; `tests/test_standalone_smoke.py` | pass |
| Audit ledger | `AuditLedgerPort` and `JsonlAuditLedgerAdapter` provide local append/read/verify smoke evidence only. Production persistence, locking, retention, deletion, reconstruction, and concurrency remain host-owned. | `govengine/admission.py`; `tests/test_admission_contracts.py`; `docs/ADMISSION_POLICY.md` | pass |
| Runner safety | Dry-run remains the only GovEngine-owned runner behavior. `evaluate_local_subprocess_runner_readiness()` keeps `LocalSubprocessRunner` not applicable until missing host-owned safety prerequisites are satisfied. | `govengine/execution/supervision.py`; `tests/test_execution_supervision.py`; `docs/RUNNER_SUPERVISION.md`; `docs/LOCAL_SUBPROCESS_RUNNER_DECISION.md` | pass |
| Operator docs | The MVP runbook now ties admission, trust, replay, runner profile, receipt obligation, and evidence/review binding into one operator-facing chain while preserving non-claims. | `docs/GOVERNED_RUNTIME_MVP_RUNBOOK.md`; `README.md`; `docs/VALIDATION.md` | pass |
| Public truth | Public truth and alpha readiness validators cover package version, SCLite dependency line, public surfaces, no retired modules, package dry-run, docs markers, and alpha non-claims. | `scripts/validate_public_truth.py`; `scripts/validate_alpha_readiness.py`; `tests/test_public_truth_consistency.py` | pass |

## Test and CI Evidence

Local validation for this audit branch:

- `python3 scripts/validate_clean_package_install.py --venv /tmp/govengine-ge043-clean-source --dev --json`
- `/tmp/govengine-ge043-clean-source/bin/python scripts/validate_public_truth.py`
- `/tmp/govengine-ge043-clean-source/bin/python scripts/validate_alpha_readiness.py`
- `/tmp/govengine-ge043-clean-source/bin/python -m pytest tests/ -q`
- `/tmp/govengine-ge043-clean-source/bin/python -m pip check`
- `ruff check .`
- `git diff --check`

Recent integrated CI evidence:

- PR #91 for GE-040 passed `pytest (3.11)`, `pytest (3.12)`,
  `pytest (3.13)`, and `package-dry-run`.
- PR #92 for GE-041 passed `pytest (3.11)`, `pytest (3.12)`,
  `pytest (3.13)`, and `package-dry-run`.
- PR #93 for GE-042 passed `pytest (3.11)`, `pytest (3.12)`,
  `pytest (3.13)`, and `package-dry-run`.

The local worker shell exposes Python 3.14.4 only. Supported Python 3.11, 3.12,
and 3.13 coverage comes from GitHub Actions PR CI.

## Workflow Audit

Signposter lifecycle successfully moved GE-040, GE-041, and GE-042 through
report, gate, completion, PR, review, merge, integration, cleanup, local branch
sync, and planner advance.

Known Signposter/GovEngine workflow gap:

- Signposter worktree and PR planning propose `work/issue-*` branches and PR
  base `main`.
- This repository's active integration branch is `work`.
- Local Git rejects `work/issue-*` because `refs/heads/work` already exists.

Safe recovery used for this roadmap:

1. Run Signposter dry-run/plan first and record the blocker.
2. Create an isolated manual branch `issue-<n>-...` from `work`.
3. Keep claim, prompt, report, gate, complete, review, merge, integration,
   cleanup, and planner advance under Signposter lifecycle surfaces.
4. Create the PR with fallback `gh pr create --base work` only after
   Signposter PR plan documents the incompatible base/head proposal.

This gap is not a GovEngine runtime safety blocker, but it should remain visible
for Signposter hardening.

## Residual Risks

- Production audit/replay persistence remains host-owned. The current JSONL and
  in-memory adapters are development evidence only.
- Production trust anchors, key storage, revocation, rotation, PKI, CA, and KMS
  remain host-owned ports.
- Live subprocess execution remains intentionally absent/not applicable.
- Local Python-version coverage is limited by the worker shell; CI supplies the
  supported Python 3.11-3.13 matrix.
- Signposter label inference currently classified GE-043 as low/ci from labels
  even though the issue contract says high/review. This audit used the stricter
  contract interpretation for review/merge handling.

## Decision

GE-043 is complete when this artifact, local validation, PR CI, review, merge,
integration, cleanup, and planner advance pass. No blocker requires a side-DAG
before GE-044. The remaining risks are documented and should be carried into
GE-045 final roadmap completion reporting.
