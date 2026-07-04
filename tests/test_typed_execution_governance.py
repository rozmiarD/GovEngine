from __future__ import annotations

import pytest

from govengine import admit_typed_execution, explain_typed_execution_governance
from govengine.api import GovApiError


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
        'capability_descriptor_digest': _digest('b'),
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
    bundle = explain_typed_execution_governance(
        _request(
            backend_class='http_api',
            payload_schema='rexecop.http_action_execution_spec.v0.1',
            capability_descriptor=capability,
            allowed_network_egress=['no_network'],
            required_capability_descriptors=['connector.http.rest.read'],
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


def test_mutation_allowed_with_approval_evidence_ref() -> None:
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

    assert bundle.status == 'passed'
    assert admission.allowed is True


def test_forbidden_metadata_rejected() -> None:
    with pytest.raises(GovApiError, match='forbidden_typed_execution_metadata:command'):
        explain_typed_execution_governance(_request(metadata={'command': 'rm -rf /'}))