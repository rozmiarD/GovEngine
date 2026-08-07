from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Mapping

from govengine.policy.compiler import (
    CompiledPolicyPack,
    PolicyRule,
    _validated_compiled_policy_pack_snapshot,
)
from govengine.policy.enforcement import (
    SUPPORTED_POLICY_CONSTRAINTS,
    SUPPORTED_POLICY_OBLIGATIONS,
    admit_policy_execution,
    policy_pack_digest,
)
from govengine.policy.model import PolicyRequest, PolicyVerdict, validate_policy_request
from govengine.policy.reasons import POLICY_REASON_CODE_REGISTRY_SCHEMA_VERSION
from govengine.policy.runtime import PolicyEngine, _condition_matches, _matches
from govengine.signing import govengine_record_digest

POLICY_EXPLANATION_SCHEMA_VERSION = "v0.1"
POLICY_EXPLANATION_V1_SCHEMA_VERSION = "v1"
INVARIANT_REASONS = frozenset(
    {
        "unsafe_execution_shape",
        "destructive_action_without_approval_evidence",
        "critical_mutating_action_requires_approval",
    }
)


@dataclass(frozen=True)
class PolicyEvaluationExplanation:
    """Stable, redacted explanation of one deterministic policy evaluation."""

    schema_version: str
    status: str
    request_id: str
    subject_ref: str
    policy_id: str
    policy_version: str
    decision: str
    reason_code: str
    evaluation_path: str
    matched_rule: Mapping[str, Any] = field(default_factory=dict)
    invariant: Mapping[str, Any] = field(default_factory=dict)
    rule_evaluations: tuple[Mapping[str, Any], ...] = field(default_factory=tuple)
    risk: Mapping[str, Any] = field(default_factory=dict)
    obligations: tuple[Mapping[str, Any], ...] = field(default_factory=tuple)
    constraints: tuple[Mapping[str, Any], ...] = field(default_factory=tuple)
    unsupported_controls: tuple[str, ...] = field(default_factory=tuple)
    projected_controls: Mapping[str, Any] = field(default_factory=dict)
    enforcement_plan: Mapping[str, Any] = field(default_factory=dict)
    blockers: tuple[str, ...] = field(default_factory=tuple)
    non_claims: tuple[str, ...] = field(default_factory=tuple)
    policy_pack_digest: str = ""
    policy_issuer_ref: str = ""
    policy_epoch: int = 0
    reason_registry_version: str = ""
    trace_digest: str = ""

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": self.schema_version,
            "status": self.status,
            "request_id": self.request_id,
            "subject_ref": self.subject_ref,
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "decision": self.decision,
            "reason_code": self.reason_code,
            "evaluation_path": self.evaluation_path,
            "matched_rule": dict(self.matched_rule),
            "invariant": dict(self.invariant),
            "rule_evaluations": [dict(item) for item in self.rule_evaluations],
            "risk": dict(self.risk),
            "obligations": [dict(item) for item in self.obligations],
            "constraints": [dict(item) for item in self.constraints],
            "unsupported_controls": list(self.unsupported_controls),
            "projected_controls": dict(self.projected_controls),
            "enforcement_plan": dict(self.enforcement_plan),
            "blockers": list(self.blockers),
            "non_claims": list(self.non_claims),
        }
        if self.schema_version == POLICY_EXPLANATION_V1_SCHEMA_VERSION:
            payload.update(
                {
                    "policy_pack_digest": self.policy_pack_digest,
                    "policy_issuer_ref": self.policy_issuer_ref,
                    "policy_epoch": self.policy_epoch,
                    "reason_registry_version": self.reason_registry_version,
                    "trace_digest": self.trace_digest,
                }
            )
        return payload


def explain_policy_evaluation(
    request: Mapping[str, Any] | PolicyRequest,
    policy_pack: CompiledPolicyPack,
    *,
    context: Mapping[str, Any] | None = None,
) -> PolicyEvaluationExplanation:
    checked_request = validate_policy_request(request)
    policy_pack = _validated_compiled_policy_pack_snapshot(policy_pack)
    runtime_context = dict(context or {})
    verdict = PolicyEngine().evaluate(
        checked_request,
        policy_pack,
        context=runtime_context,
    )
    plan = admit_policy_execution(policy_pack, verdict)
    rule_evaluations = tuple(
        _rule_evaluation(
            rule,
            checked_request,
            runtime_context,
            schema_version=policy_pack.schema_version,
        )
        for rule in policy_pack.rules
    )
    matched_rules = tuple(item for item in rule_evaluations if item["matched"])
    invariant = _invariant(verdict)
    matched_rule = _matched_rule(verdict, policy_pack, matched_rules)
    evaluation_path = _evaluation_path(verdict, invariant, matched_rule)
    unsupported = _unsupported_controls(verdict)
    schema_version = (
        POLICY_EXPLANATION_V1_SCHEMA_VERSION
        if policy_pack.schema_version == "v1"
        else POLICY_EXPLANATION_SCHEMA_VERSION
    )
    explanation = PolicyEvaluationExplanation(
        schema_version=schema_version,
        status="blocked" if plan.blockers else "explained",
        request_id=checked_request.request_id,
        subject_ref=checked_request.subject_ref,
        policy_id=policy_pack.policy_id,
        policy_version=policy_pack.version,
        decision=verdict.decision,
        reason_code=verdict.reason_code,
        evaluation_path=evaluation_path,
        matched_rule=matched_rule,
        invariant=invariant,
        rule_evaluations=rule_evaluations,
        risk={"risk_class": verdict.risk_class, "risk_score": verdict.risk_score},
        obligations=tuple(_obligation(item) for item in verdict.obligations),
        constraints=tuple(_constraint(item) for item in verdict.constraints),
        unsupported_controls=unsupported,
        projected_controls=plan.controls.as_dict(),
        enforcement_plan={
            "plan_id": plan.plan_id,
            "status": plan.status,
            "reason_code": plan.reason_code,
            "blockers": list(plan.blockers),
        },
        blockers=tuple(plan.blockers or verdict.blockers),
        non_claims=(
            "Does not execute work.",
            "Does not approve operators or run approval workflow.",
            "Does not verify SCLite artifacts or host enforcement.",
            "Does not expose raw request payload values.",
        ),
        policy_pack_digest=(
            policy_pack_digest(policy_pack)
            if schema_version == POLICY_EXPLANATION_V1_SCHEMA_VERSION
            else ""
        ),
        policy_issuer_ref=policy_pack.issuer_ref,
        policy_epoch=policy_pack.policy_epoch,
        reason_registry_version=(
            POLICY_REASON_CODE_REGISTRY_SCHEMA_VERSION
            if schema_version == POLICY_EXPLANATION_V1_SCHEMA_VERSION
            else ""
        ),
    )
    if schema_version == POLICY_EXPLANATION_V1_SCHEMA_VERSION:
        body = explanation.as_dict()
        body.pop("trace_digest")
        explanation = replace(
            explanation,
            trace_digest=govengine_record_digest(
                body,
                record_type="govengine.policy.PolicyEvaluationExplanation",
                schema_version=POLICY_EXPLANATION_V1_SCHEMA_VERSION,
            ),
        )
    return explanation


def _rule_evaluation(
    rule: PolicyRule,
    request: PolicyRequest,
    context: Mapping[str, Any],
    *,
    schema_version: str,
) -> dict[str, Any]:
    conditions = []
    for condition in rule.conditions:
        item = {
            "matched": _condition_matches(condition, request, context),
            "redacted": True,
        }
        if schema_version == "v0.1":
            item["key"] = condition.path
        else:
            item["path"] = condition.path
            item["operator"] = condition.operator
        conditions.append(item)
    return {
        "rule_id": rule.rule_id,
        "effect": rule.effect,
        "priority": rule.priority,
        "reason_code": rule.reason_code,
        "matched": _matches(rule, request, context),
        "conditions": conditions,
    }


def _invariant(verdict: PolicyVerdict) -> dict[str, Any]:
    if verdict.reason_code not in INVARIANT_REASONS:
        return {}
    return {
        "triggered": True,
        "reason_code": verdict.reason_code,
        "blockers": list(verdict.blockers),
    }


def _matched_rule(
    verdict: PolicyVerdict,
    policy_pack: CompiledPolicyPack,
    matched_rules: tuple[Mapping[str, Any], ...],
) -> dict[str, Any]:
    if verdict.reason_code in INVARIANT_REASONS or not matched_rules:
        return {}
    chosen = _chosen_rule(verdict, policy_pack, matched_rules)
    return dict(chosen) if chosen else {}


def _chosen_rule(
    verdict: PolicyVerdict,
    policy_pack: CompiledPolicyPack,
    matched_rules: tuple[Mapping[str, Any], ...],
) -> Mapping[str, Any] | None:
    if verdict.decision == "deny":
        return _first(matched_rules, effect="deny", reason_code=verdict.reason_code)
    if verdict.decision == "approval_required":
        return _first(matched_rules, effect="approval_required", reason_code=verdict.reason_code)
    if verdict.decision == "allow_with_obligations":
        return _first(matched_rules, effect="allow_with_obligations", reason_code=verdict.reason_code)
    if verdict.decision == "allow":
        return _first(matched_rules, effect="allow", reason_code=verdict.reason_code) or matched_rules[0]
    for rule in policy_pack.rules:
        if rule.reason_code == verdict.reason_code:
            return next((item for item in matched_rules if item["rule_id"] == rule.rule_id), None)
    return None


def _first(
    rules: tuple[Mapping[str, Any], ...],
    *,
    effect: str,
    reason_code: str,
) -> Mapping[str, Any] | None:
    return next(
        (
            item
            for item in rules
            if item["effect"] == effect and item["reason_code"] == reason_code
        ),
        None,
    )


def _evaluation_path(
    verdict: PolicyVerdict,
    invariant: Mapping[str, Any],
    matched_rule: Mapping[str, Any],
) -> str:
    if invariant:
        return "invariant"
    if matched_rule:
        return "matched_rule"
    if verdict.reason_code == "no_matching_policy_rule":
        return "no_match"
    return "verdict"


def _obligation(value: Any) -> dict[str, Any]:
    return {
        "obligation_id": value.obligation_id,
        "kind": value.kind,
        "supported": value.kind in SUPPORTED_POLICY_OBLIGATIONS,
    }


def _constraint(value: Any) -> dict[str, Any]:
    return {
        "constraint_id": value.constraint_id,
        "kind": value.kind,
        "supported": value.kind in SUPPORTED_POLICY_CONSTRAINTS,
    }


def _unsupported_controls(verdict: PolicyVerdict) -> tuple[str, ...]:
    unsupported: list[str] = []
    for obligation in verdict.obligations:
        if obligation.kind not in SUPPORTED_POLICY_OBLIGATIONS:
            unsupported.append(f"unsupported_policy_obligation:{obligation.kind}")
    for constraint in verdict.constraints:
        if constraint.kind not in SUPPORTED_POLICY_CONSTRAINTS:
            unsupported.append(f"unsupported_policy_constraint:{constraint.kind}")
    return tuple(sorted(set(unsupported)))
