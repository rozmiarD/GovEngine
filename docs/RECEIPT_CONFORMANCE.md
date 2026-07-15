# Runtime receipt conformance

`govengine.receipt_conformance` checks whether one bounded RExecOp terminal
attempt receipt conforms to the exact allowed `GovernanceDecision` that
preceded connector I/O.

The input binds:

- decision and opaque RExecOp runtime-permit digests;
- operation, step, attempt and runtime instance;
- lease, fencing, scope and capability inventory;
- execution spec, payload and policy epoch;
- terminal status, bounded output digests and measured output bytes.

GovEngine recomputes the receipt digest and returns a deterministic
`ReceiptConformanceResult`. A mismatch or unmet `output_digest_required` /
`max_output_bytes` postcondition is nonconformant with a stable reason code.
Malformed or digest-drifted records fail closed with `GovApiError`.

This surface does not execute I/O, claim the decision, verify the runtime
permit's internal semantics, store receipts, or prove that a compromised host
reported honest facts. RExecOp owns those runtime mechanics and supplies the
recomputed permit digest. SCLite remains the owner of final lifecycle receipt,
ticket-use and review-bundle truth.
