from __future__ import annotations

import pytest

from govengine import (
    PolicyCompiler,
    PolicyEngine,
    admit_policy_execution,
    admit_typed_execution,
    evaluate_typed_execution_stack_compatibility,
    explain_typed_execution_governance,
    map_policy_verdict_to_typed_execution_controls,
    project_typed_execution_policy_overlay,
    typed_execution_control_catalog,
)
from govengine.api import GovApiError
from govengine.signing import govengine_record_digest
from govengine.typed_execution_governance import runtime_capability_descriptor_digest


def _digest(seed: str) -> str:
    return f'sha256:{seed * 64}'[:71]


def _capability(**overrides):
    payload = {
        'schema_version': 'v0.1',
        'backend_class': 'static_fixture',
        'identity_class': 'none',
        'egress_class': 'no_network',
        'read_only_backend': False,
        'live_backend_posture': 'fixture_only',
        'network_boundary': {'egress': 'no_network', 'host_declared': False},
        'secret_ref_requirements': [],
        'declared_capability_descriptors': ['connector.fixture.static'],
        'certification_tier': 'core',
        'mode': 'dry_run',
    }
    payload.update(overrides)
    return payload


def _request(**overrides):
    capability = overrides.pop('capability_descriptor', _capability())
    payload = {
        'schema_version': 'v0.1',
        'request_id': 'typed-exec-1',
        'operation_id': 'operation-1',
        'step_id': 'inspect_state',
        'operation_mode': 'dry_run',
        'step_execution_spec_digest': _digest('a'),
        'capability_descriptor_digest': runtime_capability_descriptor_digest(
            capability
        ),
        'payload_schema': 'rexecop.static_fixture_execution_spec.v0.1',
        'payload_digest': _digest('c'),
        'backend_class': capability['backend_class'],
        'connector': 'fixture_source',
        'action': 'read_fixture_state',
        'read_only': True,
        'side_effect_class': 'read_only',
        'capability_descriptor': capability,
        'evidence_requirements': {
            'receipt_required': True,
            'output_digest_required': False,
        },
        'allowed_network_egress': ['no_network'],
        'required_capability_descriptors': ['connector.fixture.static'],
    }
    payload.update(overrides)
    return payload


def test_allowed_read_only_typed_execution_spec() -> None:
    bundle = explain_typed_execution_governance(_request())
    admission = admit_typed_execution(_request())

    assert bundle.status == 'passed'
    assert bundle.governance.status == 'passed'
    assert bundle.compatibility.status == 'passed'
    assert bundle.bundle_digest.startswith('sha256:')
    assert admission.allowed is True
    assert admission.outcome == 'allowed'
    assert admission.reason_code == 'typed_execution_admission_allowed'


def test_capability_descriptor_digest_mismatch_is_rejected() -> None:
    with pytest.raises(GovApiError, match='capability_descriptor_digest_mismatch'):
        explain_typed_execution_governance(
            _request(capability_descriptor_digest=_digest('f'))
        )


def test_blocked_raw_shell_backend() -> None:
    capability = _capability(
        backend_class='shell',
        egress_class='local_subprocess',
        network_boundary={'egress': 'local_subprocess', 'host_declared': False},
        declared_capability_descriptors=[],
    )
    bundle = explain_typed_execution_governance(
        _request(
            backend_class='shell',
            capability_descriptor=capability,
            allowed_network_egress=['local_subprocess'],
        )
    )

    assert bundle.status == 'blocked'
    assert 'raw_shell_backend_blocked' in bundle.compatibility.blockers


def test_blocked_unsupported_backend() -> None:
    capability = _capability(
        backend_class='undeclared_plugin',
        egress_class='plugin_undeclared',
        network_boundary={'egress': 'plugin_undeclared', 'host_declared': False},
        declared_capability_descriptors=['connector.plugin.undeclared_plugin'],
        certification_tier='plugin',
        identity_class='plugin_declared',
    )
    bundle = explain_typed_execution_governance(
        _request(
            backend_class='undeclared_plugin',
            capability_descriptor=capability,
            allowed_network_egress=['plugin_undeclared'],
        )
    )

    assert bundle.status == 'blocked'
    assert 'unsupported_backend_class' in bundle.compatibility.blockers


def test_host_registration_boolean_does_not_certify_plugin_backend() -> None:
    capability = _capability(
        backend_class='unreviewed_plugin',
        egress_class='plugin_undeclared',
        network_boundary={'egress': 'plugin_undeclared', 'host_declared': False},
        declared_capability_descriptors=['connector.plugin.unreviewed'],
        certification_tier='plugin',
        identity_class='plugin_declared',
    )
    bundle = explain_typed_execution_governance(
        _request(
            backend_class='unreviewed_plugin',
            capability_descriptor=capability,
            allowed_network_egress=['plugin_undeclared'],
            required_capability_descriptors=['connector.plugin.unreviewed'],
            metadata={'registered_plugin_backend': True},
        )
    )

    assert bundle.status == 'blocked'
    assert 'unsupported_backend_class' in bundle.compatibility.blockers


def test_http_destination_binding_is_admitted_without_raw_host() -> None:
    destination = {
        'scheme': 'https',
        'effective_port': 8443,
        'address_class': 'private',
        'origin_binding_digest': _digest('d'),
    }
    capability = _capability(
        backend_class='http_api',
        egress_class='outbound_http',
        identity_class='api_token_optional',
        live_backend_posture='live_backend',
        network_boundary={
            'egress': 'outbound_http',
            'destination_binding': destination,
        },
        declared_capability_descriptors=['connector.http.rest.read'],
    )
    network_policy = {
        'allowed_network_egress': ['outbound_http'],
        'allowed_network_schemes': ['https'],
        'allowed_address_classes': ['private'],
        'required_origin_binding_digest': destination['origin_binding_digest'],
    }
    request = _request(
        backend_class='http_api',
        capability_descriptor=capability,
        allowed_network_egress=['outbound_http'],
        required_capability_descriptors=['connector.http.rest.read'],
        destination_binding=destination,
        allowed_network_schemes=['https'],
        allowed_address_classes=['private'],
        required_origin_binding_digest=destination['origin_binding_digest'],
        network_policy_binding=network_policy,
        network_policy_binding_digest=govengine_record_digest(
            network_policy,
            record_type='govengine.typed_execution.NetworkPolicyBinding',
        ),
        metadata={'require_destination_binding': True},
    )
    admission = admit_typed_execution(request)
    assert admission.allowed is True
    assert (
        admission.signal['step_execution_spec_digest']
        == request['step_execution_spec_digest']
    )
    assert 'private-api' not in repr(admission.as_dict())


def test_destination_cannot_supply_its_own_allowlist() -> None:
    destination = {
        'scheme': 'https',
        'effective_port': 443,
        'address_class': 'public',
        'origin_binding_digest': _digest('d'),
    }
    capability = _capability(
        backend_class='http_api',
        egress_class='outbound_http',
        identity_class='api_token_optional',
        live_backend_posture='live_backend',
        network_boundary={
            'egress': 'outbound_http',
            'destination_binding': destination,
        },
        declared_capability_descriptors=['connector.http.rest.read'],
    )
    bundle = explain_typed_execution_governance(
        _request(
            backend_class='http_api',
            capability_descriptor=capability,
            allowed_network_egress=['outbound_http'],
            required_capability_descriptors=['connector.http.rest.read'],
            destination_binding=destination,
            allowed_network_schemes=['https'],
            allowed_address_classes=['public'],
            required_origin_binding_digest=destination['origin_binding_digest'],
            metadata={'require_destination_binding': True},
        )
    )

    assert bundle.status == 'blocked'
    assert 'network_policy_binding_missing' in bundle.compatibility.blockers


def test_http_destination_binding_drift_is_blocked() -> None:
    destination = {
        'scheme': 'https',
        'effective_port': 443,
        'address_class': 'dns_name',
        'origin_binding_digest': _digest('d'),
    }
    capability = _capability(
        backend_class='http_api',
        egress_class='outbound_http',
        identity_class='api_token_optional',
        live_backend_posture='live_backend',
        network_boundary={
            'egress': 'outbound_http',
            'destination_binding': destination,
        },
        declared_capability_descriptors=['connector.http.rest.read'],
    )
    network_policy = {
        'allowed_network_egress': ['outbound_http'],
        'allowed_network_schemes': ['https'],
        'allowed_address_classes': ['dns_name'],
        'required_origin_binding_digest': destination['origin_binding_digest'],
    }
    request = _request(
        backend_class='http_api',
        capability_descriptor=capability,
        allowed_network_egress=['outbound_http'],
        required_capability_descriptors=['connector.http.rest.read'],
        destination_binding={**destination, 'effective_port': 444},
        allowed_network_schemes=['https'],
        allowed_address_classes=['dns_name'],
        required_origin_binding_digest=destination['origin_binding_digest'],
        network_policy_binding=network_policy,
        network_policy_binding_digest=govengine_record_digest(
            network_policy,
            record_type='govengine.typed_execution.NetworkPolicyBinding',
        ),
        metadata={'require_destination_binding': True},
    )
    bundle = explain_typed_execution_governance(request)
    assert bundle.status == 'blocked'
    assert 'network_destination_binding_mismatch' in bundle.compatibility.blockers


def test_blocked_missing_output_digest_ref() -> None:
    bundle = explain_typed_execution_governance(
        _request(
            evidence_requirements={
                'receipt_required': True,
                'output_digest_required': True,
            }
        )
    )

    assert bundle.status == 'blocked'
    assert 'missing_output_digest_ref' in bundle.governance.blockers
    assert 'missing_output_digest_ref' in bundle.compatibility.blockers


def test_blocked_network_boundary_mismatch() -> None:
    capability = _capability(
        backend_class='http_api',
        identity_class='api_token_optional',
        egress_class='outbound_http',
        live_backend_posture='live_backend',
        network_boundary={'egress': 'outbound_http', 'endpoint_declared': True},
        declared_capability_descriptors=['connector.http.rest.read'],
        secret_ref_requirements=[
            {
                'path': 'base_url_secret_ref',
                'required': True,
                'present': True,
                'kind': 'secret_ref',
            }
        ],
    )
    network_policy = {'allowed_network_egress': ['no_network']}
    bundle = explain_typed_execution_governance(
        _request(
            backend_class='http_api',
            payload_schema='rexecop.http_action_execution_spec.v0.1',
            capability_descriptor=capability,
            allowed_network_egress=['no_network'],
            required_capability_descriptors=['connector.http.rest.read'],
            network_policy_binding=network_policy,
            network_policy_binding_digest=govengine_record_digest(
                network_policy,
                record_type='govengine.typed_execution.NetworkPolicyBinding',
            ),
        )
    )

    assert bundle.status == 'blocked'
    assert 'network_boundary_mismatch' in bundle.compatibility.blockers


def test_blocked_mutation_requiring_approval() -> None:
    capability = _capability(
        mutating=True,
        read_only_backend=False,
        live_backend_posture='fixture_only',
    )
    bundle = explain_typed_execution_governance(
        _request(
            operation_mode='apply',
            read_only=False,
            side_effect_class='mutation',
            capability_descriptor=capability,
            evidence_requirements={'receipt_required': True},
        )
    )
    admission = admit_typed_execution(
        _request(
            operation_mode='apply',
            read_only=False,
            side_effect_class='mutation',
            capability_descriptor=capability,
            evidence_requirements={'receipt_required': True},
        )
    )

    assert bundle.status == 'blocked'
    assert 'mutation_requires_approval_evidence' in bundle.governance.blockers
    assert admission.allowed is False
    assert admission.outcome == 'denied'


def test_mutation_is_not_allowed_with_opaque_approval_evidence_ref() -> None:
    capability = _capability(
        read_only_backend=False,
        live_backend_posture='fixture_only',
    )
    request = _request(
        operation_mode='apply',
        read_only=False,
        side_effect_class='mutation',
        capability_descriptor=capability,
        evidence_requirements={
            'receipt_required': True,
            'approval_evidence_ref': _digest('d'),
        },
        allowed_network_egress=['no_network'],
    )
    bundle = explain_typed_execution_governance(request)
    admission = admit_typed_execution(request)

    assert bundle.status == 'blocked'
    assert 'mutation_requires_approval_attestation' in bundle.governance.blockers
    assert admission.allowed is False
    assert admission.blockers.count('mutation_requires_approval_attestation') == 1


def test_forbidden_metadata_rejected() -> None:
    with pytest.raises(GovApiError, match='forbidden_typed_execution_metadata:command'):
        explain_typed_execution_governance(_request(metadata={'command': 'rm -rf /'}))


def test_forbidden_metadata_inside_list_is_rejected() -> None:
    with pytest.raises(
        GovApiError, match='forbidden_typed_execution_metadata:password'
    ):
        explain_typed_execution_governance(
            _request(metadata={'items': [{'password': 'redacted-test-value'}]})
        )


def test_operation_capability_requirements_must_be_explicit() -> None:
    bundle = explain_typed_execution_governance(
        _request(required_capability_descriptors=[])
    )

    assert bundle.status == 'blocked'
    assert 'operation_capability_requirements_missing' in bundle.compatibility.blockers


def _stack_request(**overrides):
    payload = {
        'schema_version': 'v0.1',
        'request_id': 'stack-compat-1',
        'backend_descriptors': [
            {
                'backend_class': 'static_fixture',
                'egress_class': 'no_network',
                'identity_class': 'none',
                'capability_descriptors': ['connector.fixture.static'],
                'certification_tier': 'core',
            },
            {
                'backend_class': 'http_api',
                'egress_class': 'outbound_http',
                'identity_class': 'api_token_optional',
                'capability_descriptors': [
                    'connector.http.rest.read',
                    'connector.http.rest.mutate',
                ],
                'certification_tier': 'core',
            },
        ],
    }
    payload.update(overrides)
    return payload


def test_typed_execution_stack_compatibility_passes_for_builtin_backends() -> None:
    report = evaluate_typed_execution_stack_compatibility(_stack_request())

    assert report.status == 'passed'
    assert report.report_digest.startswith('sha256:')
    assert 'static_fixture' in report.supported_backends
    assert 'http_api' in report.supported_backends


def test_typed_execution_stack_compatibility_blocks_raw_shell_backend() -> None:
    report = evaluate_typed_execution_stack_compatibility(
        _stack_request(
            backend_descriptors=[
                {
                    'backend_class': 'shell',
                    'egress_class': 'local_subprocess',
                    'identity_class': 'none',
                    'capability_descriptors': [],
                    'certification_tier': 'bootstrap',
                }
            ]
        )
    )

    assert report.status == 'blocked'
    assert 'shell' in report.unsupported_backends
    assert 'raw_shell_backend_blocked' in report.blockers


def test_typed_execution_control_catalog_lists_baseline_controls() -> None:
    catalog = typed_execution_control_catalog()

    assert catalog['schema_version'] == 'v0.1'
    assert 'backend_class_supported' in catalog['controls']
    assert 'http_api' in catalog['supported_backend_classes']
    assert catalog['entries']
    assert 'allowed_network_egress' in catalog['policy_constraint_kinds']
    entry_ids = {item['control_id'] for item in catalog['entries']}
    assert entry_ids == set(catalog['controls'])


def test_project_typed_execution_policy_overlay_maps_runtime_controls() -> None:
    overlay = project_typed_execution_policy_overlay(
        {
            'receipt_required': True,
            'output_digest_required': True,
            'no_raw_shell': True,
            'read_only_required': True,
            'allowed_network_egress': ['no_network', 'outbound_http'],
            'allowed_backend_classes': ['static_fixture', 'http_api'],
            'typed_execution_control_ids': [
                'output_digest_required',
                'network_boundary_match',
            ],
            'control_ids': ['digest-output', 'network-egress'],
        }
    )

    assert overlay['output_digest_required'] is True
    assert 'output_digest_required' not in overlay['evidence_requirements']
    assert overlay['allowed_network_egress'] == ['no_network', 'outbound_http']
    assert overlay['allowed_backend_classes'] == ['static_fixture', 'http_api']
    assert overlay['no_raw_shell'] is True
    assert 'network_boundary_match' in overlay['typed_execution_control_ids']


def test_map_policy_verdict_to_typed_execution_controls_from_bounded_pack() -> None:
    compiled = PolicyCompiler().compile(
        {
            'policy_id': 'typed-execution-read',
            'version': '1',
            'rules': [
                {
                    'rule_id': 'bounded-read',
                    'effect': 'allow_with_obligations',
                    'conditions': {'action.mode': 'read'},
                    'obligations': [
                        {'obligation_id': 'receipt', 'kind': 'receipt'},
                        {
                            'obligation_id': 'output-digests',
                            'kind': 'output_digest_required',
                        },
                    ],
                    'constraints': [
                        {
                            'constraint_id': 'no-shell',
                            'kind': 'no_raw_shell',
                            'value': True,
                        },
                        {
                            'constraint_id': 'network',
                            'kind': 'allowed_network_egress',
                            'value': ['no_network'],
                        },
                    ],
                }
            ],
        }
    )
    assert compiled.policy_pack is not None
    verdict = PolicyEngine().evaluate(
        {
            'request_id': 'request-typed',
            'subject_ref': 'runner:operation-1',
            'action': {'mode': 'read'},
        },
        compiled.policy_pack,
    )
    plan = admit_policy_execution(compiled.policy_pack, verdict)
    overlay = map_policy_verdict_to_typed_execution_controls(verdict.as_dict())

    assert plan.controls.output_digest_required is True
    assert plan.controls.no_raw_shell is True
    assert overlay['allowed_network_egress'] == ['no_network']
    assert overlay['output_digest_required'] is True
    assert 'no_raw_shell' in overlay['typed_execution_control_ids']
