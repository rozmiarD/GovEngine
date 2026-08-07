from __future__ import annotations

from dataclasses import fields, replace

import pytest

from govengine import (
    GovApiError,
    PolicyCompiler,
    PolicyEngine,
    admit_policy_execution,
    evaluate_policy,
    explain_policy_evaluation,
    policy_enforcement_admission,
    policy_enforcement_admission_digest,
    policy_enforcement_plan_digest,
    policy_pack_digest,
    policy_verdict_digest,
    validate_policy_enforcement_admission,
    validate_policy_enforcement_plan,
)
from govengine.signing import govengine_record_digest


def _evaluate(*, constraints: list[dict] | None = None, obligations: list[dict] | None = None):
    compiled = PolicyCompiler().compile(
        {
            "policy_id": "runtime-bounds",
            "version": "1",
            "rules": [
                {
                    "rule_id": "bounded-read",
                    "effect": "allow_with_obligations",
                    "conditions": {"action.mode": "read"},
                    "obligations": obligations or [],
                    "constraints": constraints or [],
                }
            ],
        }
    )
    assert compiled.policy_pack is not None
    verdict = PolicyEngine().evaluate(
        {
            "request_id": "request-1",
            "subject_ref": "runner:operation-1",
            "action": {"mode": "read"},
        },
        compiled.policy_pack,
    )
    return compiled.policy_pack, verdict


def _compiled_parity_pack(schema_version: str):
    payload = {
        'policy_id': f'parity-{schema_version}',
        'version': '1',
        'schema_version': schema_version,
        'rules': [
            {
                'rule_id': 'allow-read',
                'effect': 'allow',
                'conditions': (
                    [{'path': 'action.mode', 'operator': 'eq', 'value': 'read'}]
                    if schema_version == 'v1'
                    else {'action.mode': 'read'}
                ),
            }
        ],
        'metadata': {'owner': 'governance'},
    }
    if schema_version == 'v1':
        payload.update(
            {
                'issuer_ref': 'organization:example',
                'policy_epoch': 7,
                'validity': {
                    'not_before': '2026-07-01T00:00:00Z',
                    'expires_at': '2026-09-01T00:00:00Z',
                },
                'supersedes': [],
            }
        )
    result = PolicyCompiler().compile(payload)
    assert result.ok
    assert result.policy_pack is not None
    return result.policy_pack


@pytest.mark.parametrize('schema_version', ['v0.1', 'v1'])
def test_safe_compiled_pack_consumers_match_detached_canonical_snapshot(
    schema_version: str,
) -> None:
    pack = _compiled_parity_pack(schema_version)
    detached_result = PolicyCompiler().compile(pack.as_dict())
    assert detached_result.ok
    assert detached_result.policy_pack is not None
    detached = detached_result.policy_pack
    assert pack == detached
    assert pack.as_dict() == detached.as_dict()
    assert '_integrity_seal' not in {item.name for item in fields(pack)}
    assert '_integrity_seal' not in repr(pack)
    request = {
        'request_id': f'request-{schema_version}',
        'subject_ref': f'artifact://request/{schema_version}',
        'action': {'mode': 'read'},
    }

    verdict = evaluate_policy(request, pack)
    detached_verdict = evaluate_policy(request, detached)
    assert verdict == detached_verdict
    assert admit_policy_execution(pack, verdict) == admit_policy_execution(
        detached,
        detached_verdict,
    )
    assert policy_pack_digest(pack) == policy_pack_digest(detached)
    assert policy_pack_digest(pack) == govengine_record_digest(
        pack,
        record_type='govengine.policy.compiler.CompiledPolicyPack',
    )
    assert explain_policy_evaluation(request, pack).as_dict() == (
        explain_policy_evaluation(request, detached).as_dict()
    )


@pytest.mark.parametrize(
    'mutation',
    ['obligation-metadata', 'constraint-value', 'constraint-metadata'],
)
def test_enforcement_consumers_reject_mutated_compiled_controls(
    mutation: str,
) -> None:
    pack, verdict = _evaluate(
        obligations=[
            {
                'obligation_id': 'receipt',
                'kind': 'receipt',
                'metadata': {'labels': {'tier': 'safe'}},
            }
        ],
        constraints=[
            {
                'constraint_id': 'network',
                'kind': 'allowed_network_egress',
                'value': ['no_network'],
                'metadata': {'labels': {'tier': 'safe'}},
            }
        ],
    )
    if mutation == 'obligation-metadata':
        labels = pack.rules[0].obligations[0].metadata['labels']
        assert isinstance(labels, dict)
        labels['tier'] = 'mutated'
    elif mutation == 'constraint-value':
        value = pack.rules[0].constraints[0].value
        assert isinstance(value, list)
        value.append('outbound_http')
    else:
        labels = pack.rules[0].constraints[0].metadata['labels']
        assert isinstance(labels, dict)
        labels['tier'] = 'mutated'

    with pytest.raises(GovApiError, match='invalid_compiled_policy_pack'):
        policy_pack_digest(pack)
    with pytest.raises(GovApiError, match='invalid_compiled_policy_pack'):
        admit_policy_execution(pack, verdict)


def test_policy_enforcement_plan_binds_pack_verdict_controls_and_admission() -> None:
    pack, verdict = _evaluate(
        obligations=[
            {"obligation_id": "receipt", "kind": "receipt"},
            {"obligation_id": "digests", "kind": "output_digest_required"},
        ],
        constraints=[
            {"constraint_id": "timeout", "kind": "timeout", "value": 5},
            {"constraint_id": "steps", "kind": "max_steps", "value": 3},
            {"constraint_id": "output", "kind": "output_limit", "value": 4096},
        ],
    )

    plan = admit_policy_execution(pack, verdict)
    admission = policy_enforcement_admission(plan)

    assert plan.allowed
    assert admission.allowed
    assert plan.policy_pack_digest == policy_pack_digest(pack)
    assert plan.verdict_digest == policy_verdict_digest(verdict)
    assert plan.controls.timeout_seconds == 5
    assert plan.controls.max_steps == 3
    assert plan.controls.max_output_bytes == 4096
    assert plan.controls.receipt_required is True
    assert plan.controls.output_digest_required is True
    assert policy_enforcement_plan_digest(plan).startswith("sha256:")
    assert policy_enforcement_admission_digest(admission).startswith("sha256:")
    assert validate_policy_enforcement_plan(
        plan,
        policy_pack=pack,
        verdict=verdict,
    ) == plan
    assert validate_policy_enforcement_admission(admission, plan=plan) == admission


def test_policy_enforcement_plan_uses_least_numeric_limit() -> None:
    pack, verdict = _evaluate(
        constraints=[
            {"constraint_id": "output-wide", "kind": "output_limit", "value": 8192},
            {"constraint_id": "output-tight", "kind": "output_limit", "value": 1024},
        ]
    )

    plan = admit_policy_execution(pack, verdict)

    assert plan.allowed
    assert plan.controls.max_output_bytes == 1024


def test_unsupported_control_is_a_fail_closed_admission() -> None:
    pack, verdict = _evaluate(
        constraints=[
            {"constraint_id": "domain", "kind": "vendor_specific", "value": True}
        ]
    )

    plan = admit_policy_execution(pack, verdict)
    admission = policy_enforcement_admission(plan)

    assert not plan.allowed
    assert not admission.allowed
    assert plan.reason_code == "unsupported_policy_constraint"
    assert plan.blockers == ("unsupported_policy_constraint",)
    with pytest.raises(GovApiError, match="policy_enforcement_not_ready"):
        validate_policy_enforcement_plan(
            plan,
            policy_pack=pack,
            verdict=verdict,
        )


def test_policy_enforcement_plan_projects_typed_execution_controls() -> None:
    pack, verdict = _evaluate(
        constraints=[
            {'constraint_id': 'no-shell', 'kind': 'no_raw_shell', 'value': True},
            {
                'constraint_id': 'network',
                'kind': 'allowed_network_egress',
                'value': ['no_network', 'outbound_http'],
            },
            {
                'constraint_id': 'backends',
                'kind': 'allowed_backend_classes',
                'value': ['static_fixture', 'http_api'],
            },
            {
                'constraint_id': 'mutation',
                'kind': 'mutation_requires_approval',
                'value': True,
            },
            {'constraint_id': 'read-only', 'kind': 'read_only_required', 'value': True},
        ]
    )

    plan = admit_policy_execution(pack, verdict)

    assert plan.allowed
    assert plan.controls.no_raw_shell is True
    assert plan.controls.read_only_required is True
    assert plan.controls.mutation_requires_approval is True
    assert plan.controls.allowed_network_egress == ('no_network', 'outbound_http')
    assert plan.controls.allowed_backend_classes == ('http_api', 'static_fixture')
    assert 'network_boundary_match' in plan.controls.typed_execution_control_ids


def test_policy_enforcement_plan_detects_binding_drift() -> None:
    pack, verdict = _evaluate()
    plan = admit_policy_execution(pack, verdict)
    drifted = replace(plan, verdict_digest="sha256:" + "0" * 64)

    with pytest.raises(GovApiError, match="policy_enforcement_plan_drift"):
        validate_policy_enforcement_plan(
            drifted,
            policy_pack=pack,
            verdict=verdict,
        )
