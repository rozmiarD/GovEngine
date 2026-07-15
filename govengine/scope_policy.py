from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from govengine._governance_validation import (
    reject_forbidden_governance_input,
    reject_unknown_fields,
    require_sha256_digest,
    required_nonnegative_int,
    required_text,
    schema_version,
    text_tuple,
)
from govengine._json_boundary import bounded_json_copy
from govengine.api import GovApiError, require_mapping
from govengine.signing import govengine_record_digest


SCOPE_POLICY_BINDING_SCHEMA_VERSION = 'v1'
SCOPE_DECISION_SCHEMA_VERSION = 'v1'
SUPPORTED_SCOPE_SCHEMES = frozenset({'http', 'https'})
SUPPORTED_ADDRESS_CLASSES = frozenset(
    {'public', 'private', 'loopback', 'link_local'}
)
SUPPORTED_REDIRECT_POLICIES = frozenset({'deny', 'same_origin'})
PRIVATE_ADDRESS_CLASSES = frozenset({'private', 'loopback', 'link_local'})
SELF_AUTHORIZED_SCOPE_KEYS = frozenset(
    {
        'allowed_address_classes',
        'allowed_ports',
        'allowed_schemes',
        'allowed_target_namespaces',
        'network_allowed',
        'private_networks_allowed',
        'redirect_policy',
    }
)
RAW_DESTINATION_KEYS = frozenset({'address', 'host', 'hostname', 'ip', 'url'})
SCOPE_POLICY_BINDING_FIELDS = frozenset(
    {
        'schema_version',
        'binding_id',
        'policy_pack_digest',
        'policy_epoch',
        'source_ref',
        'attestation_ref',
        'allowed_target_namespaces',
        'network_allowed',
        'allowed_schemes',
        'allowed_ports',
        'allowed_address_classes',
        'redirect_policy',
        'private_networks_allowed',
    }
)


@dataclass(frozen=True)
class ScopePolicyBinding:
    """Independent scope/network policy input owned by GovEngine policy."""

    binding_id: str
    policy_pack_digest: str
    policy_epoch: int
    source_ref: str
    attestation_ref: str
    allowed_target_namespaces: tuple[str, ...]
    network_allowed: bool
    allowed_schemes: tuple[str, ...]
    allowed_ports: tuple[int, ...]
    allowed_address_classes: tuple[str, ...]
    redirect_policy: str
    private_networks_allowed: bool
    schema_version: str = SCOPE_POLICY_BINDING_SCHEMA_VERSION

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> 'ScopePolicyBinding':
        raw = require_mapping(value, reason_code='invalid_scope_policy_binding')
        reject_unknown_fields(
            raw,
            allowed=SCOPE_POLICY_BINDING_FIELDS,
            reason_code='unknown_scope_policy_binding_field',
        )
        item = cls(
            binding_id=required_text(
                raw,
                'binding_id',
                'missing_scope_policy_binding_id',
            ),
            policy_pack_digest=require_sha256_digest(
                required_text(
                    raw,
                    'policy_pack_digest',
                    'missing_scope_policy_pack_digest',
                ),
                'invalid_scope_policy_pack_digest',
            ),
            policy_epoch=required_nonnegative_int(
                raw,
                'policy_epoch',
                'invalid_scope_policy_epoch',
            ),
            source_ref=required_text(
                raw,
                'source_ref',
                'missing_scope_policy_source_ref',
            ),
            attestation_ref=required_text(
                raw,
                'attestation_ref',
                'missing_scope_policy_attestation_ref',
            ),
            allowed_target_namespaces=_canonical_text_tuple(
                raw.get('allowed_target_namespaces'),
                'invalid_allowed_target_namespaces',
            ),
            network_allowed=_strict_bool(
                raw,
                'network_allowed',
                'invalid_scope_network_allowed',
            ),
            allowed_schemes=_canonical_text_tuple(
                raw.get('allowed_schemes'),
                'invalid_allowed_network_schemes',
                allow_empty=True,
            ),
            allowed_ports=_port_tuple(raw.get('allowed_ports')),
            allowed_address_classes=_canonical_text_tuple(
                raw.get('allowed_address_classes'),
                'invalid_allowed_address_classes',
                allow_empty=True,
            ),
            redirect_policy=required_text(
                raw,
                'redirect_policy',
                'missing_scope_redirect_policy',
            ),
            private_networks_allowed=_strict_bool(
                raw,
                'private_networks_allowed',
                'invalid_private_networks_allowed',
            ),
            schema_version=schema_version(
                raw,
                default=SCOPE_POLICY_BINDING_SCHEMA_VERSION,
                reason_code='invalid_scope_policy_binding_schema_version',
            ),
        )
        _validate_scope_policy_binding(item)
        return item

    def as_dict(self) -> dict[str, Any]:
        return {
            'schema_version': self.schema_version,
            'binding_id': self.binding_id,
            'policy_pack_digest': self.policy_pack_digest,
            'policy_epoch': self.policy_epoch,
            'source_ref': self.source_ref,
            'attestation_ref': self.attestation_ref,
            'allowed_target_namespaces': list(self.allowed_target_namespaces),
            'network_allowed': self.network_allowed,
            'allowed_schemes': list(self.allowed_schemes),
            'allowed_ports': list(self.allowed_ports),
            'allowed_address_classes': list(self.allowed_address_classes),
            'redirect_policy': self.redirect_policy,
            'private_networks_allowed': self.private_networks_allowed,
        }


@dataclass(frozen=True)
class ScopeDecision:
    decision_id: str
    status: str
    reason_code: str
    requested_scope_digest: str
    policy_binding_digest: str
    redirect_policy: str
    blockers: tuple[str, ...] = ()
    schema_version: str = SCOPE_DECISION_SCHEMA_VERSION

    @property
    def allowed(self) -> bool:
        return self.status == 'allowed'

    def as_dict(self) -> dict[str, Any]:
        return {
            'schema_version': self.schema_version,
            'decision_id': self.decision_id,
            'status': self.status,
            'allowed': self.allowed,
            'reason_code': self.reason_code,
            'requested_scope_digest': self.requested_scope_digest,
            'policy_binding_digest': self.policy_binding_digest,
            'redirect_policy': self.redirect_policy,
            'blockers': list(self.blockers),
        }


def scope_policy_binding_digest(
    binding: Mapping[str, Any] | ScopePolicyBinding,
) -> str:
    checked = (
        binding
        if isinstance(binding, ScopePolicyBinding)
        else ScopePolicyBinding.from_mapping(binding)
    )
    _validate_scope_policy_binding(checked)
    return govengine_record_digest(
        checked,
        record_type='govengine.scope_policy.ScopePolicyBinding',
    )


def scope_decision_digest(decision: ScopeDecision) -> str:
    if not isinstance(decision, ScopeDecision):
        raise GovApiError('invalid_scope_decision')
    return govengine_record_digest(
        decision,
        record_type='govengine.scope_policy.ScopeDecision',
    )


def evaluate_scope_policy(
    requested_scope: Mapping[str, Any],
    policy_binding: Mapping[str, Any] | ScopePolicyBinding,
) -> ScopeDecision:
    scope = validate_requested_scope(requested_scope)
    policy = (
        policy_binding
        if isinstance(policy_binding, ScopePolicyBinding)
        else ScopePolicyBinding.from_mapping(policy_binding)
    )
    _validate_scope_policy_binding(policy)
    scope_digest = govengine_record_digest(
        scope,
        record_type='govengine.governance.RequestedScope',
    )
    policy_digest = scope_policy_binding_digest(policy)
    target_namespace = required_text(
        scope,
        'target_namespace',
        'missing_requested_target_namespace',
    )
    if target_namespace not in policy.allowed_target_namespaces:
        return _scope_decision(
            scope_digest,
            policy_digest,
            policy,
            'target_namespace_not_allowed',
        )

    destination = scope.get('requested_destination')
    if destination is None:
        return _scope_decision(scope_digest, policy_digest, policy, 'scope_allowed')
    raw_destination = require_mapping(
        destination,
        reason_code='invalid_requested_destination',
    )
    _reject_raw_destination(raw_destination)
    if not policy.network_allowed:
        return _scope_decision(
            scope_digest,
            policy_digest,
            policy,
            'network_not_allowed',
        )
    scheme = required_text(
        raw_destination,
        'scheme',
        'missing_requested_destination_scheme',
    )
    if scheme not in policy.allowed_schemes:
        return _scope_decision(
            scope_digest,
            policy_digest,
            policy,
            'network_scheme_not_allowed',
        )
    port = raw_destination.get('effective_port')
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise GovApiError('invalid_requested_destination_port')
    if port not in policy.allowed_ports:
        return _scope_decision(
            scope_digest,
            policy_digest,
            policy,
            'network_port_not_allowed',
        )
    address_class = required_text(
        raw_destination,
        'address_class',
        'missing_requested_address_class',
    )
    if address_class in PRIVATE_ADDRESS_CLASSES and not policy.private_networks_allowed:
        return _scope_decision(
            scope_digest,
            policy_digest,
            policy,
            'private_network_not_allowed',
        )
    if address_class not in policy.allowed_address_classes:
        return _scope_decision(
            scope_digest,
            policy_digest,
            policy,
            'network_address_class_not_allowed',
        )
    require_sha256_digest(
        required_text(
            raw_destination,
            'origin_binding_digest',
            'missing_requested_origin_binding_digest',
        ),
        'invalid_requested_origin_binding_digest',
    )
    return _scope_decision(scope_digest, policy_digest, policy, 'scope_allowed')


def validate_requested_scope(value: Mapping[str, Any]) -> Mapping[str, Any]:
    """Validate bounded requested facts without accepting policy claims."""

    return _bounded_scope(value)


def _scope_decision(
    scope_digest: str,
    policy_digest: str,
    policy: ScopePolicyBinding,
    reason_code: str,
) -> ScopeDecision:
    allowed = reason_code == 'scope_allowed'
    return ScopeDecision(
        decision_id=f'scope:{scope_digest[7:23]}:{policy_digest[7:23]}',
        status='allowed' if allowed else 'denied',
        reason_code=reason_code,
        requested_scope_digest=scope_digest,
        policy_binding_digest=policy_digest,
        redirect_policy=policy.redirect_policy,
        blockers=() if allowed else (reason_code,),
    )


def _validate_scope_policy_binding(item: ScopePolicyBinding) -> None:
    if item.schema_version != SCOPE_POLICY_BINDING_SCHEMA_VERSION:
        raise GovApiError('unknown_scope_policy_binding_schema_version')
    payload = item.as_dict()
    for key, reason_code in (
        ('binding_id', 'missing_scope_policy_binding_id'),
        ('source_ref', 'missing_scope_policy_source_ref'),
        ('attestation_ref', 'missing_scope_policy_attestation_ref'),
    ):
        required_text(payload, key, reason_code)
    require_sha256_digest(
        item.policy_pack_digest,
        'invalid_scope_policy_pack_digest',
    )
    if (
        isinstance(item.policy_epoch, bool)
        or not isinstance(item.policy_epoch, int)
        or item.policy_epoch < 0
    ):
        raise GovApiError('invalid_scope_policy_epoch')
    if not isinstance(item.network_allowed, bool):
        raise GovApiError('invalid_scope_network_allowed')
    if not isinstance(item.private_networks_allowed, bool):
        raise GovApiError('invalid_private_networks_allowed')
    if item.allowed_target_namespaces != tuple(sorted(set(item.allowed_target_namespaces))):
        raise GovApiError('invalid_allowed_target_namespaces')
    if item.allowed_schemes != tuple(sorted(set(item.allowed_schemes))):
        raise GovApiError('invalid_allowed_network_schemes')
    if item.allowed_ports != tuple(sorted(set(item.allowed_ports))):
        raise GovApiError('invalid_allowed_network_ports')
    if item.allowed_address_classes != tuple(
        sorted(set(item.allowed_address_classes))
    ):
        raise GovApiError('invalid_allowed_address_classes')
    if not item.allowed_target_namespaces:
        raise GovApiError('scope_policy_without_target_namespaces')
    if item.redirect_policy not in SUPPORTED_REDIRECT_POLICIES:
        raise GovApiError('unsupported_redirect_policy')
    if any(scheme not in SUPPORTED_SCOPE_SCHEMES for scheme in item.allowed_schemes):
        raise GovApiError('unsupported_scope_network_scheme')
    if any(
        address_class not in SUPPORTED_ADDRESS_CLASSES
        for address_class in item.allowed_address_classes
    ):
        raise GovApiError('unsupported_scope_address_class')
    if item.network_allowed and (
        not item.allowed_schemes
        or not item.allowed_ports
        or not item.allowed_address_classes
    ):
        raise GovApiError('scope_network_policy_incomplete')
    if not item.network_allowed and (
        item.allowed_schemes or item.allowed_ports or item.allowed_address_classes
    ):
        raise GovApiError('scope_network_policy_disabled_with_allowlist')


def _bounded_scope(value: Mapping[str, Any]) -> Mapping[str, Any]:
    raw = require_mapping(value, reason_code='invalid_requested_scope')
    copied = bounded_json_copy(raw)
    if not isinstance(copied, Mapping) or not copied:
        raise GovApiError('invalid_requested_scope')
    reject_forbidden_governance_input(copied)
    _reject_self_authorized_scope(copied)
    return copied


def _reject_self_authorized_scope(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if str(key).strip().lower() in SELF_AUTHORIZED_SCOPE_KEYS:
                raise GovApiError('self_authorized_scope_policy')
            _reject_self_authorized_scope(nested)
    elif isinstance(value, (list, tuple)):
        for nested in value:
            _reject_self_authorized_scope(nested)


def _reject_raw_destination(value: Mapping[str, Any]) -> None:
    if any(str(key).strip().lower() in RAW_DESTINATION_KEYS for key in value):
        raise GovApiError('raw_destination_detail_forbidden')


def _canonical_text_tuple(
    value: Any,
    reason_code: str,
    *,
    allow_empty: bool = False,
) -> tuple[str, ...]:
    result = tuple(sorted(text_tuple(value, reason_code)))
    if not result and not allow_empty:
        raise GovApiError(reason_code)
    return result


def _port_tuple(value: Any) -> tuple[int, ...]:
    if not isinstance(value, (list, tuple)):
        raise GovApiError('invalid_allowed_network_ports')
    ports: list[int] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, int) or not 1 <= item <= 65535:
            raise GovApiError('invalid_allowed_network_ports')
        ports.append(item)
    if len(ports) != len(set(ports)):
        raise GovApiError('invalid_allowed_network_ports')
    return tuple(sorted(ports))


def _strict_bool(
    value: Mapping[str, Any],
    key: str,
    reason_code: str,
) -> bool:
    raw = value.get(key)
    if not isinstance(raw, bool):
        raise GovApiError(reason_code)
    return raw
