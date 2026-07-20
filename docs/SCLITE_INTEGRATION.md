# GovEngine and SCLite

GovEngine depends exactly on the PyPI distribution `sclite-core==2.0.0`; the
Python import package is `sclite`.

The dependency exists because the projects cooperate, not because they share
ownership:

```text
GovEngine  governance decision over one bounded attempt
SCLite     canonical lifecycle/evidence artifacts and their verification
RExecOp    runtime lifecycle, artifact projection and execution
```

## Current v1 seam

RExecOp supplies GovEngine with bounded attempt facts and opaque references to
runtime-owned bytes. GovEngine evaluates policy, approval, scope and
capabilities and returns `GovernanceDecision`. After execution it checks
terminal runtime facts against that decision. RExecOp then projects the final
lifecycle, receipt and evidence artifacts that SCLite verifies.

GovEngine does not:

- define or extend SCLite schemas;
- reproduce SCLite canonical JSON or artifact hashing;
- verify SCLite lifecycle chains, Kernel Guard, ticket use or review bundles as
  its own authority;
- create SCLite receipts/evidence or store raw evidence;
- replace RExecOp's runtime artifact projection.

SCLite does not evaluate GovEngine policy, approval, scope or capability
meaning and does not perform runtime claim, lease, fencing or I/O.

## Digest boundary

Complete GovEngine-owned records are recomputed with GovEngine's record digest
rules. SCLite artifact digests and verification results are delegated inputs;
GovEngine does not reinterpret their canonicalization. See
[DIGEST_OWNERSHIP.md](DIGEST_OWNERSHIP.md).

## Compatibility bridges

`govengine.sclite_contracts` and older replay/admission/review helpers still
ship for compatibility. They call published SCLite verification/review
functions or map their outcomes into legacy GovEngine records. SCLite remains
the authority for every underlying check.

Legacy lifecycle names `verified_chain` and `verified_lifecycle`, plus migration
aliases `chain_verified` and `lifecycle_verified`, describe compatibility
projection state only. They are not a second lifecycle truth model and are not
part of the canonical v1 authorization protocol.

`ReplayClaimStore` expresses host-owned claim-once state for already verified
legacy guarded roots. Its in-memory adapter is development-only. It does not
verify HMAC, hold keys or provide production atomic storage.

## Freeze rule

SCLite 2.0 is frozen. GovEngine changes must use its existing public contracts.
A proposed new SCLite schema or semantic change is a stop condition requiring a
concrete cross-stack blocker, ownership analysis and separate review.

The full evaluation order is in
[SECURITY_INTEGRATION.md](SECURITY_INTEGRATION.md).
