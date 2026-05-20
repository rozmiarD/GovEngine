# Domain Profile Contract

A domain profile contract is the host-facing declaration that lets a runtime consume GovEngine without moving domain semantics into the kernel.

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

Current 0.2 boundary work allows profiles to consume:

- `govengine_artifact_governance_core`;
- `govengine_admission_policy_core`;
- `govengine_controlled_execution_core`;
- `govengine_security_profile_helpers`;
- `sclite_lifecycle_artifacts`;
- `sclite_review_bundles`.

Unknown consumed surfaces fail conformance so a profile cannot silently depend on an undocumented kernel capability.

## Forbidden Ownership

Profiles must not claim:

- `govengine_core_modules`;
- `sclite_schema_authority`;
- `live_execution_authority`;
- `credential_or_key_store`;
- `carrier_adapter_ownership`.

These remain outside profile ownership even when a profile has runtime code that performs concrete work.

## Ravenclaw Compatibility

The built-in Ravenclaw profile contract identifies Ravenclaw as a security-research host profile. It owns campaign/runtime semantics and Logdash/operator workflow language, while consuming GovEngine admission-policy, controlled-execution, and optional security-profile helpers plus SCLite review bundles.

## Tecrax Compatibility

Tecrax is reserved as a future governed infrastructure-operations runtime/profile. Until it is implemented, GovEngine should only document compatibility expectations: Tecrax would own infrastructure domain semantics and change-management language, while GovEngine would still own only the neutral kernel mechanics. Credential handling, host access, and live operations must stay runtime-owned and disabled by default in kernel examples.
