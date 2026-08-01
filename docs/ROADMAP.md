# GovEngine roadmap

GovEngine is in its public 1.0 release-candidate phase. The roadmap is now about
finishing and maintaining a narrow governance contract, not adding runtime
mechanics.

## Current 1.0 release-candidate line

Current source baseline: `govengine==1.0.0rc2`, exact-pinned to
`sclite-core==2.0.1`, prepared and unpublished. Published PyPI baseline remains
immutable `govengine==1.0.0rc1` on `sclite-core==2.0.0`.
Published PyPI baseline is `govengine==1.0.0rc1`.

## Responsibility boundary

```text
GovEngine   policy, approval, scope, capabilities and governance decisions
RExecOp     operation lifecycle, leases/fencing, permits, retries and I/O
SCLite      lifecycle/evidence contracts, integrity and verification truth
Profiles    domain meaning, workflows, taxonomy and connector semantics
```

GovEngine does not acquire an adjacent responsibility merely because it
validates a reference or consumes a verifier result. SCLite 2.0 remains frozen;
new governance work must not require another SCLite contract unless a concrete
cross-stack blocker proves it unavoidable.

## Delivered for the 1.0 candidate

- frozen 40-export `govengine.v1` facade;
- 15 inventoried GovEngine-owned v1 records;
- typed, bounded and deterministic PolicyEngine;
- independent approval, scope policy and capability inventory inputs;
- one attempt/lease/fencing/runtime-bound `GovernanceDecision`;
- host signing/trust seam and RExecOp-owned atomic claim handoff;
- module-scoped terminal-runtime-fact conformance;
- 33-case language-neutral governance corpus shared with RExecOp;
- strict JSON bounds, stable reason codes and redacted explanations;
- threat model, security guarantees and independent review;
- tag-bound OIDC publication with provenance and public-index evidence.

Legacy admission, audit, planning, runner, OODA, orchestration, state-machine
and runtime-shell APIs still ship as classified compatibility/experimental
surfaces. They are not part of the 1.x promise.

## Gate to the next candidate and 1.0.0

`1.0.0rc2` is required before stable promotion. The coordinated release train
published SCLite `2.0.1` patch is pinned by the prepared GovEngine
`1.0.0rc2` source. The rc2 record-only review child and tag remain deferred.

The next candidate must include the post-tag security and compatibility fixes,
the corrected package long description and the complete documentation
anti-drift gate. It receives its own immutable tag, review/qualification
evidence and observation record. Final promotion then requires all of the
following:

- the new RC observation record is completed;
- no frozen facade, schema, corpus or reason-registry drift;
- the review covering the new candidate reports no open P0/P1 security finding;
- public installation of the new exact GovEngine/SCLite candidate pair remains
  reproducible;
- the matching RExecOp candidate continues to pass shared conformance and
  pre-I/O decision gates;
- API, migration, security, validation, publishing and package metadata remain
  consistent;
- the candidate-specific RC-window record is completed and every release gate
  in [PUBLISHING.md](../PUBLISHING.md) passes.

The existing `rc1` tag and artifacts remain immutable. A contract change or a
security-relevant post-tag fix is handled through a new RC and observation
record, never by refreshing `rc1` in place.

## Release train

The current dependency order is:

```text
sclite-core 2.0.1 -> govengine 1.0.0rc2 (prepared/unpublished)

sclite-core 2.0.0 -> govengine 1.0.0rc1 -> rexecop 1.0.0rc1

tecrax 0.4.0rc3: source-aligned/unpublished on govengine/rexecop rc1
```

RExecOp is the published reference runtime. Tecrax is a downstream profile, but
its current source candidate is not aligned with the published runtime line.
Ravenclaw is a legacy/external consumer and is not the next stage of this
release train.

## After 1.0

Priority work is deliberately narrow:

1. remove or further isolate unused compatibility exports after consumer scans;
2. automate post-publish PyPI install/evidence checks;
3. keep RExecOp/GovEngine conformance synchronized without widening either
   component's ownership;
4. improve host adapter guidance for activation, revocation, signing and atomic
   state while keeping production storage outside the kernel;
5. add bounded interoperability vectors only when a real second implementation
   exists.

Remote governance services, federated trust domains, UI, policy repositories,
carrier adapters and advanced policy composition are optional later projects,
not prerequisites for 1.0. Runtime scheduling, queues, lifecycle, connectors
and I/O remain out of scope permanently.

Delivered version history is in [CHANGELOG.md](../CHANGELOG.md); a compact map
of superseded architectural lines is in
[archive/ROADMAP_VERSION_HISTORY.md](archive/ROADMAP_VERSION_HISTORY.md).
