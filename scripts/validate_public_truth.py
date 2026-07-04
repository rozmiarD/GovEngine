from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path
from typing import Iterable, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from govengine import __version__ as package_version  # noqa: E402
from govengine.contract_proofs import ravenclaw_contract_proof, tecrax_contract_proof  # noqa: E402
from govengine.surfaces import public_surface_index  # noqa: E402

EXPECTED_RELEASE_LABEL = '0.16.7'
PUBLISHED_VERSION = '0.16.7'

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

MVP_SURFACE_DOC_MARKERS = {
    'docs/RUNTIME_ADMISSION.md': (
        'RuntimeAdmissionResult',
        'Intent is not execution authority.',
        'missing policy blocks',
        'missing receipt obligation blocks',
        'production\nruntime readiness',
    ),
    'docs/RECEIPT_BINDING.md': (
        'GovRunnerReceiptBinding',
        'validate_runner_receipt_binding()',
        'A receipt without admission and ticket bindings is not runtime evidence.',
        'store raw evidence, or\nenable live execution',
    ),
    'docs/EVIDENCE_REVIEW.md': (
        'validate_evidence_review_chain()',
        'admission -> receipt -> evidence -> review',
        'does not store raw evidence',
        'evaluate SCLite review-bundle verdicts',
        'stores raw evidence, or grants live execution authority',
    ),
    'docs/ADMISSION_POLICY.md': (
        'AuditLedgerPort',
        'JsonlAuditLedgerAdapter',
        'development-only JSONL hash-chain adapter',
        'does not choose a production database',
        'concurrency',
    ),
    'docs/SCLITE_INTEGRATION.md': (
        'ReplayClaimStore',
        'claim-once adapter',
        'GUARDED_FRESH_RUNTIME_ADMISSION_EXAMPLE.md',
        'validate_runner_receipt_binding()',
        'validate_evidence_review_chain()',
    ),
    'docs/RUNNER_SUPERVISION.md': (
        'Live Runner Safety Specification',
        'GovEngine does not provide a live subprocess runner in this stage.',
        'live_backend_enabled',
        'LocalSubprocessRunner',
        'Current stage decision: `not_applicable`.',
    ),
    'docs/SECURITY_INTEGRATION.md': (
        'SCLite secure verification',
        '`RuntimeAdmissionResult` is not proof and not execution authority',
        'PKI, KMS, CA, HSM, private key storage',
        '`JsonlAuditLedgerAdapter` is a development JSONL hash-chain adapter',
    ),
}

VERSION_TRUTH_FIELDS = {
    'source_version': 'pyproject.toml:project.version',
    'package_init_version': 'govengine.__init__.__version__',
    'published_pypi_version': 'PyPI install pin / README badge',
    'release_label': 'README.md / PUBLIC_STATUS.md release label',
    'sclite_dependency': 'pyproject.toml dependencies[sclite-core]',
    'changelog_release_heading': 'CHANGELOG.md:current alpha release section',
}

GOVERNED_RUNTIME_RELEASE_MARKERS = (
    'RuntimeAdmissionResult',
    'compose_runtime_admission_result()',
    'validate_evidence_review_chain()',
)

SOURCE_PYPI_GAP_DOC_MARKERS = {
    'README.md': (
        'Current supported stack line: `0.16.7`',
        'Current supported stack line: `govengine==0.16.7` with `sclite-core==1.0.8`',
    ),
    'docs/ROADMAP.md': (
        '## Current 0.16.x release line',
        'Published PyPI baseline is `govengine==0.16.7`',
    ),
}

FORBIDDEN_CURRENT_DOC_CLAIMS = (
    ('CHANGELOG.md', 'unreleased_api_name', 'verify_evidence_review_chain()'),
    ('docs/SCLITE_INTEGRATION.md', 'retired_helper_claim', 'action validation and compilation'),
    ('docs/SCLITE_INTEGRATION.md', 'stale_sclite_version', '0.8.0b2'),
    ('docs/SCLITE_INTEGRATION.md', 'stale_policy_helper_claim', 'policy decision normalization/evaluation'),
    ('docs/RUNTIME_ADMISSION.md', 'future_inspect_claim', 'future read-only'),
    ('docs/RUNTIME_ADMISSION.md', 'future_implementation_tense', 'The implementation should expose'),
    ('docs/INSPECT_ONLY_ADMISSION_WORKFLOW.md', 'stale_plan_claim', 'GE-035 should implement'),
    ('docs/ROADMAP.md', 'stale_mvp_direction_claim', 'need focused negative'),
)

README_MVP_DOC_LINK_MARKERS = (
    'docs/API_STABILITY_MATRIX.md',
    'docs/INSPECT_ONLY_ADMISSION_WORKFLOW.md',
    'docs/GUARDED_FRESH_RUNTIME_ADMISSION_EXAMPLE.md',
    'docs/LOCAL_SUBPROCESS_RUNNER_DECISION.md',
)

MVP_DELIVERY_DOC_MARKERS = {
    'docs/RUNTIME_ADMISSION.md': (
        'Delivered in `0.14.0`',
        'scripts/inspect_runtime_admission.py',
        'The implementation exposes a small immutable record',
    ),
    'docs/INSPECT_ONLY_ADMISSION_WORKFLOW.md': (
        'The inspect-only surface is implemented as:',
        'scripts/inspect_runtime_admission.py',
    ),
}

G3_PROFILE_GOVERNANCE_DOC_MARKERS = {
    'README.md': (
        'govengine-policy profile-governance',
        'explain_profile_governance()',
        'ProfileConnectorCompatibilityReport',
    ),
    'PUBLIC_STATUS.md': (
        'Profile governance projection (G3)',
        'ProfileConnectorCompatibilityReport',
        'govengine-policy profile-governance',
    ),
    'docs/DOMAIN_PROFILE_CONTRACT.md': (
        '[PROFILE_GOVERNANCE.md](PROFILE_GOVERNANCE.md)',
        'Profile governance projection (G3)',
    ),
    'docs/PROFILE_GOVERNANCE.md': (
        'ProfileGovernanceProjection',
        'ProfileConnectorCompatibilityReport',
        'govengine-policy profile-governance',
    ),
}

G1_G2_EXPLAIN_DOC_MARKERS = {
    'README.md': (
        'govengine-policy explain|simulate --json',
        'explain_supervisor_action()',
        'govengine-supervisor explain --json',
    ),
    'PUBLIC_STATUS.md': (
        'govengine-policy explain|simulate --json',
        'explain_supervisor_action()',
        'govengine-supervisor explain --json',
    ),
    'docs/POLICY_ENGINE.md': (
        'govengine-policy explain policy.json request.json --json',
        'PolicyEvaluationExplanation',
    ),
    'docs/RUNTIME_ADMISSION.md': (
        'explain_supervisor_action()',
        'govengine-supervisor explain request.json --json',
        'SupervisorActionExplanation',
    ),
    'docs/RUNNER_SUPERVISION.md': (
        'explain_supervisor_action',
        'govengine-supervisor explain',
        'RExecOp consumes G2',
    ),
}


def _changelog_unreleased_section(changelog: str) -> str:
    if '## Unreleased' not in changelog:
        return ''
    start = changelog.index('## Unreleased') + len('## Unreleased')
    tail = changelog[start:]
    match = re.search(r'\n## \d', tail)
    if match:
        return tail[: match.start()]
    return tail


def _changelog_release_section(changelog: str, release_label: str = EXPECTED_RELEASE_LABEL) -> str:
    heading = f'## {release_label}'
    if heading not in changelog:
        return ''
    start = changelog.index(heading) + len(heading)
    tail = changelog[start:]
    match = re.search(r'\n## \d', tail)
    if match:
        return tail[: match.start()]
    return tail


def _changelog_has_current_governed_runtime_mvp(changelog: str) -> bool:
    section = _changelog_release_section(changelog)
    return all(marker in section for marker in GOVERNED_RUNTIME_RELEASE_MARKERS)


def _changelog_has_unreleased_governed_runtime_mvp(changelog: str) -> bool:
    section = _changelog_unreleased_section(changelog)
    return all(marker in section for marker in GOVERNED_RUNTIME_RELEASE_MARKERS)


def _assert_source_pypi_gap_docs(
    version: str,
    readme: str,
    public_status: str,
    roadmap: str,
    changelog: str,
) -> None:
    if version == PUBLISHED_VERSION:
        return
    _assert_contains('CHANGELOG.md', _changelog_release_section(changelog), 'explain_supervisor_action()')
    _assert_contains('CHANGELOG.md', _changelog_release_section(changelog), 'SupervisorActionExplanation')
    _assert_contains('CHANGELOG.md', _changelog_release_section(changelog), 'explain_profile_governance()')
    _assert_contains('CHANGELOG.md', _changelog_release_section(changelog), 'ProfileGovernanceProjection')
    for path, markers in SOURCE_PYPI_GAP_DOC_MARKERS.items():
        text = {'README.md': readme, 'docs/ROADMAP.md': roadmap}[path]
        for marker in markers:
            _assert_contains(path, text, marker)
    _assert_contains(
        'PUBLIC_STATUS.md',
        public_status,
        f'Source/package version: `{version}`.',
    )
    _assert_contains(
        'PUBLIC_STATUS.md',
        public_status,
        f'Latest published PyPI package: `govengine=={PUBLISHED_VERSION}`.',
    )
    install_pin = re.compile(
        rf'python -m pip install govengine=={re.escape(PUBLISHED_VERSION)}'
    )
    if not install_pin.search(readme):
        raise AssertionError('README.md:missing_exact_install_command')


def _assert_changelog_unreleased_api_names(changelog: str) -> None:
    section = _changelog_unreleased_section(changelog)
    if not section:
        return
    if 'verify_evidence_review_chain()' in section:
        raise AssertionError('CHANGELOG.md:unreleased_stale_api_name:verify_evidence_review_chain')
    if _changelog_has_unreleased_governed_runtime_mvp(changelog):
        _assert_contains('CHANGELOG.md', section, 'validate_evidence_review_chain()')


def _assert_forbidden_current_doc_claims(docs: Mapping[str, str]) -> None:
    for path, field, forbidden in FORBIDDEN_CURRENT_DOC_CLAIMS:
        text = docs[path]
        if forbidden in text:
            raise AssertionError(f'{path}:forbidden_current_claim:{field}:{forbidden}')


def _assert_sclite_integration_current_dependency_truth(
    sclite_integration: str,
    dependency: str,
) -> None:
    _assert_contains('docs/SCLITE_INTEGRATION.md', sclite_integration, dependency)
    _assert_contains('docs/SCLITE_INTEGRATION.md', sclite_integration, 'approved-spec and execution-ticket validation helpers')


def _assert_readme_mvp_doc_links(readme: str) -> None:
    for marker in README_MVP_DOC_LINK_MARKERS:
        _assert_contains('README.md', readme, marker)


def _assert_mvp_delivery_doc_truth(markers: Mapping[str, Iterable[str]] = MVP_DELIVERY_DOC_MARKERS) -> None:
    for path, expected_markers in markers.items():
        text = _read(path)
        for marker in expected_markers:
            _assert_contains(path, text, marker)


def _assert_g1_g2_explain_doc_truth(
    markers: Mapping[str, Iterable[str]] = G1_G2_EXPLAIN_DOC_MARKERS,
) -> None:
    for path, expected_markers in markers.items():
        text = _read(path)
        for marker in expected_markers:
            _assert_contains(path, text, marker)


def _assert_g3_profile_governance_doc_truth(
    markers: Mapping[str, Iterable[str]] = G3_PROFILE_GOVERNANCE_DOC_MARKERS,
) -> None:
    for path, expected_markers in markers.items():
        text = _read(path)
        for marker in expected_markers:
            _assert_contains(path, text, marker)


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


def _pyproject() -> dict:
    return tomllib.loads(_read('pyproject.toml'))


def _project_dependency(project: dict, name: str) -> str:
    prefix = name
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
    badge = f'package-govengine%20{PUBLISHED_VERSION}-blueviolet.svg'
    forbidden_dynamic_badges = (
        'img.shields.io/pypi/v/govengine',
        'label=package%3A%20govengine',
    )
    for marker in forbidden_dynamic_badges:
        if marker in readme:
            raise AssertionError(f'README.md:dynamic_prerelease_unsafe_badge:{marker}')
    _assert_contains('README.md', readme, badge)
    _assert_contains('README.md', readme, release_url)
    install_pin = re.compile(
        rf'python -m pip install govengine=={re.escape(PUBLISHED_VERSION)}'
    )
    match = install_pin.search(readme)
    if not match:
        raise AssertionError('README.md:missing_unpinned_install_command')


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
        '## Current 0.12.x alpha line',
        'The current `0.12.x` alpha line',
        '## Current 0.14.x alpha line',
        'The current `0.14.x` alpha line',
    )
    for marker in stale_markers:
        if marker in roadmap:
            raise AssertionError(f'docs/ROADMAP.md:stale_current_roadmap_claim:{marker}')
    _assert_contains('docs/ROADMAP.md', roadmap, '## Current 0.16.x release line')
    _assert_contains('docs/ROADMAP.md', roadmap, 'The current published `0.16.x` single supported line is the single supported GovEngine stack line')
    _assert_contains('docs/ROADMAP.md', roadmap, f'Published PyPI baseline is `govengine=={PUBLISHED_VERSION}`')


def _assert_validation_current_gate_precedes_history(validation: str, version: str) -> None:
    current_heading = '## Current package-line gate'
    historical_heading = '## Historical validation records'
    current_expectation = f'Expected result for the current `{version}` package line'
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


def _assert_no_published_line_candidate_drift(paths: Iterable[str]) -> None:
    forbidden = (
        ('0.12_candidate_readme', '`0.12` candidate'),
        ('0.12_alpha_candidate', '`0.12.0-alpha` candidate'),
        ('0.12_1_alpha_candidate', '`0.12.1-alpha.1` candidate'),
        ('alpha_candidate_contributing', 'alpha candidate (`0.12.0-alpha`)'),
        ('alpha_12_1_candidate_contributing', 'alpha candidate (`0.12.1-alpha.1`)'),
        ('candidate_api_narrowing_line', 'candidate API-narrowing line'),
        (
            'stale_publishing_dependency_line',
            'published GovEngine `0.11.x` alpha package line depends on `sclite-core>=0.8.0a0,<0.9`',
        ),
    )
    for path in paths:
        text = _read(path)
        for reason, marker in forbidden:
            if marker in text:
                raise AssertionError(f'{path}:published_line_candidate_drift:{reason}')


def _assert_mvp_surface_docs(markers: Mapping[str, Iterable[str]] = MVP_SURFACE_DOC_MARKERS) -> None:
    for path, expected_markers in markers.items():
        text = _read(path)
        for marker in expected_markers:
            _assert_contains(path, text, marker)


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
    _assert_contains('CONTRIBUTING.md', contributing, f'alpha package (`{release_label}`)')
    _assert_contains('CONTRIBUTING.md', contributing, 'scripts/validate_clean_package_install.py')
    _assert_contains('docs/ROADMAP.md', roadmap, f'Current package baseline: `govengine=={version}`')
    _assert_contains('docs/ROADMAP.md', roadmap, dependency)
    _assert_roadmap_current_release_truth(roadmap)
    _assert_contains('PUBLIC_STATUS.md', public_status, f'Source/package version: `{version}`.')
    _assert_contains('PUBLIC_STATUS.md', public_status, f'Release label: `{release_label}`.')
    _assert_contains('PUBLIC_STATUS.md', public_status, f'Latest published PyPI package: `govengine=={PUBLISHED_VERSION}`.')
    _assert_contains('PUBLIC_STATUS.md', public_status, dependency)
    _assert_contains('PUBLISHING.md', publishing, dependency)
    _assert_contains('PUBLISHING.md', publishing, 'scripts/validate_clean_package_install.py')
    _assert_contains('PUBLISHING.md', publishing, '--no-editable')
    _assert_contains('docs/VALIDATION.md', validation, f'current `{version}` package line')
    _assert_contains('docs/VALIDATION.md', validation, 'scripts/validate_clean_package_install.py')
    _assert_contains('docs/VALIDATION.md', validation, '--no-editable')
    _assert_contains('docs/VALIDATION.md', validation, 'broad system interpreter is not')
    _assert_validation_current_gate_precedes_history(validation, version)
    _assert_clean_pip_check_guidance(contributing, validation, publishing)
    _assert_mvp_surface_docs()
    changelog = _read('CHANGELOG.md')
    _assert_changelog_unreleased_api_names(changelog)
    _assert_source_pypi_gap_docs(version, readme, public_status, roadmap, changelog)
    _assert_forbidden_current_doc_claims({
        'CHANGELOG.md': changelog,
        'docs/SCLITE_INTEGRATION.md': sclite_integration,
        'docs/RUNTIME_ADMISSION.md': _read('docs/RUNTIME_ADMISSION.md'),
        'docs/INSPECT_ONLY_ADMISSION_WORKFLOW.md': _read('docs/INSPECT_ONLY_ADMISSION_WORKFLOW.md'),
        'docs/ROADMAP.md': roadmap,
    })
    _assert_sclite_integration_current_dependency_truth(sclite_integration, dependency)
    _assert_readme_mvp_doc_links(readme)
    _assert_mvp_delivery_doc_truth()
    _assert_g1_g2_explain_doc_truth()
    _assert_g3_profile_governance_doc_truth()
    _assert_no_published_line_candidate_drift((
        'README.md',
        'CONTRIBUTING.md',
        'PUBLISHING.md',
        'docs/ARCHITECTURE.md',
        'docs/API_BOUNDARY.md',
    ))
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
    _assert_contains('PUBLIC_STATUS.md', public_status, 'Host runtimes own lifecycle artifact projection')
    _assert_contains('docs/API_BOUNDARY.md', api_boundary, 'Host-owned lifecycle projection is outside GovEngine')
    _assert_contains('docs/SCLITE_INTEGRATION.md', sclite_integration, 'Host-owned artifact projection is outside GovEngine')
    _assert_contains('docs/DOMAIN_PROFILE_CONTRACT.md', domain_profile, 'synthetic Tecrax conformance fixture')
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
