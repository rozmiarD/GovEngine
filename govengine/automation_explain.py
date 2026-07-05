from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from govengine.admission import GovAdmissionDecision
from govengine.automation import (
    AutomationTransitionRequest,
    admit_automation_transition,
    automation_transition_admission_digest,
    automation_transition_request_digest,
    validate_automation_transition_request,
)

AUTOMATION_TRANSITION_EXPLANATION_SCHEMA_VERSION = 'v0.1'

REASON_SUMMARIES = {
    'automation_transition_allowed': (
        'Child-operation planning is admissible under the declared automation limits.'
    ),
    'automation_transition_unsupported_chain_schema': (
        'Automation transition is denied because the declared SCLite chain schema is unsupported.'
    ),
    'automation_transition_llm_authority_denied': (
        'LLM output may be recorded as a proposal only; it is not execution or planning authority.'
    ),
    'automation_transition_depth_exceeded': (
        'Automation depth exceeds the declared maximum chain depth.'
    ),
    'automation_transition_child_budget_exceeded': (
        'The parent operation has exhausted its declared child-operation budget.'
    ),
    'automation_transition_child_intent_class_denied': (
        'The proposed child intent class is not allowed by the bounded planning request.'
    ),
    'automation_transition_requires_approval': (
        'LLM-proposed automation requires explicit approval before child planning can proceed.'
    ),
}


@dataclass(frozen=True)
class AutomationTransitionExplanation:
    """Stable, redacted explanation for child-operation planning admission."""

    schema_version: str
    status: str
    request_id: str
    chain_id: str
    parent_operation_id: str
    child_operation_id: str
    source: str
    evaluation_path: str
    outcome: str
    allowed: bool
    reason_code: str
    blockers: tuple[str, ...] = field(default_factory=tuple)
    gates_checked: tuple[Mapping[str, Any], ...] = field(default_factory=tuple)
    operator_summary: str = ''
    safe_next_actions: tuple[str, ...] = field(default_factory=tuple)
    request_digest: str = ''
    admission_digest: str = ''
    admission: Mapping[str, Any] = field(default_factory=dict)
    non_claims: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        return {
            'schema_version': self.schema_version,
            'status': self.status,
            'request_id': self.request_id,
            'chain_id': self.chain_id,
            'parent_operation_id': self.parent_operation_id,
            'child_operation_id': self.child_operation_id,
            'source': self.source,
            'evaluation_path': self.evaluation_path,
            'outcome': self.outcome,
            'allowed': self.allowed,
            'reason_code': self.reason_code,
            'blockers': list(self.blockers),
            'gates_checked': [dict(item) for item in self.gates_checked],
            'operator_summary': self.operator_summary,
            'safe_next_actions': list(self.safe_next_actions),
            'request_digest': self.request_digest,
            'admission_digest': self.admission_digest,
            'admission': dict(self.admission),
            'non_claims': list(self.non_claims),
        }


def explain_automation_transition(
    request: Mapping[str, Any] | AutomationTransitionRequest,
) -> AutomationTransitionExplanation:
    checked = validate_automation_transition_request(request)
    admission = admit_automation_transition(checked)
    gates = _gates_checked(checked, admission)
    summary = REASON_SUMMARIES.get(
        admission.reason_code,
        f'Automation transition evaluated with reason_code={admission.reason_code}.',
    )
    return AutomationTransitionExplanation(
        schema_version=AUTOMATION_TRANSITION_EXPLANATION_SCHEMA_VERSION,
        status='blocked' if admission.blockers else 'explained',
        request_id=checked.request_id,
        chain_id=checked.chain_id,
        parent_operation_id=checked.parent_operation_id,
        child_operation_id=checked.child_operation_id,
        source=checked.source,
        evaluation_path=_evaluation_path(admission, gates),
        outcome=admission.outcome,
        allowed=admission.allowed,
        reason_code=admission.reason_code,
        blockers=tuple(admission.blockers),
        gates_checked=gates,
        operator_summary=summary,
        safe_next_actions=_safe_next_actions(checked, admission),
        request_digest=automation_transition_request_digest(checked),
        admission_digest=automation_transition_admission_digest(admission),
        admission=admission.as_dict(),
        non_claims=(
            'Does not create, enqueue, execute, retry or rollback child operations.',
            'Does not traverse RExecOp reaction graphs or mutate operation FSM state.',
            'Does not validate SCLite automation-chain artifacts or store evidence.',
            'Does not grant LLM execution authority or expose raw backend output.',
        ),
    )


def _gates_checked(
    request: AutomationTransitionRequest,
    admission: GovAdmissionDecision,
) -> tuple[dict[str, Any], ...]:
    return (
        {
            'gate': 'automation_chain_contract',
            'passed': admission.reason_code != 'automation_transition_unsupported_chain_schema',
            'reason_code': admission.reason_code,
            'details': {'automation_chain_schema_ref': request.automation_chain_schema_ref},
        },
        {
            'gate': 'llm_non_authority',
            'passed': admission.reason_code != 'automation_transition_llm_authority_denied',
            'reason_code': admission.reason_code,
            'details': {
                'llm_proposed': request.llm_proposed,
                'llm_authority': request.llm_authority,
                'approval_ref_present': bool(request.approval_ref),
            },
        },
        {
            'gate': 'depth_budget',
            'passed': admission.reason_code != 'automation_transition_depth_exceeded',
            'reason_code': admission.reason_code,
            'details': {'depth': request.depth, 'max_depth': request.max_depth},
        },
        {
            'gate': 'child_budget',
            'passed': admission.reason_code != 'automation_transition_child_budget_exceeded',
            'reason_code': admission.reason_code,
            'details': {
                'child_sequence': request.child_sequence,
                'max_children': request.max_children,
            },
        },
        {
            'gate': 'child_intent_class',
            'passed': admission.reason_code
            != 'automation_transition_child_intent_class_denied',
            'reason_code': admission.reason_code,
            'details': {
                'child_intent_class': request.child_intent_class,
                'allowed_child_intent_classes': list(request.allowed_child_intent_classes),
            },
        },
        {
            'gate': 'approval',
            'passed': admission.reason_code != 'automation_transition_requires_approval',
            'reason_code': admission.reason_code,
            'details': {'approval_ref_present': bool(request.approval_ref)},
        },
    )


def _evaluation_path(
    admission: GovAdmissionDecision,
    gates: tuple[Mapping[str, Any], ...],
) -> str:
    if not admission.blockers:
        return 'allowed'
    failed = next((item for item in gates if not item.get('passed')), None)
    if isinstance(failed, Mapping):
        return str(failed.get('gate') or 'denied')
    return 'denied'


def _safe_next_actions(
    request: AutomationTransitionRequest,
    admission: GovAdmissionDecision,
) -> tuple[str, ...]:
    actions = [
        f'rexecop chain explain {request.chain_id}',
        f'rexecop reaction explain --reaction {request.request_id}',
        f'rexecop explain-error {request.parent_operation_id}',
    ]
    if admission.reason_code == 'automation_transition_requires_approval':
        actions.append('record bounded operator approval before emitting child operation')
    if admission.reason_code in {
        'automation_transition_depth_exceeded',
        'automation_transition_child_budget_exceeded',
    }:
        actions.append('adjust profile-declared automation limits or stop child planning')
    if admission.reason_code == 'automation_transition_child_intent_class_denied':
        actions.append('choose a profile-declared child intent class')
    return tuple(dict.fromkeys(actions))
