from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from govengine import __version__ as package_version  # noqa: E402
from govengine.cli_contracts import cli_contract_registry  # noqa: E402
from govengine.contract_compatibility import supported_contract_report  # noqa: E402
from govengine.contract_proofs import ravenclaw_contract_proof, tecrax_contract_proof  # noqa: E402
from govengine.surfaces import public_surface_index  # noqa: E402
from scripts.validate_documentation_antidrift import (  # noqa: E402
    validate_documentation_antidrift,
)
from scripts.validate_release_record_commit import (  # noqa: E402
    resolve_release_ab_state,
)
from scripts.validate_rc_window import ELAPSED_UNCLOSED, validate_rc_window  # noqa: E402
from sclite.consumer_contracts import validate_consumer_imports  # noqa: E402

EXPECTED_RELEASE_LABEL = '1.0.0rc3'
PUBLISHED_VERSION = '1.0.0rc2'
PYPI_LONG_DESCRIPTION_PATH = 'PYPI_LONG_DESCRIPTION.md'
PYPI_LONG_DESCRIPTION_SHA256 = 'e600766f447f1d7a085176de02b7b99778b298af80344c009cce2dc3f70c37a0'
RC2_REVIEW_RECORD_PATH = 'docs/security-review/rc2-external-review.json'
RC2_WINDOW_RECORD_PATH = 'docs/rc-window/1.0.0rc2.json'
RC2_WINDOW_EFFECTIVE_STATUS = ELAPSED_UNCLOSED
RC3_REVIEW_RECORD_PATH = 'docs/security-review/rc3-external-review.json'
RC3_WINDOW_RECORD_PATH = 'docs/rc-window/1.0.0rc3.json'
PENDING_RC2_REVIEW_FORM = {
    'schema_version': 'govengine.rc2_external_security_review.v1',
    'source_commit': '',
    'artifacts': {
        'runner': 'github-hosted-runner',
        'wheel_sha256': '',
        'normalized_sdist_sha256': '',
    },
    'confidential_report_sha256': '',
    'reviewer': '',
    'reviewed_at': None,
    'verdict': 'pending_external_reviewer',
    'open_p0': None,
    'open_p1': None,
}
PENDING_RC3_REVIEW_FORM = {
    **PENDING_RC2_REVIEW_FORM,
    'schema_version': 'govengine.rc3_external_security_review.v1',
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

CURRENT_CONTRACT_DOC_MARKERS = {
    'docs/ARCHITECTURE.md': (
        'Canonical v1 flow',
        'RExecOp',
        'GovEngine',
        'SCLite',
        'Domain profile',
    ),
    'docs/API_BOUNDARY.md': (
        '`govengine.v1` exports exactly 40 names',
        'Root compatibility surface',
        'Contract-proof objects are conformance artifacts',
    ),
    'docs/SCLITE_INTEGRATION.md': (
        'GovEngine does not:',
        'SCLite 2.0 is frozen.',
        'RExecOp then projects the final',
    ),
    'docs/SECURITY_INTEGRATION.md': (
        'GovernanceRequest v1',
        'atomically claims decision digest and nonce',
        'PKI, KMS, CA, HSM, private key storage',
    ),
    'docs/API_STABILITY_MATRIX.md': (
        'typed_execution_governed_admission:v0.1',
        'typed_execution_governed_admission:v0.2',
        'does not expand `govengine.__all__` or `govengine.v1`',
        'not decision authority or an execution permit',
    ),
    'docs/THREAT_MODEL.md': (
        'discounts only the two deliberate',
        'exact singleton signed-decision controls',
        'not authority',
    ),
    'docs/SECURITY_GUARANTEES.md': (
        'Optional typed mutation/recovery admission is exact',
        'Policy-bound plugin admission is exact',
        'not decision authority',
    ),
    'docs/DIGEST_OWNERSHIP.md': (
        'optional typed governed-admission cross-binding projection',
        'validate_typed_execution_governed_admission()',
        'validate_typed_execution_governed_admission_v02()',
    ),
}

RC2_REVIEW_FORM_DOC_MARKERS = {
    'CHANGELOG.md': (
        'Publishes `govengine==1.0.0rc2` with exact `sclite-core==2.0.1`',
    ),
    'PUBLISHING.md': (
        'The immutable `v1.0.0rc2` tag names B, a single-parent child of reviewed source\nA.',
    ),
    'docs/ROADMAP.md': (
        'Authentic external re-review, the exact record-only child,',
    ),
    'docs/VALIDATION.md': (
        'Reviewed source A is',
        'one modified seeded\nreview form plus one added prepared rc2 window',
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
    'docs/ROADMAP.md': (
        '## Current 1.0 release-candidate line',
        f'Published PyPI baseline is `govengine=={PUBLISHED_VERSION}`',
    ),
}

README_STALE_RELEASE_CLAIMS = (
    'Release posture: source candidate only.',
    'Publication remains blocked until the independent v1 security review',
    'Latest published stack line: `govengine==0.16.11`',
    'python -m pip install govengine==0.16.11',
    'The published `0.16.0` line provides records and validators for that boundary.',
)

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
    'docs/README.md',
    'docs/ARCHITECTURE.md',
    'docs/API_STABILITY_MATRIX.md',
    'docs/API_COMPATIBILITY.md',
    'docs/GOVERNANCE_REQUEST.md',
    'docs/GOVERNANCE_DECISION.md',
    'docs/SECURITY_INTEGRATION.md',
)

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
    _assert_contains('docs/SCLITE_INTEGRATION.md', sclite_integration, 'define or extend SCLite schemas')


def _assert_readme_mvp_doc_links(readme: str) -> None:
    for marker in README_MVP_DOC_LINK_MARKERS:
        _assert_contains('README.md', readme, marker)


def _assert_archive_truth(readme: str, docs_index: str) -> None:
    archive = ROOT / 'docs' / 'archive'
    retained = sorted(path.name for path in archive.glob('*.md'))
    if retained != ['ROADMAP_VERSION_HISTORY.md']:
        raise AssertionError(f'docs/archive:unexpected_inventory:{retained}')
    _assert_contains(
        'docs/README.md',
        docs_index,
        'archive/ROADMAP_VERSION_HISTORY.md',
    )
    if 'docs/archive/' in readme:
        raise AssertionError('README.md:archive_promoted_to_active_docs')


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


def _pyproject() -> dict[str, Any]:
    return tomllib.loads(_read('pyproject.toml'))


def _project_dependency(project: Mapping[str, Any], name: str) -> str:
    prefix = name
    for dependency in project.get('dependencies', []):
        if str(dependency).startswith(prefix):
            return str(dependency)
    raise AssertionError(f'missing_dependency:{name}')


def _assert_contains(path: str, text: str, expected: str) -> None:
    if expected not in text:
        raise AssertionError(f'{path}:missing:{expected}')


def _assert_release_substrate() -> None:
    project = _pyproject()['project']
    if project.get('readme') != PYPI_LONG_DESCRIPTION_PATH:
        raise AssertionError('release_substrate:project_readme_mismatch')
    actual = hashlib.sha256((ROOT / PYPI_LONG_DESCRIPTION_PATH).read_bytes()).hexdigest()
    if actual != PYPI_LONG_DESCRIPTION_SHA256:
        raise AssertionError(f'{PYPI_LONG_DESCRIPTION_PATH}:sha256:{actual}!={PYPI_LONG_DESCRIPTION_SHA256}')
    expected_build = ('pip==26.1.2', 'setuptools==83.0.0', 'wheel==0.47.0', 'build==1.5.0', 'twine==6.2.0')
    expected_test = ('jsonschema==4.26.0', 'mypy==1.20.2', 'pytest==8.4.2', 'pytest-cov==6.3.0', 'ruff==0.15.20', 'types-jsonschema==4.26.0.20260518')
    for path, expected in (
        ('.github/release-build-requirements.txt', expected_build),
        ('.github/release-test-requirements.txt', expected_test),
    ):
        if tuple(_read(path).splitlines()) != expected:
            raise AssertionError(f'{path}:exact_requirement_inventory_mismatch')
    manifest = _read('MANIFEST.in')
    for path in ('scripts/build_release_artifacts.sh', 'scripts/validate_distribution_metadata.py', 'scripts/validate_rc2_release_records.py', 'scripts/validate_release_record_commit.py'):
        _assert_contains('MANIFEST.in', manifest, f'include {path}')


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
    release_url = f'https://pypi.org/project/govengine/{version}/'
    badge = f'package-govengine%20{version}-blueviolet.svg'
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
        rf'python -m pip install govengine=={re.escape(version)}'
    )
    match = install_pin.search(readme)
    if not match:
        raise AssertionError('README.md:missing_source_version_install_command')


def _assert_readme_release_truth(readme: str, version: str) -> None:
    for marker in (
        'GovEngine is an in-process Python governance kernel designed to be integrated\n'
        'into execution runtimes.',
        'It evaluates policy, approval, scope and capability\n'
        'facts for one concrete operation attempt',
        'It does not define artifact truth or verify lifecycle and evidence\n'
        'bundles; those responsibilities belong to SCLite.',
        f'published release-candidate package `{version}`',
        f'python -m pip install govengine=={version}',
    ):
        _assert_contains('README.md', readme, marker)
    for claim in README_STALE_RELEASE_CLAIMS:
        if claim in readme:
            raise AssertionError(f'README.md:stale_release_claim:{claim}')


def _assert_publishing_current_artifact_helper_dependency(
    publishing: str, dependency: str
) -> None:
    claims = re.findall(
        r'name, version, `(sclite-core==[^`]+)`, Markdown content type and '
        r'publication\s+description bytes\.',
        publishing,
    )
    if claims != [dependency]:
        raise AssertionError(
            'PUBLISHING.md:current_artifact_helper_dependency_mismatch'
        )


def _assert_readme_architecture_truth(readme: str) -> None:
    for marker in (
        'This\nset has no formal product name.',
        'Domain profile                 meaning, workflows, connector contracts',
        'RExecOp                        lifecycle, lease/fencing, permit, I/O',
        '+---- request / terminal facts -----> GovEngine',
        '+---- final lifecycle/evidence --------> SCLite',
        'Together they separate domain meaning,\ngovernance, execution and proof',
        'RExecOp and other host runtimes own enforcement. Profiles own domain meaning.',
        'SCLite owns truth and proof.',
    ):
        _assert_contains('README.md', readme, marker)
    for forbidden in (
        'govstack',
        'The published `0.15.0` line added',
        'The `0.16.x` source line also adds',
        'The published `0.16.0` line adds',
        'public_surface_index()',
        'approved_spec_dry_run_result',
        '```mermaid',
        '```plantuml',
    ):
        if forbidden in readme:
            raise AssertionError(f'README.md:stale_or_invented_overview:{forbidden}')


def _assert_candidate_maturity_truth(paths: Iterable[str]) -> None:
    forbidden = re.compile(
        r'\bcurrent\s+pre-alpha\b|\bcurrently\s+pre-alpha\b|'
        r'\bin\s+pre-alpha\s+form\b|\bGovEngine is an alpha package\b|'
        r'\bGovEngine is currently alpha\b',
        re.IGNORECASE,
    )
    for path in paths:
        text = _read(path)
        match = forbidden.search(text)
        if match:
            raise AssertionError(f'{path}:stale_maturity_claim:{match.group(0)}')
    _assert_contains(
        'SECURITY.md',
        _read('SECURITY.md'),
        'published `1.0.0rc2` release candidate',
    )
    _assert_contains(
        'docs/ARCHITECTURE.md',
        _read('docs/ARCHITECTURE.md'),
        'in-process deterministic governance kernel',
    )
    _assert_contains(
        'docs/API_BOUNDARY.md',
        _read('docs/API_BOUNDARY.md'),
        'small frozen\n1.0 candidate contract',
    )


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
    _assert_contains('docs/ROADMAP.md', roadmap, 'public 1.0 release-candidate phase')
    _assert_contains(
        'docs/ROADMAP.md',
        roadmap,
        f'Current source baseline: `govengine=={EXPECTED_RELEASE_LABEL}`',
    )
    _assert_contains('docs/ROADMAP.md', roadmap, f'Published PyPI baseline is `govengine=={PUBLISHED_VERSION}`')


def _assert_validation_current_gate_precedes_history(validation: str, version: str) -> None:
    current_expectation = f'Expected result for the current `{version}` package line'
    _assert_contains('docs/VALIDATION.md', validation, '## Current package evidence')
    _assert_contains('docs/VALIDATION.md', validation, current_expectation)
    if '## Historical validation records' in validation:
        raise AssertionError('docs/VALIDATION.md:historical_records_in_active_runbook')


def _assert_clean_pip_check_guidance(contributing: str, validation: str, publishing: str) -> None:
    for path, text in (
        ('CONTRIBUTING.md', contributing),
        ('docs/VALIDATION.md', validation),
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


def _assert_current_contract_docs(
    markers: Mapping[str, Iterable[str]] = CURRENT_CONTRACT_DOC_MARKERS,
) -> None:
    for path, expected_markers in markers.items():
        text = _read(path)
        for marker in expected_markers:
            _assert_contains(path, text, marker)


def _assert_rc2_review_form_state(
    review: object,
    *,
    window_exists: bool,
) -> None:
    if not isinstance(review, Mapping) or set(review) != set(PENDING_RC2_REVIEW_FORM):
        raise AssertionError(f'{RC2_REVIEW_RECORD_PATH}:field_inventory_invalid')
    if window_exists:
        if review.get('verdict') != 'approved':
            raise AssertionError(
                f'{RC2_REVIEW_RECORD_PATH}:record_child_review_not_approved'
            )
        return
    if review != PENDING_RC2_REVIEW_FORM:
        raise AssertionError(
            f'{RC2_REVIEW_RECORD_PATH}:source_a_pending_form_mismatch'
        )


def _assert_rc2_window_current_state() -> None:
    checked = validate_rc_window(
        ROOT / RC2_WINDOW_RECORD_PATH,
        expected_version='1.0.0rc2',
        history_mode=True,
    )
    if (
        checked['status'] != RC2_WINDOW_EFFECTIVE_STATUS
        or checked['record_status'] != 'active'
    ):
        raise AssertionError('rc2_window:current_effective_status_invalid')


def _assert_rc3_candidate_state(*, root: Path = ROOT) -> str:
    try:
        state = resolve_release_ab_state(
            root,
            candidate_version=EXPECTED_RELEASE_LABEL,
        )
    except (OSError, ValueError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        raise AssertionError(f'rc3_release_ab_state_invalid:{exc}') from exc

    review = json.loads(
        (root / RC3_REVIEW_RECORD_PATH).read_text(encoding='utf-8')
    )
    checked = validate_rc_window(
        root / RC3_WINDOW_RECORD_PATH,
        expected_version=EXPECTED_RELEASE_LABEL,
        history_mode=state.mode == 'authentic',
    )

    if state.mode == 'synthetic':
        if review != PENDING_RC3_REVIEW_FORM:
            raise AssertionError(f'{RC3_REVIEW_RECORD_PATH}:pending_form_mismatch')
        if (
            checked['status'] != 'pending_review'
            or checked['record_status'] != 'pending_review'
        ):
            raise AssertionError('rc3_window:source_a_pending_status_invalid')
        return 'source_a'

    if state.mode != 'authentic' or state.record_commit is None:
        raise AssertionError('rc3_release_ab_state_invalid:unsupported_lifecycle')
    if (
        not isinstance(review, Mapping)
        or review.get('verdict') != 'approved'
        or review.get('source_commit') != state.source_commit
    ):
        raise AssertionError(f'{RC3_REVIEW_RECORD_PATH}:record_child_identity_invalid')
    if checked['status'] != 'prepared' or checked['record_status'] != 'prepared':
        raise AssertionError('rc3_window:record_child_prepared_status_invalid')
    return 'record_child_b'


def main() -> int:
    import_errors = validate_consumer_imports('govengine', ROOT)
    if import_errors:
        raise AssertionError(';'.join(import_errors))
    project = _pyproject()['project']
    version = str(project['version'])
    release_label = EXPECTED_RELEASE_LABEL
    dependency = _project_dependency(project, 'sclite-core')
    surfaces = public_surface_index()
    surface_names = [surface.name for surface in surfaces]
    supported_cli_commands = {
        str(contract['command'])
        for contract in cli_contract_registry()['contracts']
    }
    governed_contracts = [
        item
        for item in supported_contract_report()['contracts']
        if item['surface_id'] == 'typed_execution_governed_admission'
    ]
    if len(governed_contracts) != 1:
        raise AssertionError(
            'contract_catalog:typed_execution_governed_admission_inventory'
        )
    governed_contract = governed_contracts[0]
    if (
        governed_contract['supported_versions'] != ('v0.1', 'v0.2')
        or governed_contract['rexecop_consumer'] is not False
        or governed_contract['status'] != 'supported'
    ):
        raise AssertionError(
            'contract_catalog:typed_execution_governed_admission_not_optional_v0_1_v0_2'
        )

    if package_version != version:
        raise AssertionError(f'package_version_mismatch:{package_version}!={version}')

    readme = _read('README.md')
    docs_index = _read('docs/README.md')
    roadmap = _read('docs/ROADMAP.md')
    public_status = _read('PUBLIC_STATUS.md')
    contributing = _read('CONTRIBUTING.md')
    publishing = _read('PUBLISHING.md')
    validation = _read('docs/VALIDATION.md')
    api_boundary = _read('docs/API_BOUNDARY.md')
    sclite_integration = _read('docs/SCLITE_INTEGRATION.md')
    domain_profile = _read('docs/DOMAIN_PROFILE_CONTRACT.md')
    threat_model = _read('docs/THREAT_MODEL.md')
    security_guarantees = _read('docs/SECURITY_GUARANTEES.md')
    workflow = _read('.github/workflows/pytest.yml')
    clean_install_script = _read('scripts/validate_clean_package_install.py')

    _assert_release_substrate()

    _assert_contains('README.md', readme, f'Current source is `{version}`')
    _assert_contains('README.md', readme, release_label)
    _assert_contains('README.md', readme, dependency)
    _assert_readme_package_truth(readme, PUBLISHED_VERSION)
    _assert_readme_release_truth(readme, PUBLISHED_VERSION)
    _assert_readme_architecture_truth(readme)
    _assert_contains('README.md', readme, '## License and provenance')
    _assert_contains('README.md', readme, 'originating Ravenclaw contribution lineage')
    _assert_contains('README.md', readme, 'package maintainer')
    _assert_contains(
        'CONTRIBUTING.md',
        contributing,
        f'published `{PUBLISHED_VERSION}` candidate',
    )
    _assert_contains('CONTRIBUTING.md', contributing, 'scripts/validate_clean_package_install.py')
    _assert_contains('docs/ROADMAP.md', roadmap, f'Current source baseline: `govengine=={version}`')
    _assert_contains('docs/ROADMAP.md', roadmap, dependency)
    _assert_roadmap_current_release_truth(roadmap)
    _assert_contains(
        'PUBLIC_STATUS.md',
        public_status,
        f'| Current source version | `govengine=={version}`; source A; external review pending |',
    )
    _assert_contains(
        'PUBLIC_STATUS.md',
        public_status,
        f'| Published immutable artifact | `govengine=={PUBLISHED_VERSION}` from tag `v{PUBLISHED_VERSION}` |',
    )
    _assert_contains('PUBLIC_STATUS.md', public_status, dependency)
    _assert_contains('PUBLISHING.md', publishing, dependency)
    _assert_publishing_current_artifact_helper_dependency(publishing, dependency)
    _assert_contains('PUBLISHING.md', publishing, 'scripts/validate_clean_package_install.py')
    _assert_contains('PUBLISHING.md', publishing, '--no-editable')
    _assert_contains('docs/VALIDATION.md', validation, f'current `{version}` package line')
    _assert_contains('docs/VALIDATION.md', validation, 'scripts/validate_clean_package_install.py')
    _assert_contains('docs/VALIDATION.md', validation, '--no-editable')
    _assert_contains('docs/VALIDATION.md', validation, 'A broad system\ninterpreter is not dependency evidence.')
    _assert_validation_current_gate_precedes_history(validation, version)
    _assert_clean_pip_check_guidance(contributing, validation, publishing)
    _assert_current_contract_docs()
    _assert_current_contract_docs(RC2_REVIEW_FORM_DOC_MARKERS)
    _assert_rc2_review_form_state(
        json.loads(_read(RC2_REVIEW_RECORD_PATH)),
        window_exists=(ROOT / RC2_WINDOW_RECORD_PATH).exists(),
    )
    _assert_rc2_window_current_state()
    _assert_rc3_candidate_state()
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
    _assert_archive_truth(readme, docs_index)
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
        'contracts/execution.py',
        'execution/command_shape.py',
    )
    for relative in retired_modules:
        if (ROOT / 'govengine' / relative).exists():
            raise AssertionError(f'govengine/{relative}:retired_security_module_present')
    if 'security_profile_helpers' in surface_names:
        raise AssertionError('security_profile_helpers:retired_surface_present')
    _assert_contains('PUBLIC_STATUS.md', public_status, 'RExecOp           lifecycle, queues, leases, fencing, permits, retries and I/O')
    _assert_contains('docs/API_BOUNDARY.md', api_boundary, 'GovEngine consumes but does not own:')
    _assert_contains('docs/SCLITE_INTEGRATION.md', sclite_integration, 'RExecOp then projects the final')
    _assert_contains('docs/DOMAIN_PROFILE_CONTRACT.md', domain_profile, 'synthetic Tecrax conformance fixture')
    _assert_contains(
        'docs/THREAT_MODEL.md',
        threat_model,
        'malicious or fully compromised in-process host',
    )
    _assert_contains(
        'docs/SECURITY_GUARANTEES.md',
        security_guarantees,
        'Cryptographic and digest binding table',
    )
    _assert_contains(
        'docs/SECURITY_GUARANTEES.md',
        security_guarantees,
        'Explicit non-claims',
    )
    if 'unreleased deterministic demo signer/verifier ports' in public_status:
        raise AssertionError('PUBLIC_STATUS.md:published_demo_ports_marked_unreleased')
    _assert_contains('.github/workflows/pytest.yml', workflow, 'sclite-core==2.0.1')
    _assert_contains(
        '.github/workflows/pytest.yml',
        workflow,
        'SCLite.git@66dff5cf7d75059e13db92b553c192caf67c0338',
    )
    if 'SCLite.git@main' in workflow:
        raise AssertionError('.github/workflows/pytest.yml:moving_sclite_main_ref')
    _assert_contains('.github/workflows/pytest.yml', workflow, "python-version: ['3.11', '3.12', '3.13']")
    _assert_contains('.github/workflows/pytest.yml', workflow, 'python scripts/validate_public_truth.py')
    _assert_contains(
        '.github/workflows/pytest.yml',
        workflow,
        'python scripts/validate_release_train_truth.py',
    )
    _assert_contains('.github/workflows/pytest.yml', workflow, 'python scripts/validate_api_stability.py')
    _assert_contains('.github/workflows/pytest.yml', workflow, 'python scripts/validate_v1_freeze.py')
    _assert_contains(
        '.github/workflows/pytest.yml',
        workflow,
        'python scripts/generate_conformance_corpus.py --check',
    )
    _assert_contains(
        '.github/workflows/pytest.yml',
        workflow,
        'python scripts/validate_workflow_security.py',
    )
    _assert_contains(
        '.github/workflows/pytest.yml',
        workflow,
        'python scripts/validate_release_readiness.py',
    )
    _assert_contains('.github/workflows/pytest.yml', workflow, 'Mypy stable facade strict')
    _assert_contains('.github/workflows/pytest.yml', workflow, 'python -m mypy --strict')
    _assert_contains('.github/workflows/pytest.yml', workflow, 'package-dry-run:')
    _assert_contains('.github/workflows/pytest.yml', workflow, 'scripts/build_release_artifacts.sh --outdir dist')
    _assert_contains('.github/workflows/pytest.yml', workflow, 'scripts/reproducible_build_gate.sh')
    _assert_contains('.github/workflows/pytest.yml', workflow, 'scripts/release_ab_repro_gate.sh')
    _assert_contains(
        '.github/workflows/pytest.yml',
        workflow,
        'Exercise lifecycle-aware record-only A/B gate',
    )
    _assert_contains('.github/workflows/pytest.yml', workflow, 'fetch-depth: 0')
    _assert_contains('.github/workflows/pytest.yml', workflow, 'scripts/package_smoke.sh')
    _assert_contains('.github/workflows/pytest.yml', workflow, 'govengine-hosted-runner-review-artifacts')

    for surface in surfaces:
        if not surface.status.startswith('alpha_'):
            raise AssertionError(f'surface_status_not_alpha:{surface.name}:{surface.status}')
    for marker in (
        '40 `v1-candidate` exports',
        '188 adapter exports',
        '61 experimental exports',
        '19 fixture exports',
        '3 module-owned compatibility callables',
    ):
        _assert_contains('docs/API_BOUNDARY.md', api_boundary, marker)

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
    _assert_candidate_maturity_truth(CURRENT_ALPHA_DOCS)
    documentation = validate_documentation_antidrift(
        supported_commands=supported_cli_commands,
    )

    print(
        f'public_truth_ok:govengine=={version}:{dependency}:'
        f'surfaces={len(surface_names)}:'
        f"active_docs={documentation['active_markdown_files']}"
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
