from __future__ import annotations

import re
from pathlib import Path

import govengine


ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = ROOT / 'docs' / 'API_STABILITY_MATRIX.md'
BOUNDARY_PATH = ROOT / 'docs' / 'API_BOUNDARY.md'


def _matrix_exports() -> set[str]:
    text = MATRIX_PATH.read_text(encoding='utf-8')
    exports: set[str] = set()
    for line in text.splitlines():
        if not line.startswith('| '):
            continue
        cells = [cell.strip() for cell in line.strip().strip('|').split('|')]
        if len(cells) < 3 or cells[0] in {'Stability', '---'}:
            continue
        exports.update(re.findall(r'`([A-Za-z_][A-Za-z0-9_]*)`', cells[2]))
    return exports


def test_api_stability_matrix_covers_top_level_exports() -> None:
    assert _matrix_exports() == set(govengine.__all__)


def test_api_boundary_links_to_stability_matrix() -> None:
    boundary = BOUNDARY_PATH.read_text(encoding='utf-8')
    assert 'API_STABILITY_MATRIX.md' in boundary
