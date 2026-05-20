from __future__ import annotations

import ast
from pathlib import Path

import pytest

from govengine.security_profile import security_profile_groups
from govengine.surfaces import public_surface_index


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
