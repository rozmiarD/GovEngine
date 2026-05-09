from __future__ import annotations

import json

from govengine.security_profile import (
    assert_security_profile_boundary,
    import_security_profile_module,
    security_profile_groups,
    security_profile_index,
    security_profile_module_names,
)
from govengine.surfaces import public_surface_index, security_profile_surface


def test_security_profile_facade_matches_public_surface_registry() -> None:
    surface = security_profile_surface()

    assert security_profile_module_names() == surface.modules
    assert surface.optional_profile is True
    assert surface == public_surface_index()[-1]


def test_security_profile_index_is_json_safe_and_grouped() -> None:
    payload = security_profile_index()

    assert payload['entrypoint'] == 'govengine.security_profile'
    assert payload['surface']['name'] == 'security_profile_helpers'
    assert payload['surface']['optional_profile'] is True
    assert [group['name'] for group in payload['groups']] == [
        'action_tooling',
        'policy_scope',
        'review_contracts',
    ]
    assert json.loads(json.dumps(payload)) == payload


def test_security_profile_groups_cover_exact_surface_modules() -> None:
    grouped = tuple(module for group in security_profile_groups() for module in group.modules)

    assert grouped == security_profile_module_names()
    assert len(grouped) == len(set(grouped))


def test_security_profile_lazy_import_is_allowlisted() -> None:
    module = import_security_profile_module('govengine.action_schema')

    assert module.DEFAULT_ACTION_TYPE == 'single_probe'

    try:
        import_security_profile_module('govengine.core')
    except KeyError as exc:
        assert exc.args == ('govengine.core',)
    else:  # pragma: no cover
        raise AssertionError('core module should not be importable through the security profile facade')


def test_security_profile_boundary_assertion_documents_non_claims() -> None:
    assert_security_profile_boundary()

    profile = security_profile_surface()
    assert 'govengine.core' not in profile.modules
    assert 'govengine.execution.gate' not in profile.modules
    assert any('OpenClaw/MCP/A2A adapter ownership' == claim for claim in profile.non_claims)
