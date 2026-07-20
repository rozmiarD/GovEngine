# Downstream GovEngine import map

This snapshot records the live GovEngine imports used by the current RExecOp
and Tecrax source trees. It is migration evidence, not a promise that every
legacy import will enter the stable facade.

Baseline checked on 2026-07-20:

- GovEngine `7a0a53d` plus the documentation corrections in this working tree;
- RExecOp `a3e6404`;
- Tecrax `a870658`.

The map is produced by `consumer_import_map()` in
`scripts/validate_api_stability.py`. The scanner covers Python files while
excluding virtual environments, build output, caches, and Git metadata.

## RExecOp

RExecOp has 44 unique `from govengine import ...` symbols, 35 unique deep
module imports and one package import, for 80 unique import paths:

- 12 root `v1-candidate` imports covering the API envelope, PolicyEngine and
  governance trace;
- 30 root adapter imports covering legacy admission, trigger/supervisor/automation,
  typed-execution, compatibility, profile explanation, and evidence review;
- 2 root `internal-exposed` imports: `build_scope_assertion` and
  `build_scope_decision`;
- 35 deep module imports: 22 `deep-only`, 6 `v1-candidate`, 5 adapters and
  2 signing fixtures. These include the canonical decision/signing/receipt
  conformance integration used by the runtime;
- one package import used for version/surface inspection.

Supported candidate imports should migrate to `govengine.v1` where the facade
exports the required symbol. Adapter and deep-only imports stay on their
existing module paths; the canonical G2/G3 contracts exist, but their
runtime-integration helpers are intentionally module-scoped. Internal-exposed
and deep-only imports must not be promoted merely because RExecOp consumes them.

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
