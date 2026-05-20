from __future__ import annotations

import pytest

from govengine import (
    GovAdmissionDecision,
    GovApprovalRequest,
    GovAuditRecord,
    GovPolicyDecision,
    admission_decision_from_host_gate,
    validate_admission_decision,
    validate_approval_request,
    validate_audit_record,
    validate_policy_decision,
)
from govengine.api import GovApiError


def test_admission_decision_models_host_gate_without_raw_target_or_command() -> None:
    decision = admission_decision_from_host_gate(
        decision_id='admit-1',
        subject_ref='sha256:task-ref',
        subject_kind='task',
        allowed=False,
        reason_code='planner_activation_phase_skip',
        detail='phase=3;requires=confirmed_signal',
        blockers=['planner_phase_gate'],
        context={'activation_phase': 3, 'expected_depth': 'deep'},
        signal={'has_confirmed_signal': False, 'preferred_stages': {'validation'}},
        explainability={'source': 'host_gate_projection'},
        metadata={'target_redacted': True},
    )

    payload = decision.as_dict()

    assert isinstance(decision, GovAdmissionDecision)
    assert payload['subject_ref'] == 'sha256:task-ref'
    assert payload['allowed'] is False
    assert payload['outcome'] == 'denied'
    assert payload['signal']['preferred_stages'] == ['validation']
    assert validate_admission_decision(payload).reason_code == 'planner_activation_phase_skip'


def test_admission_decision_rejects_forbidden_raw_runtime_data() -> None:
    with pytest.raises(GovApiError, match='forbidden_admission_metadata:target'):
        validate_admission_decision({
            'decision_id': 'admit-1',
            'subject_ref': 'sha256:task-ref',
            'context': {'target': 'https://example.com/'},
        })

    for key in ('prompt', 'command', 'credential', 'schedule', 'runtime_storage'):
        with pytest.raises(GovApiError, match=f'forbidden_admission_metadata:{key}'):
            validate_admission_decision({
                'decision_id': f'admit-{key}',
                'subject_ref': 'sha256:task-ref',
                'allowed': False,
                'outcome': 'denied',
                'metadata': {key: 'not allowed'},
            })


def test_admission_allowed_flag_must_match_outcome() -> None:
    with pytest.raises(GovApiError, match='admission_allowed_outcome_mismatch'):
        validate_admission_decision({
            'decision_id': 'bad-1',
            'subject_ref': 'sha256:task-ref',
            'allowed': True,
            'outcome': 'denied',
        })

    with pytest.raises(GovApiError, match='admission_denied_outcome_mismatch'):
        validate_admission_decision({
            'decision_id': 'bad-2',
            'subject_ref': 'sha256:task-ref',
            'allowed': False,
            'outcome': 'allowed',
        })


def test_policy_approval_and_audit_contracts_are_shape_only() -> None:
    policy = validate_policy_decision({
        'policy_id': 'policy-1',
        'subject_ref': 'sha256:task-ref',
        'decision': 'require_approval',
        'controls': ['operator_review'],
        'blockers': ['approval_required'],
        'metadata': {'profile': 'ravenclaw-security'},
    })
    approval = validate_approval_request({
        'request_id': 'approval-1',
        'subject_ref': 'sha256:task-ref',
        'state': 'requested',
        'policy_refs': [policy.policy_id],
        'metadata': {'workflow': 'host_owned'},
    })
    audit = validate_audit_record({
        'record_id': 'audit-1',
        'record_type': 'policy_decision',
        'subject_ref': 'sha256:task-ref',
        'decision_ref': policy.policy_id,
        'event_refs': ['event-1'],
        'metadata': {'retention': 'host_owned'},
    })

    assert isinstance(policy, GovPolicyDecision)
    assert isinstance(approval, GovApprovalRequest)
    assert isinstance(audit, GovAuditRecord)
    assert policy.as_dict()['controls'] == ['operator_review']
    assert approval.as_dict()['policy_refs'] == ['policy-1']
    assert audit.as_dict()['event_refs'] == ['event-1']


def test_policy_approval_and_audit_reject_runtime_ownership_claims() -> None:
    with pytest.raises(GovApiError, match='forbidden_admission_metadata:live_execution'):
        validate_policy_decision({
            'policy_id': 'policy-bad',
            'subject_ref': 'sha256:task-ref',
            'metadata': {'live_execution': True},
        })

    with pytest.raises(GovApiError, match='forbidden_admission_metadata:carrier_payload'):
        validate_approval_request({
            'request_id': 'approval-bad',
            'subject_ref': 'sha256:task-ref',
            'metadata': {'carrier_payload': {'raw': True}},
        })

    with pytest.raises(GovApiError, match='forbidden_admission_metadata:storage_path'):
        validate_audit_record({
            'record_id': 'audit-bad',
            'subject_ref': 'sha256:task-ref',
            'metadata': {'storage_path': '/tmp/audit.db'},
        })
