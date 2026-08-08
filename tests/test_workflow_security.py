from __future__ import annotations

from pathlib import Path

import pytest

from scripts.validate_workflow_security import ROOT, validate_workflow_security


def test_workflows_pin_actions_and_use_oidc_release_security() -> None:
    report = validate_workflow_security()

    assert report['workflows'] == 3
    assert report['actions'] == 18


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
