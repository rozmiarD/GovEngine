# OODA Receipt and Evidence Notes

GovEngine's OODA controller is a safety/control contract, not a raw telemetry publication channel.

This note defines how OODA decisions should be carried into receipts and evidence surfaces without leaking raw output.

## What may be recorded

A host runner may record a compact OODA decision record in its runner receipt or downstream execution receipt:

```json
{
  "decision": "pause",
  "reason_code": "operator_pause_requested",
  "interrupting": true,
  "step_index": 1,
  "observation_kinds": ["before_step"],
  "orientation_summary": {
    "scope_ok": true,
    "policy_ok": true,
    "ticket_ok": true,
    "spec_ok": true,
    "host_health": "ok",
    "output_shape": "expected",
    "operator_control": "pause",
    "budget_state": "ok"
  }
}
```

Allowed fields are intentionally summary-level:

- decision and reason code;
- whether the decision interrupted execution;
- step index or bounded step identifier;
- observation kinds, severity, and safe subject labels;
- orientation booleans/enums such as scope, policy, ticket, spec, host-health, output-shape, operator-control, and budget state;
- cooldown subject only when already public-safe, otherwise a redacted/hashed host label;
- links to approved specs, tickets, execution contracts, and receipt/evidence artifacts by descriptor/path.

## What must not be recorded

OODA receipt/evidence surfaces must not include:

- raw stdout/stderr;
- raw command logs;
- request/response bodies;
- credentials, cookies, bearer tokens, or private headers;
- private filesystem paths;
- unredacted private/live target identifiers;
- full host telemetry dumps;
- LLM private reasoning or prompts.

## Receipt behavior

A runner receipt should append OODA decisions to a bounded `control_decisions` list or equivalent field.

If a decision is interrupting (`pause`, `abort`, `cooldown`, `degrade_to_dry_run`, `require_owner_review`), the host runner should stop scheduling the next step and set the receipt status/reason from the OODA decision.

If a decision is non-interrupting (`continue`, `replan_after_step`), the host runner may continue or re-enter planning according to host policy while preserving the compact decision record.

## Verification chain

OODA decision summaries are reviewable only after the governed receipt chain is
bounded. A host should verify this order before treating control decisions as
runtime evidence:

```text
RuntimeAdmissionResult
  -> GovRunnerRequest
  -> GovRunnerReceipt
  -> GovEvidenceClaim
  -> GovReviewResult
```

`validate_runner_receipt_binding()` verifies the admission, ticket, request,
receipt, and digest references on the receipt boundary. After that,
`validate_evidence_review_chain()` verifies that the evidence claim references
the expected receipt, matches the admitted subject or admission digest, stays
within receipt status bounds, and, when present, links the review result to the
computed evidence qualification.

This chain is reference validation only. It does not store raw evidence, does
not evaluate SCLite review-bundle verdicts, and does not make an OODA decision
or receipt into execution authority.

## Evidence behavior

Evidence artifacts should treat OODA decisions as governance evidence, not vulnerability evidence.

A valid evidence summary may claim:

- OODA control decisions were evaluated before or between runner steps;
- an interrupting decision stopped or reshaped execution;
- the decision was linked to the approved execution shape and receipt.

It must not claim:

- live vulnerability evidence;
- successful exploitation;
- authorization to continue beyond approved bounds;
- that raw telemetry is safe to publish.

## Host responsibilities

GovEngine provides deterministic decision objects and runner receipt shapes. The host runtime remains responsible for:

- redacting or hashing private subjects before publication;
- deciding where compact control decisions are persisted;
- preventing raw output from crossing into public artifacts;
- honoring interrupting decisions before scheduling the next step;
- linking decisions into SCLite/Ravenclaw lifecycle receipts when available.

## Current Ravenclaw gate

Ravenclaw has a host-runner seam test proving that `pause`, `abort`, and `cooldown` decisions are honored between approved-spec runner steps without moving live subprocess ownership into GovEngine:

- `engine/tests/test_govengine_ooda_adapter.py`

The remaining integration work is to wire compact OODA decision summaries into real runtime receipt/evidence builders, preserving the public-safety rules above.
