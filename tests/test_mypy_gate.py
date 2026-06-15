from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_mypy_package_gate_passes() -> None:
    result = subprocess.run(
        [sys.executable, '-m', 'mypy', 'govengine'],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert 'Success:' in result.stdout
