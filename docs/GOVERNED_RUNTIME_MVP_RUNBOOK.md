# Governed-Runtime MVP Operator Runbook

GovEngine's governed-runtime MVP is a small, host-neutral admission and
verification chain. It helps a host runtime decide whether a prepared request is
eligible for a dry-run or controlled runner request. It is not a platform,
agent loop, live runner, or credential store. **Policy evaluation** is provided
by `govengine.policy` (PolicyEngine MVP); SCLite remains the truth layer.

Core invariant:

```text
Intent is not execution authority.
```

## Runtime Chain

The operator-facing chain is:

```text
intent
  -> prepared execution contract
  -> PolicyEngine verdict (optional declarative pack) -> GovPolicyDecision summary
  -> SCLite execution ticket
  -> trust decision
  -> guarded-strict SCLite verification when runtime-consumable
  -> GovEngine replay freshness
  -> runner profile
  -> receipt obligation
  -> RuntimeAdmissionResult
  -> GovRunnerRequest
  -> GovRunnerReceipt
  -> validate_runner_receipt_binding()
  -> validate_evidence_review_chain()
  -> bounded evidence/review references
```

`compose_runtime_admission_result()` composes host-supplied gate summaries; it
does not verify SCLite tickets, record replay state, or execute work. For
runtime-consumable guarded/replay blockers, pass `runtime_consumable=True`.

`RuntimeAdmissionResult` is the canonical machine-readable decision. It carries
status, `allowed`, reason code, blockers, required next actions, gate inputs,
and bounded artifact references. A result can describe eligibility; it does not
execute anything by itself.

## Operator Steps

1. Start from a host-owned intent and domain policy context.
2. Prepare an execution contract or approved spec shape. Raw intent is never
   direct execution authority.
3. Evaluate policy in the host. GovEngine validates the result shape, not the
   domain meaning.
4. Bind a SCLite execution ticket or ticket reference. SCLite owns ticket
   schema, lifecycle proof, guarded verification, artifact-chain verification,
   canonicalization, and review-bundle authority.
5. Evaluate trust through host-provided signer/verifier, key-resolver, and
   trust-store ports. GovEngine keeps only bounded signer/key/trust decisions
   and GovEngine-owned record digests.
6. For runtime-consumable artifacts, require guarded-strict SCLite verification
   and a fresh GovEngine replay decision.
7. Select a runner profile. Dry-run remains the default. Live profiles stay
   blocked unless a future host adapter satisfies the runner safety checklist.
8. Require a receipt obligation that binds admission, ticket, request, receipt,
   status, and bounded output/evidence references.
9. Compose or inspect `RuntimeAdmissionResult`. For allowed admissions, optionally
    call `validate_runtime_admission_proof_inputs()` to confirm expected
    proof-input summaries are present.
10. If the result is blocked, follow `required_next_actions` instead of trying
    to execute.
11. If the result is allowed for dry-run, create a bounded runner request and
    require a receipt.
12. Validate receipt binding with `validate_runner_receipt_binding()` and qualify
    evidence/review references with `validate_evidence_review_chain()` without
    storing raw evidence in GovEngine.

## Inspect-Only Workflow

Use the inspect-only workflow for operator review of an existing admission
record. The workflow validates and summarizes `RuntimeAdmissionResult` records
without creating runner requests, receipts, replay claims, audit entries,
target contact, subprocesses, or live execution authority.

The contract is documented in
[INSPECT_ONLY_ADMISSION_WORKFLOW.md](INSPECT_ONLY_ADMISSION_WORKFLOW.md).

Operator verifiers:

- `scripts/inspect_runtime_admission.py` — inspect admission records;
- `scripts/verify_runner_receipt_binding.py` — verify admission/ticket/request/
  receipt binding references;
- `scripts/verify_audit_ledger.py` — verify development JSONL audit chains.

## Audit and Replay

GovEngine exposes neutral audit/replay ports:

- `AuditLedgerPort` and `JsonlAuditLedgerAdapter` provide local append/read/
  verify smoke evidence only. Production storage, locking, retention,
  deletion, reconstruction, and concurrency remain host-owned.
- `ReplayClaimStore` expresses claim-once freshness. The in-memory adapter and
  file helper are development aids, not production atomic persistence.

## Runner Safety

GovEngine-owned runner behavior remains dry-run/default-safe. Before any future
live local runner can exist, the host adapter must satisfy the checklist in
[RUNNER_SUPERVISION.md](RUNNER_SUPERVISION.md): argv-only command shape, no
shell by default, cwd and env allowlists, required timeout, bounded output,
output digests, redaction policy, explicit live enablement, and receipt for
every attempted step.

## Non-Claims

GovEngine does not own:

- production policy meaning;
- operator approval workflow;
- live execution backend behavior;
- raw evidence storage;
- SCLite schemas, canonicalization, guarded verification, artifact-chain
  verification, ticket semantics, or review-bundle authority;
- PKI, CA, KMS, production key storage, trust anchors, rotation, revocation, or
  credential handling;
- Ravenclaw/Tecrax product UX, carrier adapters, scheduler loops, campaign
  semantics, OpenClaw, MCP, A2A, or LLM provider integrations.

## Validation

For docs/operator changes, run:

```bash
python scripts/validate_public_truth.py
python scripts/validate_alpha_readiness.py
python -m pytest tests/ -q
ruff check .
git diff --check
```

For package-readiness evidence, use the clean-install validator documented in
[VALIDATION.md](VALIDATION.md). Do not publish packages, create tags, or claim
production readiness from local validation alone.
