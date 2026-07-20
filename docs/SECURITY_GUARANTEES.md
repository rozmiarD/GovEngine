# Security guarantees and non-claims

These guarantees apply when callers use the documented v1 records, supply
honest/current host adapters and RExecOp enforces the returned decision. They
do not apply when an in-process host bypasses or modifies GovEngine.

## Guarantees

| Guarantee | Mechanism | Executable evidence |
| --- | --- | --- |
| Strict bounded input | Shared JSON byte/depth/node/collection/string limits, duplicate-key and non-finite rejection, recursive forbidden keys | `test_api_hardening.py`, `test_security_properties.py`, conformance corpus |
| Deterministic policy | Typed closed operators, strict operand types, canonical condition order, bounded compilation, deny-first evaluation | `test_policy_conditions.py`, `test_policy_v1_stability.py` |
| Active policy binding | Digest/epoch/issuer/status/validity checked against host activation port | `test_governance_decision.py` |
| Approval is independent | Exact subject binding, trust policy, validity, revocation and host signature verification | `test_governance_request.py`, `test_governance_decision.py` |
| Scope is not self-authorized | Requested destination is compared with an independent scope policy | `test_scope_capabilities.py`, corpus |
| Capabilities are operation-driven | Requirements and inventory are independent; host registration booleans fail | `test_scope_capabilities.py`, corpus |
| Allowed decision is exact and short-lived | Authorization binds attempt/runtime/lease/fencing/spec/payload/scope/inventory/policy, nonce and expiry | `test_governance_decision.py` |
| Conforming runtime rejects replay | RExecOp verifies signature/bindings/expiry and atomically claims digest plus nonce before I/O | RExecOp G3 and shared conformance gates |
| Receipt postconditions are bound | Runtime receipt binds decision, permit, attempt and governance facts; output digest/limit checked after I/O | `test_receipt_conformance.py`, corpus |
| Frozen 1.0 candidate contract | 40-export facade and v1 record inventory are wheel-shipped and CI-frozen | `validate_api_stability.py`, `validate_v1_freeze.py` |

## Cryptographic and digest binding table

| Binding | Complete payload owner | GovEngine behavior | Security meaning |
| --- | --- | --- | --- |
| Policy pack digest | GovEngine | Recomputes canonical GovEngine digest | Exact compiled policy content, not issuer identity |
| Execution facts digest | GovEngine bounded projection | Recomputes | Exact bounded policy-evaluation facts |
| Requested scope digest | GovEngine bounded projection | Recomputes | Exact requested namespace/destination metadata |
| Scope policy digest | GovEngine | Recomputes | Exact independent allow policy |
| Capability requirements digest | GovEngine | Recomputes | Exact operation requirements |
| Capability inventory digest | GovEngine | Recomputes | Exact attested inventory record, not truth of attestor |
| Approval attestation digest | GovEngine | Recomputes and checks request binding | Exact approval record; identity still requires verifier/trust policy |
| Governance request digest | GovEngine | Produces | Exact governance transaction input |
| Governance decision digest | GovEngine | Produces/recomputes | Exact decision and authorization body |
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
- DNS, redirect, proxy, socket or subprocess enforcement;
- production storage atomicity for host-provided activation/revocation/claim
  ports;
- accuracy of host clocks, inventory attestations or external catalogs;
- raw evidence/output authenticity or storage;
- SCLite canonicalization, lifecycle or review-bundle verdicts;
- legal authorization, compliance certification or production readiness of
  the whole stack;
- `mutation_ready` posture.

## Required host behavior

The host must use current activation/revocation/trust adapters, verify the
signed decision, compare all runtime bindings, atomically claim authorization,
check a fresh runtime permit immediately before I/O, enforce connector/network
controls and emit the bound terminal receipt. Skipping any step voids the
corresponding guarantee.
