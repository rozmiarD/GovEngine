# GovEngine Public Status

GovEngine is a **pre-alpha governed-execution helper package** extracted from Ravenclaw.

## Current maturity

- Package import: working.
- Standalone tests: present.
- GitHub Actions: pytest on supported Python versions.
- Version: `0.1.2`.
- SCLite integration: present through helper seams via `sclite-core>=0.2.1,<0.3`.
- Runner protocol: dry-run/control-plane shape only.
- OODA safety loop: deterministic between-step decision contract.
- Live subprocess execution: not owned by GovEngine.
- Carrier adapters: deferred.
- PyPI publication: completed for the `0.1.x` line; each new release still requires the standard release checklist and operator approval before upload.

## What is public-safe today

GovEngine can be reviewed as a small Python package for:

- governed action/spec validation helpers;
- policy and scope helper seams;
- execution-ticket and approved-spec validation helpers;
- runner request/receipt shapes;
- OODA decision objects;
- signal, analysis, and evidence-confirmation contracts extracted from Ravenclaw;
- SCLite lifecycle integration boundaries.

## What is not claimed

GovEngine does not currently claim:

- production runtime readiness;
- live exploit or scanner capability;
- authorization to run tools against targets;
- protocol adapter correctness;
- complete API stability;
- production/stable PyPI API readiness;
- a full replacement for Ravenclaw Runtime.

## Release posture

Keep GovEngine in `0.y.z` until:

1. GovEngine's public API boundary remains documented and tested enough for external users;
2. changelog, security, contribution, validation, and publishing docs stay complete;
3. release artifacts can be built and checked reproducibly;
4. Ravenclaw consumes the released package without Git URL pin drift.
