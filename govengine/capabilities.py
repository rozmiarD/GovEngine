from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from govengine._governance_validation import (
    reject_unknown_fields,
    require_sha256_digest,
    required_nonnegative_int,
    required_text,
    schema_version,
    text_tuple,
)
from govengine.api import GovApiError, require_mapping
from govengine.signing import govengine_record_digest


OPERATION_CAPABILITY_REQUIREMENTS_SCHEMA_VERSION = 'v1'
CAPABILITY_INVENTORY_BINDING_SCHEMA_VERSION = 'v1'
CAPABILITY_COMPATIBILITY_DECISION_SCHEMA_VERSION = 'v1'
SUPPORTED_CAPABILITY_SIDE_EFFECT_CLASSES = frozenset({'read_only', 'mutation'})
SELF_ATTESTED_CAPABILITY_KEYS = frozenset(
    {'backend_supported', 'plugin_registered', 'registered_plugin_backend'}
)
OPERATION_CAPABILITY_REQUIREMENTS_FIELDS = frozenset(
    {
        'schema_version',
        'requirements_id',
        'operation_id',
        'step_id',
        'execution_spec_digest',
        'required_backend_class',
        'side_effect_class',
        'required_capabilities',
    }
)
CAPABILITY_INVENTORY_BINDING_FIELDS = frozenset(
    {
        'schema_version',
        'inventory_id',
        'runtime_instance_id',
        'runtime_version',
        'inventory_epoch',
        'source_ref',
        'attestation_ref',
        'backend_classes',
        'side_effect_classes',
        'capabilities',
    }
)


@dataclass(frozen=True)
class OperationCapabilityRequirements:
    requirements_id: str
    operation_id: str
    step_id: str
    execution_spec_digest: str
    required_backend_class: str
    side_effect_class: str
    required_capabilities: tuple[str, ...]
    schema_version: str = OPERATION_CAPABILITY_REQUIREMENTS_SCHEMA_VERSION

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any],
    ) -> 'OperationCapabilityRequirements':
        raw = require_mapping(
            value,
            reason_code='invalid_operation_capability_requirements',
        )
        reject_unknown_fields(
            raw,
            allowed=OPERATION_CAPABILITY_REQUIREMENTS_FIELDS,
            reason_code='unknown_operation_capability_requirements_field',
        )
        required_capabilities = _canonical_text_tuple(
            raw.get('required_capabilities'),
            'invalid_required_capabilities',
        )
        if not required_capabilities:
            raise GovApiError('operation_capability_requirements_empty')
        item = cls(
            requirements_id=required_text(
                raw,
                'requirements_id',
                'missing_capability_requirements_id',
            ),
            operation_id=required_text(
                raw,
                'operation_id',
                'missing_capability_requirements_operation_id',
            ),
            step_id=required_text(
                raw,
                'step_id',
                'missing_capability_requirements_step_id',
            ),
            execution_spec_digest=require_sha256_digest(
                required_text(
                    raw,
                    'execution_spec_digest',
                    'missing_capability_requirements_execution_spec_digest',
                ),
                'invalid_capability_requirements_execution_spec_digest',
            ),
            required_backend_class=required_text(
                raw,
                'required_backend_class',
                'missing_required_backend_class',
            ),
            side_effect_class=required_text(
                raw,
                'side_effect_class',
                'missing_capability_side_effect_class',
            ),
            required_capabilities=required_capabilities,
            schema_version=schema_version(
                raw,
                default=OPERATION_CAPABILITY_REQUIREMENTS_SCHEMA_VERSION,
                reason_code='invalid_capability_requirements_schema_version',
            ),
        )
        _validate_operation_requirements(item)
        return item

    def as_dict(self) -> dict[str, Any]:
        return {
            'schema_version': self.schema_version,
            'requirements_id': self.requirements_id,
            'operation_id': self.operation_id,
            'step_id': self.step_id,
            'execution_spec_digest': self.execution_spec_digest,
            'required_backend_class': self.required_backend_class,
            'side_effect_class': self.side_effect_class,
            'required_capabilities': list(self.required_capabilities),
        }


@dataclass(frozen=True)
class CapabilityInventoryBinding:
    inventory_id: str
    runtime_instance_id: str
    runtime_version: str
    inventory_epoch: int
    source_ref: str
    attestation_ref: str
    backend_classes: tuple[str, ...]
    side_effect_classes: tuple[str, ...]
    capabilities: tuple[str, ...]
    schema_version: str = CAPABILITY_INVENTORY_BINDING_SCHEMA_VERSION

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> 'CapabilityInventoryBinding':
        raw = require_mapping(
            value,
            reason_code='invalid_capability_inventory_binding',
        )
        if any(key in raw for key in SELF_ATTESTED_CAPABILITY_KEYS):
            raise GovApiError('self_attested_capability_support')
        reject_unknown_fields(
            raw,
            allowed=CAPABILITY_INVENTORY_BINDING_FIELDS,
            reason_code='unknown_capability_inventory_field',
        )
        item = cls(
            inventory_id=required_text(
                raw,
                'inventory_id',
                'missing_capability_inventory_id',
            ),
            runtime_instance_id=required_text(
                raw,
                'runtime_instance_id',
                'missing_capability_inventory_runtime_instance_id',
            ),
            runtime_version=required_text(
                raw,
                'runtime_version',
                'missing_capability_inventory_runtime_version',
            ),
            inventory_epoch=required_nonnegative_int(
                raw,
                'inventory_epoch',
                'invalid_capability_inventory_epoch',
            ),
            source_ref=required_text(
                raw,
                'source_ref',
                'missing_capability_inventory_source_ref',
            ),
            attestation_ref=required_text(
                raw,
                'attestation_ref',
                'missing_capability_inventory_attestation_ref',
            ),
            backend_classes=_canonical_text_tuple(
                raw.get('backend_classes'),
                'invalid_capability_inventory_backend_classes',
            ),
            side_effect_classes=_canonical_text_tuple(
                raw.get('side_effect_classes'),
                'invalid_capability_inventory_side_effect_classes',
            ),
            capabilities=_canonical_text_tuple(
                raw.get('capabilities'),
                'invalid_capability_inventory_capabilities',
            ),
            schema_version=schema_version(
                raw,
                default=CAPABILITY_INVENTORY_BINDING_SCHEMA_VERSION,
                reason_code='invalid_capability_inventory_schema_version',
            ),
        )
        _validate_capability_inventory(item)
        return item

    def as_dict(self) -> dict[str, Any]:
        return {
            'schema_version': self.schema_version,
            'inventory_id': self.inventory_id,
            'runtime_instance_id': self.runtime_instance_id,
            'runtime_version': self.runtime_version,
            'inventory_epoch': self.inventory_epoch,
            'source_ref': self.source_ref,
            'attestation_ref': self.attestation_ref,
            'backend_classes': list(self.backend_classes),
            'side_effect_classes': list(self.side_effect_classes),
            'capabilities': list(self.capabilities),
        }


@dataclass(frozen=True)
class CapabilityCompatibilityDecision:
    decision_id: str
    status: str
    reason_code: str
    requirements_digest: str
    inventory_digest: str
    inventory_epoch: int
    runtime_instance_id: str
    missing_capabilities: tuple[str, ...] = ()
    schema_version: str = CAPABILITY_COMPATIBILITY_DECISION_SCHEMA_VERSION

    @property
    def compatible(self) -> bool:
        return self.status == 'compatible'

    def as_dict(self) -> dict[str, Any]:
        return {
            'schema_version': self.schema_version,
            'decision_id': self.decision_id,
            'status': self.status,
            'compatible': self.compatible,
            'reason_code': self.reason_code,
            'requirements_digest': self.requirements_digest,
            'inventory_digest': self.inventory_digest,
            'inventory_epoch': self.inventory_epoch,
            'runtime_instance_id': self.runtime_instance_id,
            'missing_capabilities': list(self.missing_capabilities),
        }


def operation_capability_requirements_digest(
    requirements: Mapping[str, Any] | OperationCapabilityRequirements,
) -> str:
    checked = (
        requirements
        if isinstance(requirements, OperationCapabilityRequirements)
        else OperationCapabilityRequirements.from_mapping(requirements)
    )
    _validate_operation_requirements(checked)
    return govengine_record_digest(
        checked,
        record_type='govengine.capabilities.OperationCapabilityRequirements',
    )


def capability_inventory_binding_digest(
    inventory: Mapping[str, Any] | CapabilityInventoryBinding,
) -> str:
    checked = (
        inventory
        if isinstance(inventory, CapabilityInventoryBinding)
        else CapabilityInventoryBinding.from_mapping(inventory)
    )
    _validate_capability_inventory(checked)
    return govengine_record_digest(
        checked,
        record_type='govengine.capabilities.CapabilityInventoryBinding',
    )


def capability_compatibility_decision_digest(
    decision: CapabilityCompatibilityDecision,
) -> str:
    if not isinstance(decision, CapabilityCompatibilityDecision):
        raise GovApiError('invalid_capability_compatibility_decision')
    return govengine_record_digest(
        decision,
        record_type='govengine.capabilities.CapabilityCompatibilityDecision',
    )


def evaluate_capability_compatibility(
    requirements: Mapping[str, Any] | OperationCapabilityRequirements,
    inventory: Mapping[str, Any] | CapabilityInventoryBinding,
) -> CapabilityCompatibilityDecision:
    checked_requirements = (
        requirements
        if isinstance(requirements, OperationCapabilityRequirements)
        else OperationCapabilityRequirements.from_mapping(requirements)
    )
    checked_inventory = (
        inventory
        if isinstance(inventory, CapabilityInventoryBinding)
        else CapabilityInventoryBinding.from_mapping(inventory)
    )
    _validate_operation_requirements(checked_requirements)
    _validate_capability_inventory(checked_inventory)
    requirements_digest = operation_capability_requirements_digest(
        checked_requirements
    )
    inventory_digest = capability_inventory_binding_digest(checked_inventory)
    missing = tuple(
        sorted(
            set(checked_requirements.required_capabilities)
            - set(checked_inventory.capabilities)
        )
    )
    if checked_requirements.required_backend_class not in checked_inventory.backend_classes:
        reason_code = 'required_backend_class_missing'
    elif checked_requirements.side_effect_class not in checked_inventory.side_effect_classes:
        reason_code = 'side_effect_class_not_supported'
    elif missing:
        reason_code = 'required_capabilities_missing'
    else:
        reason_code = 'capabilities_compatible'
    compatible = reason_code == 'capabilities_compatible'
    return CapabilityCompatibilityDecision(
        decision_id=f'capability:{requirements_digest[7:23]}:{inventory_digest[7:23]}',
        status='compatible' if compatible else 'incompatible',
        reason_code=reason_code,
        requirements_digest=requirements_digest,
        inventory_digest=inventory_digest,
        inventory_epoch=checked_inventory.inventory_epoch,
        runtime_instance_id=checked_inventory.runtime_instance_id,
        missing_capabilities=missing,
    )


def _validate_operation_requirements(
    item: OperationCapabilityRequirements,
) -> None:
    if item.schema_version != OPERATION_CAPABILITY_REQUIREMENTS_SCHEMA_VERSION:
        raise GovApiError('unknown_capability_requirements_schema_version')
    payload = item.as_dict()
    for key, reason_code in (
        ('requirements_id', 'missing_capability_requirements_id'),
        ('operation_id', 'missing_capability_requirements_operation_id'),
        ('step_id', 'missing_capability_requirements_step_id'),
        ('required_backend_class', 'missing_required_backend_class'),
        ('side_effect_class', 'missing_capability_side_effect_class'),
    ):
        required_text(payload, key, reason_code)
    if not item.required_capabilities:
        raise GovApiError('operation_capability_requirements_empty')
    if item.required_capabilities != tuple(sorted(set(item.required_capabilities))):
        raise GovApiError('invalid_required_capabilities')
    if item.side_effect_class not in SUPPORTED_CAPABILITY_SIDE_EFFECT_CLASSES:
        raise GovApiError('unsupported_capability_side_effect_class')
    require_sha256_digest(
        item.execution_spec_digest,
        'invalid_capability_requirements_execution_spec_digest',
    )


def _validate_capability_inventory(item: CapabilityInventoryBinding) -> None:
    if item.schema_version != CAPABILITY_INVENTORY_BINDING_SCHEMA_VERSION:
        raise GovApiError('unknown_capability_inventory_schema_version')
    payload = item.as_dict()
    for key, reason_code in (
        ('inventory_id', 'missing_capability_inventory_id'),
        (
            'runtime_instance_id',
            'missing_capability_inventory_runtime_instance_id',
        ),
        ('runtime_version', 'missing_capability_inventory_runtime_version'),
        ('source_ref', 'missing_capability_inventory_source_ref'),
        ('attestation_ref', 'missing_capability_inventory_attestation_ref'),
    ):
        required_text(payload, key, reason_code)
    if (
        isinstance(item.inventory_epoch, bool)
        or not isinstance(item.inventory_epoch, int)
        or item.inventory_epoch < 0
    ):
        raise GovApiError('invalid_capability_inventory_epoch')
    if not item.backend_classes or not item.side_effect_classes or not item.capabilities:
        raise GovApiError('capability_inventory_empty')
    for values, reason_code in (
        (item.backend_classes, 'invalid_capability_inventory_backend_classes'),
        (
            item.side_effect_classes,
            'invalid_capability_inventory_side_effect_classes',
        ),
        (item.capabilities, 'invalid_capability_inventory_capabilities'),
    ):
        if values != tuple(sorted(set(values))):
            raise GovApiError(reason_code)
    if any(
        side_effect not in SUPPORTED_CAPABILITY_SIDE_EFFECT_CLASSES
        for side_effect in item.side_effect_classes
    ):
        raise GovApiError('unsupported_inventory_side_effect_class')


def _canonical_text_tuple(value: Any, reason_code: str) -> tuple[str, ...]:
    return tuple(sorted(text_tuple(value, reason_code)))
