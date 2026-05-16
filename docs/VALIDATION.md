# GovEngine Validation

GovEngine validation is local and public-safe. It does not run live targets.

## Local package gate

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
python -m pip check
```

Expected result for the published `0.1.7` source line:

- standalone pytest suite passes (`72 passed` in the `0.1.7` source tree);
- package dependencies are consistent;
- `python -m build` creates `govengine-0.1.7` sdist/wheel artifacts;
- `python -m twine check dist/*` passes for the release artifacts;
- clean wheel install reports `govengine.__version__ == 0.1.7`, distribution version `0.1.7`, import checks for the artifact-governance, surface-registry, security-profile facade, and SCLite review-bundle bridge modules pass, and `pip check` is clean;
- clean install from PyPI with `govengine==0.1.7` reports `govengine.__version__ == 0.1.7`, distribution version `0.1.7`, `sclite-core==0.5.1`, SCLite review-bundle bridge checks pass, and `pip check` is clean;
- no Ravenclaw runtime or Logdash process is started;
- demo signer/verifier tests prove deterministic descriptor-digest binding and tamper rejection, not production identity or PKI readiness; scoped-ticket use-gate tests prove SCLite receipt/evidence bounds delegation, and review-bundle tests prove GovEngine delegates pass/fail verdicts to SCLite `0.5.1`, not live runtime enforcement.

Expected result for the current unreleased 0.2 kernel-boundary line:

- full pytest passes in the source tree;
- `python -m pip check` is clean;
- import smoke checks for `govengine.boundary`, `govengine.orchestration`, `govengine.events`, `govengine.state_machine`, and `govengine.control` pass;
- the public surface registry and `kernel_boundary_report()` agree that boundary, orchestration, event, state-machine, and control helpers are metadata/contracts only;
- no queue, scheduler, carrier adapter, credential store, runtime persistence, live command, or live execution authority is introduced.

## What the focused tests cover

Current tests cover:

- public module imports;
- action compilation;
- dry-run result assembly;
- neutral scope helpers;
- approved execution spec and ticket helper shapes;
- OODA decision outcomes and runner-control receipt shape;
- signal, analysis, and confirmation-evidence policy contract helpers;
- SCLite lifecycle verifier seam availability;
- SCLite review-bundle bridge pass/fail mapping for packaged GovEngine integration fixtures;
- artifact descriptor/envelope/state and transition-decision boundary objects;
- lifecycle transition gates and blocker/next-action reporting;
- signing/trust bridge decisions and deterministic demo signer/verifier ports without PKI/key ownership;
- dry-run-only execution gates and default `DryRunRunner` behavior;
- deconfliction/change-order and artifact state-index summaries;
- public surface registry separation between artifact-governance core, controlled-execution core, and optional security-profile helpers;
- optional `govengine.security_profile` facade grouping, JSON-safe index output, allowlisted lazy imports, and boundary assertions;
- kernel/profile/runtime/SCLite boundary contracts, boundary report, and domain-profile conformance checks;
- deterministic orchestration handoff records without scheduler, UI, adapter, credential, or live-execution authority;
- transport-neutral governance event metadata without raw prompt, credential, live-command, carrier-delivery, or schedule payloads;
- neutral run-state transitions and between-step control decisions without runtime storage, queue, scheduler, command, delivery, credential, or live-execution claims.

## Ravenclaw consumption gate

Ravenclaw should validate that it can consume GovEngine as the external PyPI package `govengine` instead of using an in-tree `govengine/` copy or a Git URL pin.

The important checks are:

```bash
python -m pytest -q \
  engine/tests/test_govengine_dependency_isolation.py \
  engine/tests/test_govengine_stage2b_seams.py \
  engine/tests/test_govengine_policy_seam.py \
  engine/tests/test_govengine_command_shape_seam.py \
  engine/tests/test_govengine_runner_seam.py \
  engine/tests/test_signal_contract.py \
  engine/tests/test_analysis_contract.py \
  engine/tests/test_executor_v2.py \
  engine/tests/test_govengine_control_gate_adapter.py
```

and Ravenclaw's Security Contract validation receipt:

```bash
python scripts/run_security_contract_validation.py --include-pytest --format markdown
```

## Public-safety checks

For any Ravenclaw publication that consumes GovEngine:

- assemble the Ravenclaw public snapshot;
- run Ravenclaw residue audit;
- confirm the snapshot does not include an in-tree `govengine/` directory;
- confirm `pyproject.toml` consumes GovEngine from the intended package range, not a Git URL pin.

## Non-claims

These checks do not prove:

- live subprocess execution safety;
- authorization to test live targets;
- production deployment readiness;
- protocol adapter correctness;
- Logdash UI behavior;
- that compact OODA receipt summaries are a substitute for raw forensic logs;
- that demo digest signatures are production signatures, identity proof, or PKI validation.

GovEngine is currently a reusable governed-execution helper layer, not a full autonomous runtime.
