from __future__ import annotations

import pytest

from govengine import (
    DomainProfileContract,
    kernel_boundary_contract,
    ravenclaw_profile_contract,
    validate_domain_profile_contract,
)
from govengine.api import GovApiError


def test_kernel_boundary_contract_is_json_safe_and_separates_owners() -> None:
    payload = kernel_boundary_contract().as_dict()

    assert 'controlled_execution_gates' in payload['kernel_owns']
    assert 'domain_policy_meaning' in payload['profile_owns']
    assert 'concrete_tool_execution' in payload['runtime_owns']
    assert 'schemas' in payload['sclite_owns']
    assert 'live_execution_authority' in payload['forbidden_profile_ownership']
    assert any('does not authorize live execution' in claim for claim in payload['non_claims'])


def test_domain_profile_contract_accepts_profile_owned_meaning() -> None:
    contract = validate_domain_profile_contract({
        'name': 'tecrax',
        'owner': 'host_runtime',
        'owns': ['infrastructure_domain_profile', 'change_management_language'],
        'consumes': ['govengine_controlled_execution_core', 'sclite_review_bundles'],
        'non_claims': ['Does not make GovEngine own infrastructure credentials.'],
        'metadata': {'status': 'reserved'},
    })

    assert contract.name == 'tecrax'
    assert contract.owner == 'host_runtime'
    assert contract.as_dict()['metadata'] == {'status': 'reserved'}


def test_domain_profile_contract_rejects_missing_name() -> None:
    with pytest.raises(GovApiError, match='missing_domain_profile_name'):
        DomainProfileContract.from_mapping({'owns': ['domain_policy_meaning']})


def test_domain_profile_contract_rejects_forbidden_ownership() -> None:
    with pytest.raises(GovApiError, match='forbidden_domain_profile_ownership:live_execution_authority'):
        validate_domain_profile_contract({
            'name': 'bad-profile',
            'owns': ['domain_policy_meaning', 'live_execution_authority'],
        })


def test_ravenclaw_profile_contract_keeps_runtime_concerns_out_of_kernel() -> None:
    contract = ravenclaw_profile_contract()

    assert contract.name == 'ravenclaw'
    assert 'security_research_domain_profile' in contract.owns
    assert 'logdash_operator_ui' in contract.owns
    assert 'govengine_controlled_execution_core' in contract.consumes
    validate_domain_profile_contract(contract)
