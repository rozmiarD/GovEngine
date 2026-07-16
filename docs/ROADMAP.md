# GovEngine Roadmap

GovEngine is evolving from a Ravenclaw-extracted helper package into a deterministic governed-runtime kernel. It consumes SCLite for lifecycle/proof artifacts and exposes host/profile-facing mechanisms for planning, admission, audit, approval, runner gating, supervision, and evidence review.

Current package baseline: `govengine==1.0.0rc1` (`1.0.0rc1`), depending on
final frozen `sclite-core==2.0.0`.
Published PyPI baseline is `govengine==0.16.11`. Older alpha packages are archived only.

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

SCLite owns the contract/proof/review artifact layer. GovEngine owns
deterministic policy, governance, admission and receipt-conformance decisions.
RExecOp owns runtime lifecycle, scheduling, retries, connector dispatch and
I/O. Domain profiles such as Tecrax own semantics, UX, tools and operator
workflows.

## Responsibility boundary

The stable GovEngine v1 facade owns:

- typed policy compilation and deterministic evaluation;
- canonical governance requests and decisions;
- approval, target-scope and capability compatibility validation;
- short-lived attempt-bound authorization contracts;
- obligations, stable reason codes and redacted explanations;
- runtime receipt conformance against the decision;
- structural host ports for trust, revocation, activation and claim-once
  semantics without implementing their storage.

Legacy planning, runtime-shell, lifecycle, OODA and supervision records remain
classified compatibility/experimental surfaces. Their presence does not make
GovEngine the owner of those runtime mechanisms.

GovEngine does **not** own:

- SCLite schemas, canonicalization, chain verification, or review-bundle CLI;
- Ravenclaw campaign semantics, finding taxonomy, Logdash, or security toolchains;
- Tecrax infrastructure UX, service inventories, change-management policy, or host credentials;
- OpenClaw/MCP/A2A carrier adapters as core;
- operation lifecycle, queues, scheduler integration, retries or rollback;
- leases, fencing, runtime permit production or connector dispatch;
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

## Current 1.0 release-candidate line

The `1.0.0rc1` source candidate freezes the small `govengine.v1` facade and its
GovEngine-owned v1 schema inventory. It provides one canonical
`GovernanceRequest -> GovernanceDecision -> runtime claim -> receipt
conformance` flow with typed policy evaluation, independently bound approval,
scope and capability facts, short-lived attempt-bound authorization, stable
reason codes and a shared language-neutral corpus.

The stable promise is deliberately narrower than the package root:

- exactly the manifest-listed `govengine.v1` facade and v1 records are
  stable-candidate contracts;
- legacy root modules remain compatibility adapters, experimental surfaces or
  fixtures according to the generated stability matrix;
- GovEngine does not own runtime I/O, queueing, lifecycle or storage;
- SCLite 2.0 remains frozen and unchanged;
- publication is blocked until independent review, cross-stack immutable
  release evidence and explicit operator approval pass.

The current published `0.16.x` line remains the supported public package line
until `1.0.0rc1` is actually published.

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

- keep released consumer dependency pins aligned with the published `0.16.11`
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
