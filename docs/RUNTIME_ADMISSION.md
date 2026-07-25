# Runtime Admission Contract

> Legacy governed-runtime composition adapter outside `govengine.v1`. The
> canonical attempt path is `GovernanceRequest -> GovernanceDecision -> RExecOp
> claim/permit -> terminal runtime facts`. This document exists for consumers
> that still read `RuntimeAdmissionResult`.

`RuntimeAdmissionResult` is the legacy governed-runtime composition adapter.
It remains useful for inspect/review and existing ticket/guard workflows, but
it is not the canonical v1 authorization path. Controlled connector attempts
use `GovernanceRequest -> GovernanceDecision`, followed by RExecOp's signed
decision verification, atomic claim and runtime permit.

`GovernedExecutionAdmission` remains the legacy concept name used by existing
host documentation; it is not a second record or v1 authorization type.

This compatibility contract does not add execution authority by itself.

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
  as a compatibility helper by normalizing existing IDs, refs, paths, and digest
  strings; it does not compute content digests or redefine SCLite
  canonicalization.

## Output Shape

The implementation exposes a small immutable record with fields equivalent
to:

- `status`: `allowed`, `blocked`, `dry_run_only`, `needs_review`, or
  `record_only`.
- `allowed`: boolean, true only when all required gates pass.
- `reason_code`: deterministic machine-readable reason for the top-level
  decision.
- `blockers`: ordered blocker codes emitted by the current runtime composition
  path, including `missing_or_invalid_policy_decision`, `policy_denied`,
  `missing_or_invalid_execution_ticket`, `invalid_execution_ticket`,
  `missing_or_invalid_trust_decision`, `missing_prepared_execution_contract`,
  `missing_or_invalid_kernel_guard`, `missing_or_replayed_guarded_root`,
  `missing_runner_profile`, `runner_profile_not_allowed`,
  `live_backend_disabled`, and `receipt_obligation_required`.
  Runtime-consumable guard failures use top-level reason code
  `kernel_guard_required`; replay freshness failures use `replay_detected`.
- `required_next_actions`: ordered action codes such as `obtain_policy_decision`,
  `approve_execution_ticket`, `verify_trust_decision`,
  `verify_guarded_strict_bundle`, `record_guard_replay_freshness`,
  `select_allowed_runner_profile`, and `require_runner_receipt_obligation`.
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

`compose_runtime_admission_result()` is fail-closed and consumes host-supplied
gate summaries. It does not call SCLite verification, ticket-gate helpers, or
trust verifiers directly.

When `runtime_consumable=True`, guarded-strict and replay-freshness summaries
participate in the admission decision. When `runtime_consumable=False`,
guarded/replay failures do not block admission composition and review-only bundles
can remain distinct from runtime-consumable posture.

The result is fail-closed for missing or invalid host-supplied summaries:

- missing prepared execution contract blocks;
- missing policy blocks;
- missing or invalid policy blocks;
- denied, deferred, approval-required, dry-run-only, or record-only policy
  outcomes yield policy-specific blockers and usually keep `allowed=False`;
- missing or invalid execution ticket blocks runtime-consumable work;
- missing or invalid trust decision blocks when trust is required;
- runtime-consumable bundles require guarded-strict verification and replay
  freshness when `runtime_consumable=True`;
- missing or disallowed runner profile blocks;
- live runner profiles block when `live=True` unless the host explicitly enables
  `live_backend_enabled` on the profile;
- missing receipt obligation blocks admission composition;
- missing or disabled receipt obligation blocks admission composition with
  `receipt_obligation_required`.

`status` values such as `dry_run_only` or `needs_review` can coexist with
`allowed=False`. Only `status=allowed` with `allowed=True` means all required
composition gates passed.

Dry-run remains the default safe posture. A dry-run admission can be allowed only
when the required policy, ticket, trust, guarded/replay (if runtime-consumable),
runner-profile, and receipt-obligation rules for that dry-run profile are
satisfied.

After admission composition, hosts may call
`validate_runtime_admission_proof_inputs()` on an already-allowed record to
check that expected proof-input summaries and references are present. That helper
does not verify SCLite artifacts, signatures, or replay persistence. The
allowed proof-input path requires a guarded-strict root-chain digest, execution
ticket id, execution ticket digest or bounded ticket digest reference, and
receipt binding that includes both admission and ticket.

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

## Trigger Planning Admission

`govengine.triggers.TriggerPlanningRequest` is the bounded admission vocabulary
for trigger decisions that may create an operation plan. It is not a scheduler,
event bus, discovery engine, execution gate, or profile semantics layer.

The request carries only event/rule identifiers and digests, the trigger
decision, and the requested operation intent/mode when the decision is
`plan_operation`. It must not carry raw event payloads, private targets,
credentials, commands, stdout/stderr, URLs, or scheduler state.

`admit_trigger_planning()` returns the existing `GovAdmissionDecision` envelope:

- `plan_operation` is allowed only for `dry_run` or `read_only` operation modes
  with a bound rule digest and operation intent;
- `ignore`, `escalate`, `drop_duplicate`, and `cooldown_blocked` are
  `record_only` decisions and do not grant operation planning authority;
- validation is fail-closed for missing event/rule digests, unsupported
  decisions, mutation modes, raw metadata, or drift between request and
  admission.

RExecOp remains responsible for event intake, dedupe, cooldown and operation
planning mechanics. Profiles such as Tecrax remain responsible for domain event
meaning and rule packs. SCLite remains responsible for evidence and receipt
truth.

## Supervisor Action Admission

`govengine.supervisor_actions.SupervisorActionRequest` is the bounded admission
vocabulary for neutral runtime-supervisor decisions such as worker health
records, stale inbox dead-lettering, retry-later records and autostart blockers.
It is not a worker, queue, scheduler, recovery tool, monitoring system, runtime
store or SCLite artifact writer.

The request carries only watchdog record digests, neutral observation/action
names, bounded retry/stale-age limits, and affected operation/event/inbox
references. Signed manual-recovery requests also carry bounded `actor_ref` and
`scope` values. It must not carry raw event payloads, target topology,
credentials, commands, stdout/stderr, URLs, runtime storage paths or scheduler
state.

`admit_supervisor_action()` returns the existing `GovAdmissionDecision`
envelope:

- `record_health` is `record_only`;
- `move_to_dead_letter` and `retry_later` are allowed when bounded retry
  controls are satisfied;
- `block_autostart` is allowed only when the observed operation age meets or
  exceeds the declared stale-age threshold;
- `renew_lease`, `mark_stale`, and `escalate_operator` require explicit human
  sign-off in this alpha contract, and signed requests must include `actor_ref`
  plus `scope`;
- validation is fail-closed for missing watchdog digests, unsupported actions,
  unsafe metadata, missing affected references, limit violations or drift
  between request and admission.

RExecOp remains responsible for watchdog mechanics, watchdog decision records,
and worker/inbox/queue state. SCLite 2.0 does not define watchdog contracts; it
remains responsible for the final lifecycle and evidence truth artifacts.

### Supervisor Action Explanation

`explain_supervisor_action()` evaluates the same bounded
`SupervisorActionRequest` path as `admit_supervisor_action()` and returns
`SupervisorActionExplanation` schema `v0.1` with:

- `recovery_class` for retry, dead-letter, stale lease, block-autostart,
  manual-record and health-record paths;
- `gates_checked` for retry budget, stale age and human sign-off gates;
- `operator_summary`, `reason_code`, `blockers` and bounded
  `safe_next_actions`;
- digest-bound `request_digest` and `admission_digest`.

The CLI `govengine-supervisor explain request.json --json` is side-effect free
and does not execute recovery, mutate runtime state or verify SCLite artifacts.

## Relationship To Existing Modules

The implementation composes host-supplied summaries from existing surfaces
instead of replacing them:

- `govengine.admission` for policy/admission/approval/audit record shapes and
  runtime admission composition;
- `govengine.execution.gate` for prerequisite and guarded/replay blocker
  evaluation inside `compose_runtime_admission_result()`;
- `govengine.execution.ticket_gate` for host-side execution-ticket checks before
  summaries are composed;
- `govengine.signing` for signature/trust decisions, host verifier ports, and
  deterministic GovEngine-owned admission/receipt record digests and signed
  record envelopes;
- `govengine.replay` for guarded SCLite replay freshness summaries and
  `verify_guard_and_record_replay()`;
- `govengine.execution.runner_protocol` and `govengine.execution.supervision`
  for runner request, receipt, and `validate_runner_receipt_binding()`;
- `govengine.review` for receipt-bounded evidence/review reference checks through
  `validate_evidence_review_chain()`.

## Compatibility status

The package still ships the runtime-admission record, composer, bounded public
summaries, inspect-only command and read-only receipt/audit verifiers for
existing consumers. In-memory replay and JSONL audit helpers remain development
fixtures without production durability or concurrency guarantees.

This compatibility surface does not receive the `govengine.v1` stability
promise. It must remain side-effect free with respect to connector execution:
GovEngine does not ship `LocalSubprocessRunner`, and live backend support,
production replay/audit/evidence persistence and runtime recovery remain
RExecOp or host responsibilities. This surface must not claim production
runtime readiness.
