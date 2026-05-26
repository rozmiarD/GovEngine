from __future__ import annotations

import json
import os
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from govengine.replay import verify_guard_and_record_replay


@dataclass
class MemoryStore:
    values: dict[str, dict[str, Any]] = field(default_factory=dict)

    def read_json(self, key: str) -> dict[str, Any]:
        return dict(self.values.get(key) or {"records": []})

    def write_json(self, key: str, value: dict[str, Any]) -> None:
        self.values[key] = dict(value)


def test_source_chain_secure_bundle_first_use_then_replay(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sclite_source = os.environ.get("SCLITE_SOURCE_DIR")
    if not sclite_source:
        pytest.skip("set SCLITE_SOURCE_DIR to run source-chain SCLite+GovEngine guard replay E2E")
    monkeypatch.syspath_prepend(sclite_source)
    for name in list(sys.modules):
        if name == "sclite" or name.startswith("sclite."):
            sys.modules.pop(name, None)

    from sclite.kernel_guard import build_kernel_guard_manifest

    source_fixture = Path(sclite_source) / "sclite" / "examples" / "contract-lifecycle-v0.2"
    bundle = tmp_path / "bundle"
    shutil.copytree(source_fixture, bundle)
    manifest_path = bundle / "artifact_chain_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    guard = build_kernel_guard_manifest(
        manifest,
        key="source-chain-secret",
        key_id="source-chain-key",
        nonces=[f"nonce-{index}" for index, _entry in enumerate(manifest["entries"])],
    )
    guard_path = bundle / "kernel_guard_manifest.json"
    guard_path.write_text(json.dumps(guard, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    store = MemoryStore()

    first = verify_guard_and_record_replay(manifest_path, guard_path=guard_path, key="source-chain-secret", store=store)
    second = verify_guard_and_record_replay(manifest_path, guard_path=guard_path, key="source-chain-secret", store=store)

    assert first.allowed is True
    assert first.replay_status == "fresh"
    assert second.allowed is False
    assert second.replay_status == "replayed"
