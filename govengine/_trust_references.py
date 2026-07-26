from __future__ import annotations

import re
from typing import Any, Mapping
from unicodedata import category

from govengine.api import GovApiError


MAX_OPAQUE_TRUST_REFERENCE_LENGTH = 2_048
_REFERENCE_NAMESPACE_PATTERN = re.compile(r'[A-Za-z][A-Za-z0-9+._-]*')
_INLINE_TRUST_MATERIAL_NAMESPACES = frozenset(
    {'data', 'pem', 'pkcs8', 'privatekeymaterial'}
)
_ARMORED_TRUST_MATERIAL_MARKERS = ('PRIVATEKEY', 'PUBLICKEY', 'CERTIFICATE')
_ARMORED_TRUST_MATERIAL_CARRY_LENGTH = (
    max(len(marker) for marker in _ARMORED_TRUST_MATERIAL_MARKERS) - 1
)


def validate_opaque_trust_reference(
    value: Any,
    *,
    allow_empty: bool,
    reason_code: str,
) -> str:
    """Return one bounded reference without interpreting host trust semantics."""

    if value is None and allow_empty:
        return ''
    if not isinstance(value, str) or len(value) > MAX_OPAQUE_TRUST_REFERENCE_LENGTH:
        raise GovApiError(reason_code)
    if any(category(char) in {'Cc', 'Cf', 'Cs', 'Zl', 'Zp'} for char in value):
        raise GovApiError(reason_code)

    reference = value.strip()
    if not reference:
        if allow_empty:
            return ''
        raise GovApiError(reason_code)
    if any(char.isspace() for char in reference):
        raise GovApiError(reason_code)

    namespace, separator, opaque_id = reference.partition(':')
    if (
        separator != ':'
        or not _REFERENCE_NAMESPACE_PATTERN.fullmatch(namespace)
        or not opaque_id
        or not any(char.isalnum() for char in opaque_id)
        or _canonical_reference_namespace(namespace)
        in _INLINE_TRUST_MATERIAL_NAMESPACES
    ):
        raise GovApiError(reason_code)

    if _contains_structural_trust_material_armor(reference):
        raise GovApiError(reason_code)
    return reference


def select_validated_opaque_trust_reference(
    value: Mapping[str, Any],
    *,
    primary_key: str,
    alias_key: str,
    reason_code: str,
) -> str:
    """Validate every supplied spelling before applying explicit precedence."""

    validated: dict[str, str] = {}
    for key in (primary_key, alias_key):
        if key in value:
            validated[key] = validate_opaque_trust_reference(
                value[key],
                allow_empty=True,
                reason_code=reason_code,
            )

    if primary_key in value and value[primary_key] is not None and value[primary_key] != '':
        return validated[primary_key]
    if alias_key in value and value[alias_key] is not None and value[alias_key] != '':
        return validated[alias_key]
    return ''


def _contains_structural_trust_material_armor(reference: str) -> bool:
    opening = reference.find('-----')
    carry = ''
    while opening >= 0:
        closing = reference.find('-----', opening + 5)
        if closing < 0:
            return False
        label = ''.join(
            char
            for char in reference[opening + 5:closing].upper()
            if 'A' <= char <= 'Z'
        )
        combined = carry + label
        if any(
            marker in combined
            for marker in _ARMORED_TRUST_MATERIAL_MARKERS
        ):
            return True
        carry = combined[-_ARMORED_TRUST_MATERIAL_CARRY_LENGTH:]
        opening = closing
    return False


def _canonical_reference_namespace(namespace: str) -> str:
    return ''.join(
        char for char in namespace.lower() if char not in '+._-'
    )
