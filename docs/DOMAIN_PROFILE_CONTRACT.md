# Domain Profile Contract

A domain profile contract is the host-facing declaration that lets a runtime consume GovEngine without moving domain semantics into the kernel.

GovEngine `0.8.x` also exposes `govengine.profiles`, a minimal contract-only SDK around this boundary. The SDK provides `DomainProfile`, resource/task/stage registries, capability, runner, policy-hook, evidence-rule declarations, fixture Ravenclaw/Tecrax profiles, and `ProfileConformanceReport`. These declarations remain data and validation shapes; they do not implement adapters, credentials, product UX, domain taxonomy, or live execution.

## Contract Shape

`govengine.boundary.DomainProfileContract` is a serializable boundary object with:

- `name`: stable profile name;
- `version`: profile contract version;
- `owner`: host/runtime ownership label;
- `owns`: domain semantics the profile owns;
- `consumes`: GovEngine or SCLite surfaces the profile depends on;
- `non_claims`: explicit boundaries the profile does not claim;
- `metadata`: optional host metadata.

`validate_domain_profile_contract()` checks required shape and rejects forbidden ownership claims. `validate_domain_profile_conformance()` also rejects unknown consumed surfaces.

## Allowed Consumed Surfaces

Current boundary work allows profiles to consume:

- `govengine_artifact_governance_core`;
- `govengine_planning_contracts_core`;
- `govengine_admission_policy_core`;
- `govengine_evidence_review_core`;
- `govengine_domain_profile_sdk`;
- `govengine_controlled_execution_core`;
- `sclite_lifecycle_artifacts`;
- `sclite_review_bundles`.

Unknown consumed surfaces fail conformance so a profile cannot silently depend on an undocumented kernel capability.

## Forbidden Ownership

Profiles must not claim:

- `govengine_core_modules`;
- `sclite_schema_authority`;
- `live_execution_authority`;
- `credential_or_key_store`;
- `carrier_adapter_ownership`;
- `pki_or_kms_ownership`;
- `product_ux_ownership`.

These remain outside profile ownership even when a profile has runtime code that performs concrete work.

## Ravenclaw Compatibility

The built-in Ravenclaw profile contract identifies Ravenclaw as a security-research host profile. It owns campaign/runtime semantics and Logdash/operator workflow language, while consuming neutral GovEngine admission-policy and controlled-execution surfaces plus SCLite review bundles.

The `ravenclaw_security_profile()` SDK fixture is narrower than Ravenclaw itself: it declares security-research resource types, task families, planning stages, policy hooks, dry-run runner profile, and receipt-bounded evidence expectations. It does not make GovEngine own Ravenclaw finding taxonomy, Logdash, campaign UX, or target-test authorization.

## Tecrax Compatibility

Tecrax is reserved as a future governed infrastructure-operations runtime/profile. Its present implementation is only a dry-run/local-fixture skeleton used for conformance pressure; it does not establish infrastructure runtime ownership. Tecrax would own infrastructure domain semantics and change-management language, while GovEngine still owns only neutral kernel mechanics. Credential handling, host access, and live operations must stay runtime-owned and disabled by default in kernel examples.

The `tecrax_infra_ops_profile()` SDK fixture is a skeleton for dry-run/local-fixture infrastructure operations only. It exists to prove that GovEngine can validate a second domain profile without absorbing service inventories, credentials, change-management authority, live infrastructure control, or product UX.
