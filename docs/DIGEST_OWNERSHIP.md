# Digest ownership

GovEngine treats a digest according to the payload available at the boundary,
not according to the caller's label. The machine-readable inventory is
`govengine._digest_ownership.DIGEST_OWNERSHIP_INVENTORY`; CI validates it through
`scripts/validate_digest_ownership.py` and the release-readiness gate.

| Mode | GovEngine behavior |
| --- | --- |
| `recomputed` | A full GovEngine-owned payload is present. GovEngine recomputes its digest and compares it in constant time. A caller-supplied digest never overrides the computed value. |
| `delegated` | The payload is owned by SCLite, RExecOp, a signer, or another host boundary. GovEngine consumes the verifier result or compares an opaque digest reference; it does not reproduce the owner's canonicalization. |
| `reference_only` | Only a bounded digest reference crosses the boundary. GovEngine validates shape and binding consistency, but cannot claim payload verification. |
| `produced` | GovEngine creates the digest from a GovEngine-owned output body. |

The audited families include typed-execution descriptors and network policy,
runner request/receipt/admission records, signed GovEngine records, audit
records and ledger entries, policy enforcement and governance trace inputs,
canonical governance-request policy/facts/scope/approval bindings, independent
scope-policy and operation-requirement/runtime-inventory bindings,
canonical governance decisions and embedded attempt-bound authorizations,
the optional typed governed-admission cross-binding projection,
SCLite ticket/replay references, RExecOp execution/output references,
trigger/automation references, and GovEngine-produced projection/report/bundle
digests.

## Fail-closed recomputation points

- `validate_typed_execution_governance_request()` recomputes the full
  `RuntimeCapabilityDescriptor` and network-policy projection.
- `validate_runner_receipt_binding()` recomputes full runner requests,
  receipts, and optional runtime admissions. Explicit digest arguments are
  checked claims, not expected-value overrides.
- `validate_audit_ledger_entry()` recomputes the embedded `GovAuditRecord` and,
  when present, the ledger entry digest.
- `verify_signed_govengine_record()` recomputes the record before calling the
  host verifier.
- `project_governance_trace()` recomputes embedded enforcement-plan and
  admission bindings.
- `validate_governance_request()` recomputes the full compiled policy pack,
  bounded execution facts, requested scope, independent scope policy,
  operation capability requirements, runtime inventory and optional approval
  attestation.
- `validate_approval_attestation()` recomputes the request subject and checks
  every approval binding before consulting trust and revocation policy.
- `GovernanceDecision.from_mapping()` recomputes the complete decision body;
  the supplied decision digest cannot replace the computed value.
- `TypedExecutionGovernedAdmission.from_mapping()` recomputes the complete
  composite body. `validate_typed_execution_governed_admission()` additionally
  recomputes the unchanged typed request/projection/bundle and frozen v1
  request/decision/approval bindings against the owner records.

Execution-spec, raw-payload and fencing-token bytes remain RExecOp-owned opaque
references. SCLite tickets and guarded replay roots remain delegated. This repository does
not add SCLite schemas, canonicalizers, or verification behavior.

## Error contract

`GovApiError.reason_code` is a stable, bounded identifier. Dynamic values such
as an unknown enum member or JSONL line number are stored in bounded
`context`, never appended to the machine-readable reason code. `str(error)`
retains the compact `reason_code:detail` diagnostic form for compatibility,
while `as_dict()` emits the separated structure.
