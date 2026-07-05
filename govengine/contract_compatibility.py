from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from govengine import __version__ as GOVENGINE_VERSION
from govengine.api import GovApiError, require_mapping
from govengine.signing import govengine_record_digest

SUPPORTED_CONTRACT_REPORT_SCHEMA_VERSION = 'v0.1'
CONTRACT_COMPATIBILITY_REQUEST_SCHEMA_VERSION = 'v0.1'

_CONTRACT_ENTRIES: tuple[dict[str, Any], ...] = (
    {
        'surface_id': 'policy_request',
        'owner': 'govengine.policy',
        'record_type': 'govengine.policy.model.PolicyRequest',
        'supported_versions': ('v0.1',),
        'rexecop_consumer': True,
        'status': 'supported',
    },
    {
        'surface_id': 'policy_verdict',
        'owner': 'govengine.policy',
        'record_type': 'govengine.policy.model.PolicyVerdict',
        'supported_versions': ('v0.1',),
        'rexecop_consumer': True,
        'status': 'supported',
    },
    {
        'surface_id': 'policy_enforcement_plan',
        'owner': 'govengine.policy.enforcement',
        'record_type': 'govengine.policy.enforcement.PolicyEnforcementPlan',
        'supported_versions': ('v0.1',),
        'rexecop_consumer': True,
        'status': 'supported',
    },
    {
        'surface_id': 'runtime_control_projection',
        'owner': 'govengine.policy.enforcement',
        'record_type': 'govengine.policy.enforcement.RuntimeControlProjection',
        'supported_versions': ('v0.1',),
        'rexecop_consumer': True,
        'status': 'supported',
    },
    {
        'surface_id': 'gov_admission_decision',
        'owner': 'govengine.admission',
        'record_type': 'govengine.admission.GovAdmissionDecision',
        'supported_versions': ('v0.1',),
        'rexecop_consumer': True,
        'status': 'supported',
    },
    {
        'surface_id': 'trigger_planning_request',
        'owner': 'govengine.triggers',
        'record_type': 'govengine.triggers.TriggerPlanningRequest',
        'supported_versions': ('v0.1',),
        'rexecop_consumer': True,
        'status': 'supported',
    },
    {
        'surface_id': 'supervisor_action_request',
        'owner': 'govengine.supervisor_actions',
        'record_type': 'govengine.supervisor_actions.SupervisorActionRequest',
        'supported_versions': ('v0.1',),
        'rexecop_consumer': True,
        'status': 'supported',
    },
    {
        'surface_id': 'automation_transition_request',
        'owner': 'govengine.automation',
        'record_type': 'govengine.automation.AutomationTransitionRequest',
        'supported_versions': ('v0.1',),
        'rexecop_consumer': True,
        'status': 'supported',
    },
    {
        'surface_id': 'automation_transition_explanation',
        'owner': 'govengine.automation_explain',
        'record_type': 'govengine.automation_explain.AutomationTransitionExplanation',
        'supported_versions': ('v0.1',),
        'rexecop_consumer': True,
        'status': 'supported',
    },
    {
        'surface_id': 'typed_execution_governance_request',
        'owner': 'govengine.typed_execution_governance',
        'record_type': 'govengine.typed_execution_governance.TypedExecutionGovernanceRequest',
        'supported_versions': ('v0.1',),
        'rexecop_consumer': True,
        'status': 'supported',
    },
    {
        'surface_id': 'typed_execution_governance_projection',
        'owner': 'govengine.typed_execution_governance',
        'record_type': 'govengine.typed_execution_governance.TypedExecutionGovernanceProjection',
        'supported_versions': ('v0.1',),
        'rexecop_consumer': True,
        'status': 'supported',
    },
    {
        'surface_id': 'typed_execution_stack_compatibility',
        'owner': 'govengine.typed_execution_governance',
        'record_type': 'govengine.typed_execution_governance.TypedExecutionStackCompatibilityReport',
        'supported_versions': ('v0.1',),
        'rexecop_consumer': True,
        'status': 'supported',
    },
    {
        'surface_id': 'typed_execution_control_catalog',
        'owner': 'govengine.typed_execution_governance',
        'record_type': 'govengine.typed_execution_governance.TypedExecutionControlCatalog',
        'supported_versions': ('v0.1',),
        'rexecop_consumer': True,
        'status': 'supported',
    },
    {
        'surface_id': 'profile_governance_request',
        'owner': 'govengine.profile_governance',
        'record_type': 'govengine.profile_governance.ProfileGovernanceRequest',
        'supported_versions': ('v0.1',),
        'rexecop_consumer': False,
        'status': 'supported',
    },
    {
        'surface_id': 'governance_trace',
        'owner': 'govengine.governance_trace',
        'record_type': 'govengine.governance_trace.GovernanceTrace',
        'supported_versions': ('v0.1',),
        'rexecop_consumer': True,
        'status': 'supported',
    },
)

_CONTRACT_INDEX = {item['surface_id']: item for item in _CONTRACT_ENTRIES}

_REPORT_NON_CLAIMS = (
    'Does not execute work or validate SCLite artifact storage.',
    'Does not prove a host enforced projected controls.',
    'Planned surfaces are listed for roadmap visibility only.',
)


@dataclass(frozen=True)
class ContractCompatibilityRequest:
    schema_version: str
    request_id: str
    consumer: str
    consumer_version: str
    declared_contracts: tuple[Mapping[str, Any], ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            'schema_version': self.schema_version,
            'request_id': self.request_id,
            'consumer': self.consumer,
            'consumer_version': self.consumer_version,
            'declared_contracts': [dict(item) for item in self.declared_contracts],
        }


@dataclass(frozen=True)
class ContractCompatibilityReport:
    schema_version: str
    status: str
    request_id: str
    reason_code: str
    govengine_version: str
    supported_contracts: tuple[Mapping[str, Any], ...]
    matched_contracts: tuple[str, ...] = ()
    unsupported_contracts: tuple[str, ...] = ()
    missing_contracts: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
    report_digest: str = ''
    non_claims: tuple[str, ...] = _REPORT_NON_CLAIMS

    def as_dict(self) -> dict[str, Any]:
        return {
            'schema_version': self.schema_version,
            'status': self.status,
            'request_id': self.request_id,
            'reason_code': self.reason_code,
            'govengine_version': self.govengine_version,
            'supported_contracts': [dict(item) for item in self.supported_contracts],
            'matched_contracts': list(self.matched_contracts),
            'unsupported_contracts': list(self.unsupported_contracts),
            'missing_contracts': list(self.missing_contracts),
            'blockers': list(self.blockers),
            'report_digest': self.report_digest,
            'non_claims': list(self.non_claims),
        }


def supported_contract_report() -> dict[str, Any]:
    """Emit the central GovEngine supported-contract catalog for stack consumers."""
    contracts = [dict(item) for item in _CONTRACT_ENTRIES]
    body = {
        'schema_version': SUPPORTED_CONTRACT_REPORT_SCHEMA_VERSION,
        'govengine_version': GOVENGINE_VERSION,
        'contracts': contracts,
        'supported_surfaces': sorted(_CONTRACT_INDEX),
        'rexecop_surfaces': sorted(
            item['surface_id']
            for item in _CONTRACT_ENTRIES
            if item['rexecop_consumer'] and item.get('status') == 'supported'
        ),
        'report_digest': '',
        'non_claims': list(_REPORT_NON_CLAIMS),
    }
    body['report_digest'] = govengine_record_digest(
        body,
        record_type='govengine.contract_compatibility.SupportedContractReport',
        schema_version=SUPPORTED_CONTRACT_REPORT_SCHEMA_VERSION,
    )
    return body


def contract_major_version(version: str) -> str:
    text = str(version or '').strip()
    if not text:
        return ''
    return text.split('.', 1)[0]


def validate_supported_contract_version(surface_id: str, version: str) -> None:
    """Fail closed when a host declares an unknown major contract version."""
    entry = _CONTRACT_INDEX.get(str(surface_id or '').strip())
    if entry is None:
        raise GovApiError(f'unsupported_contract_surface:{surface_id}')
    if entry.get('status') != 'supported':
        raise GovApiError(f'unsupported_contract_surface_status:{surface_id}')
    supported_versions = tuple(entry.get('supported_versions') or ())
    if not supported_versions:
        raise GovApiError(f'unsupported_contract_surface_status:{surface_id}')
    normalized = str(version or '').strip()
    if normalized in supported_versions:
        return
    supported_majors = {contract_major_version(item) for item in supported_versions}
    major = contract_major_version(normalized)
    if major and major not in supported_majors:
        raise GovApiError(f'unsupported_contract_major_version:{surface_id}:{normalized}')
    raise GovApiError(f'unsupported_contract_version:{surface_id}:{normalized}')


def validate_contract_compatibility_request(
    value: Mapping[str, Any] | ContractCompatibilityRequest,
) -> ContractCompatibilityRequest:
    if isinstance(value, ContractCompatibilityRequest):
        return value
    raw = require_mapping(value, reason_code='invalid_contract_compatibility_request')
    schema_version = str(raw.get('schema_version') or '').strip()
    if schema_version != CONTRACT_COMPATIBILITY_REQUEST_SCHEMA_VERSION:
        raise GovApiError(
            f'unsupported_contract_compatibility_request_version:{schema_version}'
        )
    return ContractCompatibilityRequest(
        schema_version=schema_version,
        request_id=_required_text(raw, 'request_id'),
        consumer=_required_text(raw, 'consumer'),
        consumer_version=_required_text(raw, 'consumer_version'),
        declared_contracts=_mapping_tuple(raw.get('declared_contracts') or ()),
    )


def evaluate_contract_compatibility(
    request: Mapping[str, Any] | ContractCompatibilityRequest,
) -> ContractCompatibilityReport:
    """Evaluate one consumer's declared contract versions against GovEngine catalog."""
    checked = validate_contract_compatibility_request(request)
    catalog = supported_contract_report()
    supported = tuple(dict(item) for item in catalog['contracts'])
    matched: list[str] = []
    unsupported: list[str] = []
    missing: list[str] = []
    blockers: list[str] = []

    for item in checked.declared_contracts:
        surface_id = str(item.get('surface_id') or '').strip()
        version = str(item.get('schema_version') or item.get('version') or '').strip()
        if not surface_id:
            blockers.append('missing_declared_contract_surface')
            continue
        entry = _CONTRACT_INDEX.get(surface_id)
        if entry is None:
            unsupported.append(surface_id)
            blockers.append(f'unsupported_contract_surface:{surface_id}')
            continue
        if entry.get('status') != 'supported':
            unsupported.append(surface_id)
            blockers.append(f'unsupported_contract_surface_status:{surface_id}')
            continue
        try:
            validate_supported_contract_version(surface_id, version)
        except GovApiError:
            unsupported.append(surface_id)
            blockers.append(f'unsupported_contract_version:{surface_id}:{version}')
            continue
        matched.append(surface_id)

    required = {
        item['surface_id']
        for item in _CONTRACT_ENTRIES
        if item.get('rexecop_consumer') and item.get('status') == 'supported'
    }
    if checked.consumer == 'rexecop':
        for surface_id in sorted(required - set(matched)):
            missing.append(surface_id)
            blockers.append(f'missing_declared_contract:{surface_id}')

    blockers_tuple = tuple(dict.fromkeys(item for item in blockers if item))
    status = 'passed' if not blockers_tuple else 'blocked'
    reason_code = (
        'contract_compatibility_passed' if not blockers_tuple else blockers_tuple[0]
    )
    body = {
        'schema_version': SUPPORTED_CONTRACT_REPORT_SCHEMA_VERSION,
        'status': status,
        'request_id': checked.request_id,
        'reason_code': reason_code,
        'govengine_version': GOVENGINE_VERSION,
        'matched_contracts': matched,
        'unsupported_contracts': unsupported,
        'missing_contracts': missing,
        'blockers': list(blockers_tuple),
    }
    report_digest = govengine_record_digest(
        body,
        record_type='govengine.contract_compatibility.ContractCompatibilityReport',
        schema_version=SUPPORTED_CONTRACT_REPORT_SCHEMA_VERSION,
    )
    return ContractCompatibilityReport(
        schema_version=SUPPORTED_CONTRACT_REPORT_SCHEMA_VERSION,
        status=status,
        request_id=checked.request_id,
        reason_code=reason_code,
        govengine_version=GOVENGINE_VERSION,
        supported_contracts=supported,
        matched_contracts=tuple(matched),
        unsupported_contracts=tuple(unsupported),
        missing_contracts=tuple(missing),
        blockers=blockers_tuple,
        report_digest=report_digest,
    )


def _required_text(value: Mapping[str, Any], key: str) -> str:
    text = str(value.get(key) or '').strip()
    if not text:
        raise GovApiError(f'missing_contract_compatibility_{key}')
    return text


def _mapping_tuple(value: Any) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    items: list[Mapping[str, Any]] = []
    for item in value:
        if isinstance(item, Mapping):
            items.append(dict(item))
    return tuple(items)
