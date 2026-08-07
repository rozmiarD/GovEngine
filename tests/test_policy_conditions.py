from __future__ import annotations

import pytest

from govengine import PolicyCompiler, PolicyEngine, explain_policy_evaluation
from govengine.api import GovApiError
from govengine.policy.compiler import (
    _POLICY_CONDITION_V1_FIELDS,
    _POLICY_PACK_V1_FIELDS,
    _POLICY_RULE_V1_FIELDS,
    _POLICY_VALIDITY_V1_FIELDS,
    PolicyCondition,
)
from govengine.policy.schema import policy_json_schema


def _v1_fields() -> dict[str, object]:
    return {
        "schema_version": "v1",
        "issuer_ref": "organization:example",
        "policy_epoch": 7,
        "validity": {
            "not_before": "2026-07-16T00:00:00Z",
            "expires_at": "2026-08-16T00:00:00Z",
        },
        "supersedes": [],
    }


def _v1_policy_pack() -> dict[str, object]:
    return {
        **_v1_fields(),
        "policy_id": "typed-policy",
        "version": "1.0.0",
        "rules": [
            {
                "rule_id": "typed-allow",
                "effect": "allow",
                "conditions": [
                    {"path": "action.mode", "operator": "eq", "value": "read"}
                ],
            }
        ],
    }


def _compile(*conditions: dict[str, object]):
    result = PolicyCompiler().compile(
        {
            **_v1_fields(),
            "policy_id": "typed-policy",
            "version": "1.0.0",
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


def test_v1_runtime_closed_field_inventories_exactly_match_json_schema() -> None:
    schema = policy_json_schema("policy-pack-v1")
    rule_schema = schema["properties"]["rules"]["items"]
    validity_schema = schema["properties"]["validity"]
    condition_schema = rule_schema["properties"]["conditions"]["items"]

    assert schema["additionalProperties"] is False
    assert rule_schema["additionalProperties"] is False
    assert validity_schema["additionalProperties"] is False
    assert condition_schema["additionalProperties"] is False
    assert _POLICY_PACK_V1_FIELDS == frozenset(schema["properties"])
    assert _POLICY_RULE_V1_FIELDS == frozenset(rule_schema["properties"])
    assert _POLICY_VALIDITY_V1_FIELDS == frozenset(validity_schema["properties"])
    assert _POLICY_CONDITION_V1_FIELDS == frozenset(condition_schema["properties"])


@pytest.mark.parametrize(
    ("object_level", "unknown_field", "reason_code"),
    [
        ("pack", "unexpected_pack_field", "invalid_policy_pack"),
        ("rule", "unexpected_rule_field", "invalid_policy_rule"),
        ("validity", "unexpected_validity_field", "invalid_policy_validity"),
        ("condition", "unexpected_condition_field", "unknown_policy_condition_field"),
    ],
)
def test_v1_schema_and_compiler_reject_unknown_closed_object_fields(
    object_level: str,
    unknown_field: str,
    reason_code: str,
) -> None:
    policy = _v1_policy_pack()
    schema = policy_json_schema("policy-pack-v1")
    schema_node = schema

    if object_level == "pack":
        policy[unknown_field] = True
    elif object_level == "validity":
        validity = policy["validity"]
        assert isinstance(validity, dict)
        validity[unknown_field] = True
        schema_node = schema["properties"]["validity"]
    else:
        rules = policy["rules"]
        assert isinstance(rules, list)
        rule = rules[0]
        assert isinstance(rule, dict)
        schema_node = schema["properties"]["rules"]["items"]
        if object_level == "rule":
            rule[unknown_field] = True
        else:
            conditions = rule["conditions"]
            assert isinstance(conditions, list)
            condition = conditions[0]
            assert isinstance(condition, dict)
            condition[unknown_field] = True
            schema_node = schema_node["properties"]["conditions"]["items"]

    assert schema_node["additionalProperties"] is False
    assert unknown_field not in schema_node["properties"]
    result = PolicyCompiler().compile(policy)
    assert not result.ok
    assert result.policy_pack is None
    assert result.reason_code == reason_code


def test_v1_constraint_typo_is_rejected_before_policy_evaluation() -> None:
    policy = _v1_policy_pack()
    rules = policy["rules"]
    assert isinstance(rules, list)
    rule = rules[0]
    assert isinstance(rule, dict)
    rule["constraintss"] = [
        {"constraint_id": "output", "kind": "output_limit", "value": 1}
    ]

    result = PolicyCompiler().compile(policy)

    assert result.status == "rejected"
    assert result.policy_pack is None
    assert result.reason_code == "invalid_policy_rule"


def test_legacy_v0_1_preserves_unknown_field_tolerance_and_aliases() -> None:
    result = PolicyCompiler().compile(
        {
            "id": "legacy-policy",
            "version": "0.1",
            "schema_version": "v0.1",
            "legacy_pack_extension": True,
            "rules": [
                {
                    "id": "legacy-read",
                    "decision": "allow",
                    "conditions": {"action.mode": "read"},
                    "legacy_rule_extension": True,
                }
            ],
        }
    )

    assert result.ok
    assert result.policy_pack is not None
    assert result.policy_pack.policy_id == "legacy-policy"
    assert result.policy_pack.rules[0].rule_id == "legacy-read"
    assert result.policy_pack.rules[0].effect == "allow"


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
            **_v1_fields(),
            "policy_id": "invalid-typed-policy",
            "version": "1",
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
            **_v1_fields(),
            "policy_id": "conflict",
            "version": "1",
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


@pytest.mark.parametrize(
    ("rules", "reason_code"),
    [
        (
            [
                {
                    "rule_id": "same-id",
                    "effect": "allow",
                    "conditions": [{"path": "action.mode", "operator": "eq", "value": "read"}],
                },
                {
                    "rule_id": "same-id",
                    "effect": "deny",
                    "conditions": [{"path": "action.mode", "operator": "eq", "value": "write"}],
                },
            ],
            "duplicate_policy_rule_id",
        ),
        (
            [
                {
                    "rule_id": "first",
                    "effect": "allow",
                    "conditions": [{"path": "action.mode", "operator": "eq", "value": "read"}],
                },
                {
                    "rule_id": "second",
                    "effect": "allow",
                    "conditions": [{"path": "action.mode", "operator": "eq", "value": "read"}],
                },
            ],
            "redundant_policy_rules",
        ),
    ],
)
def test_policy_rule_identity_analysis_fails_closed(
    rules: list[dict[str, object]],
    reason_code: str,
) -> None:
    result = PolicyCompiler().compile(
        {**_v1_fields(), "policy_id": "analysis", "version": "1", "rules": rules}
    )

    assert result.reason_code == reason_code


def test_conflicting_control_id_fails_closed() -> None:
    result = PolicyCompiler().compile(
        {
            **_v1_fields(),
            "policy_id": "controls",
            "version": "1",
            "rules": [
                {
                    "rule_id": "read",
                    "effect": "allow",
                    "conditions": [{"path": "action.mode", "operator": "eq", "value": "read"}],
                    "constraints": [
                        {"constraint_id": "output", "kind": "output_limit", "value": 4096}
                    ],
                },
                {
                    "rule_id": "observe",
                    "effect": "allow",
                    "conditions": [{"path": "action.mode", "operator": "eq", "value": "observe"}],
                    "constraints": [
                        {"constraint_id": "output", "kind": "output_limit", "value": 8192}
                    ],
                },
            ],
        }
    )

    assert result.reason_code == "conflicting_policy_controls"


def test_policy_compiler_enforces_rule_condition_and_control_limits() -> None:
    too_many_rules = PolicyCompiler().compile(
        {
            **_v1_fields(),
            "policy_id": "too-many-rules",
            "version": "1",
            "rules": [
                {
                    "rule_id": f"rule-{index}",
                    "effect": "allow",
                    "conditions": [
                        {"path": "action.index", "operator": "eq", "value": index}
                    ],
                }
                for index in range(257)
            ],
        }
    )
    too_many_conditions = PolicyCompiler().compile(
        {
            **_v1_fields(),
            "policy_id": "too-many-conditions",
            "version": "1",
            "rules": [
                {
                    "rule_id": "wide",
                    "effect": "allow",
                    "conditions": [
                        {"path": f"action.field_{index}", "operator": "eq", "value": index}
                        for index in range(33)
                    ],
                }
            ],
        }
    )
    too_many_controls = PolicyCompiler().compile(
        {
            **_v1_fields(),
            "policy_id": "too-many-controls",
            "version": "1",
            "rules": [
                {
                    "rule_id": "controlled",
                    "effect": "allow",
                    "conditions": [{"path": "action.mode", "operator": "eq", "value": "read"}],
                    "constraints": [
                        {
                            "constraint_id": f"limit-{index}",
                            "kind": "output_limit",
                            "value": index + 1,
                        }
                        for index in range(65)
                    ],
                }
            ],
        }
    )

    assert too_many_rules.reason_code == "policy_rule_limit_exceeded"
    assert too_many_conditions.reason_code == "policy_rule_condition_limit_exceeded"
    assert too_many_controls.reason_code == "policy_rule_control_limit_exceeded"
