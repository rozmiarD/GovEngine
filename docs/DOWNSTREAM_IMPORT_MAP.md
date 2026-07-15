# Downstream GovEngine import map

This snapshot records the live GovEngine imports used by the current RExecOp
and Tecrax source trees. It is migration evidence, not a promise that every
legacy import will enter the stable facade.

Baseline checked on 2026-07-15:

- GovEngine `6397c70`;
- RExecOp `abce051`;
- Tecrax `a9f72b1`.

The map is produced by `consumer_import_map()` in
`scripts/validate_api_stability.py`. The scanner covers Python files while
excluding virtual environments, build output, caches, and Git metadata.

## RExecOp

RExecOp has 44 unique `from govengine import ...` symbols and 55 unique import
paths across root and module imports:

- 15 `v1-candidate` imports: `GovApiError`, `PolicyCompiler`,
  `PolicyEnforcementPlan`, `PolicyEngine`, `CompiledPolicyPack`,
  `PolicyVerdict`, `admit_policy_execution`, `explain_policy_evaluation`,
  `policy_pack_digest`, `policy_enforcement_admission`,
  `policy_enforcement_admission_digest`, `policy_enforcement_plan_digest`,
  `project_governance_trace`, `validate_policy_enforcement_admission`, and
  `validate_policy_enforcement_plan`;
- 32 adapter imports covering legacy admission, trigger/supervisor/automation,
  typed-execution, compatibility, profile explanation, and evidence review;
- 2 `internal-exposed` imports: `build_scope_assertion` and
  `build_scope_decision`;
- 5 deep-only imports: `normalize_argv`, `GovRunnerRequest`, `GovRunnerStep`,
  `network_policy_binding_digest`, and
  `runtime_capability_descriptor_digest`;
- one package import used for version/surface inspection.

The 15 candidate imports may migrate to `govengine.v1`. Adapter imports stay on
their existing alpha paths until G2/G3 provides canonical decision and receipt
contracts. Internal-exposed and deep-only imports must not be promoted merely
because RExecOp currently consumes them.

## Tecrax fixture

Tecrax has no root `from govengine import ...` imports. Its local fixture uses
14 module-level imports:

- 5 adapters from supervision, profile conformance, and review;
- 6 experimental planning/runtime-shell symbols;
- 3 fixtures: `tecrax_contract_proof`, `validate_runtime_contract_proof`, and
  `tecrax_infra_ops_profile`.

These imports remain fixture/profile integration evidence. They are not a
reason to move planning or runtime-shell mechanics into `govengine.v1`.

## Gate

```bash
python scripts/validate_api_stability.py \
  --consumer-root /path/to/rexecop \
  --consumer-root /path/to/tecrax
```

The gate rejects an unclassified root export, an undocumented root callable,
a duplicate classification, a missing owner/migration note, facade drift, a
v1 facade larger than 40 symbols, or an unsupported downstream root import.
