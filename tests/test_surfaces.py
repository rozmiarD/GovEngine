from __future__ import annotations

from govengine.surfaces import (
    artifact_governance_surface,
    controlled_execution_surface,
    public_surface_index,
    security_profile_surface,
    surface_by_name,
)


def test_public_surface_index_names_core_before_optional_profile() -> None:
    surfaces = public_surface_index()

    assert [surface.name for surface in surfaces] == [
        'artifact_governance_core',
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
    execution = controlled_execution_surface()

    assert artifact.optional_profile is False
    assert execution.optional_profile is False
    assert 'govengine.boundary' in artifact.modules
    assert 'govengine.signing' in artifact.modules
    assert 'govengine.execution.gate' in execution.modules
    assert 'raw-intent execution' in execution.non_claims
    assert 'default live subprocess execution' in execution.non_claims
    assert 'protocol adapter ownership' in execution.non_claims


def test_surface_metadata_is_public_safe_and_lookup_is_strict() -> None:
    forbidden_fragments = ('Ravenclaw engine/', 'Logdash UI/API', 'OpenClaw session wiring')

    for surface in public_surface_index():
        payload = surface.as_dict()
        assert payload['name'] == surface.name
        assert payload['modules'] == list(surface.modules)
        joined = repr(payload)
        assert all(fragment not in joined for fragment in forbidden_fragments)

    assert surface_by_name('controlled_execution_core').name == 'controlled_execution_core'

    try:
        surface_by_name('missing')
    except KeyError as exc:
        assert exc.args == ('missing',)
    else:  # pragma: no cover
        raise AssertionError('missing surface should raise KeyError')
