from __future__ import annotations

import re
import inspect
from pathlib import Path

import govengine


ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = ROOT / 'docs' / 'API_STABILITY_MATRIX.md'
BOUNDARY_PATH = ROOT / 'docs' / 'API_BOUNDARY.md'


def _matrix_exports(*, statuses: set[str] | None = None) -> set[str]:
    text = MATRIX_PATH.read_text(encoding='utf-8')
    exports: set[str] = set()
    for line in text.splitlines():
        if not line.startswith('| '):
            continue
        cells = [cell.strip() for cell in line.strip().strip('|').split('|')]
        if len(cells) < 3 or cells[0] in {'Stability', '---'}:
            continue
        if statuses is not None and cells[0] not in statuses:
            continue
        exports.update(re.findall(r'`([A-Za-z_][A-Za-z0-9_]*)`', cells[2]))
    return exports


def test_api_stability_matrix_covers_top_level_exports() -> None:
    assert _matrix_exports(statuses={'alpha', 'fixture', 'deprecated'}) == set(
        govengine.__all__
    )


def test_api_stability_summary_matches_live_inventory() -> None:
    text = MATRIX_PATH.read_text(encoding='utf-8')
    counts = {
        status: len(_matrix_exports(statuses={status}))
        for status in ('stable', 'alpha', 'fixture', 'deprecated', 'internal-exposed')
    }
    for status, count in counts.items():
        assert f'- {status} exports: {count}' in text
    assert sum(counts.values()) == 303
    assert len(govengine.__all__) == 300


def test_module_owned_top_level_callables_are_inventory_classified() -> None:
    exposed = {
        name
        for name, value in vars(govengine).items()
        if not name.startswith('_')
        and name not in govengine.__all__
        and (inspect.isfunction(value) or inspect.isclass(value))
        and str(getattr(value, '__module__', '')).startswith('govengine')
    }

    assert exposed == _matrix_exports(statuses={'internal-exposed'})


def test_api_boundary_links_to_stability_matrix() -> None:
    boundary = BOUNDARY_PATH.read_text(encoding='utf-8')
    assert 'API_STABILITY_MATRIX.md' in boundary
