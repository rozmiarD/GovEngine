from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from govengine import __version__ as package_version  # noqa: E402
from govengine.contract_proofs import ravenclaw_contract_proof, tecrax_contract_proof  # noqa: E402
from govengine.surfaces import public_surface_index  # noqa: E402

EXPECTED_RELEASE_LABEL = '0.12.0-alpha'
PUBLISHED_VERSION = '0.12.0a0'

SURFACE_HEADINGS = {
    'Artifact-governance core': 'artifact_governance_core',
    'Planning-contracts core': 'planning_contracts_core',
    'Admission-policy core': 'admission_policy_core',
    'Evidence-review core': 'evidence_review_core',
    'Domain-profile SDK': 'domain_profile_sdk',
    'Runtime contract proofs': 'runtime_contract_proofs',
    'Controlled-execution core': 'controlled_execution_core',
}

STATUS_MARKERS = {
    'artifact_governance_core': 'Core artifact governance boundaries',
    'planning_contracts_core': 'Planning contracts',
    'admission_policy_core': 'Admission/policy contracts',
    'evidence_review_core': 'Evidence review contracts',
    'domain_profile_sdk': 'Domain profile SDK',
    'runtime_contract_proofs': 'Runtime contract proofs',
    'controlled_execution_core': 'Controlled execution gate',
}

CURRENT_ALPHA_DOCS = (
    'README.md',
    'CONTRIBUTING.md',
    'PUBLIC_STATUS.md',
    'SECURITY.md',
    'docs/ARCHITECTURE.md',
    'docs/API_BOUNDARY.md',
    'docs/ROADMAP.md',
)


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


def _pyproject() -> dict:
    return tomllib.loads(_read('pyproject.toml'))


def _project_dependency(project: dict, name: str) -> str:
    prefix = f'{name}>='
    for dependency in project.get('dependencies', []):
        if str(dependency).startswith(prefix):
            return str(dependency)
    raise AssertionError(f'missing_dependency:{name}')


def _assert_contains(path: str, text: str, expected: str) -> None:
    if expected not in text:
        raise AssertionError(f'{path}:missing:{expected}')


def _documented_surface_names(api_boundary: str) -> list[str]:
    names: list[str] = []
    for heading in re.findall(r'^### (.+)$', api_boundary, flags=re.MULTILINE):
        if heading in SURFACE_HEADINGS:
            names.append(SURFACE_HEADINGS[heading])
    return names


def _module_is_documented(module: str, api_boundary: str) -> bool:
    if f'`{module}`' in api_boundary:
        return True
    parts = module.split('.')
    for idx in range(1, len(parts)):
        wildcard = '.'.join(parts[:idx]) + '.*'
        if f'`{wildcard}`' in api_boundary:
            return True
    return False


def _assert_no_current_stale_status(paths: Iterable[str], version: str) -> None:
    del version
    stale_current = re.compile(
        r'(current|Current|source baseline|Source version|Version:|PyPI publication: completed through)'
        r'.{0,80}`?(0\.1\.6|0\.1\.7|0\.2\.0|0\.3\.0|0\.4\.0|0\.5\.0|0\.6\.0(?!a0))`?',
        flags=re.MULTILINE,
    )
    for path in paths:
        text = _read(path)
        for match in stale_current.finditer(text):
            raise AssertionError(f'{path}:stale_current_claim:{match.group(0)}')


def _assert_readme_package_truth(readme: str, version: str) -> None:
    release_url = f'https://pypi.org/project/govengine/{PUBLISHED_VERSION}/'
    badge = f'source-govengine%20{version}-blueviolet.svg'
    install_command = f'python -m pip install govengine=={PUBLISHED_VERSION}'
    forbidden_dynamic_badges = (
        'img.shields.io/pypi/v/govengine',
        'label=package%3A%20govengine',
    )
    for marker in forbidden_dynamic_badges:
        if marker in readme:
            raise AssertionError(f'README.md:dynamic_prerelease_unsafe_badge:{marker}')
    _assert_contains('README.md', readme, badge)
    _assert_contains('README.md', readme, release_url)
    _assert_contains('README.md', readme, install_command)
    unpinned_install = re.compile(r'python -m pip install govengine(?![=<>\[])')
    match = unpinned_install.search(readme)
    if match:
        raise AssertionError(f'README.md:unpinned_alpha_install:{match.group(0)}')


def _assert_alpha_maturity_truth(paths: Iterable[str]) -> None:
    forbidden = re.compile(r'\bcurrent\s+pre-alpha\b|\bcurrently\s+pre-alpha\b|\bin\s+pre-alpha\s+form\b', re.IGNORECASE)
    for path in paths:
        text = _read(path)
        match = forbidden.search(text)
        if match:
            raise AssertionError(f'{path}:stale_maturity_claim:{match.group(0)}')
    _assert_contains('SECURITY.md', _read('SECURITY.md'), 'currently alpha and still pre-1.0')
    _assert_contains('docs/ARCHITECTURE.md', _read('docs/ARCHITECTURE.md'), 'kernel in alpha form')
    _assert_contains('docs/API_BOUNDARY.md', _read('docs/API_BOUNDARY.md'), 'current alpha public surface set')


def _assert_roadmap_current_release_truth(roadmap: str) -> None:
    stale_markers = (
        '## Current implemented baseline: 0.10.x alpha',
        'GovEngine stays on the 0.10 alpha stabilization line',
    )
    for marker in stale_markers:
        if marker in roadmap:
            raise AssertionError(f'docs/ROADMAP.md:stale_current_roadmap_claim:{marker}')
    _assert_contains('docs/ROADMAP.md', roadmap, '## Current 0.12.x alpha line')
    _assert_contains('docs/ROADMAP.md', roadmap, 'The current `0.12.x` alpha line')
    _assert_contains('docs/ROADMAP.md', roadmap, 'Published PyPI baseline is `govengine==0.12.0a0`')


def _assert_validation_current_gate_precedes_history(validation: str, version: str) -> None:
    current_heading = '## Current source-line gate'
    historical_heading = '## Historical validation records'
    current_expectation = f'Expected result for the current `{version}` source line'
    current_pos = validation.find(current_heading)
    historical_pos = validation.find(historical_heading)
    expectation_pos = validation.find(current_expectation)
    if min(current_pos, historical_pos, expectation_pos) < 0:
        raise AssertionError('docs/VALIDATION.md:missing_current_or_historical_section')
    if not current_pos < expectation_pos < historical_pos:
        raise AssertionError('docs/VALIDATION.md:current_gate_not_before_history')
    _assert_contains('docs/VALIDATION.md', validation, 'not the active gate')


def _assert_clean_pip_check_guidance(contributing: str, validation: str, publishing: str) -> None:
    current_validation = validation.split('## Historical validation records', 1)[0]
    for path, text in (
        ('CONTRIBUTING.md', contributing),
        ('docs/VALIDATION.md', current_validation),
        ('PUBLISHING.md', publishing),
    ):
        if re.search(r'(?m)^python -m pip check\s*$', text):
            raise AssertionError(f'{path}:unscoped_pip_check_guidance')


def main() -> int:
    project = _pyproject()['project']
    version = str(project['version'])
    release_label = EXPECTED_RELEASE_LABEL
    dependency = _project_dependency(project, 'sclite-core')
    surfaces = public_surface_index()
    surface_names = [surface.name for surface in surfaces]

    if package_version != version:
        raise AssertionError(f'package_version_mismatch:{package_version}!={version}')

    readme = _read('README.md')
    roadmap = _read('docs/ROADMAP.md')
    public_status = _read('PUBLIC_STATUS.md')
    contributing = _read('CONTRIBUTING.md')
    publishing = _read('PUBLISHING.md')
    validation = _read('docs/VALIDATION.md')
    api_boundary = _read('docs/API_BOUNDARY.md')
    sclite_integration = _read('docs/SCLITE_INTEGRATION.md')
    domain_profile = _read('docs/DOMAIN_PROFILE_CONTRACT.md')
    workflow = _read('.github/workflows/pytest.yml')
    clean_install_script = _read('scripts/validate_clean_package_install.py')

    _assert_contains('README.md', readme, f'alpha package {version}')
    _assert_contains('README.md', readme, release_label)
    _assert_contains('README.md', readme, dependency)
    _assert_readme_package_truth(readme, version)
    _assert_contains('README.md', readme, '## License and provenance')
    _assert_contains('README.md', readme, 'originating Ravenclaw contribution lineage')
    _assert_contains('README.md', readme, 'package maintainer')
    _assert_contains('CONTRIBUTING.md', contributing, f'alpha candidate (`{release_label}`)')
    _assert_contains('CONTRIBUTING.md', contributing, 'scripts/validate_clean_package_install.py')
    _assert_contains('docs/ROADMAP.md', roadmap, f'Current source baseline: `govengine=={version}`')
    _assert_contains('docs/ROADMAP.md', roadmap, dependency)
    _assert_roadmap_current_release_truth(roadmap)
    _assert_contains('PUBLIC_STATUS.md', public_status, f'Source/package version: `{version}`.')
    _assert_contains('PUBLIC_STATUS.md', public_status, f'Release label: `{release_label}`.')
    _assert_contains('PUBLIC_STATUS.md', public_status, f'PyPI package: `govengine=={PUBLISHED_VERSION}` is the published current alpha package.')
    _assert_contains('PUBLIC_STATUS.md', public_status, dependency)
    _assert_contains('PUBLISHING.md', publishing, dependency)
    _assert_contains('PUBLISHING.md', publishing, 'scripts/validate_clean_package_install.py')
    _assert_contains('PUBLISHING.md', publishing, '--no-editable')
    _assert_contains('docs/VALIDATION.md', validation, f'current `{version}` source line')
    _assert_contains('docs/VALIDATION.md', validation, 'scripts/validate_clean_package_install.py')
    _assert_contains('docs/VALIDATION.md', validation, '--no-editable')
    _assert_contains('docs/VALIDATION.md', validation, 'broad system interpreter is not')
    _assert_validation_current_gate_precedes_history(validation, version)
    _assert_clean_pip_check_guidance(contributing, validation, publishing)
    _assert_contains('scripts/validate_clean_package_install.py', clean_install_script, "'-m', 'pip', 'check'")
    _assert_contains('scripts/validate_clean_package_install.py', clean_install_script, 'venv_already_exists_choose_new_path')
    if (ROOT / 'govengine/sclite_adapter.py').exists():
        raise AssertionError('govengine/sclite_adapter.py:retired_host_projection_present')
    retired_modules = (
        'security_profile.py',
        'action_schema.py',
        'action_validators.py',
        'action_compiler.py',
        'capability_recipes.py',
        'tool_registry.py',
        'semantic_loss_policy.py',
        'scope.py',
        'policy/core.py',
        'policy/gateway.py',
        'contracts/signal.py',
        'contracts/analysis.py',
        'contracts/evidence_policy.py',
    )
    for relative in retired_modules:
        if (ROOT / 'govengine' / relative).exists():
            raise AssertionError(f'govengine/{relative}:retired_security_module_present')
    if 'security_profile_helpers' in surface_names:
        raise AssertionError('security_profile_helpers:retired_surface_present')
    _assert_contains('PUBLIC_STATUS.md', public_status, 'Ravenclaw owns lifecycle artifact projection from its runtime payloads')
    _assert_contains('docs/API_BOUNDARY.md', api_boundary, 'Host-owned lifecycle projection is outside GovEngine')
    _assert_contains('docs/SCLITE_INTEGRATION.md', sclite_integration, 'Host-owned artifact projection is outside GovEngine')
    _assert_contains('docs/DOMAIN_PROFILE_CONTRACT.md', domain_profile, 'dry-run/local-fixture skeleton used for conformance pressure')
    if 'unreleased deterministic demo signer/verifier ports' in public_status:
        raise AssertionError('PUBLIC_STATUS.md:published_demo_ports_marked_unreleased')
    _assert_contains(
        '.github/workflows/pytest.yml',
        workflow,
        'sclite-core @ git+https://github.com/rozmiarD/SCLite.git@main',
    )
    _assert_contains('.github/workflows/pytest.yml', workflow, "python-version: ['3.11', '3.12', '3.13']")
    _assert_contains('.github/workflows/pytest.yml', workflow, 'python scripts/validate_public_truth.py')
    _assert_contains('.github/workflows/pytest.yml', workflow, 'python scripts/validate_alpha_readiness.py')
    _assert_contains('.github/workflows/pytest.yml', workflow, 'package-dry-run:')
    _assert_contains('.github/workflows/pytest.yml', workflow, 'rm -rf dist build *.egg-info')
    _assert_contains('.github/workflows/pytest.yml', workflow, 'python -m twine check dist/*')
    _assert_contains('.github/workflows/pytest.yml', workflow, '/tmp/govengine-wheel-smoke/bin/python -m pip check')

    documented = _documented_surface_names(api_boundary)
    if documented != surface_names:
        raise AssertionError(f'api_boundary_surface_mismatch:{documented}!={surface_names}')

    for surface in surfaces:
        if not surface.status.startswith('alpha_'):
            raise AssertionError(f'surface_status_not_alpha:{surface.name}:{surface.status}')
        marker = STATUS_MARKERS[surface.name]
        _assert_contains('PUBLIC_STATUS.md', public_status, marker)
        for module in surface.modules:
            if not _module_is_documented(module, api_boundary):
                raise AssertionError(f'docs/API_BOUNDARY.md:missing_module:{module}')

    for proof in (ravenclaw_contract_proof(), tecrax_contract_proof()):
        if proof.profile_conformance.status != 'passed':
            raise AssertionError(f'contract_proof_failed:{proof.proof_id}')

    _assert_no_current_stale_status(
        (
            'README.md',
            'PUBLIC_STATUS.md',
            'PUBLISHING.md',
            'docs/ROADMAP.md',
            'docs/API_BOUNDARY.md',
            'docs/VALIDATION.md',
        ),
        version,
    )
    _assert_alpha_maturity_truth(CURRENT_ALPHA_DOCS)

    print(f'public_truth_ok:govengine=={version}:{dependency}:surfaces={len(surface_names)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
