# GovEngine v1 independent review

The v1 contract review is complete. The machine-readable record is
`v1-contract-review.json` and reports:

- reviewer: `ExatronOmega`;
- status: `independent_reviewed`;
- reviewed contract baseline:
  `bd7ac496006bd8447f6722fb346e0033815aac64`;
- open P0 findings: `0`;
- open P1 findings: `0`.

The review covers governance request/approval bindings, policy activation,
scope/capability independence, signed-decision handoff, RExecOp pre-I/O claim,
terminal-runtime-fact conformance, bounded JSON/reason codes, SCLite ownership
and the malicious-host non-claim.

Validate the committed record with:

```bash
python scripts/validate_v1_security_review.py
python scripts/validate_v1_security_review.py --require-independent
```

The first command is the normal structural CI gate. The second is the release
gate and currently passes. Neither command substitutes for reviewing later
contract changes. The reviewed baseline, RC-window baseline, release-tag commit
and later documentation commits have distinct roles; tags and signed review
records must not be rewritten to make them identical.

See [v1-review-package.md](v1-review-package.md) for immutable review inputs and
[../../PUBLISHING.md](../../PUBLISHING.md) for the release procedure.
