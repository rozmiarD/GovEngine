# GovEngine Roadmap

GovEngine is evolving from a Ravenclaw-extracted helper package into a deterministic governed-runtime kernel. It consumes SCLite for lifecycle/proof artifacts and exposes host/profile-facing mechanisms for planning, admission, audit, approval, runner gating, supervision, and evidence review.

Current package baseline: `govengine==0.16.2` (`0.16.2`), depending on `sclite-core>=1.0.5,<1.1`.
Published PyPI baseline is `govengine==0.16.2`.

## Architecture thesis

```text
LLM intent is not execution authority.
```

GovEngine exists to keep intent, permission, execution, receipt, and review as separate runtime states. A model, agent, UI, or carrier may propose an action, but execution must pass through deterministic governance boundaries:

```text
intent
  -> policy decision
  -> execution contract
  -> execution ticket
  -> trust decision
  -> runner gate
  -> execution or dry-run
  -> receipt
  -> evidence contract
  -> review bundle
```

SCLite owns the contract/proof/review artifact layer. GovEngine owns the runtime mechanics that consume those artifacts. Domain runtimes such as Ravenclaw and Tecrax own domain semantics, UX, tools, and operator workflows.

## Responsibility boundary

GovEngine owns reusable mechanics:

- event/state/control envelopes;
- reason-code and transition-decision registries;
- task and planning contracts;
- audit, policy, admission, approval, and ticket-control boundaries;
- trust/signer/verifier ports without PKI or key-store ownership;
- runner request/receipt/gate/supervisor contracts;
- OODA-style pause/abort/cooldown/replan decisions;
- deconfliction and common operational picture summaries;
- evidence qualification and review-controller contracts;
- domain-profile SDK and conformance tests.

GovEngine does **not** own:

- SCLite schemas, canonicalization, chain verification, or review-bundle CLI;
- Ravenclaw campaign semantics, finding taxonomy, Logdash, or security toolchains;
- Tecrax infrastructure UX, service inventories, change-management policy, or host credentials;
- OpenClaw/MCP/A2A carrier adapters as core;
- live subprocess execution by default;
- PKI, CA, KMS, trust-store, or key storage;
- legal authorization, organizational approval, or operator accountability.

Rule of thumb:

```text
GovEngine owns governance, PolicyEngine, admission, obligations and constraints.
Profiles own meaning.
Runtimes own lifecycle, execution and integration mechanics.
SCLite owns proof/review artifacts.
```

## Current 0.16.x release line

The current published `0.16.x` line adds digest-bound policy enforcement plans on
top of the PolicyEngine MVP published in `0.15.0`:

- deterministic pack, verdict, plan and admission digests;
- `PolicyEnforcementPlan` bound to the existing `GovAdmissionDecision`;
- neutral projections for receipt, output digest, output limit, timeout and
  maximum-step controls;
- fail-closed malformed or unsupported controls;
- docs in `docs/POLICY_ENGINE.md` and tests in `tests/test_policy_enforcement.py`.

Status: implementation, tests and PyPI publication are complete for `0.16.2`.

The line retains the neutral kernel shape from `0.14.x`, keeps
Ravenclaw-derived runtime behavior host-owned, and keeps the former optional
security facade retired:

- artifact-governance and SCLite lifecycle/review bridge helpers;
- kernel/profile/runtime/SCLite boundary reports and conformance checks;
- neutral runtime-shell, planning, admission/policy, controlled-execution, runner-supervision, and evidence-review contracts;
- contract-only domain profile SDK declarations and Ravenclaw/Tecrax conformance fixtures;
- runtime contract proof fixtures showing Ravenclaw and Tecrax over the same neutral GovEngine/SCLite contract flow;
- dry-run/default-deny execution posture with no default live subprocess backend;
- public surface registry limited to neutral core, contract-only domain profile SDK, and proof surfaces;
- public truth validation for version/dependency/status/API-boundary drift.
- package-build, clean wheel-install, and Ravenclaw public downstream compatibility checks for the alpha release line.
- explicit host ownership of Ravenclaw lifecycle projection after removal of
  `govengine.sclite_adapter` from the neutral package surface.

This is alpha, not stable. The next roadmap should not be a file move from Ravenclaw into GovEngine. It should remain contract-first extraction: define neutral contracts, add GovEngine tests, add host compatibility wrappers, then thin host code only after behavior is preserved.

The active alpha hygiene gate requires neutral public surfaces to stay free of
Ravenclaw host context and domain security helper imports. The former
`security_profile_helpers` compatibility surface is removed in this line;
profile-owned tool, policy, and UX semantics remain in Ravenclaw. New neutral
extraction should land in typed core/profile surfaces only when the code and a
second host prove it there.

## Post-0.12.3 governed-runtime MVP

Status: published in `0.14.0` and retained as the current governed-runtime MVP baseline.

GovEngine already had useful pieces across policy, execution tickets, signing/trust,
guarded SCLite replay, runner requests/receipts, and dry-run gates. The public
kernel now exposes one bounded machine-readable decision that composes those
pieces without turning intent into execution authority.

Delivered MVP surface:

- `RuntimeAdmissionResult`, `compose_runtime_admission_result()`,
  `validate_runtime_admission_result()`, and `normalize_admission_artifact_refs()`;
- `ReplayClaimStore`, `InMemoryReplayClaimStore`, and
  `verify_guard_and_record_replay()`;
- `validate_runner_receipt_binding()` and `validate_evidence_review_chain()`;
- GovEngine-owned record digests and signed-record helpers;
- `AuditLedgerPort` and development-only `JsonlAuditLedgerAdapter`;
- `LocalSubprocessRunnerReadiness` with `not_applicable` as the current local
  runner posture;
- `scripts/inspect_runtime_admission.py` and operator docs under
  `docs/GOVERNED_RUNTIME_MVP_RUNBOOK.md`,
  `docs/INSPECT_ONLY_ADMISSION_WORKFLOW.md`, and
  `docs/GUARDED_FRESH_RUNTIME_ADMISSION_EXAMPLE.md`;
- focused negative tests for admission composition, replay claim-once behavior,
  receipt/evidence binding, audit tamper cases, inspect-only workflow, and
  governed-runtime smoke coverage.

The MVP contract is named `RuntimeAdmissionResult`; `GovernedExecutionAdmission`
remains an equivalent concept name for hosts and roadmap discussion. It reports:

- status and `allowed`;
- deterministic reason code;
- blockers and required next actions;
- prepared execution contract status;
- policy decision status;
- execution ticket status and reference or digest;
- trust decision status;
- guarded-strict SCLite verification status when the artifact is
  runtime-consumable;
- GovEngine replay freshness;
- runner profile;
- receipt obligation;
- bounded artifact references or digests.

This admission result is not a live execution backend. It is the reviewable
decision surface that trust, receipt, ledger, replay-store, inspect-only, and
optional runner work must use. Live subprocess execution remains disabled by
default and out of scope until a future host adapter satisfies the runner safety
requirements and negative tests for any optional live backend.

Remaining follow-up for the next release line:

- keep released consumer dependency floors aligned with the published `0.16.2`
  enforcement-plan API;
- keep production replay, audit, and evidence persistence host-owned;
- keep optional `LocalSubprocessRunner` out of the kernel while readiness stays
  `not_applicable`.

Delivered version milestones (`0.2.x` through `0.11.x`) are archived in
[archive/ROADMAP_VERSION_HISTORY.md](archive/ROADMAP_VERSION_HISTORY.md).
Release facts belong in [CHANGELOG.md](../CHANGELOG.md).

## Domain profiles

### Ravenclaw Security Research Profile

Ravenclaw supplies security meaning:

- resource types: `host`, `url`, `endpoint`, `web_app`;
- task families: `recon`, `authz`, `idor`, `workflow`, `content_discovery`, `tls_assessment`;
- planning stages: `discovery`, `validation`, `control_boundary_confirmation`, `state_transition_confirmation`, `bounded_exploit_proof`, `report_artifact_capture`;
- security-specific audit checklists, policy rules, tools, and evidence rules.

In GovEngine 0.8 this profile is represented as a conformance fixture
and declaration shape only. Ravenclaw remains the authority for security finding
taxonomy, tool semantics, disclosure workflow, and Logdash/campaign UX.

### Tecrax Infrastructure Operations Profile

Tecrax is the reserved name for the future governed infrastructure-operations runtime/profile. Avoid inherited working-name/product framing until public language is deliberately chosen.

Tecrax should supply infrastructure meaning:

- resource types: `server`, `service`, `container`, `firewall`, `switch`, `vm`, `backup_job`;
- task families: `inspect`, `diagnose`, `propose_change`, `dry_run_change`, `verify_fixture`, `rollback_plan`;
- planning stages: `observe`, `diagnose`, `plan_change`, `validate_dry_run`, `approval_required`, `verify_fixture`, `rollback_plan_ready`.

Operational Tecrax read-only slices now run through RExecOp; the GovEngine copy
remains only a synthetic conformance fixture. Tecrax must not bring service
inventories, host credentials, domain thresholds, live infrastructure control,
or product UX into GovEngine core.

## Carrier adapters

Carrier adapters remain deferred. OpenClaw should be evaluated first because it is the natural operator/carrier environment. MCP should come later. A2A should stay last and example-first.

Correct model:

```text
carrier or harness proposes
  -> domain runtime maps to workflow/profile semantics
  -> GovEngine gates and supervises
  -> SCLite artifacts bind lifecycle and review
  -> operator approves where required
  -> runner performs bounded step or dry-run
  -> receipt/evidence returns to carrier
```

Incorrect model:

```text
agent says execute -> runner executes
```

## Refactor rule

Do not move files mechanically from Ravenclaw into GovEngine. For each extraction:

1. identify the reusable concept;
2. name it neutrally;
3. define the GovEngine contract;
4. add GovEngine tests;
5. add Ravenclaw compatibility wrappers/adapters;
6. route Ravenclaw seam tests through the new contract;
7. remove or thin old code only after parity is proven.

## Research documentation backlog

Later, after the boundaries are implemented enough to support claims, add:

- `docs/RESEARCH_THESIS.md`;
- `docs/RESEARCH_EVALUATION_MATRIX.md`;
- `docs/BASELINE_COMPARISON.md`;
- `examples/research-scenarios/`.

Candidate scenarios:

- raw intent rejected;
- ticket digest drift rejected;
- policy changed after ticket;
- receipt overclaim rejected;
- evidence overclaim rejected;
- signature digest mismatch rejected;
- OODA scope drift abort;
- live runner disabled by default;
- common operational picture shows blocked state.
