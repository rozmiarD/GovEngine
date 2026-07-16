# GovEngine v1 independent review package

This package prepares, but does not complete, the independent v1 contract
security review. The implementing agent and stack maintainer cannot mark the
review record independent.

## Immutable contract baseline

Review these exact source commits:

| Repository | Version | Commit | Role |
| --- | --- | --- | --- |
| GovEngine | `1.0.0rc1` | `bd7ac496006bd8447f6722fb346e0033815aac64` | v1 governance contract baseline |
| RExecOp | `0.3.0rc3` | `78676f0d6ecd46011553ce2106dbf4fae5594885` | reference runtime consumer and claim enforcement |
| SCLite | `2.0.0` | `2470373c6384c284ab48df7ce763f0938797d155` | frozen proof/review authority |
| Tecrax | `0.4.0rc3` | `0c737c821451489af17e5e1d5a0db0fdd51ee01f` | downstream profile/pin evidence only |

The GovEngine RC-window record binds the facade/schema manifest, conformance
manifest and reason-code registry. Any drift in those inputs requires a new RC
and invalidates this review target.

## Required review scope

Review at least:

1. approval identity, expiry, revocation and exact subject bindings;
2. policy activation, issuer, validity, epoch and typed operator semantics;
3. independent requested scope/network policy and capability inventory inputs;
4. decision authorization binding to attempt, runtime, lease, fencing,
   inventory and policy;
5. trusted signature verification and RExecOp-owned atomic claim-once;
6. pre-I/O rejection for stale/untrusted/drifted decisions;
7. runtime receipt conformance and post-I/O obligations;
8. bounded JSON validation, reason codes and explanation leakage;
9. TCB and the explicit lack of malicious in-process host resistance;
10. SCLite ownership/freeze and absence of new SCLite contracts.

Use these as primary evidence:

- `govengine/v1_compatibility_manifest.json`;
- `docs/THREAT_MODEL.md`;
- `docs/SECURITY_GUARANTEES.md`;
- `docs/MIGRATING_TO_1.md`;
- `govengine/conformance/v1/`;
- RExecOp `scripts/validate_g3_runtime_governance_gate.py`;
- RExecOp `scripts/validate_g6_release_candidate_gate.py`;
- RExecOp `scripts/validate_governance_conformance.py`.

## Reproduction commands

GovEngine:

```bash
python scripts/validate_public_truth.py
python scripts/validate_v1_freeze.py
python scripts/validate_rc_window.py
python scripts/generate_conformance_corpus.py --check
python scripts/validate_v1_security_review.py
python -m pytest -q
```

RExecOp:

```bash
python scripts/validate_release_train_preflight.py
python scripts/validate_governance_conformance.py
python scripts/validate_g3_runtime_governance_gate.py
python scripts/validate_g6_release_candidate_gate.py
bash scripts/run_alpha_signoff_checks.sh
```

The release-only command below must fail before the reviewer completes the
record:

```bash
python scripts/validate_v1_security_review.py --require-independent
```

## Completion

After review, update `v1-contract-review.json`:

- `status`: `independent_reviewed`;
- non-empty reviewer identity and organization/reference;
- `independent_of_implementation`: `true`;
- `reviewed_commit`:
  `bd7ac496006bd8447f6722fb346e0033815aac64`;
- aware UTC completion timestamp;
- every finding with severity, summary and disposition;
- computed `open_p0` and `open_p1`, both zero for release.

P2/P3/informational findings may remain accepted non-blocking only when the
reviewer explicitly records that disposition. Any P0/P1 or required contract
change blocks rc1 and requires remediation; contract drift requires a new RC.
