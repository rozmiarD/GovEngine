# GovEngine public status

GovEngine is an in-process Python governance kernel. The published
`govengine==1.0.0rc1` package evaluates policy, approval, scope and capability
facts for one concrete operation attempt and returns a deterministic governance
decision. It does not execute the operation or define artifact truth.

## Current release

| Item | Current truth |
| --- | --- |
| Current `main` version label | `1.0.0rc1`; contains unreleased post-tag fixes |
| Published immutable artifact | `govengine==1.0.0rc1` from tag `v1.0.0rc1` |
| Python | `>=3.11`; CI covers 3.11, 3.12 and 3.13 |
| Required dependency | `sclite-core==2.0.0` |
| Stable-candidate facade | `govengine.v1`, exactly 40 exports |
| GovEngine-owned v1 records | 15 |
| Conformance corpus | 33 cases: 5 valid, 28 negative |
| Independent review | published `rc1` complete; current `main` requires new-candidate review |
| RC observation | active until `2026-07-27T17:39:58.058090Z` |
| Reference runtime | `rexecop==1.0.0rc1` |
| Profile alignment | Tecrax `0.4.0rc3` pending realignment from `rexecop==0.3.0rc3` |

The release was published from immutable tag `v1.0.0rc1` through the
tag-confirmed OIDC workflow. Current `main` retains the `1.0.0rc1` version label
but differs from the published artifact because it includes unreleased
security, compatibility and documentation fixes. Those changes require
`1.0.0rc2` qualification before final `1.0.0`; the published RC observation
does not qualify them by itself.

The immutable PyPI long description for `1.0.0rc1` is stale: it contains the
pre-publication README, including obsolete release-blocked and `0.16.11`
installation wording. The wheel version, exact dependency and recorded hashes
remain valid. The corrected description will ship with the next candidate.
The machine-readable current release train is
[`docs/release-train.json`](docs/release-train.json).

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
