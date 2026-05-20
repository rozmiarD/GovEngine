from __future__ import annotations

import pytest

from govengine import (
    DomainProfile,
    EvidenceRuleDeclaration,
    PlanningStageRegistry,
    ResourceTypeRegistry,
    RunnerProfileDeclaration,
    TaskFamilyRegistry,
    profile_conformance_report,
    ravenclaw_security_profile,
    tecrax_infra_ops_profile,
    validate_domain_profile,
    validate_profile_conformance,
)
from govengine.api import GovApiError


def test_ravenclaw_security_profile_is_contract_only_and_conformant() -> None:
    report = validate_profile_conformance(ravenclaw_security_profile())
    payload = report.as_dict()

    assert report.status == 'passed'
    assert payload['profile']['name'] == 'ravenclaw-security'
    assert payload['profile']['runner_profiles'][0]['mode'] == 'dry_run'
    assert payload['profile']['runner_profiles'][0]['live_enabled'] is False
    assert 'govengine_security_profile_helpers' in payload['profile']['consumes']
    assert 'govengine_domain_profile_sdk' in payload['profile']['consumes']
    assert 'Does not grant live execution authority.' in payload['profile']['non_claims']


def test_tecrax_profile_is_skeleton_fixture_only_and_conformant() -> None:
    report = validate_profile_conformance(tecrax_infra_ops_profile())
    payload = report.as_dict()

    assert report.status == 'passed'
    assert payload['profile']['name'] == 'tecrax-infra-ops'
    assert payload['profile']['runner_profiles'][0] == {
        'name': 'local_fixture_only',
        'mode': 'local_fixture',
        'live_enabled': False,
        'non_claims': [],
    }
    assert payload['profile']['metadata'] == {
        'status': 'skeleton',
        'execution_scope': 'dry_run_local_fixture_only',
    }


def test_domain_profile_boundary_contract_consumes_only_known_surfaces() -> None:
    profile = tecrax_infra_ops_profile()
    contract = profile.boundary_contract()

    assert 'govengine_planning_contracts_core' in contract.consumes
    assert 'govengine_domain_profile_sdk' in contract.consumes
    assert validate_profile_conformance(profile).boundary_report['status'] == 'passed'


def test_domain_profile_rejects_forbidden_ownership_claims() -> None:
    profile = DomainProfile(
        name='bad',
        version='0.8.0',
        owner='host',
        resource_types=ResourceTypeRegistry(('resource',)),
        task_families=TaskFamilyRegistry(('task',)),
        planning_stages=PlanningStageRegistry(('stage',)),
        owns=('live_execution_authority',),
    )

    with pytest.raises(GovApiError, match='forbidden_profile_claim:live_execution_authority'):
        validate_domain_profile(profile)


def test_domain_profile_rejects_live_or_unknown_runner_modes() -> None:
    profile = DomainProfile(
        name='bad-runner',
        version='0.8.0',
        owner='host',
        resource_types=ResourceTypeRegistry(('resource',)),
        task_families=TaskFamilyRegistry(('task',)),
        planning_stages=PlanningStageRegistry(('stage',)),
        runner_profiles=(RunnerProfileDeclaration(name='live', mode='live_subprocess', live_enabled=True),),
    )

    with pytest.raises(GovApiError, match='forbidden_runner_profile:live'):
        validate_domain_profile(profile)


def test_domain_profile_rejects_unbounded_evidence_rules() -> None:
    profile = DomainProfile(
        name='bad-evidence',
        version='0.8.0',
        owner='host',
        resource_types=ResourceTypeRegistry(('resource',)),
        task_families=TaskFamilyRegistry(('task',)),
        planning_stages=PlanningStageRegistry(('stage',)),
        evidence_rules=(EvidenceRuleDeclaration(name='raw-output', receipt_bound_required=False),),
    )

    with pytest.raises(GovApiError, match='unbounded_evidence_rule:raw-output'):
        validate_domain_profile(profile)


def test_profile_conformance_reports_missing_required_registries() -> None:
    profile = DomainProfile(
        name='incomplete',
        version='0.8.0',
        owner='host',
        resource_types=ResourceTypeRegistry(()),
        task_families=TaskFamilyRegistry(('task',)),
        planning_stages=PlanningStageRegistry(('stage',)),
    )

    with pytest.raises(GovApiError, match='missing_resource_types'):
        profile_conformance_report(profile)


def test_domain_profile_rejects_unknown_consumed_surfaces() -> None:
    profile = DomainProfile(
        name='unknown-consume',
        version='0.8.0',
        owner='host',
        resource_types=ResourceTypeRegistry(('resource',)),
        task_families=TaskFamilyRegistry(('task',)),
        planning_stages=PlanningStageRegistry(('stage',)),
        consumes=('mystery_surface',),
    )

    with pytest.raises(GovApiError, match='unknown_domain_profile_consume:mystery_surface'):
        validate_profile_conformance(profile)


def test_domain_profile_mapping_requires_real_booleans() -> None:
    with pytest.raises(GovApiError, match='invalid_profile_boolean'):
        validate_domain_profile({
            'name': 'bad-bool',
            'owner': 'host',
            'resource_types': {'names': ['resource']},
            'task_families': {'names': ['task']},
            'planning_stages': {'names': ['stage']},
            'runner_profiles': [{'name': 'runner', 'live_enabled': 'false'}],
        })
