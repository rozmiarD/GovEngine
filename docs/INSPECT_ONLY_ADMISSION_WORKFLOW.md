# Inspect-Only Admission Workflow

This document defines the operator-facing inspect workflow for
`RuntimeAdmissionResult` records. It is a design contract for GE-034 and does
not implement execution.

The workflow exists so an operator or host runtime can inspect a canonical
runtime-admission record before any runner request is considered.

```text
Intent is not execution authority.
```

## Goal

The inspect-only workflow reads one GovEngine-owned runtime admission record,
validates it with `validate_runtime_admission_result()`, and prints a compact,
deterministic decision summary.

It must answer:

- admission id;
- status;
- allowed flag;
- reason code;
- blockers;
- required next actions;
- bounded artifact references or digests;
- whether a receipt obligation is present.

It must not execute live work, contact targets, open raw evidence, resolve
credentials, call a runner backend, mutate SCLite artifacts, claim replay keys,
or store audit entries.

## Proposed Operator Shape

GE-035 should implement this as a small inspect-only script or CLI surface. The
preferred initial command shape is:

```bash
python scripts/inspect_runtime_admission.py path/to/runtime-admission.json
```

The command should be read-only and should exit non-zero only when the input
record is malformed or unsafe to summarize.

Optional future flags may be added only if they remain inspect-only:

- `--format text` for compact human output;
- `--format json` for bounded machine-readable output;
- `--show-artifact-refs` to include already-bounded references and digests.

No future flag may grant execution authority.

## Output Contract

Text output should be stable enough for operators and tests:

```text
Runtime admission: runtime-admission-1
status: blocked
allowed: false
reason_code: missing_or_invalid_policy_decision
blockers:
- missing_or_invalid_policy_decision
required_next_actions:
- obtain_policy_decision
receipt_obligation: required
artifact_refs: 2 bounded refs
execution: not performed
```

JSON output, if implemented, should contain the same bounded fields and should
omit raw payloads, credentials, prompts, stdout, stderr, commands, targets, and
raw evidence. It should never include environment variables or secret material.

## Validation Rules

The inspect workflow must:

1. parse a single JSON mapping;
2. call `RuntimeAdmissionResult.from_mapping()` or
   `validate_runtime_admission_result()`;
3. rely on the admission validator to reject forbidden raw fields;
4. preserve ordered blockers and required next actions;
5. report missing or disabled receipt obligation as a blocker, not as an
   implicit approval;
6. treat `allowed=True` as informational only, not as execution permission;
7. state explicitly that no execution was performed.

The workflow must fail closed when input is malformed, missing the admission id,
missing subject reference, carries inconsistent `status` and `allowed`, or
contains forbidden raw runtime data.

## Boundary Rules

GovEngine owns this inspect surface only as a neutral admission-record reviewer.

GovEngine does not own:

- host policy meaning;
- operator approval workflow;
- production keys, PKI, CA, KMS, or trust anchors;
- SCLite schema, canonicalization, ticket authority, guarded verification, or
  review-bundle authority;
- raw evidence storage;
- target access;
- live runner backend behavior.

SCLite remains the authority for SCLite ticket and guarded-proof semantics.
Hosts remain the authority for domain policy, identity, storage, and live
execution enablement.

## Non-Goals

- no live subprocess runner;
- no runner request creation;
- no receipt creation;
- no replay claim mutation;
- no audit ledger append;
- no SCLite artifact rewriting;
- no raw evidence loading;
- no Ravenclaw, OpenClaw, MCP, A2A, scheduler, carrier, or credential adapter.

## GE-035 Implementation Acceptance

The implementation task should add tests proving:

- an allowed dry-run admission prints compact allowed output;
- a blocked admission prints blockers and required next actions;
- malformed input fails closed;
- forbidden raw fields fail closed through the existing validator;
- output states that execution was not performed;
- no live backend is imported or invoked.

## Implementation Status

The initial inspect-only surface is implemented as:

```bash
python scripts/inspect_runtime_admission.py path/to/runtime-admission.json
```

The script validates a single JSON `RuntimeAdmissionResult`, emits compact text
by default, supports bounded JSON output, exits with code 2 for malformed or
unsafe inputs, and always reports `execution: not performed`.
