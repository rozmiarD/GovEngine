# GovEngine roadmap

GovEngine is in its public 1.0 release-candidate phase. The roadmap is now about
finishing and maintaining a narrow governance contract, not adding runtime
mechanics.

Current package baseline: `govengine==1.0.0rc1`, exact-pinned to
`sclite-core==2.0.0`. Published PyPI baseline is `govengine==1.0.0rc1`.

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

## Gate to 1.0.0

Final promotion requires all of the following:

- the RC observation window ends at `2026-07-27T17:39:58.058090Z` and its
  record is completed;
- no frozen facade, schema, corpus or reason-registry drift;
- no open P0/P1 security finding;
- public installation of `govengine==1.0.0rc1` with
  `sclite-core==2.0.0` remains reproducible;
- the matching RExecOp candidate continues to pass shared conformance and
  pre-I/O decision gates;
- API, migration, security, validation, publishing and package metadata remain
  consistent;
- `python scripts/validate_rc_window.py --require-completed` and every release
  gate in [PUBLISHING.md](../PUBLISHING.md) pass.

If a frozen contract changes, the correct response is a new RC and observation
record, not refreshing `rc1` in place.

## Release train

The current dependency order is:

```text
sclite-core 2.0.0 -> govengine 1.0.0rc1
                  -> rexecop 0.3.0rc3
                  -> tecrax 0.4.0rc3
```

RExecOp is the reference runtime. Tecrax is a downstream profile. Ravenclaw is
a legacy/external consumer and is not the next stage of this release train.

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
