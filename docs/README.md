# GovEngine documentation map

Start here when navigating `docs/`. Package-level status lives in
[`../PUBLIC_STATUS.md`](../PUBLIC_STATUS.md); release facts in
[`../CHANGELOG.md`](../CHANGELOG.md).

## Tier 1 — package shape

| Doc | Purpose |
| --- | --- |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Layers, public surfaces, dependency direction |
| [API_BOUNDARY.md](API_BOUNDARY.md) | Module/surface ownership (machine-checked vs registry) |
| [API_STABILITY_MATRIX.md](API_STABILITY_MATRIX.md) | Export stability classification |
| [GOVENGINE_KERNEL_BOUNDARY.md](GOVENGINE_KERNEL_BOUNDARY.md) | Kernel vs profile vs runtime vs SCLite |
| [ROADMAP.md](ROADMAP.md) | Current alpha line and near-term direction |
| [VALIDATION.md](VALIDATION.md) | **Active** release and operator validation gate |

## Tier 2 — governed-runtime MVP (operators)

| Doc | Purpose |
| --- | --- |
| [GOVERNED_RUNTIME_MVP_RUNBOOK.md](GOVERNED_RUNTIME_MVP_RUNBOOK.md) | Operator chain and procedures |
| [SECURITY_INTEGRATION.md](SECURITY_INTEGRATION.md) | Required security evaluation order |
| [RUNTIME_ADMISSION.md](RUNTIME_ADMISSION.md) | `RuntimeAdmissionResult`, supervisor admission and **supervisor explain (G2)** |
| [POLICY_ENGINE.md](POLICY_ENGINE.md) | `govengine.policy` MVP and **policy explain/simulate (G1)** |
| [ADMISSION_POLICY.md](ADMISSION_POLICY.md) | Admission/audit record validators |
| [RECEIPT_BINDING.md](RECEIPT_BINDING.md) | Runner receipt binding |
| [EVIDENCE_REVIEW.md](EVIDENCE_REVIEW.md) | Evidence/review chain + OODA receipt bounds |
| [INSPECT_ONLY_ADMISSION_WORKFLOW.md](INSPECT_ONLY_ADMISSION_WORKFLOW.md) | Read-only admission CLI |
| [GUARDED_FRESH_RUNTIME_ADMISSION_EXAMPLE.md](GUARDED_FRESH_RUNTIME_ADMISSION_EXAMPLE.md) | Guarded-strict + replay-fresh example |
| [RUNNER_SUPERVISION.md](RUNNER_SUPERVISION.md) | Runner supervision + live-runner safety |
| [LOCAL_SUBPROCESS_RUNNER_DECISION.md](LOCAL_SUBPROCESS_RUNNER_DECISION.md) | Why no live subprocess runner ships |
| [SCLITE_INTEGRATION.md](SCLITE_INTEGRATION.md) | How GovEngine consumes SCLite |

## Tier 3 — neutral contract models

| Doc | Module focus |
| --- | --- |
| [ORCHESTRATOR_MODEL.md](ORCHESTRATOR_MODEL.md) | `govengine.orchestration` |
| [EVENT_MODEL.md](EVENT_MODEL.md) | `govengine.events` |
| [STATE_MACHINE.md](STATE_MACHINE.md) | `govengine.state_machine` |
| [CONTROL_MODEL.md](CONTROL_MODEL.md) | `govengine.control` |
| [RUNTIME_SHELL.md](RUNTIME_SHELL.md) | `govengine.runtime_shell` |
| [DOMAIN_PROFILE_CONTRACT.md](DOMAIN_PROFILE_CONTRACT.md) | `govengine.profiles` |

Planning contracts (`GovTaskContract`, `GovPlanIntentContract`, `PlannerPort`) are
documented under **Planning-contracts core** in [API_BOUNDARY.md](API_BOUNDARY.md#planning-contracts-core).

## Archive

Historical material kept for audit evidence, not as the active gate:

| Doc | Contents |
| --- | --- |
| [archive/VALIDATION_HISTORY.md](archive/VALIDATION_HISTORY.md) | Per-release validation records |
| [archive/ROADMAP_VERSION_HISTORY.md](archive/ROADMAP_VERSION_HISTORY.md) | Delivered `0.2.x`–`0.11.x` milestones |

When docs disagree, trust `scripts/validate_public_truth.py` and the current
sections of [VALIDATION.md](VALIDATION.md) over archived records.
