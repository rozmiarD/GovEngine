# GovEngine Public Status

GovEngine is a **pre-alpha governed-execution helper package** extracted from Ravenclaw.

## Current maturity

- Package import: working.
- Standalone tests: present.
- GitHub Actions: pytest on supported Python versions.
- SCLite integration: present through helper seams.
- Runner protocol: dry-run/control-plane shape only.
- OODA safety loop: deterministic between-step decision contract.
- Live subprocess execution: not owned by GovEngine.
- Carrier adapters: deferred.
- PyPI publication: not ready yet.

## What is public-safe today

GovEngine can be reviewed as a small Python package for:

- governed action/spec validation helpers;
- policy and scope helper seams;
- execution-ticket and approved-spec validation helpers;
- runner request/receipt shapes;
- OODA decision objects;
- SCLite lifecycle integration boundaries.

## What is not claimed

GovEngine does not currently claim:

- production runtime readiness;
- live exploit or scanner capability;
- authorization to run tools against targets;
- protocol adapter correctness;
- complete API stability;
- PyPI release readiness;
- a full replacement for Ravenclaw Runtime.

## Release posture

Keep GovEngine in `0.y.z` until:

1. SCLite is available through a stable package dependency path;
2. GovEngine's public API boundary is documented and tested enough for external users;
3. changelog, security, contribution, validation, and publishing docs are complete;
4. release artifacts can be built and checked reproducibly;
5. Ravenclaw consumes the released package without git pin drift.
