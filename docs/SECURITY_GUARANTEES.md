# Security guarantees and non-claims

These guarantees apply when callers use the documented v1 records, supply
honest/current host adapters and RExecOp enforces the returned decision. They
do not apply when an in-process host bypasses or modifies GovEngine.

## Guarantees

| Guarantee | Mechanism | Executable evidence |
| --- | --- | --- |
| Strict bounded input | Shared JSON byte/depth/node/collection/string limits, duplicate-key and non-finite rejection, recursive forbidden keys | `test_api_hardening.py`, `test_security_properties.py`, conformance corpus |
| Deterministic policy | Typed closed operators, strict operand types, canonical condition order, bounded compilation, deny-first evaluation | `test_policy_conditions.py`, `test_policy_v1_stability.py` |
| Compiled policy snapshot integrity | Private complete-payload seal plus detached canonical recompilation before evaluation, digesting and enforcement admission | `test_policy_conditions.py`, `test_policy_engine.py`, `test_policy_enforcement.py` |
| Active policy binding | Digest/epoch/issuer/status/validity checked against host activation port; authorization cannot outlive the activation observed at issuance | `test_governance_decision.py` |
| Approval is independent | Exact subject binding, trust policy, validity, revocation and host signature verification | `test_governance_request.py`, `test_governance_decision.py` |
| Scope is not self-authorized | Requested destination is compared with an independent scope policy | `test_scope_capabilities.py`, corpus |
| Capabilities are operation-driven | Requirements and inventory are independent; host registration booleans fail | `test_scope_capabilities.py`, corpus |
| Allowed decision is exact and short-lived | Authorization binds attempt/runtime/lease/fencing/spec/payload/scope/inventory/policy and nonce; expiry is bounded by 60 seconds, policy activation and approval when present | `test_governance_decision.py` |
| Optional typed mutation/recovery admission is exact | A deep-module-only composite calls the actual v1 evaluator, preserves typed v0.1 denial semantics, discounts only its deliberate approval blocker and cross-binds actual mode plus typed/request/decision/approval digests | `test_typed_execution_governed_admission.py` |
| Policy-bound plugin admission is exact | Additive v0.2 discounts exactly one approval blocker plus `unsupported_backend_class` only for an exact non-built-in/non-raw-shell plugin posture, then requires matching frozen-v1 requirements/inventory and exact singleton signed-decision backend/egress controls; request metadata never authorizes | `test_typed_execution_governed_admission_v02.py` |
| Conforming runtime rejects replay | RExecOp verifies signature/bindings/expiry and atomically claims digest plus nonce before I/O | RExecOp G3 and shared conformance gates |
| Receipt postconditions are bound | Runtime receipt binds decision, permit, attempt and governance facts; output digest/limit checked after I/O | `test_receipt_conformance.py`, corpus |
| Frozen 1.0 candidate contract | 40-export facade and v1 record inventory are wheel-shipped and CI-frozen | `validate_api_stability.py`, `validate_v1_freeze.py` |

## Cryptographic and digest binding table

| Binding | Complete payload owner | GovEngine behavior | Security meaning |
| --- | --- | --- | --- |
| Policy pack digest | GovEngine | Validates a sealed detached snapshot, then recomputes the unchanged canonical GovEngine digest | Exact compiled policy content, not issuer identity or producer authenticity |
| Execution facts digest | GovEngine bounded projection | Recomputes | Exact bounded policy-evaluation facts |
| Requested scope digest | GovEngine bounded projection | Recomputes | Exact requested namespace/destination metadata |
| Scope policy digest | GovEngine | Recomputes | Exact independent allow policy |
| Capability requirements digest | GovEngine | Recomputes | Exact operation requirements |
| Capability inventory digest | GovEngine | Recomputes | Exact attested inventory record, not truth of attestor |
| Approval attestation digest | GovEngine | Recomputes and checks request binding | Exact approval record; identity still requires verifier/trust policy |
| Governance request digest | GovEngine | Produces | Exact governance transaction input |
| Governance decision digest | GovEngine | Produces/recomputes | Exact decision and authorization body |
| Typed governed admission digest | GovEngine | Produces/recomputes | Version-specific exact binding projection across unchanged typed v0.1 and frozen v1 records; v0.2 additionally binds plugin posture, capability requirements and decision controls; not decision authority |
| Signed decision | Host signer/verifier | Binds decision digest, purpose and signer policy | Authenticity only as strong as host trust configuration |
| Runtime permit digest | RExecOp | Treated as opaque and checked in receipt | Exact immutable RExecOp permit under RExecOp canonicalization |
| Execution spec/payload/fencing digests | RExecOp | Validates shape and binds | Opaque references to exact runtime-owned bytes/facts |
| SCLite artifact digests | SCLite | Delegates verification | SCLite canonical artifact integrity/lifecycle truth |

Digest equality does not prove that the producer was honest, that I/O occurred,
or that an identifier has legal authority.

## Stable failure behavior

Public security decisions use bounded machine-readable reason codes. Dynamic
details such as an invalid field, source reason or drifted binding belong in
bounded context. Unknown v1 states fail closed. Redacted explanation traces do
not include actual request operand values.

## Explicit non-claims

GovEngine does not guarantee:

- resistance to a malicious or compromised in-process RExecOp/host;
- production identity, PKI/KMS/HSM/key custody or trust-root administration;
- correctness, isolation or certification of plugins/connectors;
- plugin entry-point provenance, wrapper correctness, process/network isolation
  or live Chrony behavior;
- DNS, redirect, proxy, socket or subprocess enforcement;
- production storage atomicity for host-provided activation/revocation/claim
  ports;
- continuous activation lookup or background invalidation of an authorization
  after it is issued;
- accuracy of host clocks, inventory attestations or external catalogs;
- raw evidence/output authenticity or storage;
- SCLite canonicalization, lifecycle or review-bundle verdicts;
- legal authorization, compliance certification or production readiness of
  the whole stack;
- `mutation_ready` posture.
- a production approval provider, signed-decision claim store, runtime permit,
  exactly-once I/O, automatic retry, crash recovery or live recovery execution
  from the optional typed governed-admission projection alone.
- release/publication, mutation readiness or production qualification from the
  v0.2 plugin posture projection alone.

Specifically, v0.2 does not certify plugin code or entry-point provenance,
validate a wrapper implementation, isolate a process or network, qualify live
Chrony, prove mutation readiness, guarantee exactly-once I/O or crash/power-loss
recovery, provide production approval infrastructure, or authorize release or
publication. It adds no standalone plugin certificate.

## Required host behavior

The host must use current activation/revocation/trust adapters, verify the
signed decision, compare all runtime bindings, atomically claim authorization,
check a fresh runtime permit immediately before I/O, enforce connector/network
controls and emit the bound terminal receipt. If the deployment requires a
policy status change after issuance to take effect before the bounded
authorization expiry, the host must perform a fresh activation check or
re-evaluate governance. Skipping any required step voids the corresponding
guarantee.
