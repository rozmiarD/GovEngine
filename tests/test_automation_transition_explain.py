from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from govengine import SUPPORTED_AUTOMATION_CHAIN_SCHEMA_REF, explain_automation_transition

ROOT = Path(__file__).resolve().parents[1]
POLICY_SCRIPT = ROOT / 'scripts' / 'govengine_policy.py'


def _digest(char: str) -> str:
    return 'sha256:' + char * 64


def _request(**overrides):
    payload = {
        'request_id': 'automation-request-1',
        'chain_id': 'chain-1',
        'parent_operation_id': 'op-parent',
        'parent_operation_ref': _digest('a'),
        'parent_intent': 'collect_basic_host_inventory',
        'parent_status': 'completed',
        'child_operation_id': 'op-child',
        'child_intent': 'summarize_inventory',
        'child_intent_class': 'readonly_followup',
        'transition_reason': 'parent_completed_with_followup',
        'automation_chain_ref': _digest('b'),
        'automation_chain_schema_ref': SUPPORTED_AUTOMATION_CHAIN_SCHEMA_REF,
        'source': 'reaction',
        'depth': 1,
        'max_depth': 3,
        'child_sequence': 1,
        'max_children': 2,
        'allowed_child_intent_classes': ['readonly_followup', 'evidence_review'],
    }
    payload.update(overrides)
    return payload


def test_explain_automation_transition_allowed() -> None:
    explanation = explain_automation_transition(_request()).as_dict()

    assert explanation['schema_version'] == 'v0.1'
    assert explanation['status'] == 'explained'
    assert explanation['reason_code'] == 'automation_transition_allowed'
    assert explanation['evaluation_path'] == 'allowed'
    assert explanation['gates_checked'][0]['gate'] == 'automation_chain_contract'
    assert explanation['request_digest'].startswith('sha256:')
    assert explanation['admission_digest'].startswith('sha256:')
    assert 'Does not create' in explanation['non_claims'][0]


def test_explain_automation_transition_llm_proposal_requires_approval() -> None:
    explanation = explain_automation_transition(
        _request(source='llm_proposal', llm_proposed=True)
    ).as_dict()

    assert explanation['status'] == 'blocked'
    assert explanation['reason_code'] == 'automation_transition_requires_approval'
    assert explanation['evaluation_path'] == 'approval'
    assert 'record bounded operator approval' in explanation['safe_next_actions'][-1]


def test_policy_cli_automation_transition_json(tmp_path: Path) -> None:
    request_path = tmp_path / 'request.json'
    request_path.write_text(json.dumps(_request()), encoding='utf-8')

    proc = subprocess.run(
        [
            sys.executable,
            str(POLICY_SCRIPT),
            'automation-transition',
            str(request_path),
            '--json',
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    payload = json.loads(proc.stdout)

    assert proc.returncode == 0
    assert payload['status'] == 'explained'
    assert payload['reason_code'] == 'automation_transition_allowed'


def test_policy_cli_automation_transition_blocked_exits_two(tmp_path: Path) -> None:
    request_path = tmp_path / 'request.json'
    request_path.write_text(json.dumps(_request(depth=4)), encoding='utf-8')

    proc = subprocess.run(
        [
            sys.executable,
            str(POLICY_SCRIPT),
            'automation-transition',
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
    assert payload['reason_code'] == 'automation_transition_depth_exceeded'
