from __future__ import annotations

from datetime import datetime
from math import isfinite
from typing import Any, Mapping

from govengine.api import GovApiError


FORBIDDEN_GOVERNANCE_INPUT_KEYS = frozenset(
    {
        'access_key',
        'api_key',
        'authorization',
        'cookie',
        'credential',
        'password',
        'private_key',
        'raw_output',
        'raw_target',
        'secret',
        'stderr',
        'stdout',
        'target_url',
        'token',
    }
)


def required_text(
    value: Mapping[str, Any],
    key: str,
    reason_code: str,
) -> str:
    raw = value.get(key)
    if not isinstance(raw, str) or not raw.strip():
        raise GovApiError(reason_code)
    return raw.strip()


def require_ascii_identifier(value: Any, reason_code: str) -> str:
    if not isinstance(value, str) or not value.strip() or not value.isascii():
        raise GovApiError(reason_code)
    return value


def optional_text(value: Mapping[str, Any], key: str) -> str:
    raw = value.get(key, '')
    if raw is None:
        return ''
    if not isinstance(raw, str):
        raise GovApiError(f'invalid_{key}')
    return raw.strip()


def schema_version(
    value: Mapping[str, Any],
    *,
    default: str,
    reason_code: str,
) -> str:
    raw = value.get('schema_version', default)
    if not isinstance(raw, str) or not raw.strip():
        raise GovApiError(reason_code)
    return raw.strip()


def required_nonnegative_int(
    value: Mapping[str, Any],
    key: str,
    reason_code: str,
) -> int:
    raw = value.get(key)
    if isinstance(raw, bool) or not isinstance(raw, int) or raw < 0:
        raise GovApiError(reason_code)
    return raw


def required_nonnegative_number(
    value: Mapping[str, Any],
    key: str,
    reason_code: str,
) -> float:
    raw = value.get(key)
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise GovApiError(reason_code)
    try:
        normalized = float(raw)
    except OverflowError as exc:
        raise GovApiError(reason_code) from exc
    if not isfinite(normalized) or normalized < 0:
        raise GovApiError(reason_code)
    return normalized


def optional_nonnegative_int(
    value: Mapping[str, Any],
    key: str,
    *,
    default: int,
    reason_code: str,
) -> int:
    if key not in value:
        return default
    return required_nonnegative_int(value, key, reason_code)


def optional_nonnegative_number(
    value: Mapping[str, Any],
    key: str,
    *,
    default: float,
    reason_code: str,
) -> float:
    if key not in value:
        return default
    return required_nonnegative_number(value, key, reason_code)


def optional_bool(
    value: Mapping[str, Any],
    key: str,
    *,
    default: bool,
    reason_code: str,
) -> bool:
    raw = value.get(key, default)
    if not isinstance(raw, bool):
        raise GovApiError(reason_code)
    return raw


def require_sha256_digest(value: str, reason_code: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != len('sha256:') + 64
        or not value.startswith('sha256:')
        or any(char not in '0123456789abcdef' for char in value[len('sha256:') :])
    ):
        raise GovApiError(reason_code)
    return value


def optional_sha256_digest(
    value: Mapping[str, Any],
    key: str,
    *,
    reason_code: str,
) -> str:
    if key not in value or value[key] in (None, ''):
        return ''
    return require_sha256_digest(value[key], reason_code)


def parse_aware_timestamp(value: str, reason_code: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise GovApiError(reason_code)
    normalized = value.strip()
    if normalized.endswith('Z'):
        normalized = normalized[:-1] + '+00:00'
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise GovApiError(reason_code) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise GovApiError(reason_code)
    return parsed


def text_tuple(value: Any, reason_code: str) -> tuple[str, ...]:
    if isinstance(value, str) or not isinstance(value, (list, tuple)):
        raise GovApiError(reason_code)
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise GovApiError(reason_code)
        result.append(item.strip())
    if len(result) != len(set(result)):
        raise GovApiError(reason_code)
    return tuple(result)


def optional_text_tuple(
    value: Mapping[str, Any],
    key: str,
    *,
    default: tuple[str, ...] = (),
    reason_code: str,
) -> tuple[str, ...]:
    if key not in value:
        return default
    return text_tuple(value[key], reason_code)


def reject_forbidden_governance_input(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized = str(key).strip().lower()
            if normalized in FORBIDDEN_GOVERNANCE_INPUT_KEYS:
                raise GovApiError(
                    'forbidden_governance_input',
                    context={'detail': normalized},
                )
            reject_forbidden_governance_input(nested)
    elif isinstance(value, (list, tuple)):
        for nested in value:
            reject_forbidden_governance_input(nested)


def reject_unknown_fields(
    value: Mapping[Any, Any],
    *,
    allowed: frozenset[str],
    reason_code: str,
) -> None:
    for key in value:
        if not isinstance(key, str) or key not in allowed:
            raise GovApiError(reason_code)
