# GovEngine 1.x API and schema compatibility

The candidate stable import boundary is `govengine.v1`. Its exact 40 exports
and every GovEngine-owned v1 schema constant are recorded in the wheel-shipped
`govengine/v1_compatibility_manifest.json`. The release gate runs
`scripts/validate_v1_freeze.py`; an unrecorded export, v1 record, schema change
or manifest drift fails closed.

## Compatibility rules

- Changing a required field, field type, validation meaning, digest input or
  security semantic of a v1 record requires a new schema version and a major
  release.
- An optional addition within a schema requires an explicit compatibility
  decision, a manifest update, positive and negative conformance cases, and a
  migration note. It must not weaken fail-closed behavior.
- Record validators define unknown-field behavior. New governance v1 boundary
  records reject unknown fields; legacy records retain their documented
  compatibility behavior.
- `govengine.v1` cannot gain, remove or rename an export without an API
  decision, consumer evidence and a major-version plan.
- `govengine.experimental.*`, fixtures, legacy root imports and module-scoped
  compatibility helpers are outside the stable facade.

## Legacy policy migration

Policy pack `v0.1` remains compatibility-only and receives no new language
features. `govengine.policy.migration.migrate_policy_pack_v0_1_to_v1()` converts
the equality map into typed `eq` conditions, but requires the caller to provide
issuer, epoch and validity. It does not sign, trust, activate or store policy.

Consumers should:

1. replace supported root imports with `govengine.v1`;
2. migrate policy packs to schema v1 and establish an authenticated
   `PolicyActivationBinding`;
3. submit the v1 `GovernanceRequest` and validate the v1
   `GovernanceDecision`;
4. keep runtime claim, permit and I/O mechanics in RExecOp.

## Deprecation

During the 1.x line, a stable facade symbol is not removed or behaviorally
repurposed in a minor release. A planned removal is first documented as
deprecated with a replacement and migration note, remains available through
the next minor line, and is removed only in the next major release.

Legacy alpha/root symbols may be reclassified or removed after downstream
import scans prove no supported consumer remains. Experimental and fixture
surfaces have no compatibility guarantee.

## Conformance corpus

The wheel includes `govengine/conformance/v1`. Every case is plain JSON with a
fixed operation, serialized input, expected outcome for both `govengine` and
`rexecop`, binding digests or explicit `not_applicable`, maximum schema version
and forbidden output keys. `scripts/generate_conformance_corpus.py --check`
prevents generated fixture drift. GovEngine executes every GovEngine-owned
case and validates RExecOp-owned cases as explicit ownership handoffs; RExecOp
is the reference runtime consumer for atomic decision claim behavior.
