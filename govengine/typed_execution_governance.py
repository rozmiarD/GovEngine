from __future__ import annotations

from dataclasses import dataclass, field
from string import hexdigits
from typing import Any, Mapping

from govengine.admission import (
    GovAdmissionDecision,
    admission_decision_from_host_gate,
    validate_admission_decision,
)
from govengine.api import GovApiError, require_mapping
from govengine.signing import govengine_record_digest

TYPED_EXECUTION_GOVERNANCE_REQUEST_SCHEMA_VERSION = 'v0.1'
TYPED_EXECUTION_GOVERNANCE_PROJECTION_SCHEMA_VERSION = 'v0.1'
TYPED_EXECUTION_CAPABILITY_COMPATIBILITY_SCHEMA_VERSION = 'v0.1'
TYPED_EXECUTION_STACK_COMPATIBILITY_SCHEMA_VERSION = 'v0.1'
TYPED_EXECUTION_CONTROL_CATALOG_SCHEMA_VERSION = 'v0.1'
RUNTIME_CAPABILITY_DESCRIPTOR_SCHEMA_VERSION = 'v0.1'

SUPPORTED_OPERATION_MODES = frozenset(
    {'dry_run', 'observe', 'emergency_readonly', 'read_only', 'apply'}
)
READ_ONLY_OPERATION_MODES = frozenset(
    {'dry_run', 'observe', 'emergency_readonly', 'read_only'}
)
SUPPORTED_SIDE_EFFECT_CLASSES = frozenset({'read_only', 'mutation'})
SUPPORTED_BACKEND_CLASSES = frozenset(
    {
        'http_api',
        'local_shell_readonly',
        'mock',
        'ssh_readonly',
        'static_fixture',
    }
)
RAW_SHELL_BACKEND_CLASSES = frozenset(
    {
        'local_shell',
        'raw_shell',
        'shell',
        'ssh',
        'subprocess',
    }
)
SUPPORTED_EGRESS_CLASSES = frozenset(
    {
        'local_subprocess',
        'no_network',
        'outbound_http',
        'outbound_ssh',
        'plugin_undeclared',
    }
)
SUPPORTED_IDENTITY_CLASSES = frozenset(
    {
        'api_token_optional',
        'none',
        'plugin_declared',
        'ssh_identity',
    }
)
SUPPORTED_LIVE_BACKEND_POSTURES = frozenset(
    {'fixture_only', 'live_backend', 'mock'}
)

BASELINE_TYPED_EXECUTION_CONTROLS = (
    'backend_class_supported',
    'no_raw_shell',
    'read_only_posture',
    'capability_descriptor_digest_present',
    'step_execution_spec_digest_present',
    'payload_digest_present',
    'receipt_required',
    'output_digest_required',
    'network_boundary_match',
    'secret_ref_requirements_met',
    'mutation_requires_approval',
)

FORBIDDEN_TYPED_EXECUTION_METADATA_KEYS = (
    'api_key',
    'argv',
    'base_url',
    'command',
    'commands',
    'credential',
    'credentials',
    'endpoint',
    'host',
    'hostname',
    'identity_file',
    'ip',
    'password',
    'path',
    'raw_output',
    'secret',
    'stderr',
    'stdout',
    'subprocess',
    'target',
    'target_url',
    'token',
    'url',
)


@dataclass(frozen=True)
class RuntimeCapabilityDescriptor:
    """Bounded compatibility input derived from a RExecOp capability descriptor."""

    schema_version: str
    backend_class: str
    identity_class: str
    egress_class: str
    read_only_backend: bool
    live_backend_posture: str
    network_boundary: Mapping[str, Any] = field(default_factory=dict)
    secret_ref_requirements: tuple[Mapping[str, Any], ...] = ()
    declared_capability_descriptors: tuple[str, ...] = ()
    certification_tier: str = ''
    mode: str = ''

    def as_dict(self) -> dict[str, Any]:
        return {
            'schema_version': self.schema_version,
            'backend_class': self.backend_class,
            'identity_class': self.identity_class,
            'egress_class': self.egress_class,
            'read_only_backend': self.read_only_backend,
            'live_backend_posture': self.live_backend_posture,
            'network_boundary': dict(self.network_boundary),
            'secret_ref_requirements': [dict(item) for item in self.secret_ref_requirements],
            'declared_capability_descriptors': list(self.declared_capability_descriptors),
            'certification_tier': self.certification_tier,
            'mode': self.mode,
        }


@dataclass(frozen=True)
class TypedExecutionGovernanceRequest:
    """GovEngine-owned projection for typed execution admission.

    RExecOp owns typed execution specs, backend IO and receipt binding. This
    request carries only digests, bounded shape metadata and capability posture
    so GovEngine can decide whether one step may proceed before backend IO.
    """

    schema_version: str
    request_id: str
    step_id: str
    operation_mode: str
    step_execution_spec_digest: str
    capability_descriptor_digest: str
    payload_schema: str
    payload_digest: str
    backend_class: str
    connector: str
    action: str
    read_only: bool
    side_effect_class: str
    capability_descriptor: RuntimeCapabilityDescriptor
    operation_id: str = ''
    evidence_requirements: Mapping[str, Any] = field(default_factory=dict)
    allowed_network_egress: tuple[str, ...] = ()
    required_capability_descriptors: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            'schema_version': self.schema_version,
            'request_id': self.request_id,
            'step_id': self.step_id,
            'operation_mode': self.operation_mode,
            'step_execution_spec_digest': self.step_execution_spec_digest,
            'capability_descriptor_digest': self.capability_descriptor_digest,
            'payload_schema': self.payload_schema,
            'payload_digest': self.payload_digest,
            'backend_class': self.backend_class,
            'connector': self.connector,
            'action': self.action,
            'read_only': self.read_only,
            'side_effect_class': self.side_effect_class,
            'capability_descriptor': self.capability_descriptor.as_dict(),
            'evidence_requirements': dict(self.evidence_requirements),
            'allowed_network_egress': list(self.allowed_network_egress),
            'required_capability_descriptors': list(self.required_capability_descriptors),
            'metadata': dict(self.metadata),
        }
        if self.operation_id:
            payload['operation_id'] = self.operation_id
        return payload


@dataclass(frozen=True)
class TypedExecutionGovernanceProjection:
    schema_version: str
    status: str
    request_id: str
    step_id: str
    reason_code: str
    governance_checks: tuple[Mapping[str, Any], ...] = ()
    blockers: tuple[str, ...] = ()
    request_digest: str = ''
    projection_digest: str = ''
    non_claims: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        return {
            'schema_version': self.schema_version,
            'status': self.status,
            'request_id': self.request_id,
            'step_id': self.step_id,
            'reason_code': self.reason_code,
            'governance_checks': [dict(item) for item in self.governance_checks],
            'blockers': list(self.blockers),
            'request_digest': self.request_digest,
            'projection_digest': self.projection_digest,
            'non_claims': list(self.non_claims),
        }


@dataclass(frozen=True)
class TypedExecutionCapabilityCompatibilityReport:
    schema_version: str
    status: str
    request_id: str
    step_id: str
    reason_code: str
    required_capability_descriptors: tuple[str, ...] = ()
    satisfied_capability_descriptors: tuple[str, ...] = ()
    missing_capability_descriptors: tuple[str, ...] = ()
    policy_controls: tuple[Mapping[str, Any], ...] = ()
    blockers: tuple[str, ...] = ()
    report_digest: str = ''
    non_claims: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        return {
            'schema_version': self.schema_version,
            'status': self.status,
            'request_id': self.request_id,
            'step_id': self.step_id,
            'reason_code': self.reason_code,
            'required_capability_descriptors': list(self.required_capability_descriptors),
            'satisfied_capability_descriptors': list(self.satisfied_capability_descriptors),
            'missing_capability_descriptors': list(self.missing_capability_descriptors),
            'policy_controls': [dict(item) for item in self.policy_controls],
            'blockers': list(self.blockers),
            'report_digest': self.report_digest,
            'non_claims': list(self.non_claims),
        }


@dataclass(frozen=True)
class TypedExecutionStackCompatibilityRequest:
    """Stack-level compatibility input over RExecOp backend descriptors."""

    schema_version: str
    request_id: str
    backend_descriptors: tuple[Mapping[str, Any], ...] = ()
    required_controls: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            'schema_version': self.schema_version,
            'request_id': self.request_id,
            'backend_descriptors': [dict(item) for item in self.backend_descriptors],
            'required_controls': list(self.required_controls),
        }


@dataclass(frozen=True)
class TypedExecutionStackCompatibilityReport:
    schema_version: str
    status: str
    request_id: str
    reason_code: str
    supported_backends: tuple[str, ...] = ()
    unsupported_backends: tuple[str, ...] = ()
    supported_controls: tuple[str, ...] = ()
    missing_controls: tuple[str, ...] = ()
    policy_controls: tuple[Mapping[str, Any], ...] = ()
    blockers: tuple[str, ...] = ()
    report_digest: str = ''
    non_claims: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        return {
            'schema_version': self.schema_version,
            'status': self.status,
            'request_id': self.request_id,
            'reason_code': self.reason_code,
            'supported_backends': list(self.supported_backends),
            'unsupported_backends': list(self.unsupported_backends),
            'supported_controls': list(self.supported_controls),
            'missing_controls': list(self.missing_controls),
            'policy_controls': [dict(item) for item in self.policy_controls],
            'blockers': list(self.blockers),
            'report_digest': self.report_digest,
            'non_claims': list(self.non_claims),
        }


@dataclass(frozen=True)
class TypedExecutionGovernanceBundle:
    schema_version: str
    status: str
    request_id: str
    step_id: str
    governance: TypedExecutionGovernanceProjection
    compatibility: TypedExecutionCapabilityCompatibilityReport
    bundle_digest: str = ''
    non_claims: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        return {
            'schema_version': self.schema_version,
            'status': self.status,
            'request_id': self.request_id,
            'step_id': self.step_id,
            'governance': self.governance.as_dict(),
            'compatibility': self.compatibility.as_dict(),
            'bundle_digest': self.bundle_digest,
            'non_claims': list(self.non_claims),
        }


def validate_runtime_capability_descriptor(
    value: Mapping[str, Any] | RuntimeCapabilityDescriptor,
) -> RuntimeCapabilityDescriptor:
    if isinstance(value, RuntimeCapabilityDescriptor):
        return value
    raw = require_mapping(value, reason_code='invalid_runtime_capability_descriptor')
    schema_version = str(raw.get('schema_version') or '').strip()
    if schema_version != RUNTIME_CAPABILITY_DESCRIPTOR_SCHEMA_VERSION:
        raise GovApiError(
            f'unsupported_runtime_capability_descriptor_version:{schema_version}'
        )
    backend_class = _required_text(raw, 'backend_class')
    identity_class = str(raw.get('identity_class') or '').strip()
    egress_class = str(raw.get('egress_class') or '').strip()
    live_backend_posture = str(raw.get('live_backend_posture') or '').strip()
    if identity_class and identity_class not in SUPPORTED_IDENTITY_CLASSES:
        raise GovApiError(f'unsupported_identity_class:{identity_class}')
    if egress_class and egress_class not in SUPPORTED_EGRESS_CLASSES:
        raise GovApiError(f'unsupported_egress_class:{egress_class}')
    if live_backend_posture and live_backend_posture not in SUPPORTED_LIVE_BACKEND_POSTURES:
        raise GovApiError(f'unsupported_live_backend_posture:{live_backend_posture}')
    network_boundary = require_mapping(
        raw.get('network_boundary') or {},
        reason_code='invalid_runtime_capability_network_boundary',
    )
    return RuntimeCapabilityDescriptor(
        schema_version=schema_version,
        backend_class=backend_class,
        identity_class=identity_class,
        egress_class=egress_class,
        read_only_backend=bool(raw.get('read_only_backend', False)),
        live_backend_posture=live_backend_posture,
        network_boundary=dict(network_boundary),
        secret_ref_requirements=_mapping_tuple(raw.get('secret_ref_requirements') or ()),
        declared_capability_descriptors=_string_tuple(
            raw.get('declared_capability_descriptors') or ()
        ),
        certification_tier=str(raw.get('certification_tier') or '').strip(),
        mode=str(raw.get('mode') or '').strip(),
    )


def validate_typed_execution_governance_request(
    value: Mapping[str, Any] | TypedExecutionGovernanceRequest,
) -> TypedExecutionGovernanceRequest:
    if isinstance(value, TypedExecutionGovernanceRequest):
        return value
    raw = require_mapping(value, reason_code='invalid_typed_execution_governance_request')
    schema_version = str(raw.get('schema_version') or '').strip()
    if schema_version != TYPED_EXECUTION_GOVERNANCE_REQUEST_SCHEMA_VERSION:
        raise GovApiError(
            f'unsupported_typed_execution_governance_request_version:{schema_version}'
        )
    capability = validate_runtime_capability_descriptor(
        require_mapping(
            raw.get('capability_descriptor') or {},
            reason_code='missing_runtime_capability_descriptor',
        )
    )
    item = TypedExecutionGovernanceRequest(
        schema_version=schema_version,
        request_id=_required_text(raw, 'request_id'),
        step_id=_required_text(raw, 'step_id'),
        operation_mode=_required_text(raw, 'operation_mode'),
        step_execution_spec_digest=_required_digest(
            raw,
            'step_execution_spec_digest',
            'missing_step_execution_spec_digest',
        ),
        capability_descriptor_digest=_required_digest(
            raw,
            'capability_descriptor_digest',
            'missing_capability_descriptor_digest',
        ),
        payload_schema=_required_text(raw, 'payload_schema'),
        payload_digest=_required_digest(raw, 'payload_digest', 'missing_payload_digest'),
        backend_class=_required_text(raw, 'backend_class'),
        connector=_required_text(raw, 'connector'),
        action=_required_text(raw, 'action'),
        read_only=bool(raw.get('read_only', False)),
        side_effect_class=_required_text(raw, 'side_effect_class'),
        capability_descriptor=capability,
        operation_id=str(raw.get('operation_id') or '').strip(),
        evidence_requirements=require_mapping(
            raw.get('evidence_requirements') or {},
            reason_code='invalid_typed_execution_evidence_requirements',
        ),
        allowed_network_egress=_string_tuple(raw.get('allowed_network_egress') or ()),
        required_capability_descriptors=_string_tuple(
            raw.get('required_capability_descriptors') or ()
        ),
        metadata=_metadata(raw.get('metadata')),
    )
    _validate_typed_execution_request_shape(item)
    return item


def typed_execution_control_catalog() -> dict[str, Any]:
    return {
        'schema_version': TYPED_EXECUTION_CONTROL_CATALOG_SCHEMA_VERSION,
        'controls': list(BASELINE_TYPED_EXECUTION_CONTROLS),
        'supported_backend_classes': sorted(SUPPORTED_BACKEND_CLASSES),
        'raw_shell_backend_classes': sorted(RAW_SHELL_BACKEND_CLASSES),
        'supported_egress_classes': sorted(SUPPORTED_EGRESS_CLASSES),
        'supported_identity_classes': sorted(SUPPORTED_IDENTITY_CLASSES),
    }


def validate_typed_execution_stack_compatibility_request(
    value: Mapping[str, Any] | TypedExecutionStackCompatibilityRequest,
) -> TypedExecutionStackCompatibilityRequest:
    if isinstance(value, TypedExecutionStackCompatibilityRequest):
        return value
    raw = require_mapping(value, reason_code='invalid_typed_execution_stack_compatibility_request')
    schema_version = str(raw.get('schema_version') or '').strip()
    if schema_version != TYPED_EXECUTION_STACK_COMPATIBILITY_SCHEMA_VERSION:
        raise GovApiError(
            f'unsupported_typed_execution_stack_compatibility_version:{schema_version}'
        )
    return TypedExecutionStackCompatibilityRequest(
        schema_version=schema_version,
        request_id=_required_text(raw, 'request_id'),
        backend_descriptors=_mapping_tuple(raw.get('backend_descriptors') or ()),
        required_controls=_string_tuple(
            raw.get('required_controls') or BASELINE_TYPED_EXECUTION_CONTROLS
        ),
    )


def evaluate_typed_execution_stack_compatibility(
    request: Mapping[str, Any] | TypedExecutionStackCompatibilityRequest,
) -> TypedExecutionStackCompatibilityReport:
    """Evaluate stack-level backend/control compatibility for typed execution G5."""
    checked = validate_typed_execution_stack_compatibility_request(request)
    supported_backends: list[str] = []
    unsupported_backends: list[str] = []
    backend_controls: list[dict[str, Any]] = []

    for item in checked.backend_descriptors:
        backend = str(item.get('backend_class') or '').strip()
        if not backend:
            unsupported_backends.append('missing_backend_class')
            continue
        if backend in RAW_SHELL_BACKEND_CLASSES:
            unsupported_backends.append(backend)
            backend_controls.append(
                {
                    'control': 'raw_shell_backend_blocked',
                    'passed': False,
                    'details': {'backend_class': backend},
                }
            )
            continue
        passed = _stack_backend_supported(item)
        backend_controls.append(
            {
                'control': 'backend_class_supported',
                'passed': passed,
                'details': {
                    'backend_class': backend,
                    'certification_tier': item.get('certification_tier'),
                    'egress_class': item.get('egress_class'),
                    'identity_class': item.get('identity_class'),
                },
            }
        )
        if passed:
            supported_backends.append(backend)
        else:
            unsupported_backends.append(backend)

    catalog_controls = set(BASELINE_TYPED_EXECUTION_CONTROLS)
    required_controls = list(checked.required_controls)
    missing_controls = [
        control for control in required_controls if control not in catalog_controls
    ]
    control_checks = [
        {
            'control': 'typed_execution_control_catalog',
            'passed': not missing_controls,
            'details': {
                'required': required_controls,
                'missing': missing_controls,
            },
        }
    ]
    policy_controls = backend_controls + control_checks
    blockers = [item['control'] for item in policy_controls if not item['passed']]
    if unsupported_backends:
        blockers.append('unsupported_backend_descriptors')
    if missing_controls:
        blockers.append('missing_typed_execution_controls')
    status = 'passed' if not blockers else 'blocked'
    reason_code = (
        'typed_execution_stack_compatible' if not blockers else blockers[0]
    )
    body = {
        'schema_version': TYPED_EXECUTION_STACK_COMPATIBILITY_SCHEMA_VERSION,
        'status': status,
        'request_id': checked.request_id,
        'reason_code': reason_code,
        'supported_backends': supported_backends,
        'unsupported_backends': unsupported_backends,
        'supported_controls': list(catalog_controls),
        'missing_controls': missing_controls,
        'policy_controls': policy_controls,
        'blockers': blockers,
    }
    report_digest = govengine_record_digest(
        body,
        record_type='govengine.typed_execution_governance.TypedExecutionStackCompatibilityReport',
        schema_version=TYPED_EXECUTION_STACK_COMPATIBILITY_SCHEMA_VERSION,
    )
    return TypedExecutionStackCompatibilityReport(
        schema_version=TYPED_EXECUTION_STACK_COMPATIBILITY_SCHEMA_VERSION,
        status=status,
        request_id=checked.request_id,
        reason_code=reason_code,
        supported_backends=tuple(supported_backends),
        unsupported_backends=tuple(unsupported_backends),
        supported_controls=tuple(sorted(catalog_controls)),
        missing_controls=tuple(missing_controls),
        policy_controls=tuple(policy_controls),
        blockers=tuple(blockers),
        report_digest=report_digest,
        non_claims=_STACK_COMPATIBILITY_NON_CLAIMS,
    )


def project_typed_execution_governance(
    request: Mapping[str, Any] | TypedExecutionGovernanceRequest,
) -> TypedExecutionGovernanceProjection:
    checked = validate_typed_execution_governance_request(request)
    checks: list[dict[str, Any]] = []
    blockers: list[str] = []

    digest_check = _check_required_digests(checked)
    checks.append(digest_check)
    if not digest_check['passed']:
        blockers.append('missing_typed_execution_digest_binding')

    posture_check = _check_read_only_posture(checked)
    checks.append(posture_check)
    if not posture_check['passed']:
        blockers.append('read_only_side_effect_required')

    evidence_check = _check_evidence_requirements(checked)
    checks.append(evidence_check)
    if not evidence_check['passed']:
        blockers.extend(evidence_check['details']['blockers'])

    status = 'passed' if not blockers else 'blocked'
    reason_code = 'typed_execution_governance_passed' if not blockers else blockers[0]
    request_digest = typed_execution_governance_request_digest(checked)
    body = {
        'schema_version': TYPED_EXECUTION_GOVERNANCE_PROJECTION_SCHEMA_VERSION,
        'status': status,
        'request_id': checked.request_id,
        'step_id': checked.step_id,
        'reason_code': reason_code,
        'governance_checks': checks,
        'blockers': blockers,
        'request_digest': request_digest,
    }
    projection_digest = govengine_record_digest(
        body,
        record_type='govengine.typed_execution_governance.TypedExecutionGovernanceProjection',
        schema_version=TYPED_EXECUTION_GOVERNANCE_PROJECTION_SCHEMA_VERSION,
    )
    return TypedExecutionGovernanceProjection(
        schema_version=TYPED_EXECUTION_GOVERNANCE_PROJECTION_SCHEMA_VERSION,
        status=status,
        request_id=checked.request_id,
        step_id=checked.step_id,
        reason_code=reason_code,
        governance_checks=tuple(checks),
        blockers=tuple(blockers),
        request_digest=request_digest,
        projection_digest=projection_digest,
        non_claims=_GOVERNANCE_NON_CLAIMS,
    )


def evaluate_typed_execution_capability_compatibility(
    request: Mapping[str, Any] | TypedExecutionGovernanceRequest,
) -> TypedExecutionCapabilityCompatibilityReport:
    checked = validate_typed_execution_governance_request(request)
    descriptor = checked.capability_descriptor
    provided = set(descriptor.declared_capability_descriptors)
    provided.add(descriptor.backend_class)
    provided.add(f'connector.{descriptor.backend_class}')
    satisfied: list[str] = []
    missing: list[str] = []
    for capability in checked.required_capability_descriptors:
        if capability in provided or _matches_declared_capability(capability, descriptor):
            satisfied.append(capability)
        else:
            missing.append(capability)

    policy_controls = _typed_execution_policy_controls(checked, missing)
    blockers = [item['control'] for item in policy_controls if not item['passed']]
    if missing:
        blockers.append('missing_required_capability_descriptors')
    status = 'passed' if not blockers else 'blocked'
    reason_code = (
        'typed_execution_capability_compatible' if not blockers else blockers[0]
    )
    body = {
        'schema_version': TYPED_EXECUTION_CAPABILITY_COMPATIBILITY_SCHEMA_VERSION,
        'status': status,
        'request_id': checked.request_id,
        'step_id': checked.step_id,
        'reason_code': reason_code,
        'required_capability_descriptors': list(checked.required_capability_descriptors),
        'satisfied_capability_descriptors': satisfied,
        'missing_capability_descriptors': missing,
        'policy_controls': policy_controls,
        'blockers': blockers,
    }
    report_digest = govengine_record_digest(
        body,
        record_type=(
            'govengine.typed_execution_governance.TypedExecutionCapabilityCompatibilityReport'
        ),
        schema_version=TYPED_EXECUTION_CAPABILITY_COMPATIBILITY_SCHEMA_VERSION,
    )
    return TypedExecutionCapabilityCompatibilityReport(
        schema_version=TYPED_EXECUTION_CAPABILITY_COMPATIBILITY_SCHEMA_VERSION,
        status=status,
        request_id=checked.request_id,
        step_id=checked.step_id,
        reason_code=reason_code,
        required_capability_descriptors=checked.required_capability_descriptors,
        satisfied_capability_descriptors=tuple(satisfied),
        missing_capability_descriptors=tuple(missing),
        policy_controls=tuple(policy_controls),
        blockers=tuple(blockers),
        report_digest=report_digest,
        non_claims=_COMPATIBILITY_NON_CLAIMS,
    )


def explain_typed_execution_governance(
    request: Mapping[str, Any] | TypedExecutionGovernanceRequest,
) -> TypedExecutionGovernanceBundle:
    checked = validate_typed_execution_governance_request(request)
    governance = project_typed_execution_governance(checked)
    compatibility = evaluate_typed_execution_capability_compatibility(checked)
    blockers = list(dict.fromkeys([*governance.blockers, *compatibility.blockers]))
    status = 'passed' if not blockers else 'blocked'
    bundle_body = {
        'schema_version': TYPED_EXECUTION_GOVERNANCE_PROJECTION_SCHEMA_VERSION,
        'status': status,
        'request_id': checked.request_id,
        'step_id': checked.step_id,
        'governance_digest': governance.projection_digest,
        'compatibility_digest': compatibility.report_digest,
        'blockers': blockers,
    }
    bundle_digest = govengine_record_digest(
        bundle_body,
        record_type='govengine.typed_execution_governance.TypedExecutionGovernanceBundle',
        schema_version=TYPED_EXECUTION_GOVERNANCE_PROJECTION_SCHEMA_VERSION,
    )
    return TypedExecutionGovernanceBundle(
        schema_version=TYPED_EXECUTION_GOVERNANCE_PROJECTION_SCHEMA_VERSION,
        status=status,
        request_id=checked.request_id,
        step_id=checked.step_id,
        governance=governance,
        compatibility=compatibility,
        bundle_digest=bundle_digest,
        non_claims=_BUNDLE_NON_CLAIMS,
    )


def typed_execution_governance_request_digest(
    request: Mapping[str, Any] | TypedExecutionGovernanceRequest,
) -> str:
    checked = validate_typed_execution_governance_request(request)
    return govengine_record_digest(
        checked.as_dict(),
        record_type='govengine.typed_execution_governance.TypedExecutionGovernanceRequest',
        schema_version=TYPED_EXECUTION_GOVERNANCE_REQUEST_SCHEMA_VERSION,
    )


def admit_typed_execution(
    request: Mapping[str, Any] | TypedExecutionGovernanceRequest,
) -> GovAdmissionDecision:
    checked = validate_typed_execution_governance_request(request)
    bundle = explain_typed_execution_governance(checked)
    allowed = bundle.status == 'passed'
    outcome = 'allowed' if allowed else 'denied'
    reason_code = (
        'typed_execution_admission_allowed'
        if allowed
        else bundle.governance.reason_code
        if bundle.governance.blockers
        else bundle.compatibility.reason_code
    )
    blockers = bundle.governance.blockers + bundle.compatibility.blockers
    admission = admission_decision_from_host_gate(
        decision_id=f'typed-execution-admission:{checked.request_id}',
        subject_ref=typed_execution_governance_request_digest(checked),
        subject_kind='generic',
        allowed=allowed,
        reason_code=reason_code,
        blockers=blockers,
        signal={
            'request_id': checked.request_id,
            'operation_id': checked.operation_id,
            'step_id': checked.step_id,
            'operation_mode': checked.operation_mode,
            'backend_class': checked.backend_class,
            'connector': checked.connector,
            'action': checked.action,
            'side_effect_class': checked.side_effect_class,
            'step_execution_spec_digest': checked.step_execution_spec_digest,
            'capability_descriptor_digest': checked.capability_descriptor_digest,
            'payload_schema': checked.payload_schema,
            'payload_digest': checked.payload_digest,
            'governance_digest': bundle.governance.projection_digest,
            'compatibility_digest': bundle.compatibility.report_digest,
            'bundle_digest': bundle.bundle_digest,
        },
        metadata={
            'source': 'typed_execution_governance_request',
            'schema_version': checked.schema_version,
        },
    )
    if admission.outcome != outcome or admission.blockers != blockers:
        admission = GovAdmissionDecision(
            decision_id=admission.decision_id,
            subject_ref=admission.subject_ref,
            subject_kind=admission.subject_kind,
            outcome=outcome,
            allowed=allowed,
            reason_code=admission.reason_code,
            blockers=blockers,
            signal=admission.signal,
            metadata=admission.metadata,
        )
    return validate_admission_decision(admission)


def typed_execution_admission_digest(
    admission: Mapping[str, Any] | GovAdmissionDecision,
) -> str:
    checked = validate_admission_decision(admission)
    return govengine_record_digest(
        checked,
        record_type='govengine.admission.GovAdmissionDecision',
    )


def validate_typed_execution_admission(
    admission: Mapping[str, Any] | GovAdmissionDecision,
    *,
    request: Mapping[str, Any] | TypedExecutionGovernanceRequest,
) -> GovAdmissionDecision:
    checked = validate_admission_decision(admission)
    expected = admit_typed_execution(request)
    if checked.as_dict() != expected.as_dict():
        raise GovApiError('typed_execution_admission_drift')
    return checked


def _validate_typed_execution_request_shape(item: TypedExecutionGovernanceRequest) -> None:
    if item.operation_mode not in SUPPORTED_OPERATION_MODES:
        raise GovApiError(f'unsupported_typed_execution_operation_mode:{item.operation_mode}')
    if item.side_effect_class not in SUPPORTED_SIDE_EFFECT_CLASSES:
        raise GovApiError(f'unsupported_side_effect_class:{item.side_effect_class}')
    if item.backend_class != item.capability_descriptor.backend_class:
        raise GovApiError('typed_execution_backend_class_mismatch')
    _reject_forbidden_typed_execution_metadata(item.metadata)
    _reject_forbidden_typed_execution_metadata(item.evidence_requirements)


def _check_required_digests(item: TypedExecutionGovernanceRequest) -> dict[str, Any]:
    missing = [
        name
        for name, value in (
            ('step_execution_spec_digest', item.step_execution_spec_digest),
            ('capability_descriptor_digest', item.capability_descriptor_digest),
            ('payload_digest', item.payload_digest),
        )
        if not value
    ]
    return {
        'gate': 'required_digests',
        'passed': not missing,
        'details': {'missing': missing},
    }


def _check_read_only_posture(item: TypedExecutionGovernanceRequest) -> dict[str, Any]:
    read_only_mode = item.operation_mode in READ_ONLY_OPERATION_MODES
    passed = True
    details: dict[str, Any] = {
        'operation_mode': item.operation_mode,
        'side_effect_class': item.side_effect_class,
        'read_only': item.read_only,
    }
    if read_only_mode:
        passed = item.side_effect_class == 'read_only' and item.read_only
    return {
        'gate': 'read_only_posture',
        'passed': passed,
        'details': details,
    }


def _check_evidence_requirements(item: TypedExecutionGovernanceRequest) -> dict[str, Any]:
    evidence = dict(item.evidence_requirements)
    blockers: list[str] = []
    receipt_required = bool(evidence.get('receipt_required', True))
    if not receipt_required:
        blockers.append('receipt_required')
    output_digest_required = bool(evidence.get('output_digest_required', False))
    output_digest_ref = str(evidence.get('output_digest_ref') or '').strip()
    if output_digest_required and not output_digest_ref:
        blockers.append('missing_output_digest_ref')
    approval_ref = str(evidence.get('approval_evidence_ref') or '').strip()
    if item.side_effect_class == 'mutation' and not approval_ref:
        blockers.append('mutation_requires_approval_evidence')
    return {
        'gate': 'evidence_requirements',
        'passed': not blockers,
        'details': {
            'receipt_required': receipt_required,
            'output_digest_required': output_digest_required,
            'blockers': blockers,
        },
    }


def _typed_execution_policy_controls(
    request: TypedExecutionGovernanceRequest,
    missing_capabilities: list[str],
) -> list[dict[str, Any]]:
    descriptor = request.capability_descriptor
    controls: list[dict[str, Any]] = []

    backend_supported = request.backend_class in SUPPORTED_BACKEND_CLASSES
    controls.append(
        {
            'control': 'backend_class_supported',
            'passed': backend_supported,
            'details': {'backend_class': request.backend_class},
        }
    )

    raw_shell = request.backend_class in RAW_SHELL_BACKEND_CLASSES
    controls.append(
        {
            'control': 'no_raw_shell',
            'passed': not raw_shell,
            'details': {'backend_class': request.backend_class},
        }
    )
    if raw_shell:
        controls[-1]['control'] = 'raw_shell_backend_blocked'

    controls.append(
        {
            'control': 'read_only_posture',
            'passed': _check_read_only_posture(request)['passed'],
            'details': {'operation_mode': request.operation_mode},
        }
    )
    controls.append(
        {
            'control': 'capability_descriptor_digest_present',
            'passed': bool(request.capability_descriptor_digest),
            'details': {'digest': request.capability_descriptor_digest},
        }
    )
    controls.append(
        {
            'control': 'step_execution_spec_digest_present',
            'passed': bool(request.step_execution_spec_digest),
            'details': {'digest': request.step_execution_spec_digest},
        }
    )
    controls.append(
        {
            'control': 'payload_digest_present',
            'passed': bool(request.payload_digest),
            'details': {'digest': request.payload_digest},
        }
    )
    controls.append(
        {
            'control': 'receipt_required',
            'passed': bool(request.evidence_requirements.get('receipt_required', True)),
            'details': dict(request.evidence_requirements),
        }
    )
    output_digest_required = bool(
        request.evidence_requirements.get('output_digest_required', False)
    )
    output_digest_ref = str(
        request.evidence_requirements.get('output_digest_ref') or ''
    ).strip()
    output_digest_passed = (not output_digest_required) or bool(output_digest_ref)
    controls.append(
        {
            'control': 'output_digest_required'
            if output_digest_passed
            else 'missing_output_digest_ref',
            'passed': output_digest_passed,
            'details': {
                'output_digest_required': output_digest_required,
                'output_digest_ref': output_digest_ref,
            },
        }
    )

    egress = str(
        descriptor.network_boundary.get('egress')
        or descriptor.egress_class
        or ''
    ).strip()
    allowed = set(request.allowed_network_egress)
    network_passed = True if not allowed else egress in allowed
    controls.append(
        {
            'control': 'network_boundary_match',
            'passed': network_passed,
            'details': {
                'egress': egress,
                'allowed_network_egress': list(request.allowed_network_egress),
            },
        }
    )
    if not network_passed:
        controls[-1]['control'] = 'network_boundary_mismatch'

    missing_secret_refs = [
        str(item.get('path') or '')
        for item in descriptor.secret_ref_requirements
        if bool(item.get('required')) and not bool(item.get('present'))
    ]
    controls.append(
        {
            'control': 'secret_ref_requirements_met',
            'passed': not missing_secret_refs,
            'details': {'missing': missing_secret_refs},
        }
    )

    approval_ref = str(
        request.evidence_requirements.get('approval_evidence_ref') or ''
    ).strip()
    mutation_requires_approval = request.side_effect_class == 'mutation'
    controls.append(
        {
            'control': 'mutation_requires_approval',
            'passed': (not mutation_requires_approval) or bool(approval_ref),
            'details': {
                'side_effect_class': request.side_effect_class,
                'approval_evidence_ref': approval_ref,
            },
        }
    )

    controls.append(
        {
            'control': 'capability_coverage',
            'passed': not missing_capabilities,
            'details': {
                'required': len(request.required_capability_descriptors),
                'missing': missing_capabilities,
            },
        }
    )
    if not backend_supported and request.backend_class not in RAW_SHELL_BACKEND_CLASSES:
        controls[0]['control'] = 'unsupported_backend_class'
    return controls


def _matches_declared_capability(
    capability: str,
    descriptor: RuntimeCapabilityDescriptor,
) -> bool:
    aliases = _RUNTIME_CAPABILITY_ALIASES.get(capability, ())
    declared = set(descriptor.declared_capability_descriptors)
    if capability in declared or descriptor.backend_class == capability:
        return True
    if any(alias in declared for alias in aliases):
        return True
    return capability == f'connector.{descriptor.backend_class}'


_RUNTIME_CAPABILITY_ALIASES = {
    'http_api': ('connector.http.rest.read', 'connector.http.rest.mutate'),
    'local_shell_readonly': ('connector.shell.readonly',),
    'ssh_readonly': ('connector.ssh.readonly',),
    'static_fixture': ('connector.fixture.static',),
    'mock': ('connector.mock.invoke',),
}


def _required_text(value: Mapping[str, Any], key: str) -> str:
    text = str(value.get(key) or '').strip()
    if not text:
        raise GovApiError(f'missing_typed_execution_governance_{key}')
    return text


def _required_digest(value: Mapping[str, Any], key: str, reason_code: str) -> str:
    text = str(value.get(key) or '').strip()
    if not text:
        raise GovApiError(reason_code)
    _require_digest_ref(text, reason_code)
    return text


def _require_digest_ref(value: str, reason_code: str) -> None:
    prefix, separator, digest = value.partition(':')
    if separator != ':' or prefix != 'sha256' or len(digest) != 64:
        raise GovApiError(reason_code)
    if not all(char in hexdigits for char in digest):
        raise GovApiError(reason_code)


def _metadata(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    raw = require_mapping(value, reason_code='invalid_typed_execution_governance_metadata')
    return dict(raw)


def _reject_forbidden_typed_execution_metadata(value: Mapping[str, Any]) -> None:
    lowered = {str(key).lower() for key in value}
    for key in FORBIDDEN_TYPED_EXECUTION_METADATA_KEYS:
        if key in lowered:
            raise GovApiError(f'forbidden_typed_execution_metadata:{key}')
    for nested in value.values():
        if isinstance(nested, Mapping):
            _reject_forbidden_typed_execution_metadata(nested)


def _string_tuple(values: Any) -> tuple[str, ...]:
    if isinstance(values, str):
        text = values.strip()
        return (text,) if text else ()
    try:
        return tuple(str(value).strip() for value in values if str(value).strip())
    except TypeError as exc:
        raise GovApiError('invalid_typed_execution_governance_sequence') from exc


def _mapping_tuple(values: Any) -> tuple[dict[str, Any], ...]:
    try:
        return tuple(
            dict(require_mapping(value, reason_code='invalid_typed_execution_governance_mapping'))
            for value in values
        )
    except TypeError as exc:
        raise GovApiError('invalid_typed_execution_governance_mapping_sequence') from exc


_GOVERNANCE_NON_CLAIMS = (
    'Does not interpret domain semantics or connector-owned action meaning.',
    'Does not execute connectors, subprocesses, SSH, or HTTP.',
    'Does not grant live execution authority.',
)

_COMPATIBILITY_NON_CLAIMS = (
    'Does not perform backend IO or connector certification tests.',
    'Checks only declared capability descriptors against required capabilities.',
    'Does not replace RExecOp typed execution compilation or drift binding.',
)

_BUNDLE_NON_CLAIMS = _GOVERNANCE_NON_CLAIMS + _COMPATIBILITY_NON_CLAIMS

_STACK_COMPATIBILITY_NON_CLAIMS = (
    'Checks declared RExecOp backend descriptors against GovEngine typed execution controls.',
    'Does not execute connectors or certify plugin implementations.',
    'Does not replace per-step typed execution admission before backend IO.',
)


def _stack_backend_supported(descriptor: Mapping[str, Any]) -> bool:
    backend = str(descriptor.get('backend_class') or '').strip()
    if backend in SUPPORTED_BACKEND_CLASSES:
        egress = str(descriptor.get('egress_class') or '').strip()
        identity = str(descriptor.get('identity_class') or '').strip()
        if egress and egress not in SUPPORTED_EGRESS_CLASSES:
            return False
        if identity and identity not in SUPPORTED_IDENTITY_CLASSES:
            return False
        return True
    if str(descriptor.get('certification_tier') or '').strip() == 'plugin':
        identity = str(descriptor.get('identity_class') or '').strip()
        egress = str(descriptor.get('egress_class') or '').strip()
        if identity != 'plugin_declared':
            return False
        if egress and egress not in SUPPORTED_EGRESS_CLASSES:
            return False
        capabilities = descriptor.get('capability_descriptors')
        return isinstance(capabilities, list) and bool(capabilities)
    return False