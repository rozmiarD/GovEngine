from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping

import pytest

from govengine.api import GovApiError
from govengine.capabilities import (
    CapabilityCompatibilityDecision,
    CapabilityInventoryBinding,
    OperationCapabilityRequirements,
    capability_compatibility_decision_digest,
    capability_inventory_binding_digest,
    evaluate_capability_compatibility,
    operation_capability_requirements_digest,
)
from govengine.scope_policy import (
    ScopeDecision,
    ScopePolicyBinding,
    evaluate_scope_policy,
    scope_decision_digest,
    scope_policy_binding_digest,
)


def _digest(seed: str) -> str:
    return f'sha256:{seed * 64}'[:71]


def _scope_policy(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        'schema_version': 'v1',
        'binding_id': 'scope-policy-1',
        'policy_pack_digest': _digest('a'),
        'policy_epoch': 42,
        'source_ref': 'policy-pack:production-mutation@1',
        'attestation_ref': 'catalog-attestation:scope-42',
        'allowed_target_namespaces': ['service.inventory'],
        'network_allowed': True,
        'allowed_schemes': ['https'],
        'allowed_ports': [443],
        'allowed_address_classes': ['public'],
        'redirect_policy': 'same_origin',
        'private_networks_allowed': False,
    }
    payload.update(overrides)
    return payload


def _requested_scope(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        'target_namespace': 'service.inventory',
        'environment': 'production',
        'requested_destination': {
            'scheme': 'https',
            'effective_port': 443,
            'address_class': 'public',
            'origin_binding_digest': _digest('b'),
        },
    }
    payload.update(overrides)
    return payload


def _requirements(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        'schema_version': 'v1',
        'requirements_id': 'requirements-1',
        'operation_id': 'op-123',
        'step_id': 'step-4',
        'execution_spec_digest': _digest('c'),
        'required_backend_class': 'http_api',
        'side_effect_class': 'mutation',
        'required_capabilities': [
            'connector.inventory.update',
            'network.tls.required',
            'receipt.terminal',
        ],
    }
    payload.update(overrides)
    return payload


def _inventory(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        'schema_version': 'v1',
        'inventory_id': 'runtime-inventory-42',
        'runtime_instance_id': 'rexecop-1',
        'runtime_version': '0.3.0rc2',
        'inventory_epoch': 42,
        'source_ref': 'runtime-registry:rexecop-1',
        'attestation_ref': 'runtime-inventory-attestation:42',
        'backend_classes': ['http_api'],
        'side_effect_classes': ['read_only', 'mutation'],
        'capabilities': [
            'connector.inventory.read',
            'connector.inventory.update',
            'network.tls.required',
            'receipt.terminal',
        ],
    }
    payload.update(overrides)
    return payload


def test_scope_policy_allows_only_independently_declared_destination() -> None:
    policy = ScopePolicyBinding.from_mapping(_scope_policy())

    decision = evaluate_scope_policy(_requested_scope(), policy)

    assert isinstance(decision, ScopeDecision)
    assert decision.allowed is True
    assert decision.status == 'allowed'
    assert decision.reason_code == 'scope_allowed'
    assert decision.redirect_policy == 'same_origin'
    assert decision.policy_binding_digest == scope_policy_binding_digest(policy)
    assert scope_decision_digest(decision).startswith('sha256:')


@pytest.mark.parametrize(
    ('scope_patch', 'reason_code'),
    [
        ({'target_namespace': 'service.billing'}, 'target_namespace_not_allowed'),
        (
            {'requested_destination': {**_requested_scope()['requested_destination'], 'scheme': 'http'}},
            'network_scheme_not_allowed',
        ),
        (
            {'requested_destination': {**_requested_scope()['requested_destination'], 'effective_port': 8443}},
            'network_port_not_allowed',
        ),
        (
            {'requested_destination': {**_requested_scope()['requested_destination'], 'address_class': 'private'}},
            'private_network_not_allowed',
        ),
    ],
)
def test_scope_policy_denies_scope_or_destination_drift(
    scope_patch: Mapping[str, Any],
    reason_code: str,
) -> None:
    decision = evaluate_scope_policy(
        _requested_scope(**scope_patch),
        _scope_policy(),
    )

    assert decision.allowed is False
    assert decision.reason_code == reason_code


@pytest.mark.parametrize(
    'claim',
    [
        {'allowed_schemes': ['https']},
        {'network_allowed': True},
        {'redirect_policy': 'same_origin'},
        {'private_networks_allowed': True},
    ],
)
def test_requested_scope_cannot_supply_its_own_allow_policy(
    claim: Mapping[str, Any],
) -> None:
    with pytest.raises(GovApiError, match='self_authorized_scope_policy'):
        evaluate_scope_policy(_requested_scope(**claim), _scope_policy())


def test_scope_policy_binding_digest_is_recomputed_from_full_record() -> None:
    policy = ScopePolicyBinding.from_mapping(_scope_policy())

    assert scope_policy_binding_digest(policy) != scope_policy_binding_digest(
        replace(policy, allowed_ports=(8443,))
    )


def test_direct_scope_policy_binding_still_receives_full_validation() -> None:
    policy = ScopePolicyBinding.from_mapping(_scope_policy())

    with pytest.raises(GovApiError, match='missing_scope_policy_source_ref'):
        scope_policy_binding_digest(replace(policy, source_ref=''))


def test_capability_compatibility_uses_operation_requirements_not_inventory_claims() -> None:
    requirements = OperationCapabilityRequirements.from_mapping(_requirements())
    inventory = CapabilityInventoryBinding.from_mapping(_inventory())

    decision = evaluate_capability_compatibility(requirements, inventory)

    assert isinstance(decision, CapabilityCompatibilityDecision)
    assert decision.compatible is True
    assert decision.missing_capabilities == ()
    assert decision.requirements_digest == operation_capability_requirements_digest(
        requirements
    )
    assert decision.inventory_digest == capability_inventory_binding_digest(inventory)
    assert capability_compatibility_decision_digest(decision).startswith('sha256:')


def test_capability_compatibility_reports_missing_operation_requirement() -> None:
    inventory = _inventory(
        capabilities=[
            'connector.inventory.read',
            'network.tls.required',
            'receipt.terminal',
        ]
    )

    decision = evaluate_capability_compatibility(_requirements(), inventory)

    assert decision.compatible is False
    assert decision.reason_code == 'required_capabilities_missing'
    assert decision.missing_capabilities == ('connector.inventory.update',)


@pytest.mark.parametrize(
    ('inventory_patch', 'reason_code'),
    [
        ({'backend_classes': ['static_fixture']}, 'required_backend_class_missing'),
        ({'side_effect_classes': ['read_only']}, 'side_effect_class_not_supported'),
    ],
)
def test_capability_compatibility_checks_backend_and_side_effect(
    inventory_patch: Mapping[str, Any],
    reason_code: str,
) -> None:
    decision = evaluate_capability_compatibility(
        _requirements(),
        _inventory(**inventory_patch),
    )

    assert decision.compatible is False
    assert decision.reason_code == reason_code


def test_operation_requirements_cannot_fall_back_to_inventory_capabilities() -> None:
    with pytest.raises(GovApiError, match='operation_capability_requirements_empty'):
        OperationCapabilityRequirements.from_mapping(
            _requirements(required_capabilities=[])
        )


@pytest.mark.parametrize(
    'claim',
    [
        {'registered_plugin_backend': True},
        {'plugin_registered': True},
        {'backend_supported': True},
    ],
)
def test_inventory_rejects_host_registration_booleans(claim: Mapping[str, Any]) -> None:
    with pytest.raises(GovApiError, match='self_attested_capability_support'):
        CapabilityInventoryBinding.from_mapping(_inventory(**claim))


def test_inventory_requires_independent_source_and_attestation_refs() -> None:
    with pytest.raises(GovApiError, match='missing_capability_inventory_attestation_ref'):
        CapabilityInventoryBinding.from_mapping(_inventory(attestation_ref=''))


def test_direct_capability_records_still_receive_full_validation() -> None:
    requirements = OperationCapabilityRequirements.from_mapping(_requirements())
    inventory = CapabilityInventoryBinding.from_mapping(_inventory())

    with pytest.raises(
        GovApiError,
        match='missing_capability_requirements_operation_id',
    ):
        operation_capability_requirements_digest(
            replace(requirements, operation_id='')
        )
    with pytest.raises(GovApiError, match='invalid_capability_inventory_epoch'):
        capability_inventory_binding_digest(replace(inventory, inventory_epoch=-1))
