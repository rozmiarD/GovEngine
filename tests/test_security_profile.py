from __future__ import annotations

import importlib.util
from pathlib import Path

from govengine.surfaces import public_surface_index


ROOT = Path(__file__).resolve().parents[1]


def test_retired_security_profile_facade_is_not_importable_or_exported() -> None:
    assert importlib.util.find_spec('govengine.security_profile') is None
    init_text = (ROOT / 'govengine' / '__init__.py').read_text(encoding='utf-8')
    assert 'security_profile_index' not in init_text
    assert 'security_profile_surface' not in init_text


def test_retired_security_profile_surface_is_not_published() -> None:
    assert 'security_profile_helpers' not in [surface.name for surface in public_surface_index()]
