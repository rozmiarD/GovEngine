from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from govengine.api import GovApiError
from govengine.policy.compiler import CompileResult, PolicyCompiler


DEFAULT_POLICY_MAX_BYTES = 1_048_576


def read_policy_pack(path: str | Path, *, max_bytes: int = DEFAULT_POLICY_MAX_BYTES) -> Mapping[str, Any]:
    source = Path(path)
    if max_bytes < 1:
        raise GovApiError('policy_authoring_invalid_max_bytes')
    try:
        if source.stat().st_size > max_bytes:
            raise GovApiError('policy_pack_input_too_large')
        payload = json.loads(source.read_text(encoding='utf-8'))
    except OSError as exc:
        raise GovApiError('policy_pack_read_failed', str(exc)) from exc
    except json.JSONDecodeError as exc:
        raise GovApiError('policy_pack_json_invalid', exc.msg) from exc
    if not isinstance(payload, Mapping):
        raise GovApiError('policy_pack_json_not_mapping')
    return payload


def validate_policy_pack(value: Mapping[str, Any]) -> CompileResult:
    return PolicyCompiler().compile(value)


def render_policy_pack_json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + '\n'
