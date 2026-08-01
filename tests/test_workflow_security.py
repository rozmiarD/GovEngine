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
