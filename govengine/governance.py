from __future__ import annotations

from dataclasses import dataclass
from hmac import compare_digest
from typing import Any, Mapping

from govengine._governance_validation import (
    reject_forbidden_governance_input,
    reject_unknown_fields,
    optional_text,
    require_sha256_digest,
    required_nonnegative_int,
    required_text,
    schema_version,
)
from govengine._json_boundary import bounded_json_copy
from govengine.api import GovApiError, require_mapping
from govengine.approvals import ApprovalAttestation, approval_attestation_digest
from govengine.capabilities import (
    CapabilityInventoryBinding,
    OperationCapabilityRequirements,
    capability_inventory_binding_digest,
    operation_capability_requirements_digest,
)
from govengine.policy import CompiledPolicyPack, PolicyCompiler, policy_pack_digest
from govengine.scope_policy import (
    ScopePolicyBinding,
    scope_policy_binding_digest,
    validate_requested_scope,
)
from govengine.signing import govengine_record_digest


GOVERNANCE_REQUEST_SCHEMA_VERSION = 'v1'
SUPPORTED_GOVERNANCE_SIDE_EFFECT_CLASSES = frozenset({'read_only', 'mutation'})
GOVERNANCE_REQUEST_FIELDS = frozenset(
    {
        'schema_version',
        'transaction_id',
        'operation_id',
        'step_id',
        'attempt_id',
        'policy_pack',
        'policy_pack_digest',
        'policy_epoch',
        'execution_facts',
        'execution_facts_digest',
        'execution_spec_digest',
        'payload_digest',
        'requested_scope',
        'requested_scope_digest',
        'scope_policy_binding',
        'scope_policy_binding_digest',
        'capability_requirements',
        'capability_requirements_digest',
        'capability_inventory',
        'capability_inventory_digest',
        'side_effect_class',
        'runtime_instance_id',
        'lease_id',
        'lease_epoch',
        'fencing_token_digest',
        'approval_attestation',
        'approval_attestation_digest',
    }
)


@dataclass(frozen=True)
class GovernanceRequest:
    """Canonical, bounded input to the GovEngine governance transaction.

    RExecOp owns attempts, leases, fencing and runtime execution. This request
    only binds their bounded identifiers to policy, scope and approval inputs;
    it is not an execution permit or a truth artifact.
    """

    transaction_id: str
    operation_id: str
    step_id: str
    attempt_id: str
    policy_pack: CompiledPolicyPack
    policy_pack_digest: str
    policy_epoch: int
    execution_facts: Mapping[str, Any]
    execution_facts_digest: str
    execution_spec_digest: str
    payload_digest: str
    requested_scope: Mapping[str, Any]
    requested_scope_digest: str
    scope_policy_binding: ScopePolicyBinding
    scope_policy_binding_digest: str
    capability_requirements: OperationCapabilityRequirements
    capability_requirements_digest: str
    capability_inventory: CapabilityInventoryBinding
    capability_inventory_digest: str
    side_effect_class: str
    runtime_instance_id: str
    lease_id: str
    lease_epoch: int
    fencing_token_digest: str
    schema_version: str = GOVERNANCE_REQUEST_SCHEMA_VERSION
    approval_attestation: ApprovalAttestation | None = None
    approval_attestation_digest: str = ''

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> 'GovernanceRequest':
        raw = require_mapping(value, reason_code='invalid_governance_request')
        reject_unknown_fields(
            raw,
            allowed=GOVERNANCE_REQUEST_FIELDS,
            reason_code='unknown_governance_request_field',
        )
        policy_pack = _compiled_policy_pack(raw.get('policy_pack'))
        facts = _bounded_mapping(
            raw.get('execution_facts'),
            'invalid_governance_execution_facts',
        )
        scope = _bounded_mapping(
            raw.get('requested_scope'),
            'invalid_governance_requested_scope',
        )
        scope_policy = _scope_policy_binding(raw.get('scope_policy_binding'))
        capability_requirements = _capability_requirements(
            raw.get('capability_requirements')
        )
        capability_inventory = _capability_inventory(
            raw.get('capability_inventory')
        )
        raw_attestation = raw.get('approval_attestation')
        if raw_attestation is None:
            attestation = None
        elif isinstance(raw_attestation, ApprovalAttestation):
            attestation = raw_attestation
        else:
            attestation = ApprovalAttestation.from_mapping(
                require_mapping(
                    raw_attestation,
                    reason_code='invalid_approval_attestation',
                )
            )
        item = cls(
            transaction_id=required_text(
                raw,
                'transaction_id',
                'missing_governance_transaction_id',
            ),
            operation_id=required_text(
                raw,
                'operation_id',
                'missing_governance_operation_id',
            ),
            step_id=required_text(raw, 'step_id', 'missing_governance_step_id'),
            attempt_id=required_text(
                raw,
                'attempt_id',
                'missing_governance_attempt_id',
            ),
            policy_pack=policy_pack,
            policy_pack_digest=require_sha256_digest(
                required_text(
                    raw,
                    'policy_pack_digest',
                    'missing_governance_policy_pack_digest',
                ),
                'invalid_governance_policy_pack_digest',
            ),
            policy_epoch=required_nonnegative_int(
                raw,
                'policy_epoch',
                'invalid_governance_policy_epoch',
            ),
            execution_facts=facts,
            execution_facts_digest=require_sha256_digest(
                required_text(
                    raw,
                    'execution_facts_digest',
                    'missing_governance_execution_facts_digest',
                ),
                'invalid_governance_execution_facts_digest',
            ),
            execution_spec_digest=require_sha256_digest(
                required_text(
                    raw,
                    'execution_spec_digest',
                    'missing_governance_execution_spec_digest',
                ),
                'invalid_governance_execution_spec_digest',
            ),
            payload_digest=require_sha256_digest(
                required_text(
                    raw,
                    'payload_digest',
                    'missing_governance_payload_digest',
                ),
                'invalid_governance_payload_digest',
            ),
            requested_scope=scope,
            requested_scope_digest=require_sha256_digest(
                required_text(
                    raw,
                    'requested_scope_digest',
                    'missing_governance_requested_scope_digest',
                ),
                'invalid_governance_requested_scope_digest',
            ),
            scope_policy_binding=scope_policy,
            scope_policy_binding_digest=require_sha256_digest(
                required_text(
                    raw,
                    'scope_policy_binding_digest',
                    'missing_scope_policy_binding_digest',
                ),
                'invalid_scope_policy_binding_digest',
            ),
            capability_requirements=capability_requirements,
            capability_requirements_digest=require_sha256_digest(
                required_text(
                    raw,
                    'capability_requirements_digest',
                    'missing_capability_requirements_digest',
                ),
                'invalid_capability_requirements_digest',
            ),
            capability_inventory=capability_inventory,
            capability_inventory_digest=require_sha256_digest(
                required_text(
                    raw,
                    'capability_inventory_digest',
                    'missing_capability_inventory_digest',
                ),
                'invalid_capability_inventory_digest',
            ),
            side_effect_class=required_text(
                raw,
                'side_effect_class',
                'missing_governance_side_effect_class',
            ),
            runtime_instance_id=required_text(
                raw,
                'runtime_instance_id',
                'missing_governance_runtime_instance_id',
            ),
            lease_id=required_text(raw, 'lease_id', 'missing_governance_lease_id'),
            lease_epoch=required_nonnegative_int(
                raw,
                'lease_epoch',
                'invalid_governance_lease_epoch',
            ),
            fencing_token_digest=require_sha256_digest(
                required_text(
                    raw,
                    'fencing_token_digest',
                    'missing_governance_fencing_token_digest',
                ),
                'invalid_governance_fencing_token_digest',
            ),
            schema_version=schema_version(
                raw,
                default=GOVERNANCE_REQUEST_SCHEMA_VERSION,
                reason_code='invalid_governance_request_schema_version',
            ),
            approval_attestation=attestation,
            approval_attestation_digest=optional_text(
                raw,
                'approval_attestation_digest',
            ),
        )
        return validate_governance_request(item)

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            'schema_version': self.schema_version,
            'transaction_id': self.transaction_id,
            'operation_id': self.operation_id,
            'step_id': self.step_id,
            'attempt_id': self.attempt_id,
            'policy_pack': self.policy_pack.as_dict(),
            'policy_pack_digest': self.policy_pack_digest,
            'policy_epoch': self.policy_epoch,
            'execution_facts': dict(self.execution_facts),
            'execution_facts_digest': self.execution_facts_digest,
            'execution_spec_digest': self.execution_spec_digest,
            'payload_digest': self.payload_digest,
            'requested_scope': dict(self.requested_scope),
            'requested_scope_digest': self.requested_scope_digest,
            'scope_policy_binding': self.scope_policy_binding.as_dict(),
            'scope_policy_binding_digest': self.scope_policy_binding_digest,
            'capability_requirements': self.capability_requirements.as_dict(),
            'capability_requirements_digest': self.capability_requirements_digest,
            'capability_inventory': self.capability_inventory.as_dict(),
            'capability_inventory_digest': self.capability_inventory_digest,
            'side_effect_class': self.side_effect_class,
            'runtime_instance_id': self.runtime_instance_id,
            'lease_id': self.lease_id,
            'lease_epoch': self.lease_epoch,
            'fencing_token_digest': self.fencing_token_digest,
        }
        if self.approval_attestation is not None:
            payload['approval_attestation'] = self.approval_attestation.as_dict()
            payload['approval_attestation_digest'] = self.approval_attestation_digest
        return payload


def execution_facts_digest(value: Mapping[str, Any]) -> str:
    facts = _bounded_mapping(value, 'invalid_governance_execution_facts')
    reject_forbidden_governance_input(facts)
    return govengine_record_digest(
        facts,
        record_type='govengine.governance.ExecutionFacts',
    )


def requested_scope_digest(value: Mapping[str, Any]) -> str:
    scope = validate_requested_scope(value)
    return govengine_record_digest(
        scope,
        record_type='govengine.governance.RequestedScope',
    )


def governance_subject_digest(
    request: Mapping[str, Any] | GovernanceRequest,
) -> str:
    checked = (
        request
        if isinstance(request, GovernanceRequest)
        else GovernanceRequest.from_mapping(request)
    )
    return govengine_record_digest(
        _subject_record(checked),
        record_type='govengine.governance.GovernanceSubject',
    )


def governance_request_digest(
    request: Mapping[str, Any] | GovernanceRequest,
) -> str:
    checked = validate_governance_request(request)
    return govengine_record_digest(
        checked,
        record_type='govengine.governance.GovernanceRequest',
    )


def validate_governance_request(
    value: Mapping[str, Any] | GovernanceRequest,
) -> GovernanceRequest:
    if not isinstance(value, GovernanceRequest):
        return GovernanceRequest.from_mapping(value)
    item = value
    if item.schema_version != GOVERNANCE_REQUEST_SCHEMA_VERSION:
        raise GovApiError('unknown_governance_request_schema_version')
    payload = item.as_dict()
    for key, reason_code in (
        ('transaction_id', 'missing_governance_transaction_id'),
        ('operation_id', 'missing_governance_operation_id'),
        ('step_id', 'missing_governance_step_id'),
        ('attempt_id', 'missing_governance_attempt_id'),
        ('runtime_instance_id', 'missing_governance_runtime_instance_id'),
        ('lease_id', 'missing_governance_lease_id'),
    ):
        required_text(payload, key, reason_code)
    if (
        isinstance(item.policy_epoch, bool)
        or not isinstance(item.policy_epoch, int)
        or item.policy_epoch < 0
    ):
        raise GovApiError('invalid_governance_policy_epoch')
    if (
        isinstance(item.lease_epoch, bool)
        or not isinstance(item.lease_epoch, int)
        or item.lease_epoch < 0
    ):
        raise GovApiError('invalid_governance_lease_epoch')
    for key, reason_code in (
        ('policy_pack_digest', 'invalid_governance_policy_pack_digest'),
        ('execution_facts_digest', 'invalid_governance_execution_facts_digest'),
        ('execution_spec_digest', 'invalid_governance_execution_spec_digest'),
        ('payload_digest', 'invalid_governance_payload_digest'),
        ('requested_scope_digest', 'invalid_governance_requested_scope_digest'),
        ('scope_policy_binding_digest', 'invalid_scope_policy_binding_digest'),
        (
            'capability_requirements_digest',
            'invalid_capability_requirements_digest',
        ),
        ('capability_inventory_digest', 'invalid_capability_inventory_digest'),
        ('fencing_token_digest', 'invalid_governance_fencing_token_digest'),
    ):
        require_sha256_digest(getattr(item, key), reason_code)
    if item.side_effect_class not in SUPPORTED_GOVERNANCE_SIDE_EFFECT_CLASSES:
        raise GovApiError('unsupported_governance_side_effect_class')
    compiled_policy = _compiled_policy_pack(item.policy_pack)
    if compiled_policy != item.policy_pack:
        raise GovApiError('invalid_governance_policy_pack')
    _bounded_mapping(item.execution_facts, 'invalid_governance_execution_facts')
    _bounded_mapping(item.requested_scope, 'invalid_governance_requested_scope')
    reject_forbidden_governance_input(item.execution_facts)
    reject_forbidden_governance_input(item.requested_scope)
    _require_equal_digest(
        policy_pack_digest(item.policy_pack),
        item.policy_pack_digest,
        'policy_pack_digest_mismatch',
    )
    if (
        item.policy_pack.schema_version == 'v1'
        and item.policy_pack.policy_epoch != item.policy_epoch
    ):
        raise GovApiError('policy_pack_epoch_mismatch')
    _require_equal_digest(
        execution_facts_digest(item.execution_facts),
        item.execution_facts_digest,
        'execution_facts_digest_mismatch',
    )
    _require_equal_digest(
        requested_scope_digest(item.requested_scope),
        item.requested_scope_digest,
        'requested_scope_digest_mismatch',
    )
    _require_equal_digest(
        scope_policy_binding_digest(item.scope_policy_binding),
        item.scope_policy_binding_digest,
        'scope_policy_binding_digest_mismatch',
    )
    _require_equal_digest(
        operation_capability_requirements_digest(item.capability_requirements),
        item.capability_requirements_digest,
        'capability_requirements_digest_mismatch',
    )
    _require_equal_digest(
        capability_inventory_binding_digest(item.capability_inventory),
        item.capability_inventory_digest,
        'capability_inventory_digest_mismatch',
    )
    _validate_scope_capability_bindings(item)
    if item.approval_attestation is None:
        if item.approval_attestation_digest:
            raise GovApiError('approval_attestation_without_payload')
        return item
    require_sha256_digest(
        item.approval_attestation_digest,
        'invalid_approval_attestation_digest',
    )
    _require_equal_digest(
        approval_attestation_digest(item.approval_attestation),
        item.approval_attestation_digest,
        'approval_attestation_digest_mismatch',
    )
    _validate_approval_binding(item)
    return item


def _compiled_policy_pack(value: Any) -> CompiledPolicyPack:
    if isinstance(value, CompiledPolicyPack):
        return value
    raw = require_mapping(value, reason_code='invalid_governance_policy_pack')
    result = PolicyCompiler().compile(raw)
    if not result.ok or result.policy_pack is None:
        raise GovApiError(result.reason_code or 'invalid_governance_policy_pack')
    return result.policy_pack


def _scope_policy_binding(value: Any) -> ScopePolicyBinding:
    if isinstance(value, ScopePolicyBinding):
        return value
    return ScopePolicyBinding.from_mapping(
        require_mapping(value, reason_code='invalid_scope_policy_binding')
    )


def _capability_requirements(value: Any) -> OperationCapabilityRequirements:
    if isinstance(value, OperationCapabilityRequirements):
        return value
    return OperationCapabilityRequirements.from_mapping(
        require_mapping(
            value,
            reason_code='invalid_operation_capability_requirements',
        )
    )


def _capability_inventory(value: Any) -> CapabilityInventoryBinding:
    if isinstance(value, CapabilityInventoryBinding):
        return value
    return CapabilityInventoryBinding.from_mapping(
        require_mapping(value, reason_code='invalid_capability_inventory_binding')
    )


def _bounded_mapping(value: Any, reason_code: str) -> Mapping[str, Any]:
    raw = require_mapping(value, reason_code=reason_code)
    copied = bounded_json_copy(raw)
    if not isinstance(copied, Mapping) or not copied:
        raise GovApiError(reason_code)
    return copied


def _require_equal_digest(actual: str, expected: str, reason_code: str) -> None:
    if not compare_digest(actual, expected):
        raise GovApiError(reason_code)


def _subject_record(item: GovernanceRequest) -> Mapping[str, Any]:
    return {
        'transaction_id': item.transaction_id,
        'operation_id': item.operation_id,
        'step_id': item.step_id,
        'attempt_id': item.attempt_id,
        'policy_pack_digest': item.policy_pack_digest,
        'policy_epoch': item.policy_epoch,
        'execution_facts_digest': item.execution_facts_digest,
        'execution_spec_digest': item.execution_spec_digest,
        'payload_digest': item.payload_digest,
        'requested_scope_digest': item.requested_scope_digest,
        'scope_policy_binding_digest': item.scope_policy_binding_digest,
        'capability_requirements_digest': item.capability_requirements_digest,
        'capability_inventory_digest': item.capability_inventory_digest,
        'side_effect_class': item.side_effect_class,
        'runtime_instance_id': item.runtime_instance_id,
        'lease_id': item.lease_id,
        'lease_epoch': item.lease_epoch,
        'fencing_token_digest': item.fencing_token_digest,
    }


def _validate_approval_binding(item: GovernanceRequest) -> None:
    from govengine.approvals import _validate_request_binding

    assert item.approval_attestation is not None
    _validate_request_binding(item.approval_attestation, item)


def _validate_scope_capability_bindings(item: GovernanceRequest) -> None:
    if not compare_digest(
        item.scope_policy_binding.policy_pack_digest,
        item.policy_pack_digest,
    ):
        raise GovApiError('scope_policy_pack_digest_mismatch')
    if item.scope_policy_binding.policy_epoch != item.policy_epoch:
        raise GovApiError('scope_policy_epoch_mismatch')
    requirements = item.capability_requirements
    if requirements.operation_id != item.operation_id:
        raise GovApiError('capability_requirements_operation_id_mismatch')
    if requirements.step_id != item.step_id:
        raise GovApiError('capability_requirements_step_id_mismatch')
    if not compare_digest(
        requirements.execution_spec_digest,
        item.execution_spec_digest,
    ):
        raise GovApiError('capability_requirements_execution_spec_digest_mismatch')
    if requirements.side_effect_class != item.side_effect_class:
        raise GovApiError('capability_requirements_side_effect_class_mismatch')
    if item.capability_inventory.runtime_instance_id != item.runtime_instance_id:
        raise GovApiError('capability_inventory_runtime_instance_id_mismatch')
