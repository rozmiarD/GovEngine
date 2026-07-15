from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from govengine import (
    JsonlAuditLedgerAdapter,
    RuntimeAdmissionResult,
    govengine_record_digest,
    validate_audit_record,
)
from govengine.execution.runner_protocol import (
    dry_run_runner_receipt,
    runner_receipt_with_binding,
    runner_request_digest,
    runner_request_from_approved_spec,
)


ROOT = Path(__file__).resolve().parents[1]
RECEIPT_SCRIPT = ROOT / 'scripts' / 'verify_runner_receipt_binding.py'
LEDGER_SCRIPT = ROOT / 'scripts' / 'verify_audit_ledger.py'
ADMISSION_DIGEST = 'sha256:' + 'a' * 64
TICKET_DIGEST = 'sha256:' + 'b' * 64


def _audit_record_digest(record) -> str:
    return govengine_record_digest(record, record_type='govengine.admission.GovAuditRecord')


def _approved_spec() -> dict:
    return {
        'spec_version': '2026-03-18.approved.v1',
        'action_type': 'single_probe',
        'capability': 'http_probe',
        'resolved_tool': 'curl',
        'execution_mode': 'normalized',
        'approval': {'decision': 'approve', 'reason': 'ok'},
        'execution_truth': {
            'artifact_type': 'approved_execution_spec',
            'execution_plan': [{'tool': 'curl', 'args': ['https://example.com/']}],
        },
    }


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, sort_keys=True, separators=(',', ':')), encoding='utf-8')


def _runtime_admission() -> RuntimeAdmissionResult:
    return RuntimeAdmissionResult.from_mapping({
        'admission_id': 'admission-1',
        'subject_ref': 'sha256:prepared-contract',
        'status': 'allowed',
        'allowed': True,
        'reason_code': 'all_required_gates_passed',
        'prepared_execution_contract': {'status': 'prepared', 'digest': 'sha256:contract'},
        'policy_decision': {'decision': 'allow', 'policy_id': 'policy-1'},
        'execution_ticket': {'status': 'passed', 'ticket_id': 'ticket-1', 'digest': TICKET_DIGEST},
        'trust_decision': {'status': 'passed', 'trust_status': 'trusted'},
        'sclite_guarded_strict': {'status': 'passed', 'required': True},
        'replay_freshness': {'status': 'allowed', 'replay_status': 'fresh'},
        'runner_profile': {'profile': 'dry_run', 'mode': 'dry_run'},
        'receipt_obligation': {'required': True, 'binds': ['admission', 'ticket']},
    })


def test_runner_receipt_binding_script_verifies_bounded_refs(tmp_path: Path) -> None:
    request = runner_request_from_approved_spec(_approved_spec(), request_id='run-bound', dry_run=True)
    admission = _runtime_admission()
    admission_digest = govengine_record_digest(admission.as_dict(), record_type='govengine.admission.RuntimeAdmissionResult')
    receipt = runner_receipt_with_binding(
        dry_run_runner_receipt(request),
        admission_id=admission.admission_id,
        admission_digest=admission_digest,
        ticket_id='ticket-1',
        ticket_digest=TICKET_DIGEST,
        request_digest=runner_request_digest(request),
        receipt_id='receipt-1',
        runner_profile='dry-run',
    )
    request_path = tmp_path / 'request.json'
    receipt_path = tmp_path / 'receipt.json'
    admission_path = tmp_path / 'admission.json'
    _write_json(request_path, request.as_dict())
    _write_json(receipt_path, receipt.as_dict())
    _write_json(admission_path, admission.as_dict())

    proc = subprocess.run(
        [
            sys.executable,
            str(RECEIPT_SCRIPT),
            '--request',
            str(request_path),
            '--receipt',
            str(receipt_path),
            '--admission',
            str(admission_path),
            '--ticket-id',
            'ticket-1',
            '--ticket-digest',
            TICKET_DIGEST,
            '--format',
            'json',
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    data = json.loads(proc.stdout)
    assert proc.returncode == 0
    assert data['status'] == 'verified'
    assert data['verified'] is True
    assert data['request_id'] == 'run-bound'
    assert data['admission_id'] == 'admission-1'
    assert data['ticket_id'] == 'ticket-1'
    assert data['execution'] == 'not performed'
    assert 'step_results' not in data


def test_runner_receipt_binding_script_blocks_tampered_receipt(tmp_path: Path) -> None:
    request = runner_request_from_approved_spec(_approved_spec(), request_id='run-bound', dry_run=True)
    receipt = runner_receipt_with_binding(
        dry_run_runner_receipt(request),
        admission_id='admission-1',
        admission_digest=ADMISSION_DIGEST,
        ticket_id='ticket-1',
        ticket_digest=TICKET_DIGEST,
        request_digest=runner_request_digest(request),
        receipt_id='receipt-1',
        runner_profile='dry-run',
    ).as_dict()
    receipt['binding']['request_digest'] = 'sha256:' + 'c' * 64
    request_path = tmp_path / 'request.json'
    receipt_path = tmp_path / 'receipt.json'
    _write_json(request_path, request.as_dict())
    _write_json(receipt_path, receipt)

    proc = subprocess.run(
        [
            sys.executable,
            str(RECEIPT_SCRIPT),
            '--request',
            str(request_path),
            '--receipt',
            str(receipt_path),
            '--admission-id',
            'admission-1',
            '--admission-digest',
            ADMISSION_DIGEST,
            '--ticket-id',
            'ticket-1',
            '--ticket-digest',
            TICKET_DIGEST,
            '--format',
            'json',
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    data = json.loads(proc.stdout)
    assert proc.returncode == 1
    assert data['status'] == 'failed'
    assert data['verified'] is False
    assert data['reason_code'] == 'runner_receipt_binding_request_digest_mismatch'
    assert data['execution'] == 'not performed'


def test_audit_ledger_script_verifies_valid_jsonl_without_raw_records(tmp_path: Path) -> None:
    path = tmp_path / 'audit-ledger.jsonl'
    ledger = JsonlAuditLedgerAdapter(path)
    record = validate_audit_record({
        'record_id': 'audit-1',
        'record_type': 'admission_decision',
        'subject_ref': 'sha256:runtime-admission',
        'decision_ref': 'runtime-admission-1',
    })
    ledger.append(record, record_digest=_audit_record_digest(record))

    proc = subprocess.run(
        [sys.executable, str(LEDGER_SCRIPT), str(path), '--format', 'json'],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    data = json.loads(proc.stdout)
    assert proc.returncode == 0
    assert data['status'] == 'verified'
    assert data['verified'] is True
    assert data['checked_entries'] == 1
    assert data['last_entry_id'] == 'audit-ledger-entry-1'
    assert data['writes'] == 'none'
    assert 'record' not in data


def test_audit_ledger_script_blocks_tampered_jsonl(tmp_path: Path) -> None:
    path = tmp_path / 'audit-ledger.jsonl'
    ledger = JsonlAuditLedgerAdapter(path)
    record = validate_audit_record({
        'record_id': 'audit-1',
        'record_type': 'policy_decision',
        'subject_ref': 'sha256:policy-subject',
        'decision_ref': 'policy-1',
    })
    ledger.append(record, record_digest=_audit_record_digest(record))
    [line] = path.read_text(encoding='utf-8').splitlines()
    tampered = json.loads(line)
    tampered['record']['decision_ref'] = 'policy-tampered'
    path.write_text(json.dumps(tampered, sort_keys=True, separators=(',', ':')) + '\n', encoding='utf-8')

    proc = subprocess.run(
        [sys.executable, str(LEDGER_SCRIPT), str(path), '--format', 'json'],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    data = json.loads(proc.stdout)
    assert proc.returncode == 1
    assert data['status'] == 'failed'
    assert data['verified'] is False
    assert data['reason_code'] == 'audit_ledger_record_digest_mismatch'
    assert data['blockers'] == ['audit_ledger_record_digest_mismatch']


def test_audit_ledger_script_fails_closed_on_malformed_jsonl(tmp_path: Path) -> None:
    path = tmp_path / 'audit-ledger.jsonl'
    path.write_text('{not-json}\n', encoding='utf-8')

    proc = subprocess.run(
        [sys.executable, str(LEDGER_SCRIPT), str(path), '--format', 'json'],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    data = json.loads(proc.stdout)
    assert proc.returncode == 1
    assert data['status'] == 'failed'
    assert data['reason_code'] == 'invalid_audit_ledger_jsonl'
    assert data['context'] == {'detail': '1'}


def test_audit_ledger_script_reports_deleted_line_as_blocked(tmp_path: Path) -> None:
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
    ledger.append(first, record_digest=_audit_record_digest(first))
    ledger.append(second, record_digest=_audit_record_digest(second))
    _, remaining = path.read_text(encoding='utf-8').splitlines()
    path.write_text(remaining + '\n', encoding='utf-8')

    proc = subprocess.run(
        [sys.executable, str(LEDGER_SCRIPT), str(path), '--format', 'json'],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    data = json.loads(proc.stdout)
    assert proc.returncode == 1
    assert data['reason_code'] == 'audit_ledger_sequence_mismatch'
    assert data['writes'] == 'none'
