from __future__ import annotations

import pytest

from govengine import PolicyCompiler, PolicyEngine, explain_policy_evaluation
from govengine.api import GovApiError
from govengine.policy.compiler import PolicyCondition
from govengine.policy.schema import policy_json_schema


def _compile(*conditions: dict[str, object]):
    result = PolicyCompiler().compile(
        {
            "policy_id": "typed-policy",
            "version": "1.0.0",
            "schema_version": "v1",
            "rules": [
                {
                    "rule_id": "typed-allow",
                    "effect": "allow",
                    "conditions": list(conditions),
                    "reason_code": "typed_condition_matched",
                }
            ],
        }
    )
    assert result.ok, result.as_dict()
    assert result.policy_pack is not None
    return result.policy_pack


def _request(**overrides: object) -> dict[str, object]:
    request: dict[str, object] = {
        "request_id": "typed-request",
        "subject_ref": "artifact://typed/request",
        "principal": {"roles": ["operator", "reviewer"]},
        "action": {
            "mode": "read",
            "capability": "connector.http.read",
            "capabilities": ["read", "digest"],
        },
        "resource": {
            "criticality": "low",
            "risk_score": 0.25,
            "replicas": 2,
        },
        "context": {"tenant": {"tier": "standard"}},
    }
    request.update(overrides)
    return request


@pytest.mark.parametrize(
    "condition",
    [
        {"path": "action.mode", "operator": "eq", "value": "read"},
        {"path": "action.mode", "operator": "neq", "value": "unsafe"},
        {"path": "action.mode", "operator": "in", "value": ["read", "observe"]},
        {"path": "action.mode", "operator": "not_in", "value": ["apply", "delete"]},
        {"path": "principal.roles", "operator": "contains", "value": "operator"},
        {"path": "resource.criticality", "operator": "exists", "value": True},
        {"path": "resource.owner", "operator": "exists", "value": False},
        {"path": "resource.risk_score", "operator": "lt", "value": 0.5},
        {"path": "resource.risk_score", "operator": "lte", "value": 0.25},
        {"path": "resource.replicas", "operator": "gt", "value": 1},
        {"path": "resource.replicas", "operator": "gte", "value": 2},
        {
            "path": "action.capabilities",
            "operator": "subset_of",
            "value": ["read", "digest", "receipt"],
        },
        {
            "path": "action.capability",
            "operator": "matches_namespace",
            "value": "connector.http",
        },
    ],
)
def test_typed_policy_condition_operators_match(condition: dict[str, object]) -> None:
    verdict = PolicyEngine().evaluate(_request(), _compile(condition))

    assert verdict.decision == "allow"
    assert verdict.reason_code == "typed_condition_matched"


def test_typed_policy_conditions_are_canonical_and_round_trip() -> None:
    pack = _compile(
        {"path": "resource.replicas", "operator": "gte", "value": 2},
        {"path": "action.mode", "operator": "eq", "value": "read"},
    )

    assert [condition.path for condition in pack.rules[0].conditions] == [
        "action.mode",
        "resource.replicas",
    ]
    payload = pack.as_dict()
    assert payload["schema_version"] == "v1"
    assert payload["rules"][0]["conditions"] == [
        {"path": "action.mode", "operator": "eq", "value": "read"},
        {"path": "resource.replicas", "operator": "gte", "value": 2},
    ]
    recompiled = PolicyCompiler().compile(payload)
    assert recompiled.ok
    assert recompiled.policy_pack == pack

    explanation = explain_policy_evaluation(_request(), pack).as_dict()
    assert explanation["matched_rule"]["conditions"] == [
        {
            "path": "action.mode",
            "operator": "eq",
            "matched": True,
            "redacted": True,
        },
        {
            "path": "resource.replicas",
            "operator": "gte",
            "matched": True,
            "redacted": True,
        },
    ]


def test_legacy_equality_map_compiles_to_typed_ast_without_wire_drift() -> None:
    result = PolicyCompiler().compile(
        {
            "policy_id": "legacy-policy",
            "version": "0.1",
            "rules": [
                {
                    "rule_id": "legacy-read",
                    "effect": "allow",
                    "conditions": {"action.mode": "read"},
                }
            ],
        }
    )

    assert result.ok
    assert result.policy_pack is not None
    condition = result.policy_pack.rules[0].conditions[0]
    assert condition == PolicyCondition(path="action.mode", operator="eq", value="read")
    assert result.policy_pack.as_dict()["rules"][0]["conditions"] == {
        "action.mode": "read"
    }


@pytest.mark.parametrize(
    ("condition", "reason_code"),
    [
        (
            {"path": "unknown.mode", "operator": "eq", "value": "read"},
            "unknown_policy_condition_path",
        ),
        (
            {"path": "action", "operator": "eq", "value": "read"},
            "unknown_policy_condition_path",
        ),
        (
            {"path": "action.mode", "operator": "regex", "value": "read.*"},
            "unknown_policy_condition_operator",
        ),
        (
            {"path": "resource.replicas", "operator": "gte", "value": "2"},
            "invalid_policy_condition_operand",
        ),
        (
            {"path": "resource.owner", "operator": "exists", "value": "yes"},
            "invalid_policy_condition_operand",
        ),
        (
            {"path": "action.mode", "operator": "in", "value": "read"},
            "invalid_policy_condition_operand",
        ),
    ],
)
def test_typed_condition_compilation_fails_closed(
    condition: dict[str, object],
    reason_code: str,
) -> None:
    result = PolicyCompiler().compile(
        {
            "policy_id": "invalid-typed-policy",
            "version": "1",
            "schema_version": "v1",
            "rules": [
                {
                    "rule_id": "invalid",
                    "effect": "allow",
                    "conditions": [condition],
                }
            ],
        }
    )

    assert not result.ok
    assert result.reason_code == reason_code


def test_missing_path_never_satisfies_negative_operator() -> None:
    verdict = PolicyEngine().evaluate(
        _request(),
        _compile(
            {
                "path": "resource.owner",
                "operator": "neq",
                "value": "root",
            }
        ),
    )

    assert verdict.decision == "deny"
    assert verdict.reason_code == "no_matching_policy_rule"


def test_wrong_runtime_operand_type_has_stable_reason_code() -> None:
    with pytest.raises(GovApiError) as exc_info:
        PolicyEngine().evaluate(
            _request(resource={"criticality": "low", "replicas": "2"}),
            _compile(
                {
                    "path": "resource.replicas",
                    "operator": "gte",
                    "value": 2,
                }
            ),
        )

    assert exc_info.value.reason_code == "policy_condition_operand_type_mismatch"


def test_equality_does_not_coerce_bool_to_integer() -> None:
    verdict = PolicyEngine().evaluate(
        _request(action={"mode": "read", "enabled": True}),
        _compile({"path": "action.enabled", "operator": "eq", "value": 1}),
    )

    assert verdict.decision == "deny"
    assert verdict.reason_code == "no_matching_policy_rule"


def test_exact_conflict_uses_canonical_condition_ast() -> None:
    result = PolicyCompiler().compile(
        {
            "policy_id": "conflict",
            "version": "1",
            "schema_version": "v1",
            "rules": [
                {
                    "rule_id": "allow",
                    "effect": "allow",
                    "conditions": [
                        {"path": "action.mode", "operator": "eq", "value": "read"},
                        {"path": "resource.criticality", "operator": "eq", "value": "low"},
                    ],
                },
                {
                    "rule_id": "deny",
                    "effect": "deny",
                    "conditions": [
                        {"path": "resource.criticality", "operator": "eq", "value": "low"},
                        {"path": "action.mode", "operator": "eq", "value": "read"},
                    ],
                },
            ],
        }
    )

    assert not result.ok
    assert result.reason_code == "conflicting_policy_rules"


def test_typed_policy_json_schema_is_available() -> None:
    schema = policy_json_schema("policy-pack-v1")

    assert schema["properties"]["schema_version"] == {"const": "v1"}
    condition = schema["properties"]["rules"]["items"]["properties"]["conditions"]
    assert condition["type"] == "array"
