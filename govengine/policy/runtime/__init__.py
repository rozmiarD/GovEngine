from __future__ import annotations

from typing import Any, Mapping

from govengine.api import GovApiError
from govengine.policy.compiler import CompiledPolicyPack, PolicyRule
from govengine.policy.model import PolicyRequest, PolicyVerdict, validate_policy_request, validate_policy_verdict


class PolicyEngine:
    """Fail-closed deterministic policy runtime for GovEngine governance."""

    def evaluate(
        self,
        request: Mapping[str, Any] | PolicyRequest,
        policy_pack: CompiledPolicyPack,
        *,
        context: Mapping[str, Any] | None = None,
    ) -> PolicyVerdict:
        checked_request = validate_policy_request(request)
        if not isinstance(policy_pack, CompiledPolicyPack):
            raise GovApiError('invalid_compiled_policy_pack')
        runtime_context = dict(context or {})

        invariant = self._evaluate_invariants(checked_request, policy_pack)
        if invariant:
            return invariant

        matched = tuple(rule for rule in policy_pack.rules if _matches(rule, checked_request, runtime_context))
        if not matched:
            return _verdict(
                checked_request,
                policy_pack,
                decision='deny',
                reason_code='no_matching_policy_rule',
                blockers=('no_matching_policy_rule',),
                risk_class='medium',
                risk_score=0.5,
            )

        deny = next((rule for rule in matched if rule.effect == 'deny'), None)
        if deny:
            return _verdict_from_rule(checked_request, policy_pack, deny, blockers=(deny.reason_code,))
        approval = next((rule for rule in matched if rule.effect == 'approval_required'), None)
        if approval:
            return _verdict_from_rule(checked_request, policy_pack, approval, blockers=(approval.reason_code,))
        obligations = next((rule for rule in matched if rule.effect == 'allow_with_obligations'), None)
        if obligations:
            return _verdict_from_rule(checked_request, policy_pack, obligations)
        return _verdict_from_rule(checked_request, policy_pack, matched[0])

    def _evaluate_invariants(self, request: PolicyRequest, policy_pack: CompiledPolicyPack) -> PolicyVerdict | None:
        if _bool_path(request.action, 'unsafe_execution_shape') or _bool_path(request.context, 'execution.unsafe_execution_shape'):
            return _verdict(
                request,
                policy_pack,
                decision='deny',
                reason_code='unsafe_execution_shape',
                blockers=('unsafe_execution_shape',),
                risk_class='critical',
                risk_score=1.0,
            )
        if _bool_path(request.action, 'destructive') and not _has_approval_evidence(request):
            return _verdict(
                request,
                policy_pack,
                decision='deny',
                reason_code='destructive_action_without_approval_evidence',
                blockers=('destructive_action_without_approval_evidence',),
                risk_class='critical',
                risk_score=1.0,
            )
        if _is_mutating(request.action) and _is_critical(request.resource) and not _has_approval_evidence(request):
            return _verdict(
                request,
                policy_pack,
                decision='approval_required',
                reason_code='critical_mutating_action_requires_approval',
                blockers=('operator_approval_required',),
                risk_class='high',
                risk_score=0.85,
            )
        return None


def evaluate_policy(
    request: Mapping[str, Any] | PolicyRequest,
    policy_pack: CompiledPolicyPack,
    *,
    context: Mapping[str, Any] | None = None,
) -> PolicyVerdict:
    return PolicyEngine().evaluate(request, policy_pack, context=context)


def _matches(rule: PolicyRule, request: PolicyRequest, context: Mapping[str, Any]) -> bool:
    for key, expected in rule.conditions.items():
        actual = _lookup_condition(str(key), request, context)
        if actual != expected:
            return False
    return True


def _lookup_condition(key: str, request: PolicyRequest, context: Mapping[str, Any]) -> Any:
    if key.startswith('principal.'):
        return _path(request.principal, key.removeprefix('principal.'))
    if key.startswith('action.'):
        return _path(request.action, key.removeprefix('action.'))
    if key.startswith('resource.'):
        return _path(request.resource, key.removeprefix('resource.'))
    if key.startswith('request_context.'):
        return _path(request.context, key.removeprefix('request_context.'))
    if key.startswith('context.'):
        return _path(context, key.removeprefix('context.'))
    return request.action.get(key, request.resource.get(key, request.context.get(key)))


def _path(value: Mapping[str, Any], path: str) -> Any:
    current: Any = value
    for part in path.split('.'):
        if not isinstance(current, Mapping):
            return None
        current = current.get(part)
    return current


def _bool_path(value: Mapping[str, Any], path: str) -> bool:
    return bool(_path(value, path))


def _is_mutating(action: Mapping[str, Any]) -> bool:
    mode = str(action.get('mode') or action.get('type') or action.get('category') or '').lower()
    return mode in {'write', 'mutating', 'mutation', 'delete', 'destructive', 'apply'}


def _is_critical(resource: Mapping[str, Any]) -> bool:
    criticality = str(resource.get('criticality') or resource.get('risk_class') or '').lower()
    return criticality in {'high', 'critical'}


def _has_approval_evidence(request: PolicyRequest) -> bool:
    if any('approval' in ref for ref in request.evidence_refs):
        return True
    evidence = request.context.get('evidence')
    if isinstance(evidence, Mapping):
        return bool(evidence.get('approval') or evidence.get('operator_approval'))
    return bool(request.context.get('approval') or request.context.get('operator_approval'))


def _verdict_from_rule(
    request: PolicyRequest,
    policy_pack: CompiledPolicyPack,
    rule: PolicyRule,
    *,
    blockers: tuple[str, ...] = (),
) -> PolicyVerdict:
    return _verdict(
        request,
        policy_pack,
        decision=rule.effect,
        reason_code=rule.reason_code,
        blockers=blockers,
        risk_class=rule.risk_class,
        risk_score=rule.risk_score,
        obligations=rule.obligations,
        constraints=rule.constraints,
    )


def _verdict(
    request: PolicyRequest,
    policy_pack: CompiledPolicyPack,
    *,
    decision: str,
    reason_code: str,
    blockers: tuple[str, ...] = (),
    risk_class: str = 'low',
    risk_score: float = 0.0,
    obligations: tuple[Any, ...] = (),
    constraints: tuple[Any, ...] = (),
) -> PolicyVerdict:
    return validate_policy_verdict(PolicyVerdict(
        verdict_id=f'{policy_pack.policy_id}:{request.request_id}',
        request_id=request.request_id,
        subject_ref=request.subject_ref,
        decision=decision,
        reason_code=reason_code,
        risk_class=risk_class,
        risk_score=risk_score,
        obligations=obligations,
        constraints=constraints,
        blockers=blockers,
        evidence_refs=request.evidence_refs,
        metadata={'policy_pack': policy_pack.policy_id, 'policy_version': policy_pack.version},
    ))
