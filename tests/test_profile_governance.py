from __future__ import annotations

import json

import pytest

from govengine import (
    explain_profile_governance,
    profile_governance_request_digest,
    project_profile_governance,
    tecrax_infra_ops_profile,
)
from govengine.api import GovApiError


def _request(**overrides):
    payload = {
        'schema_version': 'v0.1',
        'request_id': 'profile-governance-1',
        'profile_name': 'tecrax',
        'profile_version': '0.3.9a0',
        'supported_tracks': ['readonly', 'mutation'],
        'policy_hooks': [{'name': 'runtime_admission_gate', 'hook_type': 'admission'}],
        'evidence_expectations': [
            {
                'name': 'receipt_bounded_execution',
                'receipt_bound_required': True,
                'claim_types': ['execution_truth'],
            }
        ],
        'runner_posture': {
            'name': 'rexecop_default_dry_run',
            'mode': 'dry_run',
            'live_enabled': False,
        },
        'required_capabilities': ['connector.http.rest.read'],
        'available_capabilities': ['connector.http.rest.read', 'connector.shell.readonly'],
        'connector_backends': [
            {
                'backend_class': 'http_api',
                'capability_descriptors': ['connector.http.rest.read'],
                'certification_tier': 'core',
            }
        ],
    }
    payload.update(overrides)
    return payload


def test_profile_governance_passes_for_bounded_projection() -> None:
    bundle = explain_profile_governance(_request())

    assert bundle.status == 'passed'
    assert bundle.governance.status == 'passed'
    assert bundle.compatibility.status == 'passed'
    assert bundle.governance.projection_digest.startswith('sha256:')
    assert bundle.compatibility.report_digest.startswith('sha256:')
    assert bundle.bundle_digest.startswith('sha256:')
    assert profile_governance_request_digest(_request()).startswith('sha256:')


def test_profile_governance_blocks_missing_capabilities() -> None:
    bundle = explain_profile_governance(
        _request(
            required_capabilities=['connector.http.rest.read', 'connector.ssh.readonly'],
            profile_declared_capabilities=['connector.http.rest.read'],
            available_capabilities=['connector.http.rest.read'],
            connector_backends=[
                {
                    'backend_class': 'http_api',
                    'capability_descriptors': ['connector.http.rest.read'],
                    'certification_tier': 'core',
                }
            ],
        )
    )

    assert bundle.status == 'blocked'
    assert bundle.compatibility.missing_capabilities == ('connector.ssh.readonly',)
    assert 'missing_required_capabilities' in bundle.compatibility.blockers


def test_profile_governance_blocks_live_runner_posture() -> None:
    projection = project_profile_governance(
        _request(
            runner_posture={
                'name': 'live_runner',
                'mode': 'live',
                'live_enabled': True,
            }
        )
    )

    assert projection.status == 'blocked'
    assert 'invalid_runner_posture' in projection.blockers


def test_profile_governance_includes_domain_profile_conformance() -> None:
    bundle = explain_profile_governance(
        _request(domain_profile=tecrax_infra_ops_profile().as_dict())
    )

    assert bundle.governance.domain_profile_conformance is not None
    assert bundle.governance.domain_profile_conformance['status'] == 'passed'


def test_profile_governance_rejects_unsupported_request_version() -> None:
    with pytest.raises(GovApiError, match='unsupported_profile_governance_request_version'):
        explain_profile_governance(_request(schema_version='v9.9'))


def test_policy_cli_profile_governance_json(tmp_path, monkeypatch) -> None:
    from govengine.policy import cli as policy_cli

    projection_path = tmp_path / 'projection.json'
    projection_path.write_text(json.dumps(_request()), encoding='utf-8')
    monkeypatch.setattr(
        'sys.argv',
        ['govengine-policy', 'profile-governance', str(projection_path), '--json'],
    )

    assert policy_cli.main() == 0