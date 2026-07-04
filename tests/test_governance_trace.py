from __future__ import annotations

import pytest

from govengine import (
    GovApiError,
    PolicyCompiler,
    PolicyEngine,
    admit_policy_execution,
    policy_enforcement_admission,
    policy_enforcement_admission_digest,
    policy_enforcement_plan_digest,
    policy_request_digest,
    project_governance_trace,
)
from govengine.governance_trace import GovernanceTrace


def _bindings() -> tuple[dict, dict, dict]:
    compiled = PolicyCompiler().compile(
        {
            'policy_id': 'runtime-bounds',
            'version': '1',
            'rules': [
                {
                    'rule_id': 'bounded-read',
                    'effect': 'allow_with_obligations',
                    'conditions': {'action.mode': 'read'},
                    'obligations': [
                        {'obligation_id': 'receipt', 'kind': 'receipt'},
                        {'obligation_id': 'digests', 'kind': 'output_digest_required'},
                    ],
                    'constraints': [
                        {'constraint_id': 'readonly', 'kind': 'read_only_required', 'value': True},
                    ],
                }
            ],
        }
    )
    assert compiled.policy_pack is not None
    request = {
        'request_id': 'op-policy:operation-1',
        'subject_ref': 'rexecop:operation-1',
        'action': {'mode': 'read', 'intent': 'inspect_fixture_state'},
        'resource': {'target_ref': 'fixture-1', 'criticality': 'low'},
        'context': {'profile': 'runtime_fixture', 'environment': 'fixture-env'},
    }
    verdict = PolicyEngine().evaluate(request, compiled.policy_pack)
    plan = admit_policy_execution(compiled.policy_pack, verdict)
    admission = policy_enforcement_admission(plan)
    enforcement = {
        'plan': plan.as_dict(),
        'plan_digest': policy_enforcement_plan_digest(plan),
        'admission': admission.as_dict(),
        'admission_digest': policy_enforcement_admission_digest(admission),
    }
    return request, verdict.as_dict(), enforcement


def test_project_governance_trace_binds_digest_chain() -> None:
    request, verdict, enforcement = _bindings()

    trace = project_governance_trace(
        policy_request=request,
        policy_verdict=verdict,
        policy_enforcement=enforcement,
    )

    assert isinstance(trace, GovernanceTrace)
    assert trace.schema_version == 'v0.1'
    assert trace.trace_digest.startswith('sha256:')
    assert trace.policy_request_digest == policy_request_digest(request)
    assert trace.enforcement_plan_digest == enforcement['plan_digest']
    assert trace.admission_digest == enforcement['admission_digest']
    assert 'receipt_required' in trace.required_controls
    assert 'read_only_posture' in trace.required_controls
    assert trace.evidence_requirements
    assert trace.as_dict()['non_claims']


def test_project_governance_trace_rejects_digest_drift() -> None:
    request, verdict, enforcement = _bindings()
    enforcement = dict(enforcement)
    enforcement['plan_digest'] = 'sha256:' + 'f' * 64

    with pytest.raises(GovApiError, match='policy_enforcement_plan_digest_mismatch'):
        project_governance_trace(
            policy_request=request,
            policy_verdict=verdict,
            policy_enforcement=enforcement,
        )