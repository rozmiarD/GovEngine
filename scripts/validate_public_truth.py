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


SURFACE_HEADINGS = {
    'Artifact-governance core': 'artifact_governance_core',
    'Planning-contracts core': 'planning_contracts_core',
    'Admission-policy core': 'admission_policy_core',
    'Evidence-review core': 'evidence_review_core',
    'Domain-profile SDK': 'domain_profile_sdk',
    'Runtime contract proofs': 'runtime_contract_proofs',
    'Controlled-execution core': 'controlled_execution_core',
    'Optional security-profile helpers': 'security_profile_helpers',
}

STATUS_MARKERS = {
    'artifact_governance_core': 'Core artifact governance boundaries',
    'planning_contracts_core': 'Planning contracts',
    'admission_policy_core': 'Admission/policy contracts',
    'evidence_review_core': 'Evidence review contracts',
    'domain_profile_sdk': 'Domain profile SDK',
    'runtime_contract_proofs': 'Runtime contract proofs',
    'controlled_execution_core': 'Controlled execution gate',
    'security_profile_helpers': 'Security profile',
}

CURRENT_ALPHA_DOCS = (
    'README.md',
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
        r'.{0,80}`?(0\.1\.6|0\.1\.7|0\.2\.0|0\.3\.0|0\.4\.0|0\.5\.0|0\.6\.0)`?',
        flags=re.MULTILINE,
    )
    for path in paths:
        text = _read(path)
        for match in stale_current.finditer(text):
            raise AssertionError(f'{path}:stale_current_claim:{match.group(0)}')


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


def main() -> int:
    project = _pyproject()['project']
    version = str(project['version'])
    release_label = '0.10.0-alpha' if version == '0.10.0a0' else version
    dependency = _project_dependency(project, 'sclite-core')
    surfaces = public_surface_index()
    surface_names = [surface.name for surface in surfaces]

    if package_version != version:
        raise AssertionError(f'package_version_mismatch:{package_version}!={version}')

    readme = _read('README.md')
    roadmap = _read('docs/ROADMAP.md')
    public_status = _read('PUBLIC_STATUS.md')
    publishing = _read('PUBLISHING.md')
    validation = _read('docs/VALIDATION.md')
    api_boundary = _read('docs/API_BOUNDARY.md')

    _assert_contains('README.md', readme, f'alpha {version}')
    _assert_contains('README.md', readme, release_label)
    _assert_contains('README.md', readme, dependency)
    _assert_contains('docs/ROADMAP.md', roadmap, f'Current source baseline: `govengine=={version}`')
    _assert_contains('docs/ROADMAP.md', roadmap, dependency)
    _assert_contains('PUBLIC_STATUS.md', public_status, f'Source version: `{version}`.')
    _assert_contains('PUBLIC_STATUS.md', public_status, f'Public release label: `{release_label}`.')
    _assert_contains('PUBLIC_STATUS.md', public_status, dependency)
    _assert_contains('PUBLISHING.md', publishing, dependency)
    _assert_contains('docs/VALIDATION.md', validation, f'current `{version}` source line')

    documented = _documented_surface_names(api_boundary)
    if documented != surface_names:
        raise AssertionError(f'api_boundary_surface_mismatch:{documented}!={surface_names}')

    for surface in surfaces:
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
