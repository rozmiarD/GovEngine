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
        'govengine.scope',
        'govengine.state_store',
        'govengine.roles',
        'govengine.execution_backend',
        'govengine.action_schema',
        'govengine.action_validators',
        'govengine.semantic_loss_policy',
        'govengine.capability_recipes',
        'govengine.action_compiler',
        'govengine.tool_registry',
        'govengine.sclite_contracts',
        'govengine.sclite_adapter',
        'govengine.signing',
        'govengine.state_index',
        'govengine.state_machine',
        'govengine.contracts.analysis',
        'govengine.contracts.evidence_policy',
        'govengine.contracts.execution',
        'govengine.contracts.signal',
        'govengine.policy.core',
        'govengine.policy.gateway',
        'govengine.execution.approved_spec',
        'govengine.execution.command_shape',
        'govengine.execution.gate',
        'govengine.execution.runner',
        'govengine.execution.runner_protocol',
        'govengine.execution.ticket_gate',
        'govengine.ooda',
        'govengine.orchestration',
        'govengine.events',
        'govengine.control',
    ]
    for module in modules:
        importlib.import_module(module)


def test_standalone_compile_and_dry_run_helpers() -> None:
    from govengine.action_compiler import compile_action_spec
    from govengine.execution.runner import legacy_action_spec_dry_run_result

    compiled = compile_action_spec({
        'action_type': 'single_probe',
        'capability': 'http_probe',
        'tool': 'curl',
        'args': ['https://example.com'],
        'probe_recipe': {'sequence_steps': ['single'], 'evidence_goal': 'standalone smoke'},
    })
    assert compiled['tool'] == 'curl'
    result = legacy_action_spec_dry_run_result(compiled_action=compiled, planned_commands=[['curl', 'https://example.com']])
    assert result['status'] == 'dry-run'
    assert result['execution_source'] == 'legacy_direct_action_spec'


def test_scope_helpers_are_local() -> None:
    from govengine.scope import extract_host_from_url, host_in_scope, load_scope_domains

    domains = load_scope_domains('example.com\nOut of scope:\nevil.example.com\n')
    assert extract_host_from_url('https://example.com/path') == 'example.com'
    assert host_in_scope('example.com', domains)
    assert not host_in_scope('evil.example.com', domains)
