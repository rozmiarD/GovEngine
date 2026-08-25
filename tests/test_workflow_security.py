from __future__ import annotations

from pathlib import Path
import re

import pytest

from scripts.validate_workflow_security import ROOT, validate_workflow_security


def _job(text: str, name: str) -> str:
    marker = f'\n  {name}:\n'
    body = text.split(marker, 1)[1]
    next_job = re.search(r'\n  [a-zA-Z0-9_-]+:\n', body)
    return body if next_job is None else body[: next_job.start()]


def test_workflows_pin_actions_and_use_oidc_release_security() -> None:
    report = validate_workflow_security()

    assert report['workflows'] == 3
    assert report['actions'] == 28


def test_hosted_workflows_bind_exact_source_and_consumer_qualification() -> None:
    expected_checkouts = (
        (
            'repository: rozmiarD/SCLite',
            'ref: f7c740f5b06f5121dd3a13e8d66c78c7f8922614',
            'path: _govstack/sclite',
        ),
        (
            'repository: rozmiarD/RExecOP',
            'ref: c7c3a44634b00bbcdacd34d0da2fad145d02bdd8',
            'path: _govstack/rexecop',
        ),
        (
            'repository: rozmiarD/tecrax',
            'ref: e785209475b4dcce14f90fc47efc0ab39c8d2b80',
            'path: _govstack/tecrax',
        ),
    )
    for workflow in ('pytest.yml', 'publish.yml'):
        text = (ROOT / '.github' / 'workflows' / workflow).read_text(
            encoding='utf-8'
        )
        qualification = _job(text, 'stack-qualification')
        for checkout in expected_checkouts:
            assert all(marker in qualification for marker in checkout)
        assert 'scripts/validate_release_train_truth.py --cross-repo' in qualification
        assert 'scripts/validate_api_stability.py --cross-repo' in qualification
        assert '--consumer-root "$GITHUB_WORKSPACE/_govstack/rexecop"' in qualification
        assert '--consumer-root "$GITHUB_WORKSPACE/_govstack/tecrax"' in qualification
        assert '"$GITHUB_WORKSPACE/_govstack/rexecop"' in qualification
        assert ' -m pip check' in qualification
        assert '--no-deps' not in qualification

    pytest_workflow = (
        ROOT / '.github' / 'workflows' / 'pytest.yml'
    ).read_text(encoding='utf-8')
    publish_workflow = (
        ROOT / '.github' / 'workflows' / 'publish.yml'
    ).read_text(encoding='utf-8')
    assert 'python scripts/validate_release_train_truth.py --local' in pytest_workflow
    assert 'python scripts/validate_api_stability.py --local' in pytest_workflow
    assert 'needs: stack-qualification' in _job(publish_workflow, 'build')


def test_publish_workflow_orders_record_truth_artifacts_and_ab_comparison() -> None:
    publish = (ROOT / '.github/workflows/publish.yml').read_text(encoding='utf-8')
    build = _job(publish, 'build')
    ordered = (
        '- name: Require authentic candidate record child before public truth',
        'scripts/validate_release_record_commit.py',
        '- name: Run release contract gates',
        'python scripts/validate_public_truth.py',
        '--history-mode',
        '- name: Build reviewed source artifacts',
        'scripts/validate_rc2_release_records.py',
        'scripts/compare_release_builds.py',
        'actions/upload-artifact@',
    )

    positions = [build.index(marker) for marker in ordered]
    assert positions == sorted(positions)


def test_publish_workflow_rejects_synthetic_evidence_opt_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_read_text = Path.read_text

    def read_text_with_unsafe_publish_opt_in(
        path: Path, *args: object, **kwargs: object
    ) -> str:
        text = original_read_text(path, *args, **kwargs)
        if path == ROOT / '.github/workflows/publish.yml':
            return f'{text}\n--allow-synthetic\n'
        return text

    monkeypatch.setattr(Path, 'read_text', read_text_with_unsafe_publish_opt_in)
    with pytest.raises(
        AssertionError,
        match='workflow_publish_synthetic_release_evidence_opt_in',
    ):
        validate_workflow_security()


def test_package_dry_run_requires_full_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_read_text = Path.read_text

    def read_text_without_package_history(
        path: Path, *args: object, **kwargs: object
    ) -> str:
        text = original_read_text(path, *args, **kwargs)
        if path == ROOT / '.github/workflows/pytest.yml':
            package_marker = '\n  package-dry-run:\n'
            prefix, package = text.split(package_marker, 1)
            package = package.replace(
                '        with:\n          fetch-depth: 0\n', '', 1
            )
            return prefix + package_marker + package
        return text

    monkeypatch.setattr(Path, 'read_text', read_text_without_package_history)
    with pytest.raises(
        AssertionError,
        match='workflow_package_dry_run_missing:fetch-depth: 0',
    ):
        validate_workflow_security()


def test_package_dry_run_rejects_markers_moved_to_another_job(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_read_text = Path.read_text

    def read_text_with_markers_in_later_job(
        path: Path, *args: object, **kwargs: object
    ) -> str:
        text = original_read_text(path, *args, **kwargs)
        if path == ROOT / '.github/workflows/pytest.yml':
            text = text.replace(
                '        with:\n          fetch-depth: 0\n', '', 1
            ).replace(
                '      - name: Exercise lifecycle-aware record-only A/B gate\n'
                '        run: PYTHON=python bash scripts/release_ab_repro_gate.sh\n',
                '',
                1,
            )
            return text + (
                '\n  unrelated-job:\n'
                '    steps:\n'
                '      - uses: actions/checkout@'
                'df4cb1c069e1874edd31b4311f1884172cec0e10\n'
                '        with:\n'
                '          fetch-depth: 0\n'
                '      - name: Exercise lifecycle-aware record-only A/B gate\n'
                '        run: PYTHON=python bash scripts/release_ab_repro_gate.sh\n'
            )
        return text

    monkeypatch.setattr(Path, 'read_text', read_text_with_markers_in_later_job)
    with pytest.raises(
        AssertionError,
        match='workflow_package_dry_run_missing:fetch-depth: 0',
    ):
        validate_workflow_security()
