from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from govengine import PolicyEngine
from govengine.api import GovApiError
from govengine.policy import (
    available_baseline_policy_names,
    baseline_policy_pack,
    policy_json_schema,
    read_policy_pack,
    render_policy_pack_json,
    validate_policy_pack,
)

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'govengine_policy.py'


def test_policy_baseline_generator_produces_compilable_governed_runtime_pack() -> None:
    assert 'governed-runtime' in available_baseline_policy_names()
    pack = baseline_policy_pack(
        'governed-runtime',
        policy_id='tenant-governed-runtime',
        version='2026-06-20',
    )
    result = validate_policy_pack(pack)

    assert result.ok
    assert result.policy_pack is not None
    assert result.policy_pack.policy_id == 'tenant-governed-runtime'
    assert [rule.rule_id for rule in result.policy_pack.rules] == sorted(
        rule.rule_id for rule in result.policy_pack.rules
    )

    verdict = PolicyEngine().evaluate(
        {
            'request_id': 'request-1',
            'subject_ref': 'artifact://task/1',
            'action': {'mode': 'read'},
            'resource': {'criticality': 'low'},
        },
        result.policy_pack,
    )
    assert verdict.decision == 'allow_with_obligations'
    read_rule = next(
        rule
        for rule in result.policy_pack.rules
        if rule.conditions[0].path == 'action.mode'
        and rule.conditions[0].value == 'read'
    )
    assert {item.constraint_id for item in read_rule.constraints} == {
        'bounded-output',
        'digest-output',
        'network-egress',
        'no-shell',
        'read-only',
    }


def test_policy_authoring_schema_is_public_and_boundary_explicit() -> None:
    schema = policy_json_schema('policy-pack')

    assert schema['title'] == 'GovEngine policy pack'
    assert schema['required'] == ['policy_id', 'version', 'rules']
    assert 'not SCLite truth and not execution authority' in schema['description']


def test_policy_cli_scaffold_validate_schema_and_compile(tmp_path: Path) -> None:
    policy_path = tmp_path / 'policy.json'

    scaffold = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            'scaffold',
            'governed-runtime',
            '--policy-id',
            'cli-policy',
            '--version',
            'v1',
            '--output',
            str(policy_path),
        ],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=True,
    )
    assert scaffold.stdout == ''
    policy = json.loads(policy_path.read_text(encoding='utf-8'))
    assert policy['policy_id'] == 'cli-policy'

    validation = subprocess.run(
        [sys.executable, str(SCRIPT), 'validate', str(policy_path), '--json'],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=True,
    )
    report = json.loads(validation.stdout)
    assert report['status'] == 'passed'
    assert report['non_claims'] == [
        'Does not execute work.',
        'Does not verify SCLite artifacts or canonicalize evidence.',
        'Does not run operator approval workflow.',
    ]

    schema = subprocess.run(
        [sys.executable, str(SCRIPT), 'schema', 'policy-request'],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=True,
    )
    assert json.loads(schema.stdout)['title'] == 'GovEngine policy request'

    compiled = subprocess.run(
        [sys.executable, str(SCRIPT), 'compile', str(policy_path), '--json'],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=True,
    )
    assert json.loads(compiled.stdout)['policy_id'] == 'cli-policy'


def test_policy_cli_validate_fails_closed_for_invalid_policy(tmp_path: Path) -> None:
    bad_path = tmp_path / 'bad-policy.json'
    bad_path.write_text(
        render_policy_pack_json({
            'policy_id': 'bad',
            'version': 'v1',
            'rules': [
                {'rule_id': 'allow-read', 'effect': 'allow', 'conditions': {'action.mode': 'read'}},
                {'rule_id': 'deny-read', 'effect': 'deny', 'conditions': {'action.mode': 'read'}},
            ],
        }),
        encoding='utf-8',
    )

    proc = subprocess.run(
        [sys.executable, str(SCRIPT), 'validate', str(bad_path), '--json'],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    report = json.loads(proc.stdout)

    assert proc.returncode == 2
    assert report['status'] == 'failed'
    assert report['reason_code'] == 'conflicting_policy_rules'


@pytest.mark.parametrize(
    ('payload', 'reason_code'),
    [
        (
            '{"policy_id":"first","policy_id":"second","version":"1","rules":[]}',
            'json_boundary_duplicate_key',
        ),
        (
            '{"policy_id":"nan","version":"1","rules":[],"risk_score":NaN}',
            'json_boundary_non_finite_number',
        ),
    ],
)
def test_policy_authoring_rejects_ambiguous_or_non_finite_json(
    tmp_path: Path,
    payload: str,
    reason_code: str,
) -> None:
    path = tmp_path / 'invalid-boundary.json'
    path.write_text(payload, encoding='utf-8')

    with pytest.raises(GovApiError, match=reason_code):
        read_policy_pack(path)
