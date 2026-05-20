from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol
from urllib.parse import urlparse


class GovScopePort(Protocol):
    """Neutral host/scope policy port for GovEngine controlled-execution helpers."""

    def extract_host(self, value: Any) -> str:
        ...

    def host_in_scope(self, host: str, scope_domains: Any) -> bool:
        ...


@dataclass(frozen=True)
class FunctionalScopePort:
    """Scope port backed by host-provided functions."""

    extract_host_fn: Callable[[Any], Any]
    host_in_scope_fn: Callable[[str, Any], bool]

    def extract_host(self, value: Any) -> str:
        return str(self.extract_host_fn(value) or '').strip().lower()

    def host_in_scope(self, host: str, scope_domains: Any) -> bool:
        return bool(self.host_in_scope_fn(str(host or '').strip().lower(), scope_domains))


def extract_host_from_url(url: object) -> str:
    """Extract a lowercase host from a URL-like scalar."""

    text = str(url or '').strip()
    if not text:
        return ''
    try:
        parsed = urlparse(text)
        host = (parsed.hostname or '').strip().lower()
        if host:
            return host
        if '://' not in text and '.' in text and not any(ch.isspace() for ch in text):
            parsed = urlparse('//' + text)
            return (parsed.hostname or '').strip().lower()
    except Exception:
        return ''
    return ''
