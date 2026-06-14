from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest


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

    assert result.stdout.strip().startswith('public_truth_ok:govengine==0.12.2a0:')


def test_alpha_readiness_validator_passes() -> None:
    result = subprocess.run(
        [sys.executable, 'scripts/validate_alpha_readiness.py'],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert result.stdout.strip().startswith('alpha_readiness_ok:govengine==0.12.2a0:')


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


def test_public_truth_validator_rejects_validation_history_before_current_gate() -> None:
    validator = _load_validator()

    with pytest.raises(AssertionError, match='current_gate_not_before_history'):
        validator._assert_validation_current_gate_precedes_history(
            '## Historical validation records\n'
            'Historical expected result for the published `0.1.7` source line:\n'
            '## Current package-line gate\n'
            'Expected result for the current `0.12.2a0` package line\n'
            'not the active gate\n',
            '0.12.2a0',
        )


def test_public_truth_validator_rejects_unscoped_current_pip_check_guidance() -> None:
    validator = _load_validator()

    with pytest.raises(AssertionError, match='unscoped_pip_check_guidance'):
        validator._assert_clean_pip_check_guidance(
            'python -m pip check\n',
            '## Current package-line gate\n',
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


def test_public_truth_validator_tracks_current_mvp_surface_docs() -> None:
    validator = _load_validator()

    validator._assert_mvp_surface_docs({
        'docs/RUNTIME_ADMISSION.md': ('RuntimeAdmissionResult', 'Intent is not execution authority.'),
        'docs/RECEIPT_BINDING.md': ('GovRunnerReceiptBinding', 'validate_runner_receipt_binding()'),
        'docs/EVIDENCE_REVIEW.md': ('validate_evidence_review_chain()',),
        'docs/ADMISSION_POLICY.md': ('AuditLedgerPort', 'JsonlAuditLedgerAdapter'),
        'docs/SCLITE_INTEGRATION.md': ('ReplayClaimStore', 'claim-once adapter'),
        'docs/RUNNER_SUPERVISION.md': ('Live Runner Safety Specification', 'LocalSubprocessRunner'),
        'docs/SECURITY_INTEGRATION.md': ('SCLite secure verification', 'not proof and not execution authority'),
    })


def test_public_truth_validator_rejects_missing_mvp_surface_doc_marker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    validator = _load_validator()

    def fake_read(path: str) -> str:
        if path == 'docs/RUNTIME_ADMISSION.md':
            return 'RuntimeAdmissionResult without the core invariant.'
        return ''

    monkeypatch.setattr(validator, '_read', fake_read)

    with pytest.raises(AssertionError, match='docs/RUNTIME_ADMISSION.md:missing:Intent is not execution authority'):
        validator._assert_mvp_surface_docs({
            'docs/RUNTIME_ADMISSION.md': (
                'RuntimeAdmissionResult',
                'Intent is not execution authority.',
            ),
        })
