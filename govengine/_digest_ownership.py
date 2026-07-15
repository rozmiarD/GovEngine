from __future__ import annotations

from dataclasses import dataclass


DIGEST_OWNERSHIP_MODES = ('recomputed', 'delegated', 'reference_only', 'produced')


@dataclass(frozen=True)
class DigestOwnership:
    binding_id: str
    owner: str
    mode: str
    payload_available: bool
    validator: str
    mismatch_reason: str = ''


DIGEST_OWNERSHIP_INVENTORY = (
    # Full GovEngine-owned projections: supplied digests never override recomputation.
    DigestOwnership('typed_execution.capability_descriptor', 'govengine', 'recomputed', True, 'validate_typed_execution_governance_request', 'capability_descriptor_digest_mismatch'),
    DigestOwnership('typed_execution.network_policy_binding', 'govengine', 'recomputed', True, 'validate_typed_execution_governance_request', 'network_policy_binding_digest_mismatch'),
    DigestOwnership('runner.request', 'govengine', 'recomputed', True, 'validate_runner_receipt_binding', 'runner_request_digest_mismatch'),
    DigestOwnership('runner.receipt', 'govengine', 'recomputed', True, 'validate_runner_receipt_binding', 'runner_receipt_digest_mismatch'),
    DigestOwnership('runner.runtime_admission', 'govengine', 'recomputed', True, 'validate_runner_receipt_binding', 'runtime_admission_digest_mismatch'),
    DigestOwnership('signing.record', 'govengine', 'recomputed', True, 'verify_signed_govengine_record', 'signed_record_digest_mismatch'),
    DigestOwnership('audit.record', 'govengine', 'recomputed', True, 'validate_audit_ledger_entry', 'audit_ledger_record_digest_mismatch'),
    DigestOwnership('audit.ledger_entry', 'govengine', 'recomputed', True, 'validate_audit_ledger_entry', 'audit_ledger_entry_digest_mismatch'),
    DigestOwnership('governance_trace.plan', 'govengine', 'recomputed', True, 'project_governance_trace', 'policy_enforcement_plan_digest_mismatch'),
    DigestOwnership('governance_trace.admission', 'govengine', 'recomputed', True, 'project_governance_trace', 'policy_enforcement_admission_digest_mismatch'),
    DigestOwnership('policy.enforcement_plan.policy_pack_with_payload', 'govengine', 'recomputed', True, 'validate_policy_enforcement_plan', 'policy_enforcement_plan_drift'),
    DigestOwnership('policy.enforcement_plan.verdict_with_payload', 'govengine', 'recomputed', True, 'validate_policy_enforcement_plan', 'policy_enforcement_plan_drift'),
    DigestOwnership('governance_request.policy_pack', 'govengine', 'recomputed', True, 'validate_governance_request', 'policy_pack_digest_mismatch'),
    DigestOwnership('governance_request.execution_facts', 'govengine', 'recomputed', True, 'validate_governance_request', 'execution_facts_digest_mismatch'),
    DigestOwnership('governance_request.requested_scope', 'govengine', 'recomputed', True, 'validate_governance_request', 'requested_scope_digest_mismatch'),
    DigestOwnership('governance_request.approval_attestation', 'govengine', 'recomputed', True, 'validate_governance_request', 'approval_attestation_digest_mismatch'),
    DigestOwnership('approval.subject', 'govengine', 'recomputed', True, 'validate_approval_attestation', 'approval_subject_digest_mismatch'),
    DigestOwnership('governance_request.scope_policy_binding', 'govengine', 'recomputed', True, 'validate_governance_request', 'scope_policy_binding_digest_mismatch'),
    DigestOwnership('governance_request.capability_requirements', 'govengine', 'recomputed', True, 'validate_governance_request', 'capability_requirements_digest_mismatch'),
    DigestOwnership('governance_request.capability_inventory', 'govengine', 'recomputed', True, 'validate_governance_request', 'capability_inventory_digest_mismatch'),

    # Payloads owned elsewhere: GovEngine validates or compares their references only.
    DigestOwnership('runner.execution_ticket', 'sclite_or_host', 'delegated', False, 'validate_runner_receipt_binding'),
    DigestOwnership('runtime_admission.execution_ticket', 'sclite', 'delegated', False, 'validate_runtime_admission_proof_inputs'),
    DigestOwnership('replay.root_chain', 'sclite', 'delegated', False, 'validate_replay_freshness'),
    DigestOwnership('signing.envelope_binding', 'host_signer', 'delegated', False, 'signature_transition_decision'),
    DigestOwnership('deconfliction.artifact_state', 'sclite_or_host', 'delegated', False, 'ConflictDetector.detect_digest_conflicts'),
    DigestOwnership('state_index.artifact_state', 'sclite_or_host', 'delegated', False, 'build_artifact_state_index'),
    DigestOwnership('review.receipt', 'rexecop_or_host', 'reference_only', False, 'validate_evidence_review_chain'),
    DigestOwnership('review.admission', 'govengine', 'reference_only', False, 'validate_evidence_review_chain'),
    DigestOwnership('trigger.event', 'rexecop_or_host', 'reference_only', False, 'admit_trigger_planning'),
    DigestOwnership('trigger.rule_set', 'profile_or_host', 'reference_only', False, 'admit_trigger_planning'),
    DigestOwnership('trigger.rule', 'profile_or_host', 'reference_only', False, 'admit_trigger_planning'),
    DigestOwnership('automation.parent_operation', 'rexecop', 'reference_only', False, 'admit_automation_transition'),
    DigestOwnership('automation.chain', 'rexecop', 'reference_only', False, 'admit_automation_transition'),
    DigestOwnership('typed_execution.step_execution_spec', 'rexecop', 'reference_only', False, 'validate_typed_execution_governance_request'),
    DigestOwnership('typed_execution.payload', 'rexecop', 'reference_only', False, 'validate_typed_execution_governance_request'),
    DigestOwnership('typed_execution.origin_binding', 'rexecop_or_host', 'reference_only', False, 'validate_typed_execution_governance_request'),
    DigestOwnership('runner.output', 'rexecop', 'reference_only', False, 'validate_runner_receipt_binding'),
    DigestOwnership('audit.event', 'host', 'reference_only', False, 'validate_audit_ledger_entry'),
    DigestOwnership('policy.enforcement_plan.policy_pack', 'govengine', 'reference_only', False, 'validate_policy_enforcement_plan'),
    DigestOwnership('policy.enforcement_plan.verdict', 'govengine', 'reference_only', False, 'validate_policy_enforcement_plan'),
    DigestOwnership('governance_request.execution_spec', 'rexecop', 'reference_only', False, 'validate_governance_request'),
    DigestOwnership('governance_request.payload', 'rexecop', 'reference_only', False, 'validate_governance_request'),
    DigestOwnership('governance_request.fencing_token', 'rexecop', 'reference_only', False, 'validate_governance_request'),

    # Digests emitted from GovEngine-owned output bodies.
    DigestOwnership('audit.previous_entry', 'govengine', 'produced', True, 'JsonlAuditLedgerAdapter.verify'),
    DigestOwnership('audit.append_result', 'govengine', 'produced', True, 'JsonlAuditLedgerAdapter.append'),
    DigestOwnership('audit.verification_last_entry', 'govengine', 'produced', True, 'JsonlAuditLedgerAdapter.verify'),
    DigestOwnership('trigger.request', 'govengine', 'produced', True, 'trigger_planning_request_digest'),
    DigestOwnership('governance_trace.policy_request', 'govengine', 'produced', True, 'project_governance_trace'),
    DigestOwnership('governance_trace.policy_verdict', 'govengine', 'produced', True, 'project_governance_trace'),
    DigestOwnership('typed_execution.governance_projection', 'govengine', 'produced', True, 'project_typed_execution_governance'),
    DigestOwnership('typed_execution.capability_report', 'govengine', 'produced', True, 'evaluate_typed_execution_capability_compatibility'),
    DigestOwnership('typed_execution.stack_report', 'govengine', 'produced', True, 'evaluate_typed_execution_stack_compatibility'),
    DigestOwnership('typed_execution.bundle', 'govengine', 'produced', True, 'explain_typed_execution_governance'),
    DigestOwnership('profile.governance_projection', 'govengine', 'produced', True, 'project_profile_governance'),
    DigestOwnership('profile.compatibility_report', 'govengine', 'produced', True, 'evaluate_profile_connector_compatibility'),
    DigestOwnership('profile.governance_bundle', 'govengine', 'produced', True, 'explain_profile_governance'),
    DigestOwnership('contract_compatibility.supported_report', 'govengine', 'produced', True, 'supported_contract_report'),
    DigestOwnership('contract_compatibility.consumer_report', 'govengine', 'produced', True, 'evaluate_contract_compatibility'),
    DigestOwnership('automation.explanation', 'govengine', 'produced', True, 'explain_automation_transition'),
    DigestOwnership('supervisor.explanation', 'govengine', 'produced', True, 'explain_supervisor_action'),
    DigestOwnership('governance_trace.output', 'govengine', 'produced', True, 'project_governance_trace'),
    DigestOwnership('governance_request.subject', 'govengine', 'produced', True, 'governance_subject_digest'),
    DigestOwnership('governance_request.record', 'govengine', 'produced', True, 'governance_request_digest'),
    DigestOwnership('approval.attestation', 'govengine', 'produced', True, 'approval_attestation_digest'),
    DigestOwnership('scope_policy.binding', 'govengine', 'produced', True, 'scope_policy_binding_digest'),
    DigestOwnership('scope_policy.decision', 'govengine', 'produced', True, 'scope_decision_digest'),
    DigestOwnership('capability.requirements', 'govengine', 'produced', True, 'operation_capability_requirements_digest'),
    DigestOwnership('capability.inventory', 'govengine', 'produced', True, 'capability_inventory_binding_digest'),
    DigestOwnership('capability.compatibility_decision', 'govengine', 'produced', True, 'capability_compatibility_decision_digest'),
)


def validate_digest_ownership_inventory() -> tuple[DigestOwnership, ...]:
    seen: set[str] = set()
    for item in DIGEST_OWNERSHIP_INVENTORY:
        if not item.binding_id or item.binding_id in seen:
            raise ValueError(f'duplicate_or_missing_digest_binding:{item.binding_id}')
        seen.add(item.binding_id)
        if item.mode not in DIGEST_OWNERSHIP_MODES:
            raise ValueError(f'unknown_digest_ownership_mode:{item.binding_id}:{item.mode}')
        if item.mode == 'recomputed':
            if item.owner != 'govengine' or not item.payload_available or not item.mismatch_reason:
                raise ValueError(f'invalid_recomputed_digest_binding:{item.binding_id}')
        if item.mode == 'reference_only' and item.payload_available:
            raise ValueError(f'reference_only_payload_available:{item.binding_id}')
        if item.owner == 'sclite' and item.mode == 'recomputed':
            raise ValueError(f'sclite_digest_recomputed_by_govengine:{item.binding_id}')
    return DIGEST_OWNERSHIP_INVENTORY
