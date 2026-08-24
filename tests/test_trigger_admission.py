from __future__ import annotations

from dataclasses import replace

import pytest

from govengine import (
    GovApiError,
    TRIGGER_PLANNING_REQUEST_SCHEMA_VERSION,
    TriggerPlanningRequest,
    admit_trigger_planning,
    trigger_planning_admission_digest,
    trigger_planning_request_digest,
    validate_trigger_planning_admission,
    validate_trigger_planning_request,
)


def _digest(char: str) -> str:
    return "sha256:" + char * 64


def _request(**overrides):
    payload = {
        "request_id": "trigger-request-1",
        "event_ref": _digest("a"),
        "event_type": "network.host_observed",
        "decision": "plan_operation",
        "rule_set_id": "tecrax.infrastructure-readonly-triggers",
        "rule_set_version": "0.1",
        "rule_set_digest": _digest("b"),
        "rule_id": "network.known-host-observed.inventory",
        "rule_digest": _digest("c"),
        "operation_intent": "collect_basic_host_inventory",
        "operation_mode": "dry_run",
    }
    payload.update(overrides)
    return payload


def test_trigger_planning_admission_allows_readonly_plan_operation() -> None:
    request = TriggerPlanningRequest.from_mapping(_request())
    admission = admit_trigger_planning(request)

    assert request.schema_version == TRIGGER_PLANNING_REQUEST_SCHEMA_VERSION
    assert admission.allowed is True
    assert admission.outcome == "allowed"
    assert admission.reason_code == "trigger_planning_allowed"
    assert admission.signal["operation_intent"] == "collect_basic_host_inventory"
    assert admission.metadata["governance_flow"] == "planning_admission_adapter.v1"
    assert admission.metadata["execution_authority"] is False
    assert "authorization" not in admission.as_dict()
    assert trigger_planning_request_digest(request).startswith("sha256:")
    assert trigger_planning_admission_digest(admission).startswith("sha256:")
    assert validate_trigger_planning_request(request.as_dict()) == request
    assert validate_trigger_planning_admission(admission, request=request) == admission


@pytest.mark.parametrize("decision", ["ignore", "escalate", "drop_duplicate", "cooldown_blocked"])
def test_trigger_record_decisions_are_record_only(decision: str) -> None:
    request = TriggerPlanningRequest.from_mapping(
        _request(
            decision=decision,
            operation_intent="",
            operation_mode="",
        )
    )

    admission = admit_trigger_planning(request)

    assert admission.allowed is True
    assert admission.outcome == "record_only"
    assert admission.reason_code == "trigger_planning_record_only"
    assert admission.metadata["execution_authority"] is False


def test_trigger_planning_rejects_mutating_operation_mode() -> None:
    with pytest.raises(GovApiError, match="trigger_planning_unsupported_operation_mode:apply"):
        validate_trigger_planning_request(_request(operation_mode="apply"))


@pytest.mark.parametrize('field', ('event_ref', 'rule_set_digest', 'rule_digest'))
def test_trigger_planning_rejects_uppercase_digest(field: str) -> None:
    request = _request(**{field: 'sha256:' + 'A' * 64})

    with pytest.raises(GovApiError, match='invalid_trigger_planning'):
        validate_trigger_planning_request(request)


def test_trigger_planning_requires_rule_digest_for_plan_operation() -> None:
    with pytest.raises(GovApiError, match="trigger_planning_missing_rule_binding"):
        validate_trigger_planning_request(_request(rule_digest=""))


def test_trigger_planning_rejects_operation_on_record_only_decision() -> None:
    with pytest.raises(GovApiError, match="trigger_planning_record_decision_with_operation"):
        validate_trigger_planning_request(_request(decision="escalate"))


def test_trigger_planning_rejects_raw_event_or_target_metadata() -> None:
    with pytest.raises(GovApiError, match="forbidden_trigger_planning_metadata:raw_event"):
        validate_trigger_planning_request(_request(metadata={"raw_event": {"subject": "host-1"}}))
    with pytest.raises(GovApiError, match="forbidden_trigger_planning_metadata:target"):
        validate_trigger_planning_request(_request(metadata={"nested": {"target": "host-1"}}))


def test_trigger_planning_admission_detects_drift() -> None:
    request = TriggerPlanningRequest.from_mapping(_request())
    admission = admit_trigger_planning(request)
    drifted = replace(admission, reason_code="different")

    with pytest.raises(GovApiError, match="trigger_planning_admission_drift"):
        validate_trigger_planning_admission(drifted, request=request)
