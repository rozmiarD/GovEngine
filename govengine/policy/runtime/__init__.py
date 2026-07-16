from __future__ import annotations

from typing import Any, Mapping

from govengine.api import GovApiError
from govengine.policy.compiler import CompiledPolicyPack, PolicyCondition, PolicyRule
from govengine.policy.model import PolicyRequest, PolicyVerdict, validate_policy_request, validate_policy_verdict


_MISSING = object()


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
    for condition in rule.conditions:
        if not _condition_matches(condition, request, context):
            return False
    return True


def _condition_matches(
    condition: PolicyCondition,
    request: PolicyRequest,
    context: Mapping[str, Any],
) -> bool:
    actual = _lookup_condition(condition.path, request, context)
    expected = condition.value
    operator = condition.operator
    if operator == 'exists':
        return (actual is not _MISSING) is expected
    if actual is _MISSING:
        return False
    if operator == 'eq':
        return _strict_equal(actual, expected)
    if operator == 'neq':
        return not _strict_equal(actual, expected)
    if operator == 'in':
        return any(_strict_equal(actual, item) for item in expected)
    if operator == 'not_in':
        return not any(_strict_equal(actual, item) for item in expected)
    if operator == 'contains':
        if isinstance(actual, str):
            if not isinstance(expected, str):
                raise _operand_type_error(condition, actual)
            return expected in actual
        if isinstance(actual, (list, tuple)):
            return any(_strict_equal(expected, item) for item in actual)
        raise _operand_type_error(condition, actual)
    if operator in {'lt', 'lte', 'gt', 'gte'}:
        _require_numeric_pair(condition, actual, expected)
        if operator == 'lt':
            return actual < expected
        if operator == 'lte':
            return actual <= expected
        if operator == 'gt':
            return actual > expected
        return actual >= expected
    if operator == 'subset_of':
        if not isinstance(actual, (list, tuple)):
            raise _operand_type_error(condition, actual)
        return all(
            any(_strict_equal(item, candidate) for candidate in expected)
            for item in actual
        )
    if operator == 'matches_namespace':
        if not isinstance(actual, str):
            raise _operand_type_error(condition, actual)
        return actual == expected or actual.startswith(f'{expected}.')
    raise GovApiError('unknown_policy_condition_operator')


def _lookup_condition(key: str, request: PolicyRequest, context: Mapping[str, Any]) -> Any:
    namespace, _, path = key.partition('.')
    roots: dict[str, Mapping[str, Any]] = {
        'principal': request.principal,
        'action': request.action,
        'resource': request.resource,
        'request_context': request.context,
        'context': context,
    }
    root = roots.get(namespace)
    if root is None or not path:
        return _MISSING
    return _path(root, path)


def _path(value: Mapping[str, Any], path: str) -> Any:
    current: Any = value
    for part in path.split('.'):
        if not isinstance(current, Mapping) or part not in current:
            return _MISSING
        current = current[part]
    return current


def _bool_path(value: Mapping[str, Any], path: str) -> bool:
    result = _path(value, path)
    return result is not _MISSING and bool(result)


def _strict_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, Mapping):
        if left.keys() != right.keys():
            return False
        return all(_strict_equal(left[key], right[key]) for key in left)
    if isinstance(left, (list, tuple)):
        return len(left) == len(right) and all(
            _strict_equal(left_item, right_item)
            for left_item, right_item in zip(left, right, strict=True)
        )
    return bool(left == right)


def _require_numeric_pair(
    condition: PolicyCondition,
    actual: Any,
    expected: Any,
) -> None:
    if (
        isinstance(actual, bool)
        or isinstance(expected, bool)
        or type(actual) is not type(expected)
        or not isinstance(actual, (int, float))
    ):
        raise _operand_type_error(condition, actual)


def _operand_type_error(
    condition: PolicyCondition,
    actual: Any,
) -> GovApiError:
    return GovApiError(
        'policy_condition_operand_type_mismatch',
        context={
            'path': condition.path,
            'operator': condition.operator,
            'actual_type': type(actual).__name__,
        },
    )


def _is_mutating(action: Mapping[str, Any]) -> bool:
    mode = str(action.get('mode') or action.get('type') or action.get('category') or '').lower()
    return mode in {'write', 'mutating', 'mutation', 'delete', 'destructive', 'apply'}


def _is_critical(resource: Mapping[str, Any]) -> bool:
    criticality = str(resource.get('criticality') or resource.get('risk_class') or '').lower()
    return criticality in {'high', 'critical'}


def _has_approval_evidence(request: PolicyRequest) -> bool:
    # Legacy refs and booleans do not prove that an authorized principal
    # approved this exact subject. G2 introduces a bound ApprovalAttestation;
    # until then mutation remains approval-required on this compatibility path.
    return False


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
