# GovEngine public status

GovEngine is an in-process Python governance kernel. The published
`govengine==1.0.0rc2` package evaluates policy, approval, scope and capability
facts for one concrete operation attempt and returns a deterministic governance
decision. It does not execute the operation or define artifact truth.

## Current release

| Item | Current truth |
| --- | --- |
| Current source version | `govengine==1.0.0rc2`; published with active observation |
| Published immutable artifact | `govengine==1.0.0rc2` from tag `v1.0.0rc2` |
| Python | `>=3.11`; CI covers 3.11, 3.12 and 3.13 |
| Source dependency | `sclite-core==2.0.1` |
| Stable-candidate facade | `govengine.v1`, exactly 40 exports |
| GovEngine-owned v1 records | 15 |
| Conformance corpus | 33 cases: 5 valid, 28 negative |
| Independent review | rc2 external re-review #4 approved with zero open P0/P1 |
| RC observation | active through `2026-08-15T11:15:02.258488Z` |
| Reference runtime | `rexecop==1.0.0rc1` |
| Profile alignment | Tecrax `0.4.0rc3` source-aligned/unpublished on the rc1 train |

The release was published from immutable tag `v1.0.0rc2` through confirmed
workflow run `31254483143`, including source-A recovery, authentic review and
window validation, exact A/B artifact equality, provenance and PyPI OIDC.
Current `main` contains only post-tag evidence updates. Stable promotion
remains `publishable=false` until the active seven-day observation is completed
and downstream RExecOp qualification against the public rc2 pair passes.

The public wheel and normalized sdist exactly match the reviewed artifacts.
Their SHA-256 values are recorded in the rc2 external-review record and
[PUBLISHING.md](PUBLISHING.md).
The machine-readable current release train is
[`docs/release-train.json`](docs/release-train.json).

Source/package version: `1.0.0rc2`.
Latest published PyPI package: `govengine==1.0.0rc2`.

## Supported contract

The 1.x compatibility promise is limited to the wheel-shipped
`govengine.v1` facade and v1 record inventory. The candidate provides:

- deterministic, typed, deny-first policy compilation and evaluation;
- `ApprovalAttestation` validation with exact subject, validity, trust and
  revocation bindings;
- `GovernanceRequest` and `GovernanceDecision` for one operation attempt;
- independent target/network scope policy and capability compatibility;
- short-lived authorization bound to runtime, attempt, lease, fencing, policy,
  scope and capability inventory;
- stable reason codes, bounded/redacted explanations and governance traces;
- module-scoped signed-decision and terminal-runtime-fact conformance helpers;
- a language-neutral governance-protocol corpus consumed by GovEngine and
  RExecOp.

The compatibility manifest is `govengine/v1_compatibility_manifest.json`.
Availability at the package root does not imply 1.x stability.

## Ownership

```text
Domain profiles   domain meaning, intents, workflows, connector semantics
RExecOp           lifecycle, queues, leases, fencing, permits, retries and I/O
GovEngine         policy, approval, scope, capability and governance decisions
SCLite            lifecycle/evidence contracts, integrity and verification truth
```

GovEngine recomputes complete GovEngine-owned governance records. It treats
RExecOp- and SCLite-owned digests as delegated or opaque references and does
not reproduce their canonicalization.

## Compatibility surface

The package root still exposes 308 classified names inherited from pre-v1
development: 40 `v1-candidate`, 188 adapter, 61 experimental and 19 fixture
exports. Planning, runtime-shell, lifecycle, OODA, runner, audit, review and
profile helpers remain available only for compatibility or controlled
migration. They do not make GovEngine a scheduler, lifecycle owner, executor,
storage backend, domain profile or second SCLite truth layer.

RExecOp is the reference runtime consumer. Tecrax is a downstream profile.
Ravenclaw is a legacy/external consumer, not the current reference runtime.

## Security posture

GovEngine is deterministic and fail-closed at its documented boundaries, but
it runs inside the host process. A compromised host can bypass the kernel,
fabricate inputs or ignore a decision. Production identity, trust roots,
revocation, activation, claim-once persistence, clocks, connector enforcement
and secrets remain host/runtime responsibilities.

GovEngine does not claim:

- malicious-host resistance or whole-stack production certification;
- legal authorization or operator accountability;
- PKI, KMS, HSM, CA, key or credential custody;
- operation lifecycle, scheduling, queues, retries, rollback or connector I/O;
- DNS, redirect, proxy, socket, subprocess or plugin isolation;
- raw output/evidence authenticity or storage;
- SCLite schemas, canonicalization, lifecycle verification or review verdicts;
- a production replay, approval, policy or audit database;
- `mutation_ready` posture.

See [the threat model](docs/THREAT_MODEL.md),
[security guarantees](docs/SECURITY_GUARANTEES.md),
[validation](docs/VALIDATION.md), and [publishing](PUBLISHING.md).
