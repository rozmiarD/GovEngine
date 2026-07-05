from __future__ import annotations

import json
from pathlib import Path

import pytest

from govengine import (
    GovApiError,
    evaluate_contract_compatibility,
    supported_contract_report,
    validate_supported_contract_version,
)
from govengine.policy import cli as policy_cli


def test_supported_contract_report_lists_rexecop_surfaces() -> None:
    report = supported_contract_report()

    assert report['schema_version'] == 'v0.1'
    assert report['report_digest'].startswith('sha256:')
    surface_ids = {item['surface_id'] for item in report['contracts']}
    assert 'policy_request' in surface_ids
    assert 'policy_verdict' in surface_ids
    assert 'policy_enforcement_plan' in surface_ids
    assert 'typed_execution_governance_request' in surface_ids
    assert 'gov_admission_decision' in surface_ids
    assert 'trigger_planning_request' in surface_ids
    assert 'supervisor_action_request' in surface_ids
    assert 'automation_transition_request' in surface_ids
    assert 'automation_transition_explanation' in surface_ids
    assert 'governance_trace' in surface_ids
    assert report['rexecop_surfaces']
    assert 'governance_trace' in report['rexecop_surfaces']


def test_validate_supported_contract_version_fail_closed_unknown_major() -> None:
    with pytest.raises(GovApiError, match='unsupported_contract_major_version'):
        validate_supported_contract_version('policy_request', 'v9.9')


def test_evaluate_contract_compatibility_passes_for_rexecop_declarations() -> None:
    report = evaluate_contract_compatibility(
        {
            'schema_version': 'v0.1',
            'request_id': 'rexecop-contracts',
            'consumer': 'rexecop',
            'consumer_version': '0.2.12a0',
            'declared_contracts': [
                {'surface_id': 'policy_request', 'schema_version': 'v0.1'},
                {'surface_id': 'policy_verdict', 'schema_version': 'v0.1'},
                {'surface_id': 'policy_enforcement_plan', 'schema_version': 'v0.1'},
                {'surface_id': 'runtime_control_projection', 'schema_version': 'v0.1'},
                {'surface_id': 'gov_admission_decision', 'schema_version': 'v0.1'},
                {'surface_id': 'trigger_planning_request', 'schema_version': 'v0.1'},
                {'surface_id': 'supervisor_action_request', 'schema_version': 'v0.1'},
                {'surface_id': 'automation_transition_request', 'schema_version': 'v0.1'},
                {'surface_id': 'automation_transition_explanation', 'schema_version': 'v0.1'},
                {'surface_id': 'typed_execution_governance_request', 'schema_version': 'v0.1'},
                {'surface_id': 'typed_execution_governance_projection', 'schema_version': 'v0.1'},
                {'surface_id': 'typed_execution_stack_compatibility', 'schema_version': 'v0.1'},
                {'surface_id': 'typed_execution_control_catalog', 'schema_version': 'v0.1'},
                {'surface_id': 'governance_trace', 'schema_version': 'v0.1'},
            ],
        }
    )

    assert report.status == 'passed'
    assert report.report_digest.startswith('sha256:')
    assert 'policy_request' in report.matched_contracts


def test_evaluate_contract_compatibility_blocks_unknown_major() -> None:
    report = evaluate_contract_compatibility(
        {
            'schema_version': 'v0.1',
            'request_id': 'bad-contract',
            'consumer': 'rexecop',
            'consumer_version': '0.2.12a0',
            'declared_contracts': [
                {'surface_id': 'policy_request', 'schema_version': 'v9.9'},
            ],
        }
    )

    assert report.status == 'blocked'
    assert 'policy_request' in report.unsupported_contracts


def test_policy_cli_compatibility_catalog_json(monkeypatch) -> None:
    monkeypatch.setattr('sys.argv', ['govengine-policy', 'compatibility', '--json'])

    assert policy_cli.main() == 0


def test_policy_cli_compatibility_request_json(tmp_path: Path, monkeypatch) -> None:
    request_path = tmp_path / 'request.json'
    request_path.write_text(
        json.dumps(
            {
                'schema_version': 'v0.1',
                'request_id': 'cli-contracts',
                'consumer': 'rexecop',
                'consumer_version': '0.2.12a0',
                'declared_contracts': [
                    {'surface_id': 'policy_request', 'schema_version': 'v0.1'},
                ],
            }
        ),
        encoding='utf-8',
    )
    monkeypatch.setattr(
        'sys.argv',
        ['govengine-policy', 'compatibility', str(request_path), '--json'],
    )

    assert policy_cli.main() == 2
