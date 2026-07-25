# GovEngine documentation

Start with [the repository README](../README.md). Current package status is in
[PUBLIC_STATUS.md](../PUBLIC_STATUS.md), release history in
[CHANGELOG.md](../CHANGELOG.md), and the operator release procedure in
[PUBLISHING.md](../PUBLISHING.md).

## Current v1 contract

- [ARCHITECTURE.md](ARCHITECTURE.md) — ownership, dependency direction and the
  canonical governance flow.
- [API_BOUNDARY.md](API_BOUNDARY.md) — stable-candidate, module-scoped and
  compatibility surfaces.
- [API_STABILITY_MATRIX.md](API_STABILITY_MATRIX.md) — machine-checked
  classification of every root export.
- [API_COMPATIBILITY.md](API_COMPATIBILITY.md) — 1.x compatibility and
  deprecation rules.
- [GOVERNANCE_REQUEST.md](GOVERNANCE_REQUEST.md) — request and approval
  bindings.
- [GOVERNANCE_DECISION.md](GOVERNANCE_DECISION.md) — deterministic decision and
  attempt-bound authorization.
- [POLICY_ENGINE.md](POLICY_ENGINE.md) — policy language, compiler, evaluator
  and explanations.
- [SCOPE_CAPABILITY_BINDINGS.md](SCOPE_CAPABILITY_BINDINGS.md) — independent
  scope and capability decisions.
- [RECEIPT_CONFORMANCE.md](RECEIPT_CONFORMANCE.md) — post-I/O obligation checks
  over bounded terminal runtime facts.
- [CONFORMANCE.md](CONFORMANCE.md) — shared governance-protocol corpus.
- [SCLITE_INTEGRATION.md](SCLITE_INTEGRATION.md) — the GovEngine/SCLite
  ownership seam.

## Security and operations

- [SECURITY_INTEGRATION.md](SECURITY_INTEGRATION.md) — required cross-component
  evaluation order.
- [THREAT_MODEL.md](THREAT_MODEL.md) — TCB, adversaries and residual risks.
- [SECURITY_GUARANTEES.md](SECURITY_GUARANTEES.md) — tested guarantees and
  explicit non-claims.
- [DIGEST_OWNERSHIP.md](DIGEST_OWNERSHIP.md) — recomputed, delegated,
  reference-only and produced digests.
- [VALIDATION.md](VALIDATION.md) — active local, CI, package and release gates.
- [release-train.json](release-train.json) — machine-readable current versions,
  exact dependency pins and alignment status.
- [DOWNSTREAM_IMPORT_MAP.md](DOWNSTREAM_IMPORT_MAP.md) — RExecOp/Tecrax consumer
  inventory.
- [MIGRATING_TO_1.md](MIGRATING_TO_1.md) — migration from the archived 0.16
  line.
- [ROADMAP.md](ROADMAP.md) — RC completion, stable promotion and bounded
  post-1.0 work.
- [security-review/README.md](security-review/README.md) — independent v1 review
  evidence.

## Compatibility references

The following pages document APIs that still ship but are outside
`govengine.v1`: [RUNTIME_ADMISSION.md](RUNTIME_ADMISSION.md),
[RECEIPT_BINDING.md](RECEIPT_BINDING.md),
[ADMISSION_POLICY.md](ADMISSION_POLICY.md),
[EVIDENCE_REVIEW.md](EVIDENCE_REVIEW.md),
[RUNNER_SUPERVISION.md](RUNNER_SUPERVISION.md),
[INSPECT_ONLY_ADMISSION_WORKFLOW.md](INSPECT_ONLY_ADMISSION_WORKFLOW.md),
[DOMAIN_PROFILE_CONTRACT.md](DOMAIN_PROFILE_CONTRACT.md),
[PROFILE_GOVERNANCE.md](PROFILE_GOVERNANCE.md),
[ORCHESTRATOR_MODEL.md](ORCHESTRATOR_MODEL.md),
[EVENT_MODEL.md](EVENT_MODEL.md), [STATE_MACHINE.md](STATE_MACHINE.md),
[CONTROL_MODEL.md](CONTROL_MODEL.md), and [RUNTIME_SHELL.md](RUNTIME_SHELL.md).

These are compatibility/migration references, not the current authorization
protocol and not a claim that GovEngine owns runtime mechanics.

## Archive

[archive/ROADMAP_VERSION_HISTORY.md](archive/ROADMAP_VERSION_HISTORY.md) is a
compact index of superseded release lines. Detailed history remains available
in Git and `CHANGELOG.md`; obsolete operator procedures are intentionally not
kept as runnable documentation.

When prose disagrees with executable truth, use package metadata, compatibility
manifests, validators, tests and workflows, then fix the prose and anti-drift
gate together.
