from __future__ import annotations

import importlib


def test_public_modules_import() -> None:
    modules = [
        'govengine',
        'govengine.api',
        'govengine.boundary',
        'govengine.context',
        'govengine.core',
        'govengine.deconfliction',
        'govengine.lifecycle',
        'govengine.scope_ports',
        'govengine.state_store',
        'govengine.roles',
        'govengine.execution_backend',
        'govengine.sclite_contracts',
        'govengine.signing',
        'govengine.replay',
        'govengine.state_index',
        'govengine.state_machine',
        'govengine.contracts.execution',
        'govengine.execution.approved_spec',
        'govengine.execution.command_shape',
        'govengine.execution.gate',
        'govengine.execution.runner',
        'govengine.execution.runner_protocol',
        'govengine.execution.ticket_gate',
        'govengine.ooda',
        'govengine.orchestration',
        'govengine.planning',
        'govengine.policy',
        'govengine.policy.compiler',
        'govengine.policy.model',
        'govengine.policy.runtime',
        'govengine.policy.explain',
        'govengine.policy.baselines',
        'govengine.policy.schema',
        'govengine.policy.authoring',
        'govengine.policy.cli',
        'govengine.events',
        'govengine.control',
        'govengine.runtime_shell',
        'govengine.triggers',
        'govengine.supervisor_actions',
    ]
    for module in modules:
        importlib.import_module(module)


def test_standalone_approved_spec_dry_run_helper() -> None:
    from govengine.execution.runner import approved_spec_dry_run_result

    result = approved_spec_dry_run_result(
        approved_execution_spec={
            'action_type': 'bounded_request',
            'capability': 'fixture_review',
            'resolved_tool': 'fixture',
            'execution_mode': 'dry_run',
        },
        planned_commands=[['fixture', 'review']],
    )
    assert result['status'] == 'dry-run'
    assert result['execution_source'] == 'approved_execution_spec'


def test_neutral_scope_port_helpers_are_local() -> None:
    from govengine.scope_ports import FunctionalScopePort, extract_host_from_url

    assert extract_host_from_url('https://example.com/path') == 'example.com'
    port = FunctionalScopePort(extract_host_from_url, lambda host, domains: host in domains)
    assert port.host_in_scope('example.com', {'example.com'})
    assert not port.host_in_scope('evil.example.com', {'example.com'})


def test_host_compat_context_keeps_ravenclaw_alias_compatible(tmp_path) -> None:
    from govengine import host_compat_context, ravenclaw_context

    host = host_compat_context(tmp_path)
    ravenclaw = ravenclaw_context(tmp_path)

    assert host.repo_root == ravenclaw.repo_root == tmp_path.resolve()
    assert host.profile == 'host_compat'
    assert ravenclaw.profile == 'ravenclaw'


def test_runtime_admission_public_surface_smoke() -> None:
    from govengine import RuntimeAdmissionResult, normalize_admission_artifact_refs

    refs = normalize_admission_artifact_refs(
        execution_ticket={'ticket_id': 'ticket-1', 'sha256': 'A' * 64},
        artifact_refs={'raw_output': 'must stay out', 'admission_digest': 'B' * 64},
    )
    result = RuntimeAdmissionResult(
        admission_id='admission-1',
        subject_ref='sha256:subject',
        status='allowed',
        allowed=True,
        reason_code='all_required_gates_passed',
        artifact_refs=refs,
    )

    assert refs['execution_ticket']['sha256'] == 'sha256:' + ('a' * 64)
    assert refs['explicit']['admission_digest'] == 'sha256:' + ('b' * 64)
    assert 'raw_output' not in repr(result.as_dict()['artifact_refs'])


def test_end_to_end_governed_runtime_smoke_binds_admission_receipt_and_evidence() -> None:
    from govengine import compose_runtime_admission_result, govengine_record_digest, validate_evidence_review_chain
    from govengine.execution.runner_protocol import (
        dry_run_runner_receipt,
        runner_receipt_with_binding,
        runner_request_digest,
        runner_request_from_approved_spec,
        validate_runner_receipt_binding,
    )

    intent = {
        'intent_id': 'intent-ge-038',
        'subject_ref': 'artifact://intent/ge-038',
        'runtime_consumable': True,
    }
    ticket = {
        'status': 'passed',
        'ticket_id': 'ticket-ge-038',
        'digest': 'sha256:' + ('1' * 64),
    }
    admission = compose_runtime_admission_result(
        admission_id='admission-ge-038',
        subject_ref=intent['subject_ref'],
        prepared_execution_contract={'status': 'prepared', 'digest': 'sha256:' + ('2' * 64)},
        policy_decision={'decision': 'allow', 'policy_id': 'policy-ge-038'},
        execution_ticket=ticket,
        trust_decision={'status': 'passed', 'trust_status': 'trusted', 'verifier_id': 'host-fixture'},
        sclite_guarded_strict={
            'verification_status': 'passed',
            'replay_status': 'fresh',
            'guarded': True,
            'strict_lifecycle': True,
            'ticket_id': ticket['ticket_id'],
            'root_chain_digest': 'sha256:' + ('3' * 64),
        },
        replay_freshness={'replay_status': 'fresh', 'artifact_ref': 'artifact://sclite/guard/ge-038'},
        runtime_consumable=True,
        runner_profile={'name': 'dry-run', 'allowed': True, 'live_backend_enabled': False},
        receipt_obligation={'required': True, 'binds': ['admission', 'ticket']},
    )
    approved_spec = {
        'spec_version': '2026-03-18.approved.v1',
        'action_type': 'inspect_only',
        'capability': 'runtime_admission_smoke',
        'resolved_tool': 'govengine-inspect',
        'execution_mode': 'dry_run',
        'approval': {'decision': 'approve', 'reason': 'fixture-only dry-run smoke'},
        'execution_truth': {
            'artifact_type': 'approved_execution_spec',
            'execution_plan': [{'tool': 'govengine-inspect', 'args': ['artifact://admission/ge-038']}],
        },
    }

    request = runner_request_from_approved_spec(
        approved_spec,
        request_id='request-ge-038',
        execution_ticket_gate=ticket,
        dry_run=True,
    )
    admission_digest = govengine_record_digest(admission, record_type='govengine.admission.RuntimeAdmissionResult')
    request_digest = runner_request_digest(request)
    receipt = runner_receipt_with_binding(
        dry_run_runner_receipt(request),
        admission_id=admission.admission_id,
        admission_digest=admission_digest,
        ticket_id=ticket['ticket_id'],
        ticket_digest=ticket['digest'],
        request_digest=request_digest,
        receipt_id='receipt-ge-038',
        runner_profile='dry-run',
        output_digests={'stdout': 'sha256:' + ('0' * 64), 'stderr': 'sha256:' + ('0' * 64)},
        evidence_refs={'review': 'artifact://review/ge-038'},
    )
    bound_receipt = validate_runner_receipt_binding(request, receipt, admission=admission, ticket=ticket)
    qualification = validate_evidence_review_chain(
        {
            'claim_id': 'claim-ge-038',
            'subject_ref': admission_digest,
            'claim_type': 'execution_truth',
            'receipt_refs': [receipt.binding.receipt_id],
            'evidence_refs': ['artifact://evidence/ge-038'],
            'metadata': {
                'admission_id': admission.admission_id,
                'admission_digest': admission_digest,
                'receipt_digest': receipt.binding.receipt_digest,
            },
        },
        {
            'requirement_id': 'req-ge-038',
            'subject_ref': admission_digest,
            'min_receipt_status': 'dry-run',
        },
        receipt_id=receipt.binding.receipt_id,
        receipt_digest=receipt.binding.receipt_digest,
        receipt_status=receipt.status,
        admission_id=admission.admission_id,
        admission_digest=admission_digest,
        review={
            'review_id': 'review-ge-038',
            'subject_ref': admission_digest,
            'verdict': 'passed',
            'qualification_refs': ['claim-ge-038:qualification'],
        },
    )

    assert admission.allowed is True
    assert admission.reason_code == 'all_required_gates_passed'
    assert request.dry_run is True
    assert request.steps[0].tool == 'govengine-inspect'
    assert bound_receipt.status == 'dry-run'
    assert bound_receipt.binding.admission_digest == admission_digest
    assert bound_receipt.binding.ticket_digest == ticket['digest']
    assert bound_receipt.binding.request_digest == request_digest
    assert bound_receipt.binding.runner_profile == 'dry-run'
    assert admission.runner_profile['live_backend_enabled'] is False
    assert qualification.result == 'supported'
    assert qualification.reason_code == 'receipt_bounds_support_claim'
    bounded_records = repr((admission.as_dict(), bound_receipt.as_dict(), qualification.as_dict()))
    assert 'raw_output' not in bounded_records
