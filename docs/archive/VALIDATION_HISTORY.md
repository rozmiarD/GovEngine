# GovEngine validation history

Archived release-line validation evidence. The active gate lives in [../VALIDATION.md](../VALIDATION.md).

## Historical validation records

## Historical validation records

Historical expected result for the `0.14.0` package line (`0.14.0`):

- full pytest passes in the source tree;
- `python -m mypy govengine` passes for the package surface;
- `scripts/validate_clean_package_install.py` passes, rejects retired module paths from the installed artifact, and runs `pip check` inside its newly created virtual environment;
- `python scripts/validate_public_truth.py` passes;
- `python scripts/validate_alpha_readiness.py` passes;
- governed-runtime MVP surfaces (`RuntimeAdmissionResult`, receipt/evidence binding, audit ledger port, inspect-only workflow) pass without PolicyEngine MVP (`govengine.policy` landed in `0.15.0`).

Historical expected result for the published `0.1.7` source line:

- standalone pytest suite passes (`72 passed` in the `0.1.7` source tree);
- package dependencies are consistent;
- `python -m build` creates `govengine-0.1.7` sdist/wheel artifacts;
- `python -m twine check dist/*` passes for the release artifacts;
- clean wheel install reports `govengine.__version__ == 0.1.7`, distribution version `0.1.7`, import checks for the artifact-governance, surface-registry, security-profile facade, and SCLite review-bundle bridge modules pass, and `pip check` is clean;
- clean install from PyPI with `govengine==0.1.7` reports `govengine.__version__ == 0.1.7`, distribution version `0.1.7`, `sclite-core==0.5.1`, SCLite review-bundle bridge checks pass, and `pip check` is clean;
- no Ravenclaw runtime or Logdash process is started;
- demo signer/verifier tests prove deterministic descriptor-digest binding and tamper rejection, not production identity or PKI readiness; scoped-ticket use-gate tests prove SCLite receipt/evidence bounds delegation, and review-bundle tests prove GovEngine delegates pass/fail verdicts to SCLite `0.5.1`, not live runtime enforcement.

Historical expected result for the 0.2 kernel-boundary line:

- full pytest passes in the source tree;
- `python -m pip check` is clean;
- import smoke checks for `govengine.boundary`, `govengine.orchestration`, `govengine.events`, `govengine.state_machine`, and `govengine.control` pass;
- the public surface registry and `kernel_boundary_report()` agree that boundary, orchestration, event, state-machine, and control helpers are metadata/contracts only;
- no queue, scheduler, carrier adapter, credential store, runtime persistence, live command, or live execution authority is introduced.

Historical expected result for the `0.2.0` release line:

- `python -m build` creates `govengine-0.2.0` sdist/wheel artifacts;
- `python -m twine check dist/*` passes;
- clean wheel install reports `govengine.__version__ == 0.2.0`, distribution version `0.2.0`, import checks for the 0.2 boundary modules pass, and `pip check` is clean;
- clean install from PyPI with `govengine==0.2.0` reports `govengine.__version__ == 0.2.0`, distribution version `0.2.0`, and `sclite-core==0.5.1`.

Historical expected result for the 0.3 runtime-shell line:

- full pytest passes in the source tree;
- `python -m pip check` is clean;
- import smoke checks include `govengine.runtime_shell`;
- runtime-shell tests validate host control actions, queue snapshots, runtime snapshots, and scheduler-tick metadata;
- negative tests reject raw intent, commands, schedules, storage, credentials, carrier payloads, and live-execution claims;
- no queue persistence, scheduler loop, carrier adapter, credential store, runtime storage, live command, or live execution authority is introduced.

Historical expected result for the `0.3.0` release line before upload:

- `python -m build` creates `govengine-0.3.0` sdist/wheel artifacts;
- `python -m twine check dist/*` passes;
- clean wheel install reports `govengine.__version__ == 0.3.0`, distribution version `0.3.0`, `sclite-core==0.5.1`, import checks for `govengine.runtime_shell` pass, and `pip check` is clean;
- Ravenclaw validates against the 0.3 wheel/package line with `scripts/validate_public_install.py` and focused state/control projection tests;
- clean install from PyPI with `govengine==0.3.0` is required only after the operator-approved upload completes.

Historical expected result for the 0.4 planning-contract line:

- full pytest passes in the source tree;
- `python -m pip check` is clean;
- import smoke checks include `govengine.planning`;
- planning-contract tests validate `GovTaskContract`, `GovPlanIntentContract`, and `PlannerPort` shapes;
- negative tests reject raw targets, raw prompts, commands, credentials, storage/scheduler/live-execution claims, and duplicate task-contract IDs;
- no planner implementation, Ravenclaw security semantics, queue persistence, scheduler loop, adapter, credential store, runtime storage, live command, or live execution authority is introduced.

Historical expected result for the 0.5 admission-policy line:

- full pytest passes in the source tree;
- `python -m pip check` is clean;
- import smoke checks include `govengine.admission`;
- admission-policy tests validate `GovAdmissionDecision`, `GovPolicyDecision`, `GovApprovalRequest`, and `GovAuditRecord` shapes;
- negative tests reject raw targets, raw prompts, commands, credentials, carrier payloads, storage/scheduler/live-execution claims, and mismatched admission outcomes;
- no profile policy engine, operator approval workflow, audit storage/retention, adapter, credential store, runtime storage, live command, or live execution authority is introduced.

Historical expected result for the `0.5.0` release line:

- `python -m build` creates `govengine-0.5.0` sdist/wheel artifacts;
- `python -m twine check dist/*` passes;
- clean wheel install reports `govengine.__version__ == 0.5.0`, distribution version `0.5.0`, `sclite-core==0.5.1`, import checks for `govengine.admission` pass, and `pip check` is clean;
- clean install from PyPI with `govengine==0.5.0` reports `govengine.__version__ == 0.5.0`, distribution version `0.5.0`, `sclite-core==0.5.1`, `admission_policy_core` in the public surface index, and `pip check` is clean.

Historical expected result for the 0.6 runner-supervision line:

- full pytest passes in the source tree;
- `python -m pip check` is clean;
- import smoke checks include `govengine.execution.supervision`;
- runner-supervision tests validate `GovRunnerLease`, `GovSupervisionPlan`, `GovSupervisionDecision`, supervised runner requests, and runner receipts;
- negative tests reject raw-intent runner requests, missing approved specs, missing receipts, live backend use without explicit enablement, and forbidden metadata claims;
- no live subprocess backend, lease persistence, scheduler loop, carrier adapter, credential store, runtime storage, or live execution authority is introduced.

Historical expected result for the `0.6.0` release line:

- `python -m build` creates `govengine-0.6.0` sdist/wheel artifacts;
- `python -m twine check dist/*` passes;
- clean wheel install reports `govengine.__version__ == 0.6.0`, distribution version `0.6.0`, `sclite-core==0.5.1`, import checks for `govengine.execution.supervision` pass, and `pip check` is clean;
- clean install from PyPI with `govengine==0.6.0` reports `govengine.__version__ == 0.6.0`, distribution version `0.6.0`, `sclite-core==0.5.1`, `GovSupervisionPlan` import/use succeeds, and `pip check` is clean.

Historical expected result for the `0.7.0` release line:

- `python -m build` creates `govengine-0.7.0` sdist/wheel artifacts;
- `python -m twine check dist/*` passes;
- clean wheel install reports `govengine.__version__ == 0.7.0`, distribution version `0.7.0`, `sclite-core==0.5.1`, import checks for `govengine.review` pass, and `pip check` is clean;
- clean install from PyPI with `govengine==0.7.0` reports `govengine.__version__ == 0.7.0`, distribution version `0.7.0`, `sclite-core==0.5.1`, `evidence_review_core` in the public surface index, and `pip check` is clean.
