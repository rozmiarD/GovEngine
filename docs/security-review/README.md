# Independent v1 contract security review

`v1-contract-review.json` is the release-gating record for an independent
semantic review of the GovEngine v1 governance contracts. Automated tests,
CodeQL and dependency audit are required evidence, but they do not replace
this review.

The reviewer should inspect at least:

- `GovernanceRequest`, approval, scope and capability binding completeness;
- policy activation, validity and epoch drift;
- decision authorization lifetime and attempt/runtime/lease/fencing/inventory
  bindings;
- signature/trust and consume-once ownership;
- receipt-to-decision/runtime-permit binding and postconditions;
- bounded JSON, reason-code and explanation leakage behavior;
- TCB and malicious-host non-claims;
- RExecOp shared conformance and pre-I/O claim enforcement;
- SCLite freeze/ownership boundaries.

To close the gate, set:

- `status` to `independent_reviewed`;
- a reviewer identity and organization/reference;
- `reviewed_commit` to the full immutable GovEngine commit;
- `completed_at` to an aware UTC timestamp;
- every finding with severity and disposition;
- `open_p0` and `open_p1` to zero.

Then run:

```bash
python scripts/validate_v1_security_review.py --require-independent
```

Self-review by the implementing agent does not satisfy this record.
