from __future__ import annotations

import pytest

from govengine import (
    BoundaryReport,
    DomainProfileContract,
    boundary_surface_index,
    kernel_boundary_contract,
    kernel_boundary_report,
    known_profile_contracts,
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


def test_boundary_surface_index_matches_public_surfaces() -> None:
    surfaces = boundary_surface_index()

    assert [surface['name'] for surface in surfaces] == [
        'artifact_governance_core',
        'controlled_execution_core',
        'security_profile_helpers',
    ]
    assert any('govengine.boundary' in surface['modules'] for surface in surfaces)


def test_known_profile_contracts_are_boundary_valid() -> None:
    profiles = known_profile_contracts()

    assert [profile.name for profile in profiles] == ['ravenclaw']
    for profile in profiles:
        validate_domain_profile_contract(profile)


def test_kernel_boundary_report_is_machine_readable() -> None:
    report = kernel_boundary_report()
    payload = report.as_dict()

    assert isinstance(report, BoundaryReport)
    assert payload['artifact_type'] == 'govengine_boundary_report'
    assert payload['schema_version'] == 'v0.1'
    assert payload['summary'] == {
        'profile_count': 1,
        'surface_count': 3,
        'forbidden_profile_ownership_count': 5,
    }
    assert payload['profiles'][0]['name'] == 'ravenclaw'
    assert payload['surfaces'][0]['name'] == 'artifact_governance_core'
    assert 'live_execution_authority' in payload['boundary']['forbidden_profile_ownership']


def test_kernel_boundary_report_rejects_invalid_profile_claims() -> None:
    bad = DomainProfileContract(name='bad', owns=('carrier_adapter_ownership',))

    with pytest.raises(GovApiError, match='forbidden_domain_profile_ownership:carrier_adapter_ownership'):
        kernel_boundary_report(profiles=(bad,))
