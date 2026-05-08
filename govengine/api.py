from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping


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


@dataclass(frozen=True)
class GovApiError(Exception):
    """Structured API error for hard boundary failures."""

    reason_code: str
    message: str = ""
    context: Mapping[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        if self.message:
            return f"{self.reason_code}:{self.message}"
        return self.reason_code

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def require_mapping(value: Any, *, reason_code: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise GovApiError(reason_code)
    return value
