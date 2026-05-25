# GovEngine and SCLite Integration

GovEngine consumes [SCLite](https://github.com/rozmiarD/SCLite) as its contract lifecycle layer.

SCLite answers: **what artifacts prove the governed lifecycle?**
GovEngine answers: **how does a runtime prepare, check, and consume those artifacts safely?**

## Dependency

`pyproject.toml` depends on the published SCLite package distribution:

```toml
sclite-core>=0.8.0a0,<0.9
```

The PyPI distribution name is `sclite-core`; the Python import package remains `sclite`.

This keeps the dependency direction explicit:

```text
GovEngine -> SCLite
```

## Lifecycle relationship

SCLite models the lifecycle as schema-backed artifacts and review bundles:

```text
intent_contract
-> policy_decision
-> execution_contract
-> execution_ticket
-> execution_receipt
-> evidence_contract
-> artifact_chain_manifest
-> review_record / review bundle
```

GovEngine currently provides helpers around the runtime-facing parts of that lifecycle:

- action validation and compilation before contract shaping;
- policy decision normalization/evaluation;
- execution-contract shaping and redaction;
- approved-spec and execution-ticket checks;
- dry-run result assembly;
- integration seams for SCLite verification;
- guarded-root replay checks for optional SCLite `kernel_guard_hmac_v1`
  sidecars after SCLite has verified the HMAC guard;
- review-bundle verdict mapping through SCLite `0.8.0a0` review surfaces, preserving the review-bundle contract.

Host-owned artifact projection is outside GovEngine. A runtime such as
Ravenclaw constructs its domain-shaped lifecycle artifacts before consuming
neutral GovEngine gates and SCLite review/verification services.

## What GovEngine does not replace

GovEngine does not replace SCLite schemas, lifecycle verification, artifact
integrity checks, Kernel Guard HMAC verification, Scope Fidelity checks, or
review-bundle verdict semantics. Those stay in SCLite.

GovEngine's replay helper records observed guarded roots (`root_tag`,
`chain_id`, ticket/run id, and `key_id`) through a host-supplied state store so
a runtime can reject reuse in require-fresh mode. It does not store HMAC keys,
verify tags, or make public PKI claims.

GovEngine also does not execute live targets by itself. A host runtime such as Ravenclaw remains responsible for concrete execution adapters, artifact persistence, operator approval UX, and public snapshot/demo publishing.

## Why this split matters

The split keeps responsibilities reviewable:

- SCLite is the small auditable contract and integrity layer.
- GovEngine is the reusable governance service layer that consumes those contracts.
- Ravenclaw is the full reference runtime/control plane that wires the pieces into an operator workflow.

This avoids turning one repository into a mixed contract/runtime/UI/protocol bundle and makes each layer easier to validate independently.
