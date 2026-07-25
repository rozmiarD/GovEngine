from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from govengine.cli_contracts import (
    CLI_CONTRACT_REGISTRY_SCHEMA,
    cli_contract_registry,
    validate_cli_contract_registry,
)
from govengine.cli_errors import CLI_ERROR_SCHEMA

ROOT = Path(__file__).resolve().parents[1]
POLICY_SCRIPT = ROOT / 'scripts' / 'govengine_policy.py'

EXPECTED_COMMAND_SCHEMAS = {
    'govengine-policy automation-transition': 'govengine.automation_transition_explanation.v0.1',
    'govengine-policy compatibility': 'govengine.contract_compatibility_report.v0.1',
    'govengine-policy compile': 'govengine.policy_pack.v0.1_or_v1',
    'govengine-policy explain': 'govengine.policy_evaluation_explanation.v0.1_or_v1',
    'govengine-policy profile-governance': 'govengine.profile_governance_bundle.v0.1',
    'govengine-policy scaffold': 'govengine.policy_pack.v0.1',
    'govengine-policy schema': 'govengine.policy_json_schema.v0.1',
    'govengine-policy simulate': 'govengine.policy_evaluation_explanation.v0.1_or_v1',
    'govengine-policy typed-execution-compatibility': 'govengine.typed_execution_stack_compatibility.v0.1',
    'govengine-policy typed-execution-control-catalog': 'govengine.typed_execution_control_catalog.v0.1',
    'govengine-policy typed-execution-governance': 'govengine.typed_execution_governance_bundle.v0.1',
    'govengine-policy validate': 'govengine.policy_pack_validation.v0.1',
    'govengine-supervisor explain': 'govengine.supervisor_action_explanation.v0.1',
}

EXPECTED_COMMAND_GROUPS = {
    'automation_transition': {'govengine-policy automation-transition'},
    'contract_compatibility': {'govengine-policy compatibility'},
    'policy_authoring': {
        'govengine-policy compile',
        'govengine-policy scaffold',
        'govengine-policy schema',
        'govengine-policy validate',
    },
    'policy_explain': {
        'govengine-policy explain',
        'govengine-policy simulate',
    },
    'profile_governance': {'govengine-policy profile-governance'},
    'supervisor_explain': {'govengine-supervisor explain'},
    'typed_execution': {
        'govengine-policy typed-execution-compatibility',
        'govengine-policy typed-execution-control-catalog',
        'govengine-policy typed-execution-governance',
    },
}


def test_cli_contract_registry_is_valid_and_snapshot_stable() -> None:
    registry = cli_contract_registry()

    assert registry['schema'] == CLI_CONTRACT_REGISTRY_SCHEMA
    assert validate_cli_contract_registry(registry) == []
    assert {
        item['command']: item['schema'] for item in registry['contracts']
    } == EXPECTED_COMMAND_SCHEMAS
    assert {
        group['group']: set(group['commands']) for group in registry['command_groups']
    } == EXPECTED_COMMAND_GROUPS
    assert registry['contract_count'] == len(EXPECTED_COMMAND_SCHEMAS)
    assert all(
        row['error_schema'] == CLI_ERROR_SCHEMA
        for row in registry['exit_code_matrix']
    )


def test_policy_cli_explain_blocked_request_exits_two(tmp_path: Path) -> None:
    policy_path = tmp_path / 'policy.json'
    request_path = tmp_path / 'request.json'
    policy_path.write_text(
        json.dumps(
            {
                'policy_id': 'explain-policy',
                'version': 'v1',
                'rules': [
                    {
                        'rule_id': 'deny-unsafe-mode',
                        'effect': 'deny',
                        'priority': 10,
                        'conditions': {'action.mode': 'unsafe'},
                        'reason_code': 'unsafe_mode_denied',
                    }
                ],
            }
        ),
        encoding='utf-8',
    )
    request_path.write_text(
        json.dumps(
            {
                'request_id': 'request-unsafe',
                'subject_ref': 'artifact://task/unsafe',
                'action': {'mode': 'unsafe'},
                'resource': {'criticality': 'low'},
            }
        ),
        encoding='utf-8',
    )

    proc = subprocess.run(
        [
            sys.executable,
            str(POLICY_SCRIPT),
            'explain',
            str(policy_path),
            str(request_path),
            '--json',
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    payload = json.loads(proc.stdout)

    assert proc.returncode == 2
    assert payload['status'] == 'blocked'
    assert payload['reason_code'] == 'unsafe_mode_denied'


def test_policy_cli_explanation_registry_covers_legacy_and_typed_schemas(
    tmp_path: Path,
) -> None:
    request_path = tmp_path / 'request.json'
    request_path.write_text(
        json.dumps(
            {
                'request_id': 'request-read',
                'subject_ref': 'artifact://task/read',
                'action': {'mode': 'read'},
                'resource': {'criticality': 'low'},
            }
        ),
        encoding='utf-8',
    )
    policies = {
        'v0.1': {
            'policy_id': 'legacy-read',
            'version': '1',
            'rules': [
                {
                    'rule_id': 'allow-read',
                    'effect': 'allow',
                    'conditions': {'action.mode': 'read'},
                    'reason_code': 'read_allowed',
                }
            ],
        },
        'v1': {
            'schema_version': 'v1',
            'policy_id': 'typed-read',
            'version': '1.0.0',
            'issuer_ref': 'organization:test',
            'policy_epoch': 1,
            'validity': {
                'not_before': '2026-01-01T00:00:00Z',
                'expires_at': '2099-01-01T00:00:00Z',
            },
            'supersedes': [],
            'rules': [
                {
                    'rule_id': 'allow-read',
                    'effect': 'allow',
                    'conditions': [
                        {
                            'path': 'action.mode',
                            'operator': 'eq',
                            'value': 'read',
                        }
                    ],
                    'reason_code': 'read_allowed',
                }
            ],
        },
    }
    emitted_versions: set[str] = set()
    for command in ('explain', 'simulate'):
        for expected_version, policy in policies.items():
            policy_path = tmp_path / f'policy-{expected_version}.json'
            policy_path.write_text(json.dumps(policy), encoding='utf-8')
            proc = subprocess.run(
                [
                    sys.executable,
                    str(POLICY_SCRIPT),
                    command,
                    str(policy_path),
                    str(request_path),
                    '--json',
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            assert proc.returncode == 0
            emitted = json.loads(proc.stdout)['schema_version']
            assert emitted == expected_version
            emitted_versions.add(emitted)

    registry = cli_contract_registry()
    schemas = {
        item['command']: item['schema']
        for item in registry['contracts']
        if item['command'] in {
            'govengine-policy explain',
            'govengine-policy simulate',
        }
    }
    assert set(schemas.values()) == {
        'govengine.policy_evaluation_explanation.v0.1_or_v1'
    }
    assert emitted_versions == {'v0.1', 'v1'}


def test_policy_cli_invalid_request_emits_json_error_envelope(tmp_path: Path) -> None:
    policy_path = tmp_path / 'policy.json'
    request_path = tmp_path / 'request.json'
    policy_path.write_text(
        json.dumps(
            {
                'policy_id': 'cli-policy',
                'version': 'v1',
                'rules': [
                    {
                        'rule_id': 'allow-read',
                        'effect': 'allow',
                        'conditions': {'action.mode': 'read'},
                    }
                ],
            }
        ),
        encoding='utf-8',
    )
    request_path.write_text('not-json', encoding='utf-8')

    proc = subprocess.run(
        [
            sys.executable,
            str(POLICY_SCRIPT),
            'explain',
            str(policy_path),
            str(request_path),
            '--json',
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    payload = json.loads(proc.stdout)

    assert proc.returncode == 2
    assert payload['schema'] == CLI_ERROR_SCHEMA
    assert payload['status'] == 'error'
    assert payload['reason_code'] == 'policy_request_json_invalid'
    assert payload['command'] == 'govengine-policy explain'
