from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from govengine._governance_validation import (
    parse_aware_timestamp,
    reject_unknown_fields,
    require_sha256_digest,
    required_nonnegative_int,
    required_text,
    schema_version,
)
from govengine.api import GovApiError, require_mapping
from govengine.signing import govengine_record_digest


POLICY_ACTIVATION_BINDING_SCHEMA_VERSION = 'v1'
POLICY_ACTIVATION_STATUSES = frozenset(
    {'active', 'superseded', 'revoked', 'expired'}
)
_FIELDS = frozenset(
    {
        'schema_version',
        'binding_id',
        'policy_id',
        'policy_version',
        'policy_pack_digest',
        'policy_epoch',
        'issuer_ref',
        'trust_ref',
        'status',
        'not_before',
        'expires_at',
    }
)


@dataclass(frozen=True)
class PolicyActivationBinding:
    """Host-authenticated current policy binding, not a policy repository."""

    binding_id: str
    policy_id: str
    policy_version: str
    policy_pack_digest: str
    policy_epoch: int
    issuer_ref: str
    trust_ref: str
    status: str
    not_before: str
    expires_at: str
    schema_version: str = POLICY_ACTIVATION_BINDING_SCHEMA_VERSION

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> 'PolicyActivationBinding':
        raw = require_mapping(value, reason_code='invalid_policy_activation_binding')
        reject_unknown_fields(
            raw,
            allowed=_FIELDS,
            reason_code='unknown_policy_activation_binding_field',
        )
        item = cls(
            binding_id=required_text(
                raw,
                'binding_id',
                'missing_policy_activation_binding_id',
            ),
            policy_id=required_text(raw, 'policy_id', 'missing_policy_activation_id'),
            policy_version=required_text(
                raw,
                'policy_version',
                'missing_policy_activation_version',
            ),
            policy_pack_digest=require_sha256_digest(
                required_text(
                    raw,
                    'policy_pack_digest',
                    'missing_policy_activation_digest',
                ),
                'invalid_policy_activation_digest',
            ),
            policy_epoch=required_nonnegative_int(
                raw,
                'policy_epoch',
                'invalid_policy_activation_epoch',
            ),
            issuer_ref=required_text(
                raw,
                'issuer_ref',
                'missing_policy_activation_issuer',
            ),
            trust_ref=required_text(
                raw,
                'trust_ref',
                'missing_policy_activation_trust_ref',
            ),
            status=required_text(
                raw,
                'status',
                'missing_policy_activation_status',
            ),
            not_before=required_text(
                raw,
                'not_before',
                'missing_policy_activation_not_before',
            ),
            expires_at=required_text(
                raw,
                'expires_at',
                'missing_policy_activation_expires_at',
            ),
            schema_version=schema_version(
                raw,
                default=POLICY_ACTIVATION_BINDING_SCHEMA_VERSION,
                reason_code='invalid_policy_activation_schema_version',
            ),
        )
        return validate_policy_activation_binding(item)

    def as_dict(self) -> dict[str, Any]:
        return {
            'schema_version': self.schema_version,
            'binding_id': self.binding_id,
            'policy_id': self.policy_id,
            'policy_version': self.policy_version,
            'policy_pack_digest': self.policy_pack_digest,
            'policy_epoch': self.policy_epoch,
            'issuer_ref': self.issuer_ref,
            'trust_ref': self.trust_ref,
            'status': self.status,
            'not_before': self.not_before,
            'expires_at': self.expires_at,
        }


def validate_policy_activation_binding(
    value: Mapping[str, Any] | PolicyActivationBinding,
) -> PolicyActivationBinding:
    if not isinstance(value, PolicyActivationBinding):
        return PolicyActivationBinding.from_mapping(value)
    item = value
    if item.schema_version != POLICY_ACTIVATION_BINDING_SCHEMA_VERSION:
        raise GovApiError('invalid_policy_activation_schema_version')
    if item.status not in POLICY_ACTIVATION_STATUSES:
        raise GovApiError('unknown_policy_activation_status')
    for text, reason_code in (
        (item.binding_id, 'missing_policy_activation_binding_id'),
        (item.policy_id, 'missing_policy_activation_id'),
        (item.policy_version, 'missing_policy_activation_version'),
        (item.issuer_ref, 'missing_policy_activation_issuer'),
        (item.trust_ref, 'missing_policy_activation_trust_ref'),
    ):
        if not isinstance(text, str) or not text.strip():
            raise GovApiError(reason_code)
    require_sha256_digest(
        item.policy_pack_digest,
        'invalid_policy_activation_digest',
    )
    if (
        isinstance(item.policy_epoch, bool)
        or not isinstance(item.policy_epoch, int)
        or item.policy_epoch < 0
    ):
        raise GovApiError('invalid_policy_activation_epoch')
    not_before = parse_aware_timestamp(
        item.not_before,
        'invalid_policy_activation_not_before',
    )
    expires_at = parse_aware_timestamp(
        item.expires_at,
        'invalid_policy_activation_expires_at',
    )
    if expires_at <= not_before:
        raise GovApiError('invalid_policy_activation_validity_window')
    return item


def policy_activation_binding_digest(
    value: Mapping[str, Any] | PolicyActivationBinding,
) -> str:
    checked = validate_policy_activation_binding(value)
    return govengine_record_digest(
        checked,
        record_type='govengine.policy.activation.PolicyActivationBinding',
    )
