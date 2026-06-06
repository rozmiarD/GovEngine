# GE-040 Package and Clean-Install Validation Smoke

Date: 2026-06-06
Branch: `issue-40-ge-040-package-clean-install-smoke`
Issue: GE-040 / #40

## Purpose

This bounded validation artifact records the package and clean-install smoke
evidence for the governed-runtime kernel MVP stage.

The check proves that the current alpha source tree can be installed in a clean
environment, build local sdist/wheel artifacts, install the built wheel, import
the expected public surface, and pass dependency checks. It does not publish a
package, create a release, create a tag, enable live execution, or change any
host/SCLite ownership boundary.

## Environment

- Available local interpreter: `Python 3.14.4` via `python3`
- No local `python`, `python3.11`, `python3.12`, or `python3.13` executable was
  available in this worker shell.
- PR CI remains responsible for the repository-supported Python 3.11, 3.12, and
  3.13 matrix.
- Temporary validation paths:
  - clean source venv: `/tmp/govengine-ge040-clean-source`
  - build output: `/tmp/govengine-ge040-dist.Q3gaKz`
  - wheel smoke venv: `/tmp/govengine-ge040-wheel-smoke.p7vMcQ`

## Commands and Results

| Command | Result |
| --- | --- |
| `python3 scripts/validate_clean_package_install.py --venv /tmp/govengine-ge040-clean-plan --dev --dry-run --json` | passed; emitted planned clean-install steps |
| `python3 scripts/validate_clean_package_install.py --venv /tmp/govengine-ge040-clean-source --dev --json` | passed; installed GovEngine with dev dependencies, ran validators, full pytest, and scoped `pip check` |
| `/tmp/govengine-ge040-clean-source/bin/python -m pip install build twine` | passed; installed build tooling only in the temporary venv |
| `/tmp/govengine-ge040-clean-source/bin/python -m build --outdir /tmp/govengine-ge040-dist.Q3gaKz` | passed; built `govengine-0.12.2a0.tar.gz` and `govengine-0.12.2a0-py3-none-any.whl` |
| `/tmp/govengine-ge040-clean-source/bin/python -m twine check /tmp/govengine-ge040-dist.Q3gaKz/*` | passed for sdist and wheel |
| `python3 -m venv /tmp/govengine-ge040-wheel-smoke.p7vMcQ` | passed |
| `/tmp/govengine-ge040-wheel-smoke.p7vMcQ/bin/python -m pip install /tmp/govengine-ge040-dist.Q3gaKz/govengine-0.12.2a0-py3-none-any.whl` | passed; installed `govengine-0.12.2a0` and `sclite-core-1.0.1` |
| `/tmp/govengine-ge040-wheel-smoke.p7vMcQ/bin/python -c "import importlib.metadata as md, govengine; from govengine import public_surface_index; assert md.version('govengine') == govengine.__version__ == '0.12.2a0'; assert [s.name for s in public_surface_index()] == ['artifact_governance_core', 'planning_contracts_core', 'admission_policy_core', 'evidence_review_core', 'domain_profile_sdk', 'runtime_contract_proofs', 'controlled_execution_core']; print('wheel_install_smoke_ok:govengine==0.12.2a0:surfaces=7')"` | passed; printed `wheel_install_smoke_ok:govengine==0.12.2a0:surfaces=7` |
| `/tmp/govengine-ge040-wheel-smoke.p7vMcQ/bin/python -m pip check` | passed; no broken requirements |
| `/tmp/govengine-ge040-clean-source/bin/python scripts/validate_public_truth.py` | passed; `public_truth_ok:govengine==0.12.2a0:sclite-core>=1.0.1,<1.1:surfaces=7` |
| `/tmp/govengine-ge040-clean-source/bin/python scripts/validate_alpha_readiness.py` | passed; `alpha_readiness_ok:govengine==0.12.2a0:0.12.2-alpha:surfaces=7` |
| `/tmp/govengine-ge040-clean-source/bin/python -m pytest tests/ -q` | passed; full suite green with one skipped test |
| `/tmp/govengine-ge040-clean-source/bin/python -m pip check` | passed; no broken requirements |
| `ruff check .` | passed |

## Boundary Notes

- No upstream remote was mutated.
- No package was published.
- No release or tag was created.
- No live execution backend was enabled.
- No PKI/KMS/key-store scope was added.
- Raw build/test logs remain local; this artifact keeps only bounded evidence.

## Conclusion

GE-040 package and clean-install validation passed locally. The only local
environment caveat is that the worker shell exposed Python 3.14.4 only; the
GitHub Actions PR matrix must still pass for Python 3.11, 3.12, and 3.13 before
merge.
