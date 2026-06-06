from __future__ import annotations

import pytest

from govengine.api import GovApiError
from govengine.execution.runner_protocol import (
    GovRunnerReceipt,
    GovRunnerReceiptBinding,
    GovRunnerStepResult,
    dry_run_runner_receipt,
    runner_request_from_approved_spec,
)
from govengine.execution.supervision import (
    GovRunnerLease,
    GovSupervisionPlan,
    runner_lease_from_request,
    supervision_plan_from_runner_request,
    validate_runner_receipt_for_request,
    validate_supervised_runner_request,
    validate_supervision_plan,
)


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


def test_supervision_plan_and_lease_validate_dry_run_runner_request() -> None:
    request = runner_request_from_approved_spec(_approved_spec(), request_id='run-1', dry_run=True)
    plan = supervision_plan_from_runner_request(
        request,
        timeout_seconds=15,
        cwd_policy='none',
        env_policy='empty',
        stdin_policy='bounded',
        metadata={'source': 'fixture'},
    )
    lease = runner_lease_from_request(request, expires_at='2026-05-20T16:00:00Z')
    receipt = dry_run_runner_receipt(request)

    assert isinstance(plan, GovSupervisionPlan)
    assert isinstance(lease, GovRunnerLease)
    assert validate_supervised_runner_request(request, plan) is request
    assert validate_runner_receipt_for_request(request, receipt).status == 'dry-run'
    assert plan.as_dict()['receipt_required'] is True


def test_supervision_rejects_raw_intent_request_and_missing_approved_spec() -> None:
    request = runner_request_from_approved_spec(_approved_spec(), request_id='run-1', dry_run=True)
    raw_intent = type(request)(
        request_id='run-raw',
        source='raw_intent',
        steps=request.steps,
        approved_execution_spec={},
        dry_run=True,
    )
    plan = supervision_plan_from_runner_request(request)

    with pytest.raises(GovApiError, match='raw_intent_runner_request_not_allowed'):
        validate_supervised_runner_request(raw_intent, type(plan)(**{**plan.as_dict(), 'request_id': 'run-raw', 'plan_id': 'raw-plan'}))

    missing_spec = type(request)(
        request_id='run-1',
        source='approved_execution_spec',
        steps=request.steps,
        approved_execution_spec={},
        dry_run=True,
    )
    with pytest.raises(GovApiError, match='missing_approved_execution_spec'):
        validate_supervised_runner_request(missing_spec, plan)


def test_supervision_requires_receipts_and_blocks_live_backend_by_default() -> None:
    dry_request = runner_request_from_approved_spec(_approved_spec(), request_id='run-1', dry_run=True)
    live_request = runner_request_from_approved_spec(_approved_spec(), request_id='run-live', dry_run=False)

    with pytest.raises(GovApiError, match='missing_runner_receipt'):
        validate_runner_receipt_for_request(dry_request, None)

    with pytest.raises(GovApiError, match='live_backend_disabled'):
        supervision_plan_from_runner_request(live_request)

    with pytest.raises(GovApiError, match='runner_receipt_required'):
        validate_supervision_plan({
            'plan_id': 'bad-plan',
            'request_id': 'run-1',
            'receipt_required': False,
        })


def test_supervision_receipt_must_match_request_steps() -> None:
    request = runner_request_from_approved_spec(_approved_spec(), request_id='run-1', dry_run=True)
    receipt = GovRunnerReceipt(
        status='dry-run',
        request_id='run-1',
        source='approved_execution_spec',
        step_results=(GovRunnerStepResult(index=99, status='dry-run'),),
    )

    with pytest.raises(GovApiError, match='runner_receipt_step_mismatch'):
        validate_runner_receipt_for_request(request, receipt)


def test_supervision_preserves_receipt_binding_from_mapping() -> None:
    request = runner_request_from_approved_spec(_approved_spec(), request_id='run-bound', dry_run=True)
    receipt = validate_runner_receipt_for_request(request, {
        'status': 'dry-run',
        'request_id': 'run-bound',
        'source': 'approved_execution_spec',
        'reason_code': 'dry_run_requested',
        'step_results': [{'index': 0, 'status': 'dry-run'}],
        'binding': {
            'admission_id': 'admission-1',
            'admission_digest': 'sha256:admission',
            'ticket_id': 'ticket-1',
            'ticket_digest': 'sha256:ticket',
            'request_id': 'run-bound',
            'receipt_id': 'receipt-1',
        },
    })

    assert isinstance(receipt.binding, GovRunnerReceiptBinding)
    assert receipt.as_dict()['binding']['admission_id'] == 'admission-1'
    assert receipt.as_dict()['binding']['ticket_id'] == 'ticket-1'


def test_supervision_rejects_receipt_binding_request_mismatch() -> None:
    request = runner_request_from_approved_spec(_approved_spec(), request_id='run-bound', dry_run=True)

    with pytest.raises(GovApiError, match='runner_receipt_binding_request_mismatch'):
        validate_runner_receipt_for_request(request, {
            'status': 'dry-run',
            'request_id': 'run-bound',
            'source': 'approved_execution_spec',
            'reason_code': 'dry_run_requested',
            'step_results': [{'index': 0, 'status': 'dry-run'}],
            'binding': {
                'admission_id': 'admission-1',
                'ticket_id': 'ticket-1',
                'request_id': 'wrong-request',
            },
        })


def test_supervision_rejects_forbidden_metadata_claims() -> None:
    request = runner_request_from_approved_spec(_approved_spec(), request_id='run-1', dry_run=True)

    with pytest.raises(GovApiError, match='forbidden_supervision_metadata:prompt'):
        supervision_plan_from_runner_request(request, metadata={'prompt': 'run this'})

    with pytest.raises(GovApiError, match='forbidden_supervision_metadata:storage_path'):
        runner_lease_from_request(request, metadata={'storage_path': '/tmp/lease.db'})
