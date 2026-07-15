from __future__ import annotations

from dataclasses import asdict, dataclass, field
from string import hexdigits
from typing import Any, Mapping

from govengine.admission import (
    GovAdmissionDecision,
    _admission_decision_from_planning_adapter,
    validate_admission_decision,
)
from govengine.api import GovApiError, require_mapping
from govengine.signing import govengine_record_digest

AUTOMATION_TRANSITION_REQUEST_SCHEMA_VERSION = 'v0.1'
SUPPORTED_AUTOMATION_CHAIN_SCHEMA_REF = 'schemas/automation_chain.v0.1.schema.json'
AUTOMATION_TRANSITION_SOURCES = (
    'reaction',
    'trigger',
    'watchdog',
    'manual',
    'operator',
    'llm_proposal',
)
AUTOMATION_PARENT_STATUSES = (
    'completed',
    'failed',
    'blocked',
    'needs_followup',
    'partially_completed',
)
FORBIDDEN_AUTOMATION_METADATA_KEYS = (
    'api_key',
    'command',
    'commands',
    'credential',
    'credentials',
    'event_payload',
    'host',
    'hostname',
    'ip',
    'password',
    'raw_event',
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
class AutomationTransitionRequest:
    """GovEngine-owned admission request for child-operation planning.

    RExecOp owns operation lifecycle, reaction traversal and runtime emission.
    SCLite owns the canonical automation-chain artifact. This request carries
    bounded identifiers, digests and limits so GovEngine can decide whether a
    proposed parent-to-child transition is admissible.
    """

    request_id: str
    chain_id: str
    parent_operation_id: str
    parent_operation_ref: str
    parent_intent: str
    parent_status: str
    child_operation_id: str
    child_intent: str
    child_intent_class: str
    transition_reason: str
    automation_chain_ref: str
    source: str
    depth: int
    max_depth: int
    child_sequence: int
    max_children: int
    allowed_child_intent_classes: tuple[str, ...]
    automation_chain_schema_ref: str = SUPPORTED_AUTOMATION_CHAIN_SCHEMA_REF
    trigger_ref: str = ''
    approval_ref: str = ''
    llm_proposed: bool = False
    llm_authority: bool = False
    schema_version: str = AUTOMATION_TRANSITION_REQUEST_SCHEMA_VERSION
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> AutomationTransitionRequest:
        raw = require_mapping(value, reason_code='invalid_automation_transition_request')
        item = cls(
            request_id=str(raw.get('request_id') or '').strip(),
            chain_id=str(raw.get('chain_id') or '').strip(),
            parent_operation_id=str(raw.get('parent_operation_id') or '').strip(),
            parent_operation_ref=str(
                raw.get('parent_operation_ref') or raw.get('parent_operation_digest') or ''
            ).strip(),
            parent_intent=str(raw.get('parent_intent') or '').strip(),
            parent_status=str(raw.get('parent_status') or '').strip(),
            child_operation_id=str(raw.get('child_operation_id') or '').strip(),
            child_intent=str(raw.get('child_intent') or '').strip(),
            child_intent_class=str(raw.get('child_intent_class') or '').strip(),
            transition_reason=str(raw.get('transition_reason') or '').strip(),
            automation_chain_ref=str(
                raw.get('automation_chain_ref') or raw.get('automation_chain_digest') or ''
            ).strip(),
            source=str(raw.get('source') or '').strip(),
            depth=_int(raw.get('depth')),
            max_depth=_int(raw.get('max_depth')),
            child_sequence=_int(raw.get('child_sequence')),
            max_children=_int(raw.get('max_children')),
            allowed_child_intent_classes=_text_tuple(
                raw.get('allowed_child_intent_classes')
            ),
            automation_chain_schema_ref=str(
                raw.get('automation_chain_schema_ref') or SUPPORTED_AUTOMATION_CHAIN_SCHEMA_REF
            ).strip(),
            trigger_ref=str(raw.get('trigger_ref') or '').strip(),
            approval_ref=str(raw.get('approval_ref') or '').strip(),
            llm_proposed=bool(raw.get('llm_proposed', False)),
            llm_authority=bool(raw.get('llm_authority', False)),
            schema_version=str(
                raw.get('schema_version') or AUTOMATION_TRANSITION_REQUEST_SCHEMA_VERSION
            ).strip(),
            metadata=_metadata(raw.get('metadata')),
        )
        validate_automation_transition_request(item)
        return item

    def as_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out['allowed_child_intent_classes'] = list(self.allowed_child_intent_classes)
        out['metadata'] = dict(self.metadata)
        return out


def validate_automation_transition_request(
    value: Mapping[str, Any] | AutomationTransitionRequest,
) -> AutomationTransitionRequest:
    item = value if isinstance(value, AutomationTransitionRequest) else AutomationTransitionRequest.from_mapping(value)
    if item.schema_version != AUTOMATION_TRANSITION_REQUEST_SCHEMA_VERSION:
        raise GovApiError('unknown_automation_transition_request_schema')
    for field_name in (
        'request_id',
        'chain_id',
        'parent_operation_id',
        'parent_operation_ref',
        'parent_intent',
        'parent_status',
        'child_operation_id',
        'child_intent',
        'child_intent_class',
        'transition_reason',
        'automation_chain_ref',
        'source',
    ):
        if not getattr(item, field_name):
            raise GovApiError(f'missing_automation_transition_{field_name}')
    _require_digest_ref(item.parent_operation_ref, 'invalid_automation_parent_operation_ref')
    _require_digest_ref(item.automation_chain_ref, 'invalid_automation_chain_ref')
    if item.trigger_ref:
        _require_digest_ref(item.trigger_ref, 'invalid_automation_trigger_ref')
    if item.source not in AUTOMATION_TRANSITION_SOURCES:
        raise GovApiError(f'unsupported_automation_transition_source:{item.source}')
    if item.parent_status not in AUTOMATION_PARENT_STATUSES:
        raise GovApiError(f'unsupported_automation_parent_status:{item.parent_status}')
    if item.depth < 1 or item.max_depth < 1:
        raise GovApiError('invalid_automation_transition_depth')
    if item.child_sequence < 1 or item.max_children < 1:
        raise GovApiError('invalid_automation_transition_child_limits')
    if not item.allowed_child_intent_classes:
        raise GovApiError('missing_automation_allowed_child_intent_classes')
    _reject_forbidden_automation_metadata(item.metadata)
    return item


def automation_transition_request_digest(
    request: Mapping[str, Any] | AutomationTransitionRequest,
) -> str:
    checked = validate_automation_transition_request(request)
    return govengine_record_digest(
        checked,
        record_type='govengine.automation.AutomationTransitionRequest',
    )


def admit_automation_transition(
    request: Mapping[str, Any] | AutomationTransitionRequest,
) -> GovAdmissionDecision:
    checked = validate_automation_transition_request(request)
    outcome = 'allowed'
    reason_code = 'automation_transition_allowed'
    blockers: tuple[str, ...] = ()

    if checked.automation_chain_schema_ref != SUPPORTED_AUTOMATION_CHAIN_SCHEMA_REF:
        outcome = 'denied'
        reason_code = 'automation_transition_unsupported_chain_schema'
        blockers = ('unsupported_automation_chain_schema',)
    elif checked.llm_authority:
        outcome = 'denied'
        reason_code = 'automation_transition_llm_authority_denied'
        blockers = ('llm_authority_denied',)
    elif checked.depth > checked.max_depth:
        outcome = 'denied'
        reason_code = 'automation_transition_depth_exceeded'
        blockers = ('depth_exceeded',)
    elif checked.child_sequence > checked.max_children:
        outcome = 'denied'
        reason_code = 'automation_transition_child_budget_exceeded'
        blockers = ('child_budget_exceeded',)
    elif checked.child_intent_class not in checked.allowed_child_intent_classes:
        outcome = 'denied'
        reason_code = 'automation_transition_child_intent_class_denied'
        blockers = ('child_intent_class_denied',)
    elif (checked.llm_proposed or checked.source == 'llm_proposal') and not checked.approval_ref:
        outcome = 'deferred'
        reason_code = 'automation_transition_requires_approval'
        blockers = ('approval_required',)

    return _admission_decision_from_planning_adapter(
        decision_id=f'automation-transition:{checked.request_id}',
        subject_ref=automation_transition_request_digest(checked),
        subject_kind='operator_action',
        outcome=outcome,
        reason_code=reason_code,
        blockers=blockers,
        signal={
            'request_id': checked.request_id,
            'chain_id': checked.chain_id,
            'parent_operation_id': checked.parent_operation_id,
            'parent_operation_ref': checked.parent_operation_ref,
            'parent_intent': checked.parent_intent,
            'parent_status': checked.parent_status,
            'child_operation_id': checked.child_operation_id,
            'child_intent': checked.child_intent,
            'child_intent_class': checked.child_intent_class,
            'transition_reason': checked.transition_reason,
            'automation_chain_ref': checked.automation_chain_ref,
            'automation_chain_schema_ref': checked.automation_chain_schema_ref,
            'source': checked.source,
            'depth': checked.depth,
            'max_depth': checked.max_depth,
            'child_sequence': checked.child_sequence,
            'max_children': checked.max_children,
            'allowed_child_intent_classes': list(checked.allowed_child_intent_classes),
            'trigger_ref': checked.trigger_ref,
            'approval_ref': checked.approval_ref,
            'llm_proposed': checked.llm_proposed,
            'llm_authority': checked.llm_authority,
        },
        metadata={
            'source': 'automation_transition_request',
            'schema_version': checked.schema_version,
        },
    )


def automation_transition_admission_digest(
    admission: Mapping[str, Any] | GovAdmissionDecision,
) -> str:
    checked = validate_admission_decision(admission)
    return govengine_record_digest(
        checked,
        record_type='govengine.admission.GovAdmissionDecision',
    )


def validate_automation_transition_admission(
    admission: Mapping[str, Any] | GovAdmissionDecision,
    *,
    request: Mapping[str, Any] | AutomationTransitionRequest,
) -> GovAdmissionDecision:
    checked = validate_admission_decision(admission)
    expected = admit_automation_transition(request)
    if checked.as_dict() != expected.as_dict():
        raise GovApiError('automation_transition_admission_drift')
    return checked


def _metadata(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    raw = require_mapping(value, reason_code='invalid_automation_transition_metadata')
    return dict(raw)


def _reject_forbidden_automation_metadata(value: Mapping[str, Any]) -> None:
    lowered = {str(key).lower() for key in value}
    for key in FORBIDDEN_AUTOMATION_METADATA_KEYS:
        if key in lowered:
            raise GovApiError(f'forbidden_automation_transition_metadata:{key}')
    for nested in value.values():
        if isinstance(nested, Mapping):
            _reject_forbidden_automation_metadata(nested)


def _require_digest_ref(value: str, reason_code: str) -> None:
    text = str(value or '').strip()
    prefix, separator, digest = text.partition(':')
    if separator != ':' or prefix != 'sha256' or len(digest) != 64:
        raise GovApiError(reason_code)
    if not all(char in hexdigits for char in digest):
        raise GovApiError(reason_code)


def _int(value: Any) -> int:
    if value in (None, ''):
        return 0
    return int(value)


def _text_tuple(value: Any) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(str(item).strip() for item in value if str(item or '').strip())
