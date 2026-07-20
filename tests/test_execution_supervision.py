from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from govengine.api import GovApiError
from govengine.execution.runner_protocol import (
    GovRunnerReceipt,
    GovRunnerReceiptBinding,
    GovRunnerStepResult,
    dry_run_runner_receipt,
    runner_receipt_with_binding,
    runner_request_digest,
    runner_request_from_approved_spec,
)
from govengine.signing import govengine_record_digest
from govengine.execution.supervision import (
    GovRunnerLease,
    GovSupervisionPlan,
    LOCAL_SUBPROCESS_RUNNER_REQUIRED_PREREQUISITES,
    LocalSubprocessRunnerReadiness,
    evaluate_local_subprocess_runner_readiness,
    runner_lease_from_request,
    supervision_plan_from_runner_request,
    validate_runner_receipt_binding,
    validate_runner_receipt_for_request,
    validate_supervised_runner_request,
    validate_supervision_plan,
)


ADMISSION_DIGEST = 'sha256:' + 'a' * 64
TICKET_DIGEST = 'sha256:' + 'b' * 64


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


def _bound_receipt(request):
    return runner_receipt_with_binding(
        dry_run_runner_receipt(request),
        admission_id='admission-1',
        admission_digest=ADMISSION_DIGEST,
        ticket_id='ticket-1',
        ticket_digest=TICKET_DIGEST,
        request_digest=runner_request_digest(request),
        receipt_id='receipt-1',
        runner_profile='dry-run',
    )


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


def test_supervision_live_request_requires_explicit_backend_enablement() -> None:
    live_request = runner_request_from_approved_spec(_approved_spec(), request_id='run-live', dry_run=False)

    with pytest.raises(GovApiError, match='live_backend_disabled'):
        supervision_plan_from_runner_request(
            live_request,
            timeout_seconds=20,
            cwd_policy='repo_root',
            env_policy='allowlist',
        )

    plan = supervision_plan_from_runner_request(
        live_request,
        runner_profile='local-live',
        live_backend_enabled=True,
        timeout_seconds=20,
        cwd_policy='repo_root',
        env_policy='allowlist',
        stdin_policy='bounded',
    )

    assert plan.dry_run is False
    assert plan.live_backend_enabled is True
    assert plan.receipt_required is True
    assert validate_supervised_runner_request(live_request, plan) is live_request


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


def test_supervision_validates_receipt_binding_chain() -> None:
    request = runner_request_from_approved_spec(_approved_spec(), request_id='run-bound', dry_run=True)
    receipt = _bound_receipt(request)

    validated = validate_runner_receipt_binding(
        request,
        receipt,
        admission_id='admission-1',
        admission_digest=ADMISSION_DIGEST,
        ticket={'ticket_id': 'ticket-1', 'digest': TICKET_DIGEST},
    )

    assert validated is receipt
    assert validated.binding.receipt_digest.startswith('sha256:')


def test_supervision_validates_receipt_binding_from_mapping() -> None:
    request = runner_request_from_approved_spec(_approved_spec(), request_id='run-bound', dry_run=True)
    receipt = _bound_receipt(request)

    validated = validate_runner_receipt_binding(
        request,
        receipt.as_dict(),
        admission_id='admission-1',
        admission_digest=ADMISSION_DIGEST,
        ticket_id='ticket-1',
        ticket_digest=TICKET_DIGEST,
    )

    assert validated.binding.receipt_digest == receipt.binding.receipt_digest


def test_supervision_receipt_binding_requires_admission_and_ticket_refs() -> None:
    request = runner_request_from_approved_spec(_approved_spec(), request_id='run-bound', dry_run=True)
    receipt = _bound_receipt(request)

    with pytest.raises(GovApiError, match='missing_runner_receipt_binding_admission_id'):
        validate_runner_receipt_binding(request, replace(receipt, binding=replace(receipt.binding, admission_id='')))

    with pytest.raises(GovApiError, match='missing_runner_receipt_binding_ticket_digest'):
        validate_runner_receipt_binding(request, replace(receipt, binding=replace(receipt.binding, ticket_digest='')))


def test_supervision_receipt_binding_rejects_wrong_digest_refs() -> None:
    request = runner_request_from_approved_spec(_approved_spec(), request_id='run-bound', dry_run=True)
    receipt = _bound_receipt(request)

    with pytest.raises(GovApiError, match='runner_receipt_binding_admission_digest_mismatch'):
        validate_runner_receipt_binding(
            request,
            receipt,
            admission_digest='sha256:' + 'c' * 64,
            ticket_digest=TICKET_DIGEST,
        )

    with pytest.raises(GovApiError, match='runner_receipt_binding_ticket_digest_mismatch'):
        validate_runner_receipt_binding(
            request,
            receipt,
            admission_digest=ADMISSION_DIGEST,
            ticket_digest='sha256:' + 'd' * 64,
        )

    with pytest.raises(GovApiError, match='runner_receipt_binding_request_digest_mismatch'):
        validate_runner_receipt_binding(
            request,
            replace(receipt, binding=replace(receipt.binding, request_digest='sha256:' + 'e' * 64)),
            admission_digest=ADMISSION_DIGEST,
            ticket_digest=TICKET_DIGEST,
        )

    with pytest.raises(GovApiError, match='runner_receipt_binding_receipt_digest_mismatch'):
        validate_runner_receipt_binding(
            request,
            replace(receipt, binding=replace(receipt.binding, receipt_digest='sha256:' + 'f' * 64)),
            admission_digest=ADMISSION_DIGEST,
            ticket_digest=TICKET_DIGEST,
        )


def test_supervision_recomputes_owned_request_and_receipt_digests() -> None:
    request = runner_request_from_approved_spec(_approved_spec(), request_id='run-bound', dry_run=True)
    receipt = _bound_receipt(request)
    mutated_request = replace(request, approved_execution_spec={**request.approved_execution_spec, 'capability': 'tampered'})
    mutated_receipt = replace(receipt, step_results=())

    with pytest.raises(GovApiError, match='runner_request_digest_mismatch'):
        validate_runner_receipt_binding(
            mutated_request,
            receipt,
            admission_digest=ADMISSION_DIGEST,
            ticket_digest=TICKET_DIGEST,
            request_digest=receipt.binding.request_digest,
        )

    with pytest.raises(GovApiError, match='runner_receipt_digest_mismatch'):
        validate_runner_receipt_binding(
            request,
            mutated_receipt,
            admission_digest=ADMISSION_DIGEST,
            ticket_digest=TICKET_DIGEST,
            receipt_digest=receipt.binding.receipt_digest,
        )


def test_supervision_recomputes_owned_admission_digest() -> None:
    request = runner_request_from_approved_spec(_approved_spec(), request_id='run-bound', dry_run=True)
    admission = {'admission_id': 'admission-1', 'status': 'allowed'}
    admission_digest = govengine_record_digest(
        admission,
        record_type='govengine.admission.RuntimeAdmissionResult',
    )
    receipt = runner_receipt_with_binding(
        dry_run_runner_receipt(request),
        admission_id='admission-1',
        admission_digest=admission_digest,
        ticket_id='ticket-1',
        ticket_digest=TICKET_DIGEST,
        request_digest=runner_request_digest(request),
        receipt_id='receipt-1',
    )

    with pytest.raises(GovApiError, match='runtime_admission_digest_mismatch'):
        validate_runner_receipt_binding(
            request,
            receipt,
            admission={**admission, 'status': 'blocked'},
            admission_digest=admission_digest,
            ticket_digest=TICKET_DIGEST,
        )


def test_supervision_receipt_binding_rejects_mutated_status_and_missing_receipt_digest() -> None:
    request = runner_request_from_approved_spec(_approved_spec(), request_id='run-bound', dry_run=True)
    receipt = _bound_receipt(request)

    with pytest.raises(GovApiError, match='runner_receipt_binding_status_mismatch'):
        validate_runner_receipt_binding(
            request,
            replace(receipt, status='succeeded'),
            admission_digest=ADMISSION_DIGEST,
            ticket_digest=TICKET_DIGEST,
        )

    with pytest.raises(GovApiError, match='missing_runner_receipt_binding_receipt_digest'):
        validate_runner_receipt_binding(
            request,
            replace(receipt, binding=replace(receipt.binding, receipt_digest='')),
            admission_digest=ADMISSION_DIGEST,
            ticket_digest=TICKET_DIGEST,
        )


def test_supervision_rejects_forbidden_metadata_claims() -> None:
    request = runner_request_from_approved_spec(_approved_spec(), request_id='run-1', dry_run=True)

    with pytest.raises(GovApiError, match='forbidden_supervision_metadata:prompt'):
        supervision_plan_from_runner_request(request, metadata={'prompt': 'run this'})

    with pytest.raises(GovApiError, match='forbidden_supervision_metadata:storage_path'):
        runner_lease_from_request(request, metadata={'storage_path': '/tmp/lease.db'})


def test_local_subprocess_runner_readiness_is_not_applicable_by_default() -> None:
    readiness = evaluate_local_subprocess_runner_readiness()

    assert isinstance(readiness, LocalSubprocessRunnerReadiness)
    assert readiness.status == 'not_applicable'
    assert readiness.ready is False
    assert readiness.reason_code == 'local_subprocess_runner_prerequisites_incomplete'
    assert readiness.missing_prerequisites == (
        'live_runner_profile_enabled',
        'cwd_allowlist_enforced',
        'env_allowlist_enforced',
        'max_output_enforced',
        'output_digests_recorded',
        'redaction_policy_available',
    )
    assert 'missing:redaction_policy_available' in readiness.blockers
    assert 'keep_dry_run_runner_default' in readiness.required_next_actions
    assert 'no_subprocess_backend' in readiness.non_claims
    assert 'docs/RUNNER_SUPERVISION.md#live-runner-safety-specification' in readiness.evidence_refs


def test_local_subprocess_runner_readiness_can_only_be_ready_when_all_prerequisites_are_satisfied() -> None:
    readiness = evaluate_local_subprocess_runner_readiness(
        satisfied_prerequisites=LOCAL_SUBPROCESS_RUNNER_REQUIRED_PREREQUISITES,
        evidence_refs=('tests/fixture',),
    )

    assert readiness.status == 'ready'
    assert readiness.ready is True
    assert readiness.reason_code == 'local_subprocess_runner_prerequisites_satisfied'
    assert readiness.missing_prerequisites == ()
    assert readiness.blockers == ()
    assert readiness.evidence_refs == ('tests/fixture',)


def test_local_subprocess_runner_readiness_is_exported_from_top_level_package() -> None:
    import govengine

    readiness = govengine.evaluate_local_subprocess_runner_readiness()

    assert isinstance(readiness, govengine.LocalSubprocessRunnerReadiness)
    assert readiness.ready is False
    assert 'LocalSubprocessRunnerReadiness' in govengine.__all__
    assert 'evaluate_local_subprocess_runner_readiness' in govengine.__all__


def test_local_subprocess_runner_is_not_exported_when_readiness_is_not_applicable() -> None:
    import govengine

    readiness = govengine.evaluate_local_subprocess_runner_readiness()

    assert readiness.status == 'not_applicable'
    assert not hasattr(govengine, 'LocalSubprocessRunner')
    assert 'LocalSubprocessRunner' not in govengine.__all__


def test_runner_supervision_docs_define_live_runner_safety_spec() -> None:
    text = Path('docs/RUNNER_SUPERVISION.md').read_text(encoding='utf-8')
    section = ' '.join(text.split('## Live Runner Safety Specification', 1)[1].split())

    required_markers = (
        'does not provide a live subprocess runner',
        'not implementation permission',
        'Runtime admission is allowed',
        'valid policy decision',
        'approved execution ticket',
        'guarded-strict SCLite verification',
        'fresh replay state',
        'valid trust decision',
        'explicit receipt obligation',
        'dry-run remains the default profile',
        'argv-only step shapes',
        'Shell strings',
        'allowlist policy',
        'must not inherit the ambient process environment',
        'positive timeout',
        'Bounded stdout/stderr capture',
        'digests',
        'redaction hook',
        'receipt is always emitted',
        'blocked, timed out, interrupted, failed, and dry-run outcomes',
        'SCLite remains the proof/review artifact authority',
        'host-owned',
    )

    for marker in required_markers:
        assert marker in section


def test_runner_supervision_docs_record_local_runner_readiness_decision() -> None:
    text = Path('docs/RUNNER_SUPERVISION.md').read_text(encoding='utf-8')
    section = ' '.join(text.split('## Local Subprocess Runner Readiness', 1)[1].split())

    required_markers = (
        'evaluate_local_subprocess_runner_readiness()',
        'not_applicable',
        'does not grant execution authority',
        'host-owned live runner profile authorization policy',
        'enforced cwd allowlist semantics',
        'enforced environment allowlist semantics',
        'maximum-output enforcement',
        'redaction policy/hook',
        'GE-032 must not add a live subprocess backend',
        'DryRunRunner',
    )

    for marker in required_markers:
        assert marker in section


def test_unsafe_local_runner_negative_cases_are_not_applicable_without_runner() -> None:
    import govengine

    readiness = govengine.evaluate_local_subprocess_runner_readiness()
    missing = set(readiness.missing_prerequisites)
    unsafe_cases = {
        'shell_string_execution': 'no_subprocess_backend',
        'out_of_scope_cwd': 'cwd_allowlist_enforced',
        'unallowlisted_env': 'env_allowlist_enforced',
        'missing_timeout': 'positive_timeout_required',
        'max_output_bypass': 'max_output_enforced',
        'unredacted_output_excerpt': 'redaction_policy_available',
        'missing_live_receipt': 'bounded_receipt_for_all_outcomes',
    }

    assert readiness.status == 'not_applicable'
    assert not hasattr(govengine, 'LocalSubprocessRunner')
    assert unsafe_cases['shell_string_execution'] in readiness.non_claims
    assert unsafe_cases['out_of_scope_cwd'] in missing
    assert unsafe_cases['unallowlisted_env'] in missing
    assert unsafe_cases['max_output_bypass'] in missing
    assert unsafe_cases['unredacted_output_excerpt'] in missing
    assert unsafe_cases['missing_timeout'] not in missing
    assert unsafe_cases['missing_live_receipt'] not in missing
