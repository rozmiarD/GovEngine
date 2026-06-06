from __future__ import annotations

import pytest

from govengine import (
    GovAdmissionDecision,
    GovApprovalRequest,
    GovAuditRecord,
    GovPolicyDecision,
    RuntimeAdmissionResult,
    admission_decision_from_host_gate,
    compose_runtime_admission_result,
    validate_admission_decision,
    validate_approval_request,
    validate_audit_record,
    validate_policy_decision,
    validate_runtime_admission_result,
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


def test_runtime_admission_result_allows_bounded_gate_summaries() -> None:
    result = validate_runtime_admission_result({
        'admission_id': 'runtime-admission-1',
        'subject_ref': 'sha256:prepared-contract',
        'status': 'allowed',
        'allowed': True,
        'reason_code': 'all_required_gates_passed',
        'prepared_execution_contract': {'status': 'prepared', 'digest': 'sha256:contract'},
        'policy_decision': {'decision': 'allow', 'policy_id': 'policy-1'},
        'execution_ticket': {'status': 'passed', 'ticket_id': 'ticket-1', 'digest': 'sha256:ticket'},
        'trust_decision': {'status': 'passed', 'trust_status': 'trusted'},
        'sclite_guarded_strict': {'status': 'passed', 'required': True},
        'replay_freshness': {'status': 'allowed', 'replay_status': 'fresh'},
        'runner_profile': {'profile': 'dry_run', 'mode': 'dry_run'},
        'receipt_obligation': {'required': True, 'binds': ['admission', 'ticket']},
        'artifact_refs': {'admission_digest': 'sha256:admission'},
    })

    payload = result.as_dict()

    assert isinstance(result, RuntimeAdmissionResult)
    assert payload['allowed'] is True
    assert payload['status'] == 'allowed'
    assert payload['blockers'] == []
    assert payload['runner_profile']['profile'] == 'dry_run'


def test_runtime_admission_result_blocks_with_next_actions() -> None:
    result = RuntimeAdmissionResult.from_mapping({
        'id': 'runtime-admission-blocked',
        'subject_ref': 'sha256:prepared-contract',
        'status': 'blocked',
        'allowed': False,
        'reason_code': 'missing_policy_decision',
        'blockers': ['missing_policy_decision'],
        'required_next_actions': ['evaluate_policy'],
        'prepared_execution_contract': {'status': 'prepared', 'digest': 'sha256:contract'},
    })

    assert result.allowed is False
    assert result.blockers == ('missing_policy_decision',)
    assert result.required_next_actions == ('evaluate_policy',)


def test_runtime_admission_result_rejects_status_allowed_mismatch() -> None:
    with pytest.raises(GovApiError, match='runtime_admission_allowed_status_mismatch'):
        validate_runtime_admission_result(RuntimeAdmissionResult(
            admission_id='bad-runtime-admission-1',
            subject_ref='sha256:prepared-contract',
            status='blocked',
            allowed=True,
            reason_code='bad',
            blockers=('missing_policy_decision',),
        ))

    with pytest.raises(GovApiError, match='runtime_admission_blocked_status_mismatch'):
        validate_runtime_admission_result({
            'admission_id': 'bad-runtime-admission-2',
            'subject_ref': 'sha256:prepared-contract',
            'status': 'allowed',
            'allowed': False,
            'reason_code': 'bad',
        })


def test_runtime_admission_result_rejects_blocked_without_evidence() -> None:
    with pytest.raises(GovApiError, match='runtime_admission_blocked_without_evidence'):
        validate_runtime_admission_result({
            'admission_id': 'bad-runtime-admission-3',
            'subject_ref': 'sha256:prepared-contract',
            'status': 'blocked',
            'allowed': False,
            'reason_code': 'blocked',
        })


def test_runtime_admission_result_rejects_raw_payloads_and_unknown_status() -> None:
    with pytest.raises(GovApiError, match='forbidden_admission_metadata:raw_output'):
        validate_runtime_admission_result({
            'admission_id': 'bad-runtime-admission-4',
            'subject_ref': 'sha256:prepared-contract',
            'status': 'blocked',
            'allowed': False,
            'reason_code': 'raw_output_forbidden',
            'blockers': ['raw_output_forbidden'],
            'artifact_refs': {'raw_output': 'full stdout must not be carried'},
        })

    with pytest.raises(GovApiError, match='unknown_runtime_admission_status:maybe'):
        validate_runtime_admission_result({
            'admission_id': 'bad-runtime-admission-5',
            'subject_ref': 'sha256:prepared-contract',
            'status': 'maybe',
            'allowed': False,
            'blockers': ['unknown_status'],
        })


def _runtime_admission_inputs(**overrides):
    values = {
        'admission_id': 'runtime-admission-composed-1',
        'subject_ref': 'sha256:prepared-contract',
        'prepared_execution_contract': {'status': 'prepared', 'digest': 'sha256:contract'},
        'policy_decision': {'decision': 'allow', 'policy_id': 'policy-1'},
        'execution_ticket': {'status': 'passed', 'ticket_id': 'ticket-1', 'digest': 'sha256:ticket'},
        'trust_decision': {'status': 'passed', 'trust_status': 'trusted', 'verifier_id': 'fixture'},
        'runner_profile': {'name': 'dry-run', 'allowed': True, 'live_backend_enabled': False},
        'receipt_obligation': {'required': True, 'binds': ['admission', 'ticket']},
        'artifact_refs': {'admission_digest': 'sha256:admission'},
    }
    values.update(overrides)
    return values


def test_compose_runtime_admission_result_allows_complete_dry_run_chain() -> None:
    result = compose_runtime_admission_result(**_runtime_admission_inputs())

    assert result.allowed is True
    assert result.status == 'allowed'
    assert result.reason_code == 'all_required_gates_passed'
    assert result.runner_profile['name'] == 'dry-run'
    assert result.receipt_obligation['required'] is True


def test_compose_runtime_admission_result_allows_guarded_fresh_runtime_bundle() -> None:
    result = compose_runtime_admission_result(**_runtime_admission_inputs(
        runtime_consumable=True,
        sclite_guarded_strict={'status': 'allowed', 'verification_status': 'passed'},
        replay_freshness={'status': 'allowed', 'replay_status': 'fresh'},
    ))

    assert result.allowed is True
    assert result.sclite_guarded_strict['verification_status'] == 'passed'
    assert result.replay_freshness['replay_status'] == 'fresh'


def test_compose_runtime_admission_result_blocks_missing_policy() -> None:
    result = compose_runtime_admission_result(**_runtime_admission_inputs(policy_decision=None))

    assert result.allowed is False
    assert result.status == 'blocked'
    assert 'missing_or_invalid_policy_decision' in result.blockers
    assert 'obtain_policy_decision' in result.required_next_actions


def test_compose_runtime_admission_result_honors_explicit_policy_denial() -> None:
    result = compose_runtime_admission_result(**_runtime_admission_inputs(
        policy_decision={'decision': 'allow', 'allowed': False, 'policy_id': 'policy-1'},
    ))

    assert result.allowed is False
    assert 'missing_or_invalid_policy_decision' in result.blockers


def test_compose_runtime_admission_result_blocks_replayed_runtime_bundle() -> None:
    result = compose_runtime_admission_result(**_runtime_admission_inputs(
        runtime_consumable=True,
        sclite_guarded_strict={'status': 'allowed', 'verification_status': 'passed'},
        replay_freshness={'status': 'blocked', 'replay_status': 'replayed'},
    ))

    assert result.allowed is False
    assert result.reason_code == 'replay_detected'
    assert 'missing_or_replayed_guarded_root' in result.blockers


def test_compose_runtime_admission_result_requires_receipt_obligation() -> None:
    result = compose_runtime_admission_result(**_runtime_admission_inputs(receipt_obligation=None))

    assert result.allowed is False
    assert result.reason_code == 'receipt_obligation_required'
    assert result.blockers == ('receipt_obligation_required',)
    assert 'require_runner_receipt_obligation' in result.required_next_actions


def test_compose_runtime_admission_result_keeps_live_disabled_by_default() -> None:
    result = compose_runtime_admission_result(**_runtime_admission_inputs(live=True))

    assert result.allowed is False
    assert result.reason_code == 'execution_disabled'
    assert 'live_backend_disabled' in result.blockers
