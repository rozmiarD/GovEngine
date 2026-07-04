from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from govengine.admission import GovAdmissionDecision
from govengine.supervisor_actions import (
    SUPERVISOR_HUMAN_SIGNOFF_ACTIONS,
    SUPERVISOR_RECORD_ONLY_ACTIONS,
    SupervisorActionRequest,
    admit_supervisor_action,
    supervisor_action_admission_digest,
    supervisor_action_request_digest,
    validate_supervisor_action_request,
)

SUPERVISOR_EXPLANATION_SCHEMA_VERSION = 'v0.1'

RECOVERY_CLASS_BY_ACTION = {
    'record_health': 'health_record',
    'move_to_dead_letter': 'dead_letter',
    'retry_later': 'retry',
    'block_autostart': 'block_autostart',
    'renew_lease': 'stale_lease',
    'mark_stale': 'manual_record',
    'escalate_operator': 'manual_record',
}

REASON_SUMMARIES = {
    'supervisor_action_allowed': 'Supervisor action is admissible under the declared bounded limits.',
    'supervisor_action_record_only': 'Health or telemetry record only; no recovery execution is implied.',
    'supervisor_action_requires_human_signoff': (
        'Manual recovery action requires explicit human sign-off with bounded actor and scope.'
    ),
    'supervisor_action_retry_budget_exceeded': (
        'Inbox retry budget is exhausted; further automatic retries are denied fail-closed.'
    ),
    'supervisor_action_stale_age_not_exceeded': (
        'Operation age is below the stale threshold; block-autostart is premature.'
    ),
}


@dataclass(frozen=True)
class SupervisorActionExplanation:
    """Stable, redacted explanation for one supervisor admission evaluation."""

    schema_version: str
    status: str
    request_id: str
    action: str
    observation: str
    reason: str
    recovery_class: str
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
            'action': self.action,
            'observation': self.observation,
            'reason': self.reason,
            'recovery_class': self.recovery_class,
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


def explain_supervisor_action(
    request: Mapping[str, Any] | SupervisorActionRequest,
) -> SupervisorActionExplanation:
    checked = validate_supervisor_action_request(request)
    admission = admit_supervisor_action(checked)
    gates = _gates_checked(checked, admission)
    evaluation_path = _evaluation_path(checked, admission, gates)
    recovery_class = _recovery_class(checked, admission)
    summary = REASON_SUMMARIES.get(
        admission.reason_code,
        f'Supervisor action evaluated with reason_code={admission.reason_code}.',
    )
    return SupervisorActionExplanation(
        schema_version=SUPERVISOR_EXPLANATION_SCHEMA_VERSION,
        status='blocked' if admission.blockers else 'explained',
        request_id=checked.request_id,
        action=checked.action,
        observation=checked.observation,
        reason=checked.reason,
        recovery_class=recovery_class,
        evaluation_path=evaluation_path,
        outcome=admission.outcome,
        allowed=admission.allowed,
        reason_code=admission.reason_code,
        blockers=tuple(admission.blockers),
        gates_checked=gates,
        operator_summary=summary,
        safe_next_actions=_safe_next_actions(checked, admission),
        request_digest=supervisor_action_request_digest(checked),
        admission_digest=supervisor_action_admission_digest(admission),
        admission=admission.as_dict(),
        non_claims=(
            'Does not execute recovery, retry, requeue or lease renewal.',
            'Does not mutate RExecOp runtime state or operation FSM.',
            'Does not verify SCLite watchdog artifacts or host enforcement.',
            'Does not expose raw inbox payloads, commands or credentials.',
        ),
    )


def _gates_checked(
    request: SupervisorActionRequest,
    admission: GovAdmissionDecision,
) -> tuple[dict[str, Any], ...]:
    gates: list[dict[str, Any]] = []
    if request.action in SUPERVISOR_RECORD_ONLY_ACTIONS:
        gates.append(
            {
                'gate': 'record_only',
                'passed': True,
                'reason_code': admission.reason_code,
            }
        )
        return tuple(gates)

    if request.action in {'move_to_dead_letter', 'retry_later'}:
        passed = admission.reason_code != 'supervisor_action_retry_budget_exceeded'
        gates.append(
            {
                'gate': 'retry_budget',
                'passed': passed,
                'reason_code': admission.reason_code,
                'details': {
                    'attempt_count': request.attempt_count,
                    'max_attempts': request.max_attempts,
                },
            }
        )

    if request.action == 'block_autostart':
        passed = admission.reason_code != 'supervisor_action_stale_age_not_exceeded'
        gates.append(
            {
                'gate': 'stale_age',
                'passed': passed,
                'reason_code': admission.reason_code,
                'details': {
                    'age_seconds': request.age_seconds,
                    'max_age_seconds': request.max_age_seconds,
                    'operation_id': request.operation_id,
                },
            }
        )

    if request.action in SUPERVISOR_HUMAN_SIGNOFF_ACTIONS:
        passed = admission.reason_code != 'supervisor_action_requires_human_signoff'
        gates.append(
            {
                'gate': 'human_signoff',
                'passed': passed,
                'reason_code': admission.reason_code,
                'details': {
                    'human_signoff': request.human_signoff,
                    'actor_ref': request.actor_ref or None,
                    'scope': request.scope or None,
                },
            }
        )

    if not gates:
        gates.append(
            {
                'gate': 'supervisor_action',
                'passed': admission.allowed,
                'reason_code': admission.reason_code,
            }
        )
    return tuple(gates)


def _evaluation_path(
    request: SupervisorActionRequest,
    admission: GovAdmissionDecision,
    gates: tuple[Mapping[str, Any], ...],
) -> str:
    if request.action in SUPERVISOR_RECORD_ONLY_ACTIONS:
        return 'record_only'
    if admission.blockers:
        failed = next((item for item in gates if not item.get('passed')), None)
        if isinstance(failed, Mapping):
            return str(failed.get('gate') or 'denied')
        return 'denied'
    if request.action in SUPERVISOR_HUMAN_SIGNOFF_ACTIONS and request.human_signoff:
        return 'signed_manual_recovery'
    return 'allowed'


def _recovery_class(request: SupervisorActionRequest, admission: GovAdmissionDecision) -> str:
    if request.observation == 'manual_recovery':
        return 'manual_record'
    if admission.reason_code == 'supervisor_action_record_only':
        return 'health_record'
    return RECOVERY_CLASS_BY_ACTION.get(request.action, 'supervisor_action')


def _safe_next_actions(
    request: SupervisorActionRequest,
    admission: GovAdmissionDecision,
) -> tuple[str, ...]:
    actions = ['rexecop ops', 'rexecop runtime status --json']
    if request.operation_id:
        actions.append(f'rexecop explain-error {request.operation_id}')
    if request.inbox_item_name:
        actions.append(f'rexecop dead-letter show {request.inbox_item_name}')
    actions.append(f'rexecop explain-error {request.request_id}')

    if admission.reason_code == 'supervisor_action_requires_human_signoff':
        actions.append(
            'rexecop watchdog manual-record --action <renew_lease|mark_stale|escalate_operator> '
            '--reason <bounded-reason> --actor-ref <operator-ref> --scope <bounded-scope>'
        )
    if admission.reason_code == 'supervisor_action_retry_budget_exceeded':
        actions.append('rexecop dead-letter list')
    if admission.reason_code == 'supervisor_action_stale_age_not_exceeded':
        actions.append('rexecop runtime recover --json')
    return tuple(dict.fromkeys(actions))