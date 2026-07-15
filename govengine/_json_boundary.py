from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any, Mapping

from govengine.api import GovApiError


@dataclass(frozen=True)
class JsonBoundaryLimits:
    max_depth: int = 32
    max_nodes: int = 10_000
    max_collection_length: int = 1_000
    max_string_length: int = 65_536


DEFAULT_JSON_BOUNDARY_LIMITS = JsonBoundaryLimits()


def bounded_json_copy(
    value: Any,
    *,
    limits: JsonBoundaryLimits = DEFAULT_JSON_BOUNDARY_LIMITS,
    allow_tuples: bool = True,
) -> Any:
    """Return a JSON-compatible copy or fail with a stable boundary reason."""

    nodes = 0

    def walk(item: Any, *, depth: int) -> Any:
        nonlocal nodes
        nodes += 1
        if nodes > limits.max_nodes:
            raise GovApiError('json_boundary_max_nodes')
        if depth > limits.max_depth:
            raise GovApiError('json_boundary_max_depth')
        if item is None or isinstance(item, bool):
            return item
        if isinstance(item, str):
            if len(item) > limits.max_string_length:
                raise GovApiError('json_boundary_max_string_length')
            return item
        if isinstance(item, int):
            return item
        if isinstance(item, float):
            if not math.isfinite(item):
                raise GovApiError('json_boundary_non_finite_number')
            return item
        if isinstance(item, Mapping):
            if len(item) > limits.max_collection_length:
                raise GovApiError('json_boundary_max_collection_length')
            result: dict[str, Any] = {}
            for key, nested in item.items():
                if not isinstance(key, str):
                    raise GovApiError('json_boundary_non_string_key')
                if len(key) > limits.max_string_length:
                    raise GovApiError('json_boundary_max_string_length')
                result[key] = walk(nested, depth=depth + 1)
            return result
        if isinstance(item, list) or (allow_tuples and isinstance(item, tuple)):
            if len(item) > limits.max_collection_length:
                raise GovApiError('json_boundary_max_collection_length')
            return [walk(nested, depth=depth + 1) for nested in item]
        raise GovApiError(
            'json_boundary_unsupported_type',
            context={'type': type(item).__name__},
        )

    return walk(value, depth=0)


def load_bounded_json(
    source: str | bytes,
    *,
    max_bytes: int,
    limits: JsonBoundaryLimits = DEFAULT_JSON_BOUNDARY_LIMITS,
) -> Any:
    """Parse strict JSON with duplicate-key and non-finite-number rejection."""

    if max_bytes < 1:
        raise GovApiError('json_boundary_invalid_max_bytes')
    raw = source.encode('utf-8') if isinstance(source, str) else bytes(source)
    if len(raw) > max_bytes:
        raise GovApiError('json_boundary_max_bytes')

    def pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise GovApiError(
                    'json_boundary_duplicate_key',
                    context={'key': key},
                )
            result[key] = value
        return result

    def reject_constant(_value: str) -> Any:
        raise GovApiError('json_boundary_non_finite_number')

    try:
        parsed = json.loads(
            raw.decode('utf-8'),
            object_pairs_hook=pairs_hook,
            parse_constant=reject_constant,
        )
    except GovApiError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GovApiError('json_boundary_invalid_json', str(exc)) from exc
    return bounded_json_copy(parsed, limits=limits)
