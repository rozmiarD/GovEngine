from __future__ import annotations

from dataclasses import replace

import pytest

from govengine import (
    GovApiError,
    PolicyCompiler,
    PolicyEngine,
    admit_policy_execution,
    policy_enforcement_admission,
    policy_enforcement_admission_digest,
    policy_enforcement_plan_digest,
    policy_pack_digest,
    policy_verdict_digest,
    validate_policy_enforcement_admission,
    validate_policy_enforcement_plan,
)


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
