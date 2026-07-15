from __future__ import annotations

from datetime import datetime
from string import hexdigits
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
        'secret',
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


def require_sha256_digest(value: str, reason_code: str) -> str:
    if not isinstance(value, str):
        raise GovApiError(reason_code)
    prefix = 'sha256:'
    digest = value.strip()
    body = digest.removeprefix(prefix)
    if (
        not digest.startswith(prefix)
        or len(body) != 64
        or any(char not in hexdigits for char in body)
        or body != body.lower()
    ):
        raise GovApiError(reason_code)
    return digest


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
