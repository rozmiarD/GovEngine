from __future__ import annotations

import ast
from pathlib import Path

import pytest

from govengine.security_profile import security_profile_groups
from govengine.surfaces import public_surface_index
from govengine.tool_registry import (
    DEFAULT_PLANNER_PROFILES_ENV,
    LEGACY_PLANNER_PROFILES_ENV,
    REGISTRY_PATH,
    get_active_planner_profile_state,
    resolve_planner_profiles,
)


ROOT = Path(__file__).resolve().parents[1]


def _source_path(module_name: str) -> Path:
    relative = Path(*module_name.split('.')).with_suffix('.py')
    return ROOT / relative


def _govengine_imports(module_name: str) -> set[str]:
    path = _source_path(module_name)
    tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    imports: set[str] = set()
    package = module_name.rsplit('.', 1)[0]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                if name.startswith('govengine.'):
                    imports.add(name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                if node.level == 0:
                    base = node.module
                else:
                    parts = package.split('.')[: max(1, len(package.split('.')) - node.level + 1)]
                    base = '.'.join([*parts, node.module])
                if base.startswith('govengine.'):
                    imports.add(base)
    return imports


def test_neutral_public_surfaces_do_not_import_optional_security_profile_modules() -> None:
    surfaces = public_surface_index()
    optional_modules = {
        module
        for surface in surfaces
        if surface.optional_profile
        for module in surface.modules
    }
    neutral_modules = {
        module
        for surface in surfaces
        if not surface.optional_profile
        for module in surface.modules
        if _source_path(module).exists()
    }

    violations: list[str] = []
    for module in sorted(neutral_modules):
        imported = _govengine_imports(module)
        forbidden = sorted(item for item in imported if item in optional_modules)
        if forbidden:
            violations.append(f'{module} -> {forbidden}')

    assert violations == []


def test_neutral_public_surfaces_do_not_embed_ravenclaw_host_assumptions() -> None:
    neutral_modules = {
        module
        for surface in public_surface_index()
        if not surface.optional_profile
        for module in surface.modules
        if _source_path(module).exists()
    }
    forbidden_fragments = (
        'ravenclaw_context',
        'RAVENCLAW_',
    )

    violations: list[str] = []
    for module in sorted(neutral_modules):
        text = _source_path(module).read_text(encoding='utf-8')
        found = sorted(fragment for fragment in forbidden_fragments if fragment in text)
        if found:
            violations.append(f'{module} -> {found}')

    assert violations == []


def test_retired_host_projection_module_is_not_reintroduced_or_exported() -> None:
    assert not (ROOT / 'govengine' / 'sclite_adapter.py').exists()

    init_text = (ROOT / 'govengine' / '__init__.py').read_text(encoding='utf-8')
    forbidden_exports = (
        'sclite_adapter',
        'build_current_lifecycle_artifacts',
        'build_proof_trace_artifacts',
    )

    violations = [fragment for fragment in forbidden_exports if fragment in init_text]

    assert violations == []


def test_neutral_public_surfaces_do_not_import_host_runtime_or_carrier_packages() -> None:
    neutral_modules = {
        module
        for surface in public_surface_index()
        if not surface.optional_profile
        for module in surface.modules
        if _source_path(module).exists()
    }
    forbidden_roots = (
        'engine',
        'ravenclaw',
        'logdash',
        'openclaw',
        'mcp',
        'a2a',
    )

    violations: list[str] = []
    for module in sorted(neutral_modules):
        path = _source_path(module)
        tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        found: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split('.', 1)[0]
                    if root in forbidden_roots:
                        found.add(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                root = node.module.split('.', 1)[0]
                if root in forbidden_roots:
                    found.add(node.module)
        if found:
            violations.append(f'{module} -> {sorted(found)}')

    assert violations == []


def test_neutral_surfaces_keep_runtime_authority_as_non_claims() -> None:
    required_by_surface = {
        'artifact_governance_core': ('key-store', 'storage', 'scheduling'),
        'planning_contracts_core': ('adapter', 'storage', 'live-execution'),
        'admission_policy_core': ('credential', 'adapter', 'live-execution'),
        'evidence_review_core': ('credential', 'adapter', 'live-execution'),
        'domain_profile_sdk': ('credential', 'adapter', 'live subprocess'),
        'runtime_contract_proofs': ('credential', 'scheduler', 'storage', 'live subprocess'),
        'controlled_execution_core': ('adapter', 'storage', 'scheduler', 'live'),
    }

    violations: list[str] = []
    for surface in public_surface_index():
        if surface.optional_profile:
            continue
        non_claims = ' '.join(surface.non_claims).lower()
        missing = [
            fragment
            for fragment in required_by_surface[surface.name]
            if fragment not in non_claims
        ]
        if missing:
            violations.append(f'{surface.name} -> {missing}')

    assert violations == []


def test_optional_helper_modules_use_neutral_host_compat_context_name() -> None:
    helper_modules = (
        'govengine.policy.core',
        'govengine.policy.gateway',
        'govengine.scope',
        'govengine.tool_registry',
    )
    violations: list[str] = []
    for module in helper_modules:
        text = _source_path(module).read_text(encoding='utf-8')
        if 'ravenclaw_context' in text:
            violations.append(module)

    assert violations == []


def test_optional_tool_registry_uses_neutral_profile_env_name_by_default() -> None:
    text = REGISTRY_PATH.read_text(encoding='utf-8')

    assert f'planner_profiles_env: {DEFAULT_PLANNER_PROFILES_ENV}' in text
    assert f'planner_profiles_env: {LEGACY_PLANNER_PROFILES_ENV}' not in text


def test_optional_tool_registry_supports_neutral_profile_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(DEFAULT_PLANNER_PROFILES_ENV, 'extended')
    monkeypatch.delenv(LEGACY_PLANNER_PROFILES_ENV, raising=False)

    assert resolve_planner_profiles(None) == ['core', 'extended']
    state = get_active_planner_profile_state()
    assert state['env_name'] == DEFAULT_PLANNER_PROFILES_ENV
    assert state['env_override_name'] == DEFAULT_PLANNER_PROFILES_ENV
    assert state['legacy_env_override'] is False


def test_optional_tool_registry_keeps_legacy_profile_env_as_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(DEFAULT_PLANNER_PROFILES_ENV, raising=False)
    monkeypatch.setenv(LEGACY_PLANNER_PROFILES_ENV, 'specialized')

    assert resolve_planner_profiles(None) == ['core', 'extended', 'specialized']
    state = get_active_planner_profile_state()
    assert state['env_name'] == DEFAULT_PLANNER_PROFILES_ENV
    assert state['env_override_name'] == LEGACY_PLANNER_PROFILES_ENV
    assert state['legacy_env_override'] is True


def test_public_surface_index_has_single_optional_security_profile() -> None:
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
    assert [surface.name for surface in surfaces if surface.optional_profile] == ['security_profile_helpers']
    execution = next(surface for surface in surfaces if surface.name == 'controlled_execution_core')
    assert 'govengine.scope_ports' in execution.modules
    assert 'govengine.scope' not in execution.modules


@pytest.mark.parametrize('group', security_profile_groups())
def test_security_profile_groups_do_not_claim_core_or_adapter_authority(group) -> None:
    joined = ' '.join([group.claim, *group.non_claims]).lower()
    forbidden_claims = (
        'govengine core ownership',
        'sclite schema ownership',
        'sclite verdict ownership',
        'live execution authority',
        'carrier adapter ownership',
        'openclaw adapter ownership',
        'mcp adapter ownership',
        'a2a adapter ownership',
        'key-store ownership',
        'kms ownership',
    )

    assert joined
    assert group.claim.lower().find('ownership') == -1
    for fragment in forbidden_claims:
        assert fragment not in group.claim.lower()
