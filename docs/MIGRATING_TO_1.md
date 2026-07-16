# Migrating to GovEngine 1

This guide covers migration from the published `govengine==0.16.11` line to
the `govengine==1.0.0rc1` source candidate. The candidate depends on frozen
`sclite-core==2.0.0`; the matching runtime candidate is
`rexecop==0.3.0rc3`.

Do not mix the old published stack and the source-candidate stack in one
environment. Before publication, build the exact source commits into a local
wheelhouse and install all exact pins from that wheelhouse.

## Stable import boundary

Only the 40 exports listed in the wheel-shipped
`govengine/v1_compatibility_manifest.json` receive the 1.x compatibility
promise:

```python
from govengine.v1 import (
    ApprovalAttestation,
    GovernanceDecision,
    GovernanceRequest,
    PolicyEngine,
    evaluate_governance,
)
```

Do not infer stability from a symbol being available at the package root.
Legacy root imports, experimental modules, fixtures, runtime-shell, lifecycle,
OODA and supervision records remain outside the stable v1 facade.

## Governance flow

Replace flows that treat `RuntimeAdmissionResult`, a policy admission digest,
an approval-looking string or a host boolean as execution authority.

The v1 flow is:

1. compile and activate a typed v1 policy pack;
2. build a digest-bound `GovernanceRequest`;
3. validate an independently sourced `ApprovalAttestation` when required;
4. evaluate one `GovernanceDecision`;
5. let RExecOp verify and atomically claim the signed decision for the exact
   attempt immediately before I/O;
6. validate the runtime receipt against that decision;
7. let SCLite verify the final review bundle.

GovEngine does not issue RExecOp runtime permits, own queues, leases, fencing,
connector dispatch, I/O or claim storage. SCLite does not need a new schema or
feature for this migration.

## Policy packs

Policy pack `v0.1` remains compatibility-only. Convert equality-map conditions
with:

```python
from govengine.policy.migration import migrate_policy_pack_v0_1_to_v1
```

The caller must provide the issuer, policy epoch and validity window. Migration
does not sign, trust, activate, revoke or persist a policy pack. The resulting
v1 pack uses typed operators and must pass the normal compiler and activation
gates.

## Approval, scope and capabilities

- Admission is not approval. Supply a bound, expiring and revocable
  `ApprovalAttestation` for approval-required operations.
- Requested destination facts must be compared with an independent
  `ScopePolicyBinding`; requests cannot carry their own allowlist.
- Operation requirements must be declared independently of the backend.
  Compare them with a digest-bound capability inventory.
- Any policy, target, inventory, attempt, runtime, lease or fencing drift
  invalidates the decision/claim path.

## RExecOp consumer migration

Use `rexecop==0.3.0rc3` for the source-candidate stack. It consumes the shared
33-case governance corpus, verifies trusted signed decisions, atomically
claims the decision nonce, produces the runtime permit and terminal receipt,
and checks the decision again before connector I/O.

Planning-only trigger, supervisor and automation adapters remain available for
compatibility, but cannot substitute for the canonical attempt-bound v1
decision.

## Receipt and proof

GovEngine receipt conformance checks decision, attempt, runtime permit, lease,
fencing, scope, inventory and output obligations. It does not claim that a
compromised runtime reported honest output. RExecOp produces runtime receipts;
SCLite remains the final lifecycle, evidence and review-bundle authority.

## Rollback

Rollback means returning to a separate environment containing the exact
published `govengine==0.16.11` dependency line and its matching consumers. Do
not serialize v1 records and feed them to an older runtime, and do not loosen
validators to make mixed-version environments pass.

Before promotion, run:

```bash
python scripts/validate_v1_freeze.py
python scripts/generate_conformance_corpus.py --check
python scripts/validate_release_readiness.py
```

The matching RExecOp checkout must also pass:

```bash
python scripts/validate_release_train_preflight.py
python scripts/validate_g6_release_candidate_gate.py
```
