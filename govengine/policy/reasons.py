from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from govengine.api import GovApiError


POLICY_REASON_CODE_REGISTRY_SCHEMA_VERSION = 'v1'
POLICY_REASON_CODE_PATTERN = r'^[a-z][a-z0-9_]{0,127}$'
_POLICY_REASON_CODE = re.compile(POLICY_REASON_CODE_PATTERN)


@dataclass(frozen=True)
class PolicyReasonCodeDefinition:
    code: str
    phase: str
    outcome: str

    def as_dict(self) -> dict[str, str]:
        return {
            'code': self.code,
            'phase': self.phase,
            'outcome': self.outcome,
        }


_KERNEL_REASON_CODES = (
    PolicyReasonCodeDefinition('compiled', 'compile', 'success'),
    PolicyReasonCodeDefinition('conflicting_policy_controls', 'compile', 'rejected'),
    PolicyReasonCodeDefinition('conflicting_policy_rules', 'compile', 'rejected'),
    PolicyReasonCodeDefinition('duplicate_policy_condition', 'compile', 'rejected'),
    PolicyReasonCodeDefinition('duplicate_policy_rule_id', 'compile', 'rejected'),
    PolicyReasonCodeDefinition('invalid_policy_condition_operand', 'compile', 'rejected'),
    PolicyReasonCodeDefinition('invalid_policy_epoch', 'compile', 'rejected'),
    PolicyReasonCodeDefinition('invalid_policy_reason_code', 'compile', 'rejected'),
    PolicyReasonCodeDefinition('invalid_policy_risk_class', 'compile', 'rejected'),
    PolicyReasonCodeDefinition('invalid_policy_risk_score', 'compile', 'rejected'),
    PolicyReasonCodeDefinition('invalid_policy_rule_priority', 'compile', 'rejected'),
    PolicyReasonCodeDefinition('invalid_policy_validity_window', 'compile', 'rejected'),
    PolicyReasonCodeDefinition('missing_policy_condition_path', 'compile', 'rejected'),
    PolicyReasonCodeDefinition('missing_policy_condition_value', 'compile', 'rejected'),
    PolicyReasonCodeDefinition('missing_policy_issuer_ref', 'compile', 'rejected'),
    PolicyReasonCodeDefinition('policy_condition_limit_exceeded', 'compile', 'rejected'),
    PolicyReasonCodeDefinition('policy_rule_condition_limit_exceeded', 'compile', 'rejected'),
    PolicyReasonCodeDefinition('policy_rule_control_limit_exceeded', 'compile', 'rejected'),
    PolicyReasonCodeDefinition('policy_rule_limit_exceeded', 'compile', 'rejected'),
    PolicyReasonCodeDefinition('redundant_policy_rules', 'compile', 'rejected'),
    PolicyReasonCodeDefinition('unknown_policy_condition_operator', 'compile', 'rejected'),
    PolicyReasonCodeDefinition('unknown_policy_condition_path', 'compile', 'rejected'),
    PolicyReasonCodeDefinition('unknown_policy_pack_schema_version', 'compile', 'rejected'),
    PolicyReasonCodeDefinition(
        'critical_mutating_action_requires_approval',
        'evaluate',
        'approval_required',
    ),
    PolicyReasonCodeDefinition(
        'destructive_action_without_approval_evidence',
        'evaluate',
        'deny',
    ),
    PolicyReasonCodeDefinition('no_matching_policy_rule', 'evaluate', 'deny'),
    PolicyReasonCodeDefinition(
        'policy_condition_operand_type_mismatch',
        'evaluate',
        'error',
    ),
    PolicyReasonCodeDefinition('unsafe_execution_shape', 'evaluate', 'deny'),
)


def validate_policy_reason_code(value: Any) -> str:
    if not isinstance(value, str):
        raise GovApiError('invalid_policy_reason_code')
    checked = value.strip()
    if checked != value or not _POLICY_REASON_CODE.fullmatch(checked):
        raise GovApiError('invalid_policy_reason_code')
    return checked


def policy_reason_code_registry() -> dict[str, Any]:
    """Return the stable policy-kernel reason registry.

    Policy-authored rule outcomes use the same bounded identifier grammar but
    remain owned by the signed policy pack rather than this kernel registry.
    """

    return {
        'schema_version': POLICY_REASON_CODE_REGISTRY_SCHEMA_VERSION,
        'namespace': 'govengine.policy',
        'kernel_codes': [item.as_dict() for item in _KERNEL_REASON_CODES],
        'authored_codes': {
            'owner': 'policy_pack_author',
            'pattern': POLICY_REASON_CODE_PATTERN,
            'max_length': 128,
        },
    }
