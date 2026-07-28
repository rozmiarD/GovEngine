# GovEngine threat model

## Scope and security objective

GovEngine is an in-process deterministic governance kernel. Its security
objective is to make one policy/approval/scope/capability decision
machine-checkable and digest-bound so a cooperating runtime can enforce it
immediately before I/O and check terminal runtime facts against the decision.

GovEngine is not a sandbox, remote authorization service, identity provider,
secret store, network proxy or execution runtime.

## Trusted computing base

The effective trusted computing base (TCB) includes:

- the GovEngine package and Python process that executes it;
- the host integration that supplies policy activation, approval revocation,
  signature verification and clocks;
- the signer/verifier and their configured trust roots;
- RExecOp's decision verification, atomic claim, lease/fencing enforcement,
  runtime permit and connector boundary;
- storage implementations used for activation, revocation and consume-once
  semantics;
- SCLite for final artifact canonicalization, lifecycle and proof verification.

A malicious or fully compromised in-process host can skip GovEngine, replace
its inputs, ignore its decision or fabricate a receipt. The kernel does not
claim resistance to that attacker. Isolation against a malicious host requires
a separately protected service/process, independent identity and enforcement
boundary, which are outside 1.0.

## Trust boundaries

```text
policy author/repository
  -> authenticated PolicyActivationBinding
approval provider
  -> ApprovalAttestation + revocation/signature ports
RExecOp bounded attempt facts
  -> GovernanceRequest
GovEngine
  -> GovernanceDecision + typed_execution_governed_admission:v0.1 projection
host signer
  -> signed GovernanceDecision
RExecOp pre-I/O verifier + atomic claim + runtime permit
  -> connector I/O
RExecOp RuntimeReceiptBinding
  -> GovEngine ReceiptConformanceResult
SCLite
  -> final lifecycle/proof verification
```

Raw targets, secrets, commands and output remain outside the GovEngine
governance request. RExecOp provides bounded facts and opaque digests.

## Adversaries and failures considered

- malformed or adversarial callers and JSON inputs;
- stale, revoked or wrongly bound approvals;
- policy, scope, capability inventory, runtime, attempt, lease or fencing
  drift;
- replay of a previously allowed decision;
- request-supplied network allowlists or plugin-support claims;
- backend capabilities substituted for operation requirements;
- digest substitution and receipt overclaim;
- resource-exhaustion inputs within the public JSON/policy boundaries;
- explanation or reason-code leakage;
- TOCTOU between governance evaluation and connector I/O;
- buggy or malicious plugins within the host runtime.

## Threats and mitigations

| Threat | GovEngine/RExecOp mitigation | Residual risk |
| --- | --- | --- |
| Confused deputy / approval reuse | Approval binds operation, step, attempt, spec, facts, scope, policy epoch and side-effect class | Compromised trust/revocation adapter can lie |
| Typed mutation/recovery relabelling | The optional governed-admission projection cross-binds the complete unchanged typed v0.1 request, explicit actual mode, frozen v1 request/decision/approval, attempt, lease, spec, facts, payload, scope, inventory and policy | A host that skips the composite or signed-decision path remains outside the cooperating-host guarantee |
| Policy drift | Request and activation binding carry policy digest/epoch/issuer/validity | Compromised activation source can authorize a malicious pack |
| Target or destination substitution | Independent scope policy and requested-scope digest; request cannot carry allowlist fields | DNS resolution, redirect and socket enforcement remain RExecOp/plugin duties |
| Capability self-attestation | Operation requirements and independently sourced inventory are separate records | A compromised inventory attestor can lie |
| TOCTOU / stale executor | Decision authorization binds runtime, attempt, lease epoch and fencing digest and expires within 60 seconds | In-process runtime can bypass the check |
| Replay | RExecOp atomically claims decision digest and nonce before I/O | Production durability depends on the selected claim store |
| Digest substitution | GovEngine-owned complete records are recomputed and compared in constant-time where applicable | Opaque RExecOp/SCLite digests prove only the referenced owner computation |
| Receipt overclaim | Receipt binds decision, runtime permit, attempt, lease/fencing, scope, inventory, policy and postconditions | Compromised runtime can fabricate bounded facts |
| Secret/raw-data leakage | Bounded JSON walker, recursive forbidden keys, redacted explanations and digest-only output bindings | Host logs, adapters and exception handling remain host responsibilities |
| Resource exhaustion | Byte/depth/node/collection/string and policy rule/condition/control limits | Python process availability is not a hard multi-tenant isolation guarantee |
| Malicious plugin | Inventory binding and RExecOp trusted-plugin gate | GovEngine does not inspect plugin code or enforce network/syscall isolation |

## SSRF, DNS and redirect boundary

GovEngine checks bounded destination metadata against an independent scope
policy: scheme, effective port, address class, redirect posture and private
network allowance. It never receives or resolves the raw connector host.
RExecOp owns DNS resolution, rebinding defenses, redirect enforcement, socket
destination checks, proxy behavior and connector I/O.

## Security-sensitive invariants

- Unknown enums and fields fail closed on v1 governance records.
- Admission summaries and opaque refs are never approval.
- The governed typed-execution adapter discounts only the two deliberate
  typed-v0.1 mutation-approval blockers, and only after actual frozen-v1
  evaluation. Every other typed blocker remains fatal.
- `recovery` is bound explicitly by the composite and v1 execution facts; the
  unchanged nested typed-v0.1 `apply` value is only a mutating-posture alias.
- `TypedExecutionGovernedAdmission` is not authority. RExecOp must separately
  verify and atomically claim the signed `GovernanceDecision`.
- Only `GovernanceDecision.status=allowed` carries authorization.
- Authorization is short-lived, attempt/runtime/lease/fencing/inventory-bound
  and consume-once.
- RExecOp verifies the signed decision and atomically claims it before I/O.
- Receipt conformance is a postcondition and cannot authorize execution.
- SCLite remains the final lifecycle/proof authority.

## Validation evidence

- `scripts/validate_v1_freeze.py`
- `scripts/generate_conformance_corpus.py --check`
- `tests/test_security_properties.py`
- `tests/test_governance_decision.py`
- `tests/test_typed_execution_governed_admission.py`
- `tests/test_receipt_conformance.py`
- RExecOp `scripts/validate_governance_conformance.py`
- RExecOp `scripts/validate_g3_runtime_governance_gate.py`

Passing these checks is bounded implementation evidence, not a penetration
test, legal authorization, production certification or malicious-host proof.
