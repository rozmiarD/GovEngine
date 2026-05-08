# GovEngine Validation

GovEngine validation is local and public-safe. It does not run live targets.

## Local package gate

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
python -m pip check
```

Expected current result:

- standalone pytest suite passes;
- package dependencies are consistent;
- no Ravenclaw runtime or Logdash process is started.

## What the focused tests cover

Current tests cover:

- public module imports;
- action compilation;
- dry-run result assembly;
- neutral scope helpers;
- approved execution spec and ticket helper shapes;
- SCLite lifecycle verifier seam availability.

## Ravenclaw consumption gate

Ravenclaw's migration branch validates that it can consume GovEngine as an external git dependency instead of using an in-tree `govengine/` copy.

The important checks are:

```bash
python -m pytest -q \
  engine/tests/test_govengine_dependency_isolation.py \
  engine/tests/test_govengine_stage2b_seams.py \
  engine/tests/test_govengine_policy_seam.py \
  engine/tests/test_govengine_command_shape_seam.py \
  engine/tests/test_govengine_runner_seam.py \
  engine/tests/test_executor_v2.py
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
- confirm `pyproject.toml` consumes GovEngine from the intended git pin.

## Non-claims

These checks do not prove:

- live subprocess execution safety;
- authorization to test live targets;
- production deployment readiness;
- protocol adapter correctness;
- Logdash UI behavior.

GovEngine is currently a reusable governed-execution helper layer, not a full autonomous runtime.
