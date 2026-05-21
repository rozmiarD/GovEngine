from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_public_truth_validator_passes() -> None:
    result = subprocess.run(
        [sys.executable, 'scripts/validate_public_truth.py'],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert result.stdout.strip().startswith('public_truth_ok:govengine==0.10.1a0:')


def test_alpha_readiness_validator_passes() -> None:
    result = subprocess.run(
        [sys.executable, 'scripts/validate_alpha_readiness.py'],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert result.stdout.strip().startswith('alpha_readiness_ok:govengine==0.10.1a0:')


def test_current_public_docs_do_not_reintroduce_pre_alpha_maturity_claims() -> None:
    stale_markers = ('currently pre-alpha', 'current pre-alpha', 'pre-alpha form')
    for relative in (
        'README.md',
        'PUBLIC_STATUS.md',
        'SECURITY.md',
        'docs/ARCHITECTURE.md',
        'docs/API_BOUNDARY.md',
        'docs/ROADMAP.md',
    ):
        text = (ROOT / relative).read_text(encoding='utf-8').lower()
        assert not any(marker in text for marker in stale_markers), relative
