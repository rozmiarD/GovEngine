"""Small alpha facade for the GovEngine 1.0 candidate kernel.

The facade is intentionally limited to deterministic API envelopes,
PolicyEngine compilation/evaluation/enforcement, and governance trace
projection. Runtime mechanics, SCLite bridges, fixtures, and compatibility
adapters remain available through their existing alpha modules only.
"""

from __future__ import annotations

from .api import GovApiError, GovApiResult
from .governance_trace import (
    GOVERNANCE_TRACE_SCHEMA_VERSION,
    GovernanceTrace,
    policy_request_digest,
    project_governance_trace,
)
from .policy import (
    CompileResult,
    CompiledPolicyPack,
    PolicyCompiler,
    PolicyConstraint,
    PolicyEnforcementPlan,
    PolicyEngine,
    PolicyEvaluationExplanation,
    PolicyObligation,
    PolicyRequest,
    PolicyRule,
    PolicyVerdict,
    RuntimeControlProjection,
    admit_policy_execution,
    compile_policy_pack,
    evaluate_policy,
    explain_policy_evaluation,
    policy_enforcement_admission,
    policy_enforcement_admission_digest,
    policy_enforcement_plan_digest,
    policy_pack_digest,
    policy_verdict_digest,
    project_runtime_controls,
    validate_policy_enforcement_admission,
    validate_policy_enforcement_plan,
    validate_policy_request,
    validate_policy_verdict,
)

__all__ = [
    'CompileResult',
    'CompiledPolicyPack',
    'GOVERNANCE_TRACE_SCHEMA_VERSION',
    'GovApiError',
    'GovApiResult',
    'GovernanceTrace',
    'PolicyCompiler',
    'PolicyConstraint',
    'PolicyEnforcementPlan',
    'PolicyEngine',
    'PolicyEvaluationExplanation',
    'PolicyObligation',
    'PolicyRequest',
    'PolicyRule',
    'PolicyVerdict',
    'RuntimeControlProjection',
    'admit_policy_execution',
    'compile_policy_pack',
    'evaluate_policy',
    'explain_policy_evaluation',
    'policy_enforcement_admission',
    'policy_enforcement_admission_digest',
    'policy_enforcement_plan_digest',
    'policy_pack_digest',
    'policy_request_digest',
    'policy_verdict_digest',
    'project_governance_trace',
    'project_runtime_controls',
    'validate_policy_enforcement_admission',
    'validate_policy_enforcement_plan',
    'validate_policy_request',
    'validate_policy_verdict',
]
