# Runtime Admission Contract

GovEngine's governed-runtime MVP needs one canonical admission decision before
any live runner work expands. The initial public record is
`RuntimeAdmissionResult`. `GovernedExecutionAdmission` remains an equivalent
concept name for hosts and roadmap discussion, not a second implementation
surface.

This contract is a design boundary. It does not add execution authority by
itself.

```text
Intent is not execution authority.
```

## Purpose

Runtime admission composes the gate evidence a host runtime must inspect before
it may submit a bounded dry-run or controlled runner request. It makes the
decision machine-readable, deterministic, reviewable, and suitable for later
receipt/evidence binding.

The record should answer:

- whether the request is allowed;
- why it is allowed or blocked;
- which input gate blocked it;
- which next action can unblock it;
- which bounded artifact references or digests were considered.

## Inputs

The admission result composes existing GovEngine and SCLite-facing signals:

- `prepared_execution_contract`: status, reference, and digest for the prepared
  execution shape.
- `policy_decision`: host-provided policy result. GovEngine validates the
  decision shape; the host owns policy meaning.
- `execution_ticket`: SCLite ticket status, ticket id, profile, and bound
  execution-contract digest when available.
- `trust_decision`: signature or verification result from host-provided
  signer/verifier ports. GovEngine does not own production identity or keys.
- `sclite_guarded_strict`: guarded-strict SCLite verification status when an
  artifact is runtime-consumable.
- `replay_freshness`: GovEngine replay decision for guarded SCLite roots.
- `runner_profile`: selected runner posture and whether the request is dry-run
  only, host-live, or blocked.
- `receipt_obligation`: whether a runner receipt is required and which request,
  ticket, and admission references it must bind.
- `artifact_refs`: bounded references or digests for inputs. Raw payloads,
  targets, credentials, and noisy logs stay outside the admission record.
  `normalize_admission_artifact_refs()` exposes those bounded review references
  as alpha API by normalizing existing IDs, refs, paths, and digest strings; it
  does not compute content digests or redefine SCLite canonicalization.

## Output Shape

The implementation exposes a small immutable record with fields equivalent
to:

- `status`: `allowed`, `blocked`, `dry_run_only`, `needs_review`, or
  `record_only`.
- `allowed`: boolean, true only when all required gates pass.
- `reason_code`: deterministic machine-readable reason for the top-level
  decision.
- `blockers`: ordered blocker codes such as `missing_policy_decision`,
  `execution_ticket_invalid`, `trust_decision_missing`,
  `guarded_strict_required`, `replay_not_fresh`,
  `runner_profile_missing`, or `receipt_required`.
- `required_next_actions`: ordered action codes such as `evaluate_policy`,
  `issue_execution_ticket`, `verify_trust`, `verify_sclite_guarded_strict`,
  `claim_replay_freshness`, `select_runner_profile`, or
  `bind_runner_receipt`.
- `inputs`: bounded summaries of each input gate.
- `artifact_refs`: bounded paths, ids, or digests. This should never carry raw
  prompts, credentials, live command output, private target data, or raw
  evidence.

`allowed=True` must imply that `status` is `allowed`. A blocked or review-only
status must include at least one blocker or required next action.

The receipt/admission/ticket binding design is documented in
[RECEIPT_BINDING.md](RECEIPT_BINDING.md). The binding design describes
`admission_id`, `admission_digest`, `ticket_id`, `ticket_digest`, `request_id`,
`receipt_id`, status, output digests, evidence refs, and compatibility with the
existing dry-run `GovRunnerReceipt` shape. It is a review contract, not an
execution grant.

The inspect-only operator workflow is documented in
[INSPECT_ONLY_ADMISSION_WORKFLOW.md](INSPECT_ONLY_ADMISSION_WORKFLOW.md). It
validates and summarizes `RuntimeAdmissionResult` records through
`scripts/inspect_runtime_admission.py` without creating runner requests,
receipts, replay claims, audit entries, or live execution authority.

## Gate Semantics

The result is fail-closed:

- missing policy blocks;
- denied, unknown, deferred, or approval-required policy blocks unless the
  status is explicitly `needs_review` or `dry_run_only`;
- missing or invalid execution ticket blocks runtime-consumable work;
- missing or failed trust decision blocks when trust is required;
- runtime-consumable SCLite artifacts require guarded-strict verification;
- replayed or stale guarded roots block require-fresh runtime admission;
- missing runner profile blocks;
- live runner profiles block unless a future host profile explicitly enables
  them after runner safety prerequisites exist;
- missing receipt obligation blocks controlled runner requests.

Dry-run remains the default safe posture. A dry-run admission can be allowed only
when the required policy, ticket, trust, guarded/replay, runner-profile, and
receipt-obligation rules for that dry-run profile are satisfied.

## Boundary Rules

SCLite owns schemas, canonicalization, artifact-chain verification, guarded
verification, ticket semantics, and review-bundle authority. GovEngine consumes
SCLite verdicts and records bounded runtime decisions. GovEngine must not
duplicate SCLite canonicalization or review-bundle authority.

Hosts own profile/domain policy meaning, legal authorization, operator approval
workflow, production identity, production key storage, PKI/KMS/CA integration,
trust anchors, raw evidence storage, redaction pipelines, live execution
backends, sandboxing, and runtime persistence.

GovEngine owns only the neutral admission composition mechanics, validation
shape, reason codes, blockers, next actions, bounded references, and future
ports needed by host runtimes.

## Relationship To Existing Modules

The implementation composes the existing surfaces instead of replacing
them:

- `govengine.admission` for policy/admission/approval/audit record shapes;
- `govengine.execution.ticket_gate` for execution-ticket checks;
- `govengine.signing` for signature/trust decisions, host verifier ports, and
  deterministic GovEngine-owned admission/receipt record digests and signed
  record envelopes;
- `govengine.signing` key-resolver and trust-store ports for host-owned signer
  key references and trust-anchor decisions;
- `govengine.replay` for guarded SCLite replay freshness;
- `govengine.execution.runner_protocol` and `govengine.execution.supervision`
  for runner request, receipt, and profile boundaries;
- `govengine.review` for later receipt/evidence review binding.

## Implementation Status And Next Tasks

Delivered on current `main` (CHANGELOG `Unreleased` until the next PyPI alpha):

1. `RuntimeAdmissionResult` exists as the core record;
2. `validate_runtime_admission_result()` enforces basic status/allowed/blocker
   consistency;
3. `compose_runtime_admission_result()` composes bounded gate summaries into the
   record;
4. `normalize_admission_artifact_refs()` is exposed as an alpha bounded-reference
   helper for admission review output;
5. `canonical_govengine_record()` and `govengine_record_digest()` provide a
   GovEngine-owned record serialization/digest boundary for admission/receipt
   binding without canonicalizing SCLite artifacts;
6. `SignedArtifact` binds a GovEngine-owned record digest to signer metadata
   and a payload reference while leaving production verification to
   host-provided verifier ports;
7. key-resolver and trust-store port records carry references and decisions
   only, not private key material, credentials, KMS, CA, or trust-anchor
   storage;
8. `validate_runner_receipt_binding()` and `validate_evidence_review_chain()`
   validate bounded receipt and evidence/review reference chains;
9. `AuditLedgerPort` and `JsonlAuditLedgerAdapter` provide a development-only
   hash-chained audit append/read/verify surface;
10. `ReplayClaimStore`, `InMemoryReplayClaimStore`, and
    `verify_guard_and_record_replay()` provide replay claim-once and
    guarded-strict composition helpers;
11. `scripts/inspect_runtime_admission.py` implements the inspect-only operator
    workflow;
12. focused negative tests cover missing policy, ticket, trust, replay,
    runner-profile, and receipt-obligation blockers in admission composition.

Remaining work:

1. publish the governed-runtime MVP as the next alpha PyPI line when operator
   release gates pass;
2. keep live backend support disabled by default;
3. keep production replay, audit, and evidence persistence host-owned beyond the
   development adapters;
4. keep optional `LocalSubprocessRunner` out of the kernel until host-owned live
   profile authorization and safety gates are implemented and tested.

The result is usable by hosts for receipt, audit-ledger, replay-store,
inspect-only, and dry-run runner workflows, but it must not claim production
runtime readiness.
