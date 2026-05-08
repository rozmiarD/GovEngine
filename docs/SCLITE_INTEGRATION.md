# GovEngine and SCLite Integration

GovEngine consumes [SCLite](https://github.com/rozmiarD/SCLite) as its contract lifecycle layer.

SCLite answers: **what artifacts prove the governed lifecycle?**
GovEngine answers: **how does a runtime prepare, check, and consume those artifacts safely?**

## Dependency

`pyproject.toml` pins SCLite as a git dependency:

```toml
sclite @ git+https://github.com/rozmiarD/SCLite.git@43dae49b44602da76611fb42cd0b10aac3b3ae3f
```

This keeps the dependency direction explicit:

```text
GovEngine -> SCLite
```

## Lifecycle relationship

SCLite v0.2 models the lifecycle as schema-backed artifacts:

```text
intent_contract
-> policy_decision
-> execution_contract
-> execution_ticket
-> execution_receipt
-> evidence_contract
-> artifact_chain_manifest
```

GovEngine currently provides helpers around the runtime-facing parts of that lifecycle:

- action validation and compilation before contract shaping;
- policy decision normalization/evaluation;
- execution-contract shaping and redaction;
- approved-spec and execution-ticket checks;
- dry-run result assembly;
- integration seams for SCLite verification.

## What GovEngine does not replace

GovEngine does not replace SCLite schemas, lifecycle verification, or artifact integrity checks. Those stay in SCLite.

GovEngine also does not execute live targets by itself. A host runtime such as Ravenclaw remains responsible for concrete execution adapters, artifact persistence, operator approval UX, and public snapshot/demo publishing.

## Why this split matters

The split keeps responsibilities reviewable:

- SCLite is the small auditable contract and integrity layer.
- GovEngine is the reusable governance service layer that consumes those contracts.
- Ravenclaw is the full reference runtime/control plane that wires the pieces into an operator workflow.

This avoids turning one repository into a mixed contract/runtime/UI/protocol bundle and makes each layer easier to validate independently.
