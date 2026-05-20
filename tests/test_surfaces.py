from __future__ import annotations

from govengine.surfaces import (
    admission_policy_surface,
    artifact_governance_surface,
    controlled_execution_surface,
    domain_profile_sdk_surface,
    evidence_review_surface,
    planning_contracts_surface,
    public_surface_index,
    runtime_contract_proofs_surface,
    security_profile_surface,
    surface_by_name,
)


def test_public_surface_index_names_core_before_optional_profile() -> None:
    surfaces = public_surface_index()

    assert [surface.name for surface in surfaces] == [
        'artifact_governance_core',
        'planning_contracts_core',
        'admission_policy_core',
        'evidence_review_core',
        'domain_profile_sdk',
        'runtime_contract_proofs',
        'controlled_execution_core',
        'security_profile_helpers',
    ]
    assert surfaces[-1].optional_profile is True


def test_security_profile_is_explicitly_optional_and_does_not_own_core_gates() -> None:
    profile = security_profile_surface()

    assert profile.optional_profile is True
    assert 'govengine.action_schema' in profile.modules
    assert 'govengine.policy.gateway' in profile.modules
    assert 'govengine.core' not in profile.modules
    assert 'govengine.execution.gate' not in profile.modules
    assert any('authorization' in claim for claim in profile.non_claims)


def test_core_surfaces_keep_live_execution_and_adapter_non_claims() -> None:
    artifact = artifact_governance_surface()
    planning = planning_contracts_surface()
    admission = admission_policy_surface()
    review = evidence_review_surface()
    profiles = domain_profile_sdk_surface()
    proofs = runtime_contract_proofs_surface()
    execution = controlled_execution_surface()

    assert artifact.optional_profile is False
    assert planning.optional_profile is False
    assert admission.optional_profile is False
    assert review.optional_profile is False
    assert profiles.optional_profile is False
    assert proofs.optional_profile is False
    assert execution.optional_profile is False
    assert 'govengine.boundary' in artifact.modules
    assert 'govengine.signing' in artifact.modules
    assert 'govengine.state_machine' in artifact.modules
    assert 'govengine.planning' in planning.modules
    assert 'govengine.admission' in admission.modules
    assert 'govengine.review' in review.modules
    assert 'govengine.profiles' in profiles.modules
    assert 'govengine.contract_proofs' in proofs.modules
    assert 'govengine.execution.gate' in execution.modules
    assert 'govengine.execution.supervision' in execution.modules
    assert 'govengine.orchestration' in execution.modules
    assert 'govengine.events' in execution.modules
    assert 'govengine.control' in execution.modules
    assert 'govengine.runtime_shell' in execution.modules
    assert 'raw-intent execution' in execution.non_claims
    assert 'planner implementation ownership' in planning.non_claims
    assert 'raw target or prompt ownership' in planning.non_claims
    assert 'domain policy meaning ownership' in admission.non_claims
    assert 'SCLite review-bundle verdict ownership' in review.non_claims
    assert 'default live subprocess execution' in profiles.non_claims
    assert 'carrier adapter ownership' in profiles.non_claims
    assert 'new OODA surface' in proofs.non_claims
    assert 'carrier adapter ownership' in proofs.non_claims
    assert 'default live subprocess execution' in execution.non_claims
    assert 'protocol adapter ownership' in execution.non_claims
    assert 'runtime storage or scheduler ownership' in execution.non_claims
    assert 'live backend ownership' in execution.non_claims


def test_surface_metadata_is_public_safe_and_lookup_is_strict() -> None:
    forbidden_fragments = ('Ravenclaw engine/', 'Logdash UI/API', 'OpenClaw session wiring')

    for surface in public_surface_index():
        payload = surface.as_dict()
        assert payload['name'] == surface.name
        assert payload['modules'] == list(surface.modules)
        joined = repr(payload)
        assert all(fragment not in joined for fragment in forbidden_fragments)

    assert surface_by_name('planning_contracts_core').name == 'planning_contracts_core'
    assert surface_by_name('admission_policy_core').name == 'admission_policy_core'
    assert surface_by_name('evidence_review_core').name == 'evidence_review_core'
    assert surface_by_name('domain_profile_sdk').name == 'domain_profile_sdk'
    assert surface_by_name('runtime_contract_proofs').name == 'runtime_contract_proofs'
    assert surface_by_name('controlled_execution_core').name == 'controlled_execution_core'

    try:
        surface_by_name('missing')
    except KeyError as exc:
        assert exc.args == ('missing',)
    else:  # pragma: no cover
        raise AssertionError('missing surface should raise KeyError')
