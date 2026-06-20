# GovEngine API Stability Matrix

This matrix classifies the current `govengine.__all__` top-level export surface for the alpha governed-runtime kernel.

Status meanings:

- stable: no current top-level export is stable.
- alpha: supported alpha contract surface; compatible changes should be additive where practical.
- fixture: public alpha fixture or demo helper; useful for tests/examples but not production authority.
- deprecated: no current top-level export is deprecated.
- internal-exposed: no current top-level export is intentionally internal-exposed.

GovEngine is still alpha. This matrix is not a production readiness claim, and it does not grant live execution, PKI/KMS, credential, raw evidence storage, scheduler, carrier, Ravenclaw, OpenClaw, MCP, or A2A ownership.

## v1.5 Candidate Kernel Contract Subset

The v1.5 candidate subset is a compatibility target inside the alpha surface,
not a stable API declaration yet. It is limited to deterministic governance
kernel contracts: `RuntimeAdmissionResult`,
`compose_runtime_admission_result()`, `validate_runtime_admission_result()`,
`validate_runtime_admission_proof_inputs()`,
`normalize_admission_artifact_refs()`, `ArtifactDescriptor`,
`ArtifactState`, `TransitionDecision`, `ReasonCode`,
`canonical_lifecycle_state()`, `TransitionGate`,
`validate_evidence_review_chain()`, `qualify_evidence_claim()`,
`VerificationResult`, `signature_transition_decision()`,
`ReplayClaimStore`, `verify_guard_and_record_replay()`,
`validate_runner_receipt_binding()`, and public-safe summary helpers.

The subset must remain one admission envelope. It must not introduce a second
runtime admission record, live executor, scheduler, planner, PKI/KMS/key
manager, replay database, raw evidence store, or host-specific Ravenclaw/Tecrax
runtime behavior.

| Stability | Source | Exports | Boundary note |
| --- | --- | --- | --- |
| alpha | govengine.admission | `AuditLedgerAppendResult`, `AuditLedgerEntry`, `AuditLedgerPort`, `AuditLedgerVerificationResult`, `GovAdmissionDecision`, `GovApprovalRequest`, `GovAuditRecord`, `GovPolicyDecision`, `JsonlAuditLedgerAdapter`, `RuntimeAdmissionResult`, `admission_decision_from_host_gate`, `audit_ledger_entry_digest`, `audit_ledger_verification_public_summary`, `audit_record_public_summary`, `compose_runtime_admission_result`, `normalize_admission_artifact_refs`, `policy_verdict_to_gov_policy_decision`, `runtime_admission_public_summary`, `validate_admission_decision`, `validate_approval_request`, `validate_audit_record`, `validate_audit_ledger_append_result`, `validate_audit_ledger_entry`, `validate_audit_ledger_verification_result`, `validate_policy_decision`, `validate_runtime_admission_result`, `validate_runtime_admission_proof_inputs` | Neutral admission/policy/runtime-admission records, PolicyEngine verdict projection, bounded audit-ledger port contracts, a JSONL hash-chain development adapter, bounded reference normalization, public-safe projection helpers, proof-input completeness checks, and gate-summary composition only; host owns policy meaning, approval workflow, live backend behavior, production audit persistence/concurrency, raw evidence storage, SCLite canonicalization, and production trust/key boundaries. |
| alpha | govengine.api | `GovApiError`, `GovApiResult` | Lightweight result/error helpers. |
| alpha | govengine.boundary | `BoundaryReport`, `DomainProfileConformance`, `DomainProfileContract`, `KernelBoundary`, `boundary_surface_index`, `domain_profile_conformance`, `kernel_boundary_contract`, `kernel_boundary_report`, `known_profile_contracts`, `ravenclaw_profile_contract`, `validate_domain_profile_contract`, `validate_domain_profile_conformance` | Kernel/profile/runtime/SCLite ownership contracts; Ravenclaw contract remains fixture/profile metadata. |
| alpha | govengine.context | `GovEngineContext`, `GovEnginePaths`, `host_compat_context`, `ravenclaw_context` | Host path/context records; Ravenclaw context remains compatibility fixture metadata. |
| alpha | govengine.control | `ControlDecision`, `apply_control_decision`, `validate_control_decision` | Between-step control decisions without scheduler/storage/live-execution ownership. |
| alpha | govengine.contract_proofs | `GovernanceVocabularyEntry`, `RuntimeContractProof`, `governance_contract_vocabulary`, `ravenclaw_contract_proof`, `tecrax_contract_proof`, `validate_governance_contract_vocabulary`, `validate_runtime_contract_proof` | Public-safe proof fixtures and neutral vocabulary; no domain runtime ownership. |
| alpha | govengine.core | `ArtifactDescriptor`, `ArtifactEnvelope`, `ArtifactState`, `ExecutionPrerequisites`, `GovernanceContext`, `ReasonCode`, `TransitionDecision` | Portable artifact and governance primitives. |
| alpha | govengine.deconfliction | `ArtifactChangeOrder`, `ArtifactConflict`, `ConflictDetector` | Digest/state conflict helpers only. |
| alpha | govengine.events | `EventEnvelope`, `GovEvent`, `validate_event_envelope`, `validate_gov_event` | Transport-neutral event metadata; no carrier payload authority. |
| alpha | govengine.execution.gate | `DryRunRunner`, `ExecutionGate`, `ExecutionGateInput`, `RunnerProfile` | Dry-run/default-deny execution gate helpers; no live backend ownership. |
| alpha | govengine.execution.runner_protocol | `runner_receipt_public_summary` | Public-safe runner receipt summary over bounded binding refs and digest counts only; no raw stdout/stderr publication and no execution authority. |
| alpha | govengine.execution.supervision | `GovRunnerLease`, `GovSupervisionDecision`, `GovSupervisionPlan`, `LocalSubprocessRunnerReadiness`, `evaluate_local_subprocess_runner_readiness`, `runner_lease_from_request`, `supervision_plan_from_runner_request`, `validate_runner_lease`, `validate_runner_receipt_binding`, `validate_runner_receipt_for_request`, `validate_supervised_runner_request`, `validate_supervision_decision`, `validate_supervision_plan` | Runner request, lease, supervision, readiness, and receipt boundary helpers; live subprocess execution remains not applicable until the missing host-owned safety prerequisites are closed. |
| alpha | govengine.execution_backend | `CommandResult`, `GovExecutionBackend` | Host-neutral backend protocol/result helpers. |
| alpha | govengine.lifecycle | `ArtifactLifecycleController`, `TransitionGate`, `TransitionPolicy`, `canonical_lifecycle_state` | Lightweight lifecycle gate/controller helpers; `verified_chain` and `verified_lifecycle` are canonical while legacy aliases are migration shims; SCLite remains lifecycle authority. |
| alpha | govengine.ooda | `GovObservation`, `GovOodaController`, `GovOodaDecision`, `GovOrientation` | Neutral OODA records/controller; no scheduler or agent framework ownership. |
| alpha | govengine.orchestration | `OrchestrationStep`, `OrchestratorBoundary`, `orchestrator_boundary_contract`, `validate_orchestration_step` | Deterministic orchestration handoff records only. |
| alpha | govengine.planning | `GovPlanIntentContract`, `GovTaskContract`, `PlannerPort`, `task_contract_from_host_task`, `validate_plan_intent_contract`, `validate_planner_port`, `validate_task_contract` | Planner-to-runtime contract shapes; no planner implementation ownership. |
| alpha | govengine.policy | `CompiledPolicyPack`, `CompileResult`, `PolicyCompiler`, `PolicyConstraint`, `PolicyEngine`, `PolicyObligation`, `PolicyRequest`, `PolicyRule`, `PolicyVerdict`, `compile_policy_pack`, `evaluate_policy`, `validate_policy_request`, `validate_policy_verdict` | Deterministic policy request/verdict contracts, declarative rule compilation, fail-closed evaluation, and bounded obligations/constraints; no SCLite truth/canonicalization ownership, operator workflow ownership, raw evidence storage, scheduler, adapter, or live execution authority. |
| alpha | govengine.profiles | `CapabilityDeclaration`, `DomainProfile`, `EvidenceRuleDeclaration`, `PlanningStageRegistry`, `PolicyHookDeclaration`, `ProfileConformanceReport`, `ResourceTypeRegistry`, `RunnerProfileDeclaration`, `TaskFamilyRegistry`, `profile_conformance_report`, `ravenclaw_security_profile`, `tecrax_infra_ops_profile`, `validate_domain_profile`, `validate_profile_conformance` | Contract-only domain profile SDK and fixtures; host owns domain semantics. |
| alpha | govengine.replay | `GuardedBundleRuntimeDecision`, `GuardReplayDecision`, `GuardReplayRecord`, `InMemoryReplayClaimStore`, `ReplayClaimStore`, `evaluate_guard_replay`, `guard_replay_record_from_guard`, `record_guard_replay`, `record_guard_replay_file`, `verify_guard_and_record_replay` | Guarded SCLite root replay freshness over host-supplied store plus a claim-once port and deterministic in-memory development adapter; no HMAC/key ownership, database ownership, or production concurrency guarantee. |
| alpha | govengine.review | `GovEvidenceClaim`, `GovEvidenceQualification`, `GovEvidenceRequirement`, `GovReviewResult`, `evidence_claim_public_summary`, `qualify_evidence_claim`, `review_result_public_summary`, `validate_evidence_claim`, `validate_evidence_qualification`, `validate_evidence_requirement`, `validate_evidence_review_chain`, `validate_review_result` | Receipt-bounded evidence review records and public-safe summaries; SCLite review bundle authority is not duplicated and raw evidence stays host-owned. |
| alpha | govengine.roles | `GovRoleAdapters` | Adapter binding record; no Ravenclaw/OpenClaw dependency. |
| alpha | govengine.runtime_shell | `GovControlAction`, `GovQueueLane`, `GovQueueSnapshot`, `GovRuntimeSnapshot`, `GovSchedulerTick`, `control_action_from_host_action`, `queue_snapshot_from_lanes`, `validate_control_action`, `validate_queue_snapshot`, `validate_runtime_snapshot`, `validate_scheduler_tick` | Host-provided runtime shell projection; no scheduler/storage/live-execution authority. |
| alpha | govengine.sclite_contracts lazy exports | `GovSCLiteLifecycleVerifier`, `review_bundle_state`, `review_bundle_transition_decision`, `review_sclite_bundle`, `verify_lifecycle_manifest` | Lazy SCLite bridge exports; SCLite owns lifecycle and review verification. |
| alpha | govengine.scope_ports | `FunctionalScopePort`, `GovScopePort` | Host-neutral scope port protocols/helpers. |
| alpha | govengine.signing | `KeyResolutionRequest`, `KeyResolutionResult`, `KeyResolverPort`, `SignatureEnvelope`, `SignedArtifact`, `SigningPolicy`, `TrustPolicy`, `TrustStoreDecision`, `TrustStorePort`, `VerificationResult`, `canonical_govengine_record`, `govengine_record_digest`, `signed_artifact_from_record`, `signature_transition_decision`, `verify_signed_govengine_record` | Host-provided signer/verifier/key-resolver/trust-store decision records plus deterministic serialization/digest, signed-envelope helpers, and signature transition decisioning for GovEngine-owned records only; no SCLite canonicalization, PKI/KMS, or key-store ownership. |
| fixture | govengine.signing demo helpers | `DemoDigestSigner`, `DemoDigestVerifier`, `demo_sign_and_verify`, `demo_sign_govengine_record` | Deterministic demo-only signer/verifier helpers; not cryptographic identity proof. |
| alpha | govengine.state_index | `ArtifactStateIndex` | Lightweight artifact state summary helper. |
| alpha | govengine.state_machine | `GovRunState`, `StateTransition`, `apply_state_transition`, `validate_run_state`, `validate_state_transition` | Neutral run-state transitions; no persistence/scheduler/live-execution authority. |
| alpha | govengine.state_store | `GovStateStore` | Neutral JSON state helper primitive; production persistence remains host-owned. |
| alpha | govengine.surfaces | `GovSurface`, `admission_policy_surface`, `domain_profile_sdk_surface`, `public_surface_index`, `runtime_contract_proofs_surface` | Machine-readable public surface registry. |

Current summary:

- stable exports: 0
- alpha exports: 203
- fixture exports: 4
- deprecated exports: 0
- internal-exposed exports: 0
