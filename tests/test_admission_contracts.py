from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from govengine import (
    AuditLedgerAppendResult,
    AuditLedgerEntry,
    AuditLedgerPort,
    AuditLedgerVerificationResult,
    GovAdmissionDecision,
    GovApprovalRequest,
    GovAuditRecord,
    GovPolicyDecision,
    JsonlAuditLedgerAdapter,
    RuntimeAdmissionResult,
    admission_decision_from_host_gate,
    audit_ledger_entry_digest,
    compose_runtime_admission_result,
    validate_admission_decision,
    validate_approval_request,
    validate_audit_record,
    validate_audit_ledger_append_result,
    validate_audit_ledger_entry,
    validate_audit_ledger_verification_result,
    validate_policy_decision,
    validate_runtime_admission_result,
)
from govengine.admission import normalize_admission_artifact_refs
from govengine.api import GovApiError

ROOT = Path(__file__).resolve().parents[1]
INSPECT_ADMISSION_SCRIPT = ROOT / 'scripts' / 'inspect_runtime_admission.py'


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


def test_audit_ledger_port_contracts_are_shape_only() -> None:
    record = validate_audit_record({
        'record_id': 'audit-1',
        'record_type': 'admission_decision',
        'subject_ref': 'sha256:runtime-admission',
        'decision_ref': 'runtime-admission-1',
        'event_refs': ['event-1'],
        'metadata': {'retention': 'host_owned'},
    })
    entry = validate_audit_ledger_entry({
        'entry_id': 'ledger-entry-1',
        'sequence': 1,
        'record': record.as_dict(),
        'record_digest': 'sha256:audit-record',
        'event_digest': 'sha256:event-1',
        'previous_entry_digest': 'sha256:previous-entry',
        'metadata': {'storage': 'host_owned'},
    })
    append = validate_audit_ledger_append_result({
        'status': 'appended',
        'entry_id': entry.entry_id,
        'sequence': entry.sequence,
        'entry_digest': 'sha256:ledger-entry-1',
    })
    verification = validate_audit_ledger_verification_result({
        'status': 'verified',
        'verified': True,
        'checked_entries': 1,
        'last_entry_id': entry.entry_id,
        'last_entry_digest': append.entry_digest,
    })

    class FixtureLedger:
        def append(
            self,
            record: GovAuditRecord,
            *,
            record_digest: str,
            event_digest: str = '',
            previous_entry_digest: str = '',
        ) -> AuditLedgerAppendResult:
            assert record.record_id == 'audit-1'
            assert record_digest == 'sha256:audit-record'
            assert event_digest == 'sha256:event-1'
            assert previous_entry_digest == 'sha256:previous-entry'
            return append

        def read(self, *, after_entry_id: str = '', limit: int = 100) -> tuple[AuditLedgerEntry, ...]:
            assert after_entry_id == ''
            assert limit == 100
            return (entry,)

        def verify(self, entries: tuple[AuditLedgerEntry, ...]) -> AuditLedgerVerificationResult:
            assert entries == (entry,)
            return verification

    ledger: AuditLedgerPort = FixtureLedger()

    assert isinstance(entry, AuditLedgerEntry)
    assert entry.as_dict()['record']['record_id'] == 'audit-1'
    assert ledger.append(
        record,
        record_digest='sha256:audit-record',
        event_digest='sha256:event-1',
        previous_entry_digest='sha256:previous-entry',
    ).entry_digest == 'sha256:ledger-entry-1'
    assert ledger.read()[0].record_digest == 'sha256:audit-record'
    assert ledger.verify(ledger.read()).verified is True


def test_audit_ledger_contracts_reject_unsafe_or_incomplete_boundaries() -> None:
    base_record = {
        'record_id': 'audit-1',
        'record_type': 'policy_decision',
        'subject_ref': 'sha256:task-ref',
    }

    with pytest.raises(GovApiError, match='missing_audit_ledger_record_digest'):
        validate_audit_ledger_entry({
            'entry_id': 'ledger-entry-1',
            'sequence': 0,
            'record': base_record,
        })

    with pytest.raises(GovApiError, match='invalid_audit_ledger_record_digest'):
        validate_audit_ledger_entry({
            'entry_id': 'ledger-entry-1',
            'sequence': 0,
            'record': base_record,
            'record_digest': 'md5:not-allowed',
        })

    with pytest.raises(GovApiError, match='forbidden_admission_metadata:storage_path'):
        validate_audit_ledger_entry({
            'entry_id': 'ledger-entry-1',
            'sequence': 0,
            'record': base_record,
            'record_digest': 'sha256:audit-record',
            'metadata': {'storage_path': '/tmp/govengine-ledger.jsonl'},
        })

    with pytest.raises(GovApiError, match='missing_audit_ledger_append_digest'):
        validate_audit_ledger_append_result({
            'status': 'appended',
            'entry_id': 'ledger-entry-1',
            'sequence': 0,
        })

    with pytest.raises(GovApiError, match='audit_ledger_failed_without_blockers'):
        validate_audit_ledger_verification_result({
            'status': 'failed',
            'checked_entries': 1,
        })

    with pytest.raises(GovApiError, match='audit_ledger_verified_status_mismatch'):
        validate_audit_ledger_verification_result({
            'status': 'verified',
            'verified': False,
            'checked_entries': 1,
            'last_entry_id': 'ledger-entry-1',
            'last_entry_digest': 'sha256:ledger-entry-1',
        })


def test_jsonl_audit_ledger_adapter_appends_reads_and_verifies(tmp_path) -> None:
    ledger = JsonlAuditLedgerAdapter(tmp_path / 'audit-ledger.jsonl')
    first = validate_audit_record({
        'record_id': 'audit-1',
        'record_type': 'admission_decision',
        'subject_ref': 'sha256:runtime-admission',
        'decision_ref': 'runtime-admission-1',
    })
    second = validate_audit_record({
        'record_id': 'audit-2',
        'record_type': 'policy_decision',
        'subject_ref': 'sha256:policy-subject',
        'decision_ref': 'policy-1',
    })

    first_append = ledger.append(first, record_digest='sha256:audit-1', event_digest='sha256:event-1')
    second_append = ledger.append(second, record_digest='sha256:audit-2', event_digest='sha256:event-2')
    entries = ledger.read()
    verification = ledger.verify(entries)

    assert first_append.status == 'appended'
    assert second_append.status == 'appended'
    assert len(entries) == 2
    assert entries[0].previous_entry_digest == ''
    assert entries[1].previous_entry_digest == first_append.entry_digest
    assert entries[0].entry_digest == audit_ledger_entry_digest(entries[0])
    assert entries[1].entry_digest == audit_ledger_entry_digest(entries[1])
    assert ledger.read(after_entry_id=entries[0].entry_id) == (entries[1],)
    assert verification.status == 'verified'
    assert verification.verified is True
    assert verification.last_entry_digest == second_append.entry_digest


def test_jsonl_audit_ledger_adapter_rejects_wrong_previous_digest(tmp_path) -> None:
    ledger = JsonlAuditLedgerAdapter(tmp_path / 'audit-ledger.jsonl')
    record = validate_audit_record({
        'record_id': 'audit-1',
        'record_type': 'approval_request',
        'subject_ref': 'sha256:approval',
        'decision_ref': 'approval-1',
    })

    first = ledger.append(record, record_digest='sha256:audit-1')
    rejected = ledger.append(record, record_digest='sha256:audit-1b', previous_entry_digest='sha256:not-current')

    assert first.status == 'appended'
    assert rejected.status == 'rejected'
    assert rejected.reason_code == 'audit_ledger_previous_digest_mismatch'
    assert rejected.blockers == ('audit_ledger_previous_digest_mismatch',)
    assert len(ledger.read()) == 1


def test_jsonl_audit_ledger_adapter_detects_one_field_tamper(tmp_path) -> None:
    path = tmp_path / 'audit-ledger.jsonl'
    ledger = JsonlAuditLedgerAdapter(path)
    record = validate_audit_record({
        'record_id': 'audit-1',
        'record_type': 'policy_decision',
        'subject_ref': 'sha256:policy-subject',
        'decision_ref': 'policy-1',
    })

    ledger.append(record, record_digest='sha256:audit-1')
    [line] = path.read_text(encoding='utf-8').splitlines()
    tampered = json.loads(line)
    tampered['record']['decision_ref'] = 'policy-tampered'
    path.write_text(json.dumps(tampered, sort_keys=True, separators=(',', ':')) + '\n', encoding='utf-8')

    verification = ledger.verify(ledger.read())

    assert verification.status == 'failed'
    assert verification.verified is False
    assert verification.reason_code == 'audit_ledger_entry_digest_mismatch'
    assert verification.blockers == ('audit_ledger_entry_digest_mismatch',)


def test_jsonl_audit_ledger_adapter_detects_deleted_line(tmp_path) -> None:
    path = tmp_path / 'audit-ledger.jsonl'
    ledger = JsonlAuditLedgerAdapter(path)
    first = validate_audit_record({
        'record_id': 'audit-1',
        'record_type': 'admission_decision',
        'subject_ref': 'sha256:runtime-admission',
        'decision_ref': 'runtime-admission-1',
    })
    second = validate_audit_record({
        'record_id': 'audit-2',
        'record_type': 'policy_decision',
        'subject_ref': 'sha256:policy-subject',
        'decision_ref': 'policy-1',
    })

    ledger.append(first, record_digest='sha256:audit-1')
    ledger.append(second, record_digest='sha256:audit-2')
    _, remaining = path.read_text(encoding='utf-8').splitlines()
    path.write_text(remaining + '\n', encoding='utf-8')

    verification = ledger.verify(ledger.read())

    assert verification.status == 'failed'
    assert verification.reason_code == 'audit_ledger_sequence_mismatch'
    assert verification.blockers == ('audit_ledger_sequence_mismatch',)


def test_jsonl_audit_ledger_adapter_rejects_malformed_jsonl(tmp_path) -> None:
    path = tmp_path / 'audit-ledger.jsonl'
    path.write_text('{not-json}\n', encoding='utf-8')
    ledger = JsonlAuditLedgerAdapter(path)

    with pytest.raises(GovApiError, match='invalid_audit_ledger_jsonl:1'):
        ledger.read()


def test_jsonl_audit_ledger_adapter_detects_chain_restart(tmp_path) -> None:
    path = tmp_path / 'audit-ledger.jsonl'
    ledger = JsonlAuditLedgerAdapter(path)
    first = validate_audit_record({
        'record_id': 'audit-1',
        'record_type': 'admission_decision',
        'subject_ref': 'sha256:runtime-admission',
        'decision_ref': 'runtime-admission-1',
    })
    restarted_record = validate_audit_record({
        'record_id': 'audit-2',
        'record_type': 'policy_decision',
        'subject_ref': 'sha256:policy-subject',
        'decision_ref': 'policy-1',
    })

    ledger.append(first, record_digest='sha256:audit-1')
    restarted = AuditLedgerEntry(
        entry_id='audit-ledger-entry-restarted',
        sequence=0,
        record=restarted_record,
        record_digest='sha256:audit-2',
        previous_entry_digest='',
        metadata={'adapter': 'jsonl_hash_chain_dev', 'storage': 'development_only'},
    )
    restarted = AuditLedgerEntry(**{**restarted.as_dict(), 'entry_digest': audit_ledger_entry_digest(restarted)})
    with path.open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(restarted.as_dict(), sort_keys=True, separators=(',', ':')))
        handle.write('\n')

    verification = ledger.verify(ledger.read())

    assert verification.status == 'failed'
    assert verification.reason_code == 'audit_ledger_sequence_mismatch'
    assert verification.blockers == ('audit_ledger_sequence_mismatch',)


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


def test_normalize_admission_artifact_refs_is_deterministic_and_bounded() -> None:
    raw_digest = 'A' * 64

    first = normalize_admission_artifact_refs(
        execution_ticket={
            'raw_payload': {'command': 'must-not-appear'},
            'ticket_id': 'ticket-1',
            'sha256': raw_digest,
        },
        artifact_refs={
            'raw_output': 'full stdout must not be carried',
            'path': 'artifacts/admission.json',
            'admission_digest': 'SHA256:' + ('B' * 64),
        },
    )
    second = normalize_admission_artifact_refs(
        artifact_refs={
            'admission_digest': 'SHA256:' + ('B' * 64),
            'path': 'artifacts/admission.json',
            'raw_output': 'full stdout must not be carried',
        },
        execution_ticket={
            'sha256': raw_digest,
            'ticket_id': 'ticket-1',
            'raw_payload': {'command': 'must-not-appear'},
        },
    )

    assert first == second
    assert first == {
        'execution_ticket': {
            'sha256': 'sha256:' + ('a' * 64),
            'ticket_id': 'ticket-1',
        },
        'explicit': {
            'admission_digest': 'sha256:' + ('b' * 64),
            'path': 'artifacts/admission.json',
        },
    }
    assert 'raw_payload' not in repr(first)
    assert 'raw_output' not in repr(first)
    assert 'command' not in repr(first)


def test_compose_runtime_admission_result_populates_bounded_artifact_refs() -> None:
    result = compose_runtime_admission_result(**_runtime_admission_inputs(
        artifact_refs={
            'raw_output': 'full stdout must not be carried',
            'admission_digest': 'C' * 64,
        },
    ))

    assert result.allowed is True
    assert result.artifact_refs['prepared_execution_contract']['digest'] == 'sha256:contract'
    assert result.artifact_refs['policy_decision']['policy_id'] == 'policy-1'
    assert result.artifact_refs['execution_ticket']['ticket_id'] == 'ticket-1'
    assert result.artifact_refs['execution_ticket']['digest'] == 'sha256:ticket'
    assert result.artifact_refs['trust_decision']['verifier_id'] == 'fixture'
    assert result.artifact_refs['explicit'] == {'admission_digest': 'sha256:' + ('c' * 64)}
    assert 'raw_output' not in repr(result.artifact_refs)


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
    assert result.reason_code == 'policy_denied'
    assert 'policy_denied' in result.blockers


@pytest.mark.parametrize(
    ('policy_decision', 'expected_status', 'expected_blocker', 'expected_action'),
    (
        ({'decision': 'deny', 'policy_id': 'policy-1'}, 'blocked', 'policy_denied', 'revise_request_or_policy'),
        ({'decision': 'defer', 'policy_id': 'policy-1'}, 'needs_review', 'policy_deferred', 'resolve_policy_deferral'),
        (
            {'decision': 'require_approval', 'policy_id': 'policy-1'},
            'needs_review',
            'policy_requires_approval',
            'obtain_operator_approval',
        ),
        (
            {'decision': 'dry_run_only', 'policy_id': 'policy-1'},
            'dry_run_only',
            'policy_dry_run_only',
            'use_dry_run_only_path',
        ),
        (
            {'decision': 'record_only', 'policy_id': 'policy-1'},
            'record_only',
            'policy_record_only',
            'record_without_execution',
        ),
        ({'status': 'maybe', 'policy_id': 'policy-1'}, 'blocked', 'unknown_policy_decision', 'obtain_valid_policy_decision'),
    ),
)
def test_compose_runtime_admission_result_blocks_non_allow_policy_states(
    policy_decision,
    expected_status,
    expected_blocker,
    expected_action,
) -> None:
    result = compose_runtime_admission_result(**_runtime_admission_inputs(policy_decision=policy_decision))

    assert result.allowed is False
    assert result.status == expected_status
    assert result.reason_code == expected_blocker
    assert expected_blocker in result.blockers
    assert expected_action in result.required_next_actions


@pytest.mark.parametrize(
    ('execution_ticket', 'expected_blocker', 'expected_action'),
    (
        (None, 'missing_or_invalid_execution_ticket', 'approve_execution_ticket'),
        (
            {'status': 'invalid', 'ticket_id': 'ticket-1'},
            'invalid_execution_ticket',
            'repair_or_reissue_execution_ticket',
        ),
        (
            {'approval_status': 'unapproved', 'ticket_id': 'ticket-1'},
            'execution_ticket_not_approved',
            'approve_execution_ticket',
        ),
        (
            {'ticket_status': 'mismatch', 'ticket_id': 'ticket-1'},
            'execution_ticket_mismatch',
            'reconcile_execution_ticket_scope',
        ),
        (
            {'status': 'stale', 'ticket_id': 'ticket-1'},
            'execution_ticket_stale',
            'refresh_execution_ticket',
        ),
        (
            {'status': 'failed', 'ticket_id': 'ticket-1'},
            'execution_ticket_failed',
            'revalidate_execution_ticket',
        ),
        (
            {'status': 'maybe', 'ticket_id': 'ticket-1'},
            'unknown_execution_ticket_status',
            'obtain_valid_execution_ticket',
        ),
    ),
)
def test_compose_runtime_admission_result_blocks_invalid_ticket_states(
    execution_ticket,
    expected_blocker,
    expected_action,
) -> None:
    result = compose_runtime_admission_result(**_runtime_admission_inputs(execution_ticket=execution_ticket))

    assert result.allowed is False
    assert result.status == 'blocked'
    assert result.reason_code == expected_blocker
    assert expected_blocker in result.blockers
    assert expected_action in result.required_next_actions


@pytest.mark.parametrize(
    ('trust_decision', 'expected_blocker', 'expected_action'),
    (
        (None, 'missing_or_invalid_trust_decision', 'verify_trust_decision'),
        (
            {'trusted': False, 'verifier_id': 'fixture'},
            'trust_decision_denied',
            'obtain_trusted_verification',
        ),
        (
            {
                'status': 'failed',
                'reason_code': 'signature_value_mismatch',
                'verifier_id': 'fixture',
            },
            'trust_verification_failed',
            'rerun_trust_verification',
        ),
        (
            {
                'status': 'failed',
                'reason_code': 'signature_digest_mismatch',
                'verifier_id': 'fixture',
            },
            'signature_digest_mismatch',
            'rebind_or_reissue_signature',
        ),
        (
            {
                'status': 'failed',
                'reason_code': 'signer_not_allowed',
                'verifier_id': 'fixture',
            },
            'trust_signer_not_allowed',
            'use_allowed_signer_or_update_trust_policy',
        ),
        (
            {'trust_status': 'maybe', 'verifier_id': 'fixture'},
            'unknown_trust_decision_status',
            'obtain_valid_trust_decision',
        ),
    ),
)
def test_compose_runtime_admission_result_blocks_invalid_trust_states(
    trust_decision,
    expected_blocker,
    expected_action,
) -> None:
    result = compose_runtime_admission_result(**_runtime_admission_inputs(trust_decision=trust_decision))

    assert result.allowed is False
    assert result.status == 'blocked'
    assert result.reason_code == expected_blocker
    assert expected_blocker in result.blockers
    assert expected_action in result.required_next_actions


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


@pytest.mark.parametrize('receipt_obligation', (None, {'required': False}, {'status': 'optional'}))
def test_compose_runtime_admission_result_blocks_missing_or_disabled_receipt_obligation(
    receipt_obligation,
) -> None:
    result = compose_runtime_admission_result(**_runtime_admission_inputs(
        receipt_obligation=receipt_obligation,
    ))

    assert result.allowed is False
    assert result.reason_code == 'receipt_obligation_required'
    assert result.blockers == ('receipt_obligation_required',)
    assert result.required_next_actions == ('require_runner_receipt_obligation',)


@pytest.mark.parametrize(
    ('runner_profile', 'expected_blocker', 'expected_action'),
    (
        (None, 'missing_runner_profile', 'select_allowed_runner_profile'),
        ({'name': 'local', 'allowed': False}, 'runner_profile_not_allowed', 'select_allowed_runner_profile'),
    ),
)
def test_compose_runtime_admission_result_blocks_missing_or_disallowed_runner_profile(
    runner_profile,
    expected_blocker,
    expected_action,
) -> None:
    result = compose_runtime_admission_result(**_runtime_admission_inputs(runner_profile=runner_profile))

    assert result.allowed is False
    assert result.reason_code == expected_blocker
    assert expected_blocker in result.blockers
    assert expected_action in result.required_next_actions


def test_compose_runtime_admission_result_keeps_live_disabled_by_default() -> None:
    result = compose_runtime_admission_result(**_runtime_admission_inputs(live=True))

    assert result.allowed is False
    assert result.reason_code == 'live_backend_disabled'
    assert 'live_backend_disabled' in result.blockers
    assert 'use_dry_run_or_select_host_enabled_live_profile' in result.required_next_actions


def test_compose_runtime_admission_result_blocks_live_even_with_complete_guarded_chain_by_default() -> None:
    result = compose_runtime_admission_result(**_runtime_admission_inputs(
        live=True,
        runtime_consumable=True,
        sclite_guarded_strict={'status': 'allowed', 'verification_status': 'passed'},
        replay_freshness={'status': 'allowed', 'replay_status': 'fresh'},
    ))

    assert result.allowed is False
    assert result.reason_code == 'live_backend_disabled'
    assert result.runner_profile['live_backend_enabled'] is False
    assert result.sclite_guarded_strict['verification_status'] == 'passed'
    assert result.replay_freshness['replay_status'] == 'fresh'
    assert result.blockers == ('live_backend_disabled',)
    assert 'missing_or_invalid_kernel_guard' not in result.blockers
    assert 'missing_or_replayed_guarded_root' not in result.blockers
    assert 'use_dry_run_or_select_host_enabled_live_profile' in result.required_next_actions


def _write_runtime_admission(tmp_path, payload: dict) -> Path:
    path = tmp_path / 'runtime-admission.json'
    path.write_text(json.dumps(payload, sort_keys=True), encoding='utf-8')
    return path


def _run_inspect(path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(INSPECT_ADMISSION_SCRIPT), str(path), *args],
        check=False,
        text=True,
        capture_output=True,
    )


def test_inspect_runtime_admission_prints_compact_allowed_output(tmp_path) -> None:
    path = _write_runtime_admission(tmp_path, compose_runtime_admission_result(**_runtime_admission_inputs()).as_dict())

    result = _run_inspect(path)

    assert result.returncode == 0
    assert result.stderr == ''
    assert 'Runtime admission: runtime-admission-composed-1' in result.stdout
    assert 'status: allowed' in result.stdout
    assert 'allowed: true' in result.stdout
    assert 'blockers:\n- none' in result.stdout
    assert 'required_next_actions:\n- none' in result.stdout
    assert 'receipt_obligation: required' in result.stdout
    assert 'execution: not performed' in result.stdout


def test_inspect_runtime_admission_prints_blockers_and_next_actions(tmp_path) -> None:
    admission = compose_runtime_admission_result(**_runtime_admission_inputs(policy_decision=None))
    path = _write_runtime_admission(tmp_path, admission.as_dict())

    result = _run_inspect(path, '--format', 'json')

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload['status'] == 'blocked'
    assert payload['allowed'] is False
    assert payload['reason_code'] == 'missing_or_invalid_policy_decision'
    assert payload['blockers'] == ['missing_or_invalid_policy_decision']
    assert 'obtain_policy_decision' in payload['required_next_actions']
    assert payload['execution'] == 'not performed'


def test_inspect_runtime_admission_fails_closed_for_malformed_input(tmp_path) -> None:
    path = tmp_path / 'runtime-admission.json'
    path.write_text('{not-json', encoding='utf-8')

    result = _run_inspect(path)

    assert result.returncode == 2
    assert result.stdout == ''
    assert 'runtime_admission_inspect_error: runtime_admission_json_invalid' in result.stderr


def test_inspect_runtime_admission_rejects_forbidden_raw_runtime_data(tmp_path) -> None:
    payload = compose_runtime_admission_result(**_runtime_admission_inputs()).as_dict()
    payload['metadata'] = {'raw_output': 'do-not-print'}
    path = _write_runtime_admission(tmp_path, payload)

    result = _run_inspect(path)

    assert result.returncode == 2
    assert result.stdout == ''
    assert 'runtime_admission_inspect_error: forbidden_admission_metadata:raw_output' in result.stderr
    assert 'do-not-print' not in result.stderr
