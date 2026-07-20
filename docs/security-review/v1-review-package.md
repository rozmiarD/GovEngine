# GovEngine v1 review package

This file records the immutable inputs used by the completed independent v1
contract review. It is evidence for the reviewed contract baseline, not a claim
that later commits were independently reviewed.

## Reviewed matrix

| Repository | Version at review | Commit | Role |
| --- | --- | --- | --- |
| GovEngine | `1.0.0rc1` candidate | `bd7ac496006bd8447f6722fb346e0033815aac64` | reviewed governance contract baseline |
| RExecOp | `0.3.0rc3` candidate | `78676f0d6ecd46011553ce2106dbf4fae5594885` | reference runtime enforcement evidence |
| SCLite | `2.0.0` | `2470373c6384c284ab48df7ce763f0938797d155` | frozen truth/verification dependency |
| Tecrax | `0.4.0rc3` candidate | `0c737c821451489af17e5e1d5a0db0fdd51ee01f` | downstream profile/pin evidence |

The later `v1.0.0rc1` tag points to
`33aefcd386351be622794e10cf5c43c8e812d6bc`; the RC-window baseline is
`0b5d483f1259aef681521a185e0cdfb19a538314`. These are release-engineering
checkpoints, not replacements for the reviewed contract baseline.

## Scope

The reviewer evaluated:

1. approval and governance-request digest bindings;
2. policy activation and typed deterministic evaluation;
3. independent scope policy and capability inventory;
4. signed decision and consume-once RExecOp handoff;
5. receipt conformance and post-I/O obligations;
6. bounded JSON, reason codes and redacted explanations;
7. RExecOp pre-I/O enforcement;
8. SCLite ownership/freeze and absence of new SCLite contracts;
9. threat model, TCB and explicit non-claims.

## Reproduction commands

GovEngine:

```bash
python scripts/validate_public_truth.py
python scripts/validate_v1_freeze.py
python scripts/generate_conformance_corpus.py --check
python scripts/validate_release_readiness.py
python -m pytest -q
```

RExecOp, from the reviewed checkout with exact stack pins:

```bash
python scripts/validate_release_train_preflight.py
python scripts/validate_g6_release_candidate_gate.py
bash scripts/run_alpha_signoff_checks.sh
```

Release review record:

```bash
python scripts/validate_v1_security_review.py --require-independent
```

The completed record is `v1-contract-review.json`. It reports an independent
review, zero findings, `open_p0=0` and `open_p1=0`. Later semantic changes to a
frozen v1 input require new review evidence; documentation-only clarification
does not move the historical reviewed commit.

## Non-claims

The review is bounded to the recorded contracts and commits. It is not a
penetration test, legal authorization, whole-stack production certification,
malicious-host proof, plugin audit or validation of future releases.
