# Profile governance projection (G3)

GovEngine G3 adds a side-effect-free profile governance projection and a
profile/connector compatibility report for M4 developer-surface work.

## Surfaces

- `ProfileGovernanceRequest` schema `v0.1` — bounded host projection with policy
  hooks, evidence expectations, runner posture, tracks, required capabilities,
  profile-declared capabilities, available runtime capabilities and connector
  backend descriptors. No raw commands, secrets, outputs or domain semantics.
- `ProfileGovernanceProjection` — validates hooks, evidence expectations,
  runner posture and supported tracks without interpreting profile taxonomy.
- `ProfileConnectorCompatibilityReport` — checks whether runtime-declared
  capabilities and connector descriptors cover required capabilities and
  baseline policy controls (`receipt_required`, `runner_dry_run_only`, etc.).
- `explain_profile_governance()` returns a digest-bound bundle with both
  records.

## CLI

```bash
govengine-policy profile-governance projection.json --json
```

The command does not execute connectors, store truth, or grant admission.

## RExecOp consumption

RExecOp builds the bounded projection from `profiles show` /
`run_profile_developer_check` and attaches the GovEngine bundle as
`govengine_governance`. RExecOp does not reimplement the compatibility logic in
core.