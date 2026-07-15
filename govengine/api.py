from __future__ import annotations

from dataclasses import asdict, dataclass, field
from math import isfinite
import re
from typing import Any, Mapping


_REASON_CODE_PATTERN = re.compile(r'^[a-z][a-z0-9_]{0,127}$')
_ERROR_MAX_DEPTH = 4
_ERROR_MAX_ITEMS = 32
_ERROR_MAX_NODES = 64
_ERROR_MAX_STRING_LENGTH = 256


@dataclass(frozen=True)
class GovApiResult:
    """Stable public API result envelope for GovEngine helpers.

    The envelope is intentionally small: callers can branch on ``status`` and
    ``reason_code`` without depending on Ravenclaw-specific exception text.
    ``data`` carries the helper-specific payload when the operation is allowed
    or otherwise successfully evaluated.
    """

    status: str
    reason_code: str = "ok"
    data: Mapping[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return self.status in {"ok", "allowed", "dry-run", "completed"}

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "ok": self.ok,
            "reason_code": self.reason_code,
            "data": dict(self.data),
            "warnings": list(self.warnings),
        }


@dataclass
class GovApiError(Exception):
    """Structured API error for hard boundary failures."""

    reason_code: str
    message: str = ""
    context: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        raw_reason = str(self.reason_code or '').strip()
        fixed_reason, separator, detail = raw_reason.partition(':')
        raw_context = dict(self.context) if isinstance(self.context, Mapping) else {}
        if separator:
            raw_context.setdefault('detail', detail)
        if not _REASON_CODE_PATTERN.fullmatch(fixed_reason):
            raw_context.setdefault('invalid_reason_code', fixed_reason)
            fixed_reason = 'invalid_error_reason_code'
        self.reason_code = fixed_reason
        self.message = _bounded_error_string(self.message)
        self.context = _bounded_error_context(raw_context)

    def __str__(self) -> str:
        if self.message:
            return f"{self.reason_code}:{self.message}"
        detail = self.context.get('detail')
        if isinstance(detail, str) and detail:
            return f'{self.reason_code}:{detail}'
        return self.reason_code

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def require_mapping(value: Any, *, reason_code: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise GovApiError(reason_code)
    return value


def _bounded_error_string(value: Any) -> str:
    return str(value or '')[:_ERROR_MAX_STRING_LENGTH]


def _bounded_error_context(value: Mapping[str, Any]) -> Mapping[str, Any]:
    nodes = [0]

    def copy(item: Any, *, depth: int) -> Any:
        nodes[0] += 1
        if nodes[0] > _ERROR_MAX_NODES or depth > _ERROR_MAX_DEPTH:
            return None
        if item is None or isinstance(item, (bool, int)):
            return item
        if isinstance(item, float):
            return item if isfinite(item) else None
        if isinstance(item, str):
            return item[:_ERROR_MAX_STRING_LENGTH]
        if isinstance(item, Mapping):
            copied: dict[str, Any] = {}
            for index, (key, nested) in enumerate(item.items()):
                if index >= _ERROR_MAX_ITEMS:
                    break
                if not isinstance(key, str):
                    continue
                copied[key[:_ERROR_MAX_STRING_LENGTH]] = copy(nested, depth=depth + 1)
            return copied
        if isinstance(item, (list, tuple)):
            return [copy(nested, depth=depth + 1) for nested in item[:_ERROR_MAX_ITEMS]]
        return None

    copied = copy(value, depth=0)
    return copied if isinstance(copied, Mapping) else {}
