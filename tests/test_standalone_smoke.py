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
        'govengine.events',
        'govengine.control',
        'govengine.runtime_shell',
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
