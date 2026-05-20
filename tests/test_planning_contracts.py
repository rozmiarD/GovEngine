from __future__ import annotations

import pytest

from govengine import (
    GovPlanIntentContract,
    GovTaskContract,
    PlannerPort,
    task_contract_from_host_task,
    validate_plan_intent_contract,
    validate_planner_port,
    validate_task_contract,
)
from govengine.api import GovApiError


def test_task_contract_models_host_task_without_raw_target_or_command() -> None:
    contract = task_contract_from_host_task(
        contract_id='task-1',
        task_family='authz',
        objective='Check boundary with public-safe evidence',
        capability='http_probe',
        action_type='differential_probe',
        target_ref='sha256:abc123',
        evidence_goal='controlled_comparison',
        priority_tier='high',
        expected_depth='deep',
        activation_phase=2,
        activation_mode='if_signal',
        conditional_gate='authenticated_or_boundary_mapping',
        constraints={'campaign_bound_context': True},
        preferences={'preferred_vector_families': ['authz']},
        rationale={'current_stage': 'control_boundary_confirmation'},
        metadata={'target_redacted': True},
    )

    payload = contract.as_dict()

    assert isinstance(contract, GovTaskContract)
    assert payload['target_ref'] == 'sha256:abc123'
    assert payload['priority_tier'] == 'high'
    assert validate_task_contract(payload).activation_phase == 2


def test_task_contract_rejects_raw_target_prompt_commands_and_credentials() -> None:
    with pytest.raises(GovApiError, match='raw_target_not_allowed'):
        validate_task_contract({'contract_id': 'task-1', 'target': 'https://example.com/'})

    for key in ('prompt', 'command', 'credential'):
        with pytest.raises(GovApiError, match=f'forbidden_planning_metadata:{key}'):
            validate_task_contract({
                'contract_id': f'task-{key}',
                'metadata': {key: 'secret-ish'},
            })


def test_plan_intent_contract_wraps_unique_task_contracts() -> None:
    task = task_contract_from_host_task(contract_id='task-1', task_family='recon', target_ref='sha256:abc')
    intent = validate_plan_intent_contract({
        'intent_id': 'plan-1',
        'profile': 'ravenclaw-security',
        'planner_id': 'planner-fixture',
        'goal': 'public-safe runtime plan',
        'task_contracts': [task.as_dict()],
        'non_claims': ['host_owns_domain_planning_semantics'],
        'metadata': {'source': 'host_projection'},
    })

    assert isinstance(intent, GovPlanIntentContract)
    assert intent.task_contracts[0].contract_id == 'task-1'
    assert intent.non_claims == ('host_owns_domain_planning_semantics',)


def test_plan_intent_rejects_duplicate_tasks_and_forbidden_metadata() -> None:
    task = task_contract_from_host_task(contract_id='task-1')

    with pytest.raises(GovApiError, match='duplicate_task_contract_id'):
        validate_plan_intent_contract({
            'intent_id': 'plan-1',
            'task_contracts': [task.as_dict(), task.as_dict()],
        })

    with pytest.raises(GovApiError, match='forbidden_planning_metadata:live_execution'):
        validate_plan_intent_contract({
            'intent_id': 'plan-2',
            'metadata': {'live_execution': True},
        })


def test_planner_port_is_descriptor_not_implementation() -> None:
    port = validate_planner_port({
        'name': 'ravenclaw-planner',
        'profile': 'ravenclaw-security',
        'supported_contracts': ['gov_task_contract', 'gov_plan_intent_contract'],
        'metadata': {'adapter': 'host-owned'},
    })

    assert isinstance(port, PlannerPort)
    assert port.as_dict()['supported_contracts'] == ['gov_task_contract', 'gov_plan_intent_contract']

    with pytest.raises(GovApiError, match='forbidden_planning_metadata:scheduler'):
        validate_planner_port({'name': 'bad', 'metadata': {'scheduler': '* * * * *'}})
