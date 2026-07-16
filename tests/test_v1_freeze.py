from __future__ import annotations

import importlib.resources
import json

from scripts.validate_v1_freeze import load_v1_manifest, validate_v1_freeze


def test_v1_freeze_manifest_matches_code_and_facade() -> None:
    assert validate_v1_freeze() == {
        'facade_exports': 40,
        'v1_records': 15,
        'legacy_records': 5,
    }


def test_v1_freeze_manifest_is_wheel_shipped() -> None:
    resource = importlib.resources.files('govengine').joinpath(
        'v1_compatibility_manifest.json'
    )
    manifest = json.loads(resource.read_text(encoding='utf-8'))

    assert manifest == load_v1_manifest()
