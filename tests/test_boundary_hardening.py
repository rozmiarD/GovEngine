from __future__ import annotations

import ast
from pathlib import Path

from govengine.surfaces import public_surface_index


ROOT = Path(__file__).resolve().parents[1]
RETIRED_SECURITY_MODULES = (
    'govengine.security_profile',
    'govengine.action_schema',
    'govengine.action_validators',
    'govengine.action_compiler',
    'govengine.capability_recipes',
    'govengine.tool_registry',
    'govengine.semantic_loss_policy',
    'govengine.policy.core',
    'govengine.policy.gateway',
    'govengine.scope',
    'govengine.contracts.signal',
    'govengine.contracts.analysis',
    'govengine.contracts.evidence_policy',
)


def _source_path(module_name: str) -> Path:
    return ROOT / Path(*module_name.split('.')).with_suffix('.py')


def test_retired_security_modules_are_not_reintroduced() -> None:
    assert [module for module in RETIRED_SECURITY_MODULES if _source_path(module).exists()] == []


def test_public_surface_index_has_neutral_surfaces_only() -> None:
    surfaces = public_surface_index()

    assert [surface.name for surface in surfaces] == [
        'artifact_governance_core',
        'planning_contracts_core',
        'admission_policy_core',
        'evidence_review_core',
        'domain_profile_sdk',
        'runtime_contract_proofs',
        'controlled_execution_core',
    ]
    assert all(surface.optional_profile is False for surface in surfaces)
    execution = surfaces[-1]
    assert 'govengine.scope_ports' in execution.modules


def test_public_surfaces_do_not_import_retired_security_modules() -> None:
    retired = set(RETIRED_SECURITY_MODULES)
    violations: list[str] = []
    for surface in public_surface_index():
        for module in surface.modules:
            path = _source_path(module)
            if not path.exists():
                continue
            tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
            imports = {
                node.module
                for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module
            }
            imports.update(
                alias.name
                for node in ast.walk(tree)
                if isinstance(node, ast.Import)
                for alias in node.names
            )
            forbidden = sorted(imports & retired)
            if forbidden:
                violations.append(f'{module} -> {forbidden}')

    assert violations == []


def test_neutral_public_surfaces_do_not_import_host_runtime_or_carrier_packages() -> None:
    forbidden_roots = {'engine', 'ravenclaw', 'logdash', 'openclaw', 'mcp', 'a2a'}
    violations: list[str] = []
    for surface in public_surface_index():
        for module in surface.modules:
            path = _source_path(module)
            if not path.exists():
                continue
            tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
            found: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    found.update(alias.name for alias in node.names if alias.name.split('.', 1)[0] in forbidden_roots)
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    if node.module.split('.', 1)[0] in forbidden_roots:
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
        non_claims = ' '.join(surface.non_claims).lower()
        missing = [fragment for fragment in required_by_surface[surface.name] if fragment not in non_claims]
        if missing:
            violations.append(f'{surface.name} -> {missing}')

    assert violations == []


def test_public_docs_keep_live_backend_disabled_by_default_non_claims() -> None:
    api_boundary = (ROOT / 'docs' / 'API_BOUNDARY.md').read_text(encoding='utf-8')
    runner_supervision = (ROOT / 'docs' / 'RUNNER_SUPERVISION.md').read_text(encoding='utf-8')
    validation = (ROOT / 'docs' / 'VALIDATION.md').read_text(encoding='utf-8')
    combined = ' '.join(f'{api_boundary}\n{runner_supervision}\n{validation}'.split())

    required_markers = (
        'Live subprocess execution is intentionally absent',
        'remains disabled by default',
        'does not provide a live subprocess runner',
        'not implementation permission',
        'dry-run remains the default profile',
        'live backend implementation remain host-owned',
        'no live subprocess backend',
    )

    for marker in required_markers:
        assert marker in combined
