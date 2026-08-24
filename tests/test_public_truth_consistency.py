from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.validate_documentation_antidrift import (
    validate_current_rc_observation_claims,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'validate_public_truth.py'


def _load_validator():
    spec = importlib.util.spec_from_file_location('govengine_validate_public_truth', SCRIPT)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_public_truth_validator_passes() -> None:
    result = subprocess.run(
        [sys.executable, 'scripts/validate_public_truth.py'],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert result.stdout.strip().startswith('public_truth_ok:govengine==1.0.0rc2:')


def test_release_readiness_validator_passes() -> None:
    result = subprocess.run(
        [sys.executable, 'scripts/validate_release_readiness.py'],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert result.stdout.strip().startswith(
        'release_source_validation_ok:govengine==1.0.0rc2:'
    )
    assert 'posture=published_elapsed_unclosed:publishable=false' in result.stdout


def test_public_truth_validator_rejects_rc2_state_other_than_elapsed_unclosed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    validator = _load_validator()
    monkeypatch.setattr(
        validator,
        'validate_rc_window',
        lambda *args, **kwargs: {'status': 'active', 'record_status': 'active'},
    )

    with pytest.raises(AssertionError, match='rc2_window:current_effective_status_invalid'):
        validator._assert_rc2_window_current_state()


@pytest.mark.parametrize(
    ('relative', 'stale_claim'),
    (
        ('README.md', '`1.0.0rc2` published; observation active'),
        (
            'PUBLISHING.md',
            'govengine 1.0.0rc2    governance; published RC, observation active',
        ),
    ),
)
def test_documentation_antidrift_rejects_expired_rc_active_claims(
    tmp_path: Path,
    relative: str,
    stale_claim: str,
) -> None:
    (tmp_path / 'README.md').write_text('current RC status\n', encoding='utf-8')
    (tmp_path / 'PUBLISHING.md').write_text('current RC status\n', encoding='utf-8')
    (tmp_path / relative).write_text(stale_claim, encoding='utf-8')

    with pytest.raises(
        AssertionError,
        match=f'{relative}:stale_current_rc_observation_claim',
    ):
        validate_current_rc_observation_claims(root=tmp_path)


def test_current_release_docs_report_elapsed_unclosed() -> None:
    readme = (ROOT / 'README.md').read_text(encoding='utf-8')
    publishing = (ROOT / 'PUBLISHING.md').read_text(encoding='utf-8')

    assert '`1.0.0rc2` published; observation elapsed_unclosed' in readme
    assert 'govengine 1.0.0rc2    governance; published RC, observation elapsed_unclosed' in publishing


def test_current_public_docs_do_not_reintroduce_pre_alpha_maturity_claims() -> None:
    stale_markers = ('currently pre-alpha', 'current pre-alpha', 'pre-alpha form')
    for relative in (
        'README.md',
        'CONTRIBUTING.md',
        'PUBLIC_STATUS.md',
        'SECURITY.md',
        'docs/ARCHITECTURE.md',
        'docs/API_BOUNDARY.md',
        'docs/ROADMAP.md',
    ):
        text = (ROOT / relative).read_text(encoding='utf-8').lower()
        assert not any(marker in text for marker in stale_markers), relative


def test_public_truth_validator_rejects_stale_current_roadmap_baseline() -> None:
    validator = _load_validator()

    with pytest.raises(AssertionError, match='stale_current_roadmap_claim'):
        validator._assert_roadmap_current_release_truth(
            '## Current implemented baseline: 0.10.x alpha\n'
            'GovEngine stays on the 0.10 alpha stabilization line.\n'
        )

    with pytest.raises(AssertionError, match='stale_current_roadmap_claim'):
        validator._assert_roadmap_current_release_truth(
            '## Current 0.12.x alpha line\n'
            'The current `0.12.x` alpha line retains the neutral kernel shape.\n'
        )


def test_public_truth_validator_rejects_history_in_active_validation_runbook() -> None:
    validator = _load_validator()

    with pytest.raises(AssertionError, match='historical_records_in_active_runbook'):
        validator._assert_validation_current_gate_precedes_history(
            '## Current package evidence\n'
            'Expected result for the current `0.16.5` package line\n'
            '## Historical validation records\n',
            '0.16.5',
        )


def test_public_truth_validator_rejects_unscoped_current_pip_check_guidance() -> None:
    validator = _load_validator()

    with pytest.raises(AssertionError, match='unscoped_pip_check_guidance'):
        validator._assert_clean_pip_check_guidance(
            'python -m pip check\n',
            '## Current package evidence\n',
            'clean release guidance\n',
        )


def test_public_truth_validator_rejects_published_line_candidate_drift(monkeypatch: pytest.MonkeyPatch) -> None:
    validator = _load_validator()

    def fake_read(path: str) -> str:
        if path == 'README.md':
            return 'The `0.12` candidate removes the old facade.'
        return ''

    monkeypatch.setattr(validator, '_read', fake_read)

    with pytest.raises(AssertionError, match='published_line_candidate_drift:0.12_candidate_readme'):
        validator._assert_no_published_line_candidate_drift(('README.md',))


def test_public_truth_validator_rejects_stale_readme_release_claim() -> None:
    validator = _load_validator()
    stale = (
        'GovEngine is an in-process Python governance kernel designed to be integrated\n'
        'into execution runtimes.\n'
        'It evaluates policy, approval, scope and capability\n'
        'facts for one concrete operation attempt.\n'
        'It does not define artifact truth or verify lifecycle and evidence\n'
        'bundles; those responsibilities belong to SCLite.\n'
        'The published release-candidate package `1.0.0rc1` is available.\n'
        'python -m pip install govengine==1.0.0rc1\n'
        'Release posture: source candidate only.\n'
    )

    with pytest.raises(AssertionError, match='README.md:stale_release_claim'):
        validator._assert_readme_release_truth(stale, '1.0.0rc1')


def test_public_truth_validator_rejects_stale_publishing_dependency_line(monkeypatch: pytest.MonkeyPatch) -> None:
    validator = _load_validator()

    def fake_read(path: str) -> str:
        if path == 'PUBLISHING.md':
            return (
                'the published GovEngine `0.11.x` alpha package line depends on '
                '`sclite-core>=0.8.0a0,<0.9`'
            )
        return ''

    monkeypatch.setattr(validator, '_read', fake_read)

    with pytest.raises(AssertionError, match='published_line_candidate_drift:stale_publishing_dependency_line'):
        validator._assert_no_published_line_candidate_drift(('PUBLISHING.md',))


def test_public_truth_validator_rejects_stale_current_artifact_helper_dependency() -> None:
    validator = _load_validator()
    publishing = (
        'Source dependency: `sclite-core==2.0.1`; published rc1 remains on `2.0.0`.\n'
        'The helper validates exact name, version, `sclite-core==2.0.0`, Markdown '
        'content type and publication\n'
        'description bytes.\n'
    )

    with pytest.raises(
        AssertionError,
        match='PUBLISHING.md:current_artifact_helper_dependency_mismatch',
    ):
        validator._assert_publishing_current_artifact_helper_dependency(
            publishing,
            'sclite-core==2.0.1',
        )


def test_public_truth_validator_rejects_additional_stale_artifact_helper_claim() -> None:
    validator = _load_validator()
    publishing = (
        'The helper validates exact name, version, `sclite-core==2.0.1`, Markdown '
        'content type and publication\n'
        'description bytes.\n'
        'A stale helper claims name, version, `sclite-core==2.0.0`, Markdown '
        'content type and publication\n'
        'description bytes.\n'
    )

    with pytest.raises(
        AssertionError,
        match='PUBLISHING.md:current_artifact_helper_dependency_mismatch',
    ):
        validator._assert_publishing_current_artifact_helper_dependency(
            publishing,
            'sclite-core==2.0.1',
        )


def test_public_truth_validator_tracks_selected_current_contract_markers() -> None:
    validator = _load_validator()

    validator._assert_current_contract_docs({
        'docs/API_BOUNDARY.md': (
            '`govengine.v1` exports exactly 40 names',
            'Root compatibility surface',
        ),
    })


def test_public_truth_validator_rejects_missing_current_contract_marker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    validator = _load_validator()

    def fake_read(path: str) -> str:
        if path == 'docs/API_BOUNDARY.md':
            return 'A boundary without the compatibility classification.'
        return ''

    monkeypatch.setattr(validator, '_read', fake_read)

    with pytest.raises(
        AssertionError,
        match='docs/API_BOUNDARY.md:missing:Root compatibility surface',
    ):
        validator._assert_current_contract_docs({
            'docs/API_BOUNDARY.md': (
                'Root compatibility surface',
            ),
        })


def test_public_truth_validator_tracks_current_architecture_docs() -> None:
    validator = _load_validator()

    validator._assert_current_contract_docs({
        'docs/ARCHITECTURE.md': ('Canonical v1 flow', 'RExecOp', 'GovEngine', 'SCLite'),
        'docs/SCLITE_INTEGRATION.md': ('SCLite 2.0 is frozen.',),
    })


def test_public_truth_validator_requires_exact_pending_rc2_review_form() -> None:
    validator = _load_validator()

    validator._assert_rc2_review_form_state(
        validator.PENDING_RC2_REVIEW_FORM,
        window_exists=False,
    )
    altered = dict(validator.PENDING_RC2_REVIEW_FORM)
    altered['verdict'] = 'approved'
    with pytest.raises(AssertionError, match='source_a_pending_form_mismatch'):
        validator._assert_rc2_review_form_state(altered, window_exists=False)


def test_public_truth_validator_accepts_approved_record_child_state() -> None:
    validator = _load_validator()

    approved = dict(validator.PENDING_RC2_REVIEW_FORM)
    approved['verdict'] = 'approved'
    validator._assert_rc2_review_form_state(approved, window_exists=True)


def test_public_truth_validator_rejects_pending_form_with_rc2_window() -> None:
    validator = _load_validator()

    with pytest.raises(AssertionError, match='record_child_review_not_approved'):
        validator._assert_rc2_review_form_state(
            validator.PENDING_RC2_REVIEW_FORM,
            window_exists=True,
        )


def test_public_truth_validator_rejects_missing_architecture_marker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    validator = _load_validator()

    def fake_read(path: str) -> str:
        if path == 'docs/ARCHITECTURE.md':
            return 'Architecture without the canonical flow.'
        return ''

    monkeypatch.setattr(validator, '_read', fake_read)

    with pytest.raises(AssertionError, match='docs/ARCHITECTURE.md:missing:Canonical v1 flow'):
        validator._assert_current_contract_docs({
            'docs/ARCHITECTURE.md': (
                'Canonical v1 flow',
            ),
        })


def test_public_truth_version_doc_truth_negative_guards() -> None:
    """Positive version/doc truth is covered by test_public_truth_validator_passes."""
    validator = _load_validator()

    assert set(validator.VERSION_TRUTH_FIELDS) == {
        'source_version',
        'package_init_version',
        'published_pypi_version',
        'release_label',
        'sclite_dependency',
        'changelog_release_heading',
    }
    assert {field for _, field, _ in validator.FORBIDDEN_CURRENT_DOC_CLAIMS} == {
        'unreleased_api_name',
        'retired_helper_claim',
        'stale_sclite_version',
        'stale_policy_helper_claim',
        'future_inspect_claim',
        'future_implementation_tense',
        'stale_plan_claim',
        'stale_mvp_direction_claim',
    }

    negative_cases = (
        (
            'stale_unreleased_api_name',
            'CHANGELOG.md:unreleased_stale_api_name:verify_evidence_review_chain',
            lambda: validator._assert_changelog_unreleased_api_names(
                '## Unreleased\n'
                '- Added `verify_evidence_review_chain()`.\n'
                '## 0.14.0\n'
            ),
        ),
        (
            'stale_sclite_integration_version',
            'docs/SCLITE_INTEGRATION.md:forbidden_current_claim:stale_sclite_version:0.8.0b2',
            lambda: validator._assert_forbidden_current_doc_claims({
                'CHANGELOG.md': validator._read('CHANGELOG.md'),
                'docs/SCLITE_INTEGRATION.md': 'review-bundle mapping through SCLite `0.8.0b2`',
                'docs/RUNTIME_ADMISSION.md': validator._read('docs/RUNTIME_ADMISSION.md'),
                'docs/INSPECT_ONLY_ADMISSION_WORKFLOW.md': validator._read('docs/INSPECT_ONLY_ADMISSION_WORKFLOW.md'),
                'docs/ROADMAP.md': validator._read('docs/ROADMAP.md'),
            }),
        ),
    )

    for case_id, matcher, invoke in negative_cases:
        with pytest.raises(AssertionError, match=matcher):
            invoke()
