# Changelog

All notable public GovEngine changes should be documented here.

GovEngine follows conservative pre-1.0 versioning while the API boundary is still being extracted from Ravenclaw.

## Unreleased

- Calibrated validation, roadmap, publishing, and public-status docs after `govengine==0.1.0` PyPI publication.

## 0.1.0 - initial PyPI candidate

- Switched SCLite dependency from a Git URL pin to the published PyPI distribution `sclite-core>=0.2.1,<0.3`.
- Normalized package license metadata to SPDX-style `MIT`.
- Added `govengine.__version__` for package/version checks.
- Added OODA receipt/evidence guidance for recording compact governance-control decisions without publishing raw output or private telemetry.
- Added deterministic OODA safety/control primitives: `GovObservation`, `GovOrientation`, `GovOodaDecision`, and `GovOodaController`.
- Added carrier-neutral runner protocol primitives: `GovRunnerStep`, `GovRunnerRequest`, `GovRunnerStepResult`, `GovRunnerReceipt`, and `GovRunner`.
- Added public API envelopes: `GovApiResult` and `GovApiError`.
- Kept SCLite imports lazy where needed so GovEngine public surface imports cleanly in standalone checks.
- Documented that carrier adapters remain deferred until the package/release boundary is more mature.

## 0.0.0

- Initial public extraction scaffold.
- Added importable `govengine` package, standalone tests, GitHub Actions pytest workflow, and initial architecture/API-boundary documentation.
- Added reusable helpers extracted around action validation, policy gateway behavior, approved execution specs, execution-ticket checks, command-shape normalization, dry-run result assembly, scope helpers, and SCLite lifecycle integration seams.
