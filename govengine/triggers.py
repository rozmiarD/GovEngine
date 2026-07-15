from __future__ import annotations

from dataclasses import asdict, dataclass, field
from string import hexdigits
from typing import Any, Mapping

from govengine.admission import (
    GovAdmissionDecision,
    _admission_decision_from_planning_adapter,
    validate_admission_decision,
)
from govengine.api import GovApiError, require_mapping
from govengine.signing import govengine_record_digest

TRIGGER_PLANNING_REQUEST_SCHEMA_VERSION = "v0.1"
TRIGGER_PLANNING_DECISIONS = (
    "plan_operation",
    "ignore",
    "escalate",
    "drop_duplicate",
    "cooldown_blocked",
)
TRIGGER_OPERATION_MODES = ("dry_run", "read_only")
TRIGGER_RECORD_ONLY_DECISIONS = ("ignore", "escalate", "drop_duplicate", "cooldown_blocked")
FORBIDDEN_TRIGGER_METADATA_KEYS = (
    "api_key",
    "command",
    "commands",
    "credential",
    "credentials",
    "event_payload",
    "host",
    "hostname",
    "ip",
    "password",
    "raw_event",
    "raw_output",
    "secret",
    "stderr",
    "stdout",
    "subprocess",
    "target",
    "target_url",
    "token",
    "url",
)


@dataclass(frozen=True)
class TriggerPlanningRequest:
    """GovEngine-owned admission request for neutral trigger planning.

    RExecOp owns event intake, dedupe, cooldown and operation creation. Profiles
    own trigger meaning. This request carries only bounded identifiers and
    digests so GovEngine can decide whether a trigger decision may create a
    normal operation plan.
    """

    request_id: str
    event_ref: str
    event_type: str
    decision: str
    rule_set_id: str
    rule_set_version: str
    rule_set_digest: str
    rule_id: str = ""
    rule_digest: str = ""
    operation_intent: str = ""
    operation_mode: str = ""
    schema_version: str = TRIGGER_PLANNING_REQUEST_SCHEMA_VERSION
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> TriggerPlanningRequest:
        raw = require_mapping(value, reason_code="invalid_trigger_planning_request")
        item = cls(
            request_id=str(raw.get("request_id") or "").strip(),
            event_ref=str(raw.get("event_ref") or raw.get("event_digest") or "").strip(),
            event_type=str(raw.get("event_type") or "").strip(),
            decision=str(raw.get("decision") or "").strip(),
            rule_set_id=str(raw.get("rule_set_id") or "").strip(),
            rule_set_version=str(raw.get("rule_set_version") or "").strip(),
            rule_set_digest=str(raw.get("rule_set_digest") or "").strip(),
            rule_id=str(raw.get("rule_id") or "").strip(),
            rule_digest=str(raw.get("rule_digest") or "").strip(),
            operation_intent=str(raw.get("operation_intent") or "").strip(),
            operation_mode=str(raw.get("operation_mode") or "").strip(),
            schema_version=str(
                raw.get("schema_version") or TRIGGER_PLANNING_REQUEST_SCHEMA_VERSION
            ).strip(),
            metadata=_metadata(raw.get("metadata")),
        )
        validate_trigger_planning_request(item)
        return item

    def as_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["metadata"] = dict(self.metadata)
        return out


def validate_trigger_planning_request(
    value: Mapping[str, Any] | TriggerPlanningRequest,
) -> TriggerPlanningRequest:
    item = value if isinstance(value, TriggerPlanningRequest) else TriggerPlanningRequest.from_mapping(value)
    if item.schema_version != TRIGGER_PLANNING_REQUEST_SCHEMA_VERSION:
        raise GovApiError("unknown_trigger_planning_request_schema")
    for field_name in (
        "request_id",
        "event_ref",
        "event_type",
        "decision",
        "rule_set_id",
        "rule_set_version",
        "rule_set_digest",
    ):
        if not getattr(item, field_name):
            raise GovApiError(f"missing_trigger_planning_{field_name}")
    if item.decision not in TRIGGER_PLANNING_DECISIONS:
        raise GovApiError(f"unsupported_trigger_planning_decision:{item.decision}")
    _require_digest_ref(item.event_ref, "invalid_trigger_planning_event_ref")
    _require_digest_ref(item.rule_set_digest, "invalid_trigger_planning_rule_set_digest")
    if item.rule_digest:
        _require_digest_ref(item.rule_digest, "invalid_trigger_planning_rule_digest")
    if item.decision == "plan_operation":
        if not item.rule_id or not item.rule_digest:
            raise GovApiError("trigger_planning_missing_rule_binding")
        if not item.operation_intent:
            raise GovApiError("trigger_planning_missing_operation_intent")
        if item.operation_mode not in TRIGGER_OPERATION_MODES:
            raise GovApiError(
                f"trigger_planning_unsupported_operation_mode:{item.operation_mode or 'missing'}"
            )
    elif item.operation_intent or item.operation_mode:
        raise GovApiError("trigger_planning_record_decision_with_operation")
    _reject_forbidden_trigger_metadata(item.metadata)
    return item


def trigger_planning_request_digest(
    request: Mapping[str, Any] | TriggerPlanningRequest,
) -> str:
    checked = validate_trigger_planning_request(request)
    return govengine_record_digest(
        checked,
        record_type="govengine.triggers.TriggerPlanningRequest",
    )


def admit_trigger_planning(
    request: Mapping[str, Any] | TriggerPlanningRequest,
) -> GovAdmissionDecision:
    checked = validate_trigger_planning_request(request)
    outcome = "allowed"
    reason_code = "trigger_planning_allowed"
    if checked.decision in TRIGGER_RECORD_ONLY_DECISIONS:
        outcome = "record_only"
        reason_code = "trigger_planning_record_only"
    return _admission_decision_from_planning_adapter(
        decision_id=f"trigger-admission:{checked.request_id}",
        subject_ref=trigger_planning_request_digest(checked),
        subject_kind="generic",
        outcome=outcome,
        reason_code=reason_code,
        signal={
            "request_id": checked.request_id,
            "event_ref": checked.event_ref,
            "event_type": checked.event_type,
            "decision": checked.decision,
            "rule_set_id": checked.rule_set_id,
            "rule_set_digest": checked.rule_set_digest,
            "rule_id": checked.rule_id,
            "rule_digest": checked.rule_digest,
            "operation_intent": checked.operation_intent,
            "operation_mode": checked.operation_mode,
        },
        metadata={
            "source": "trigger_planning_request",
            "schema_version": checked.schema_version,
        },
    )


def trigger_planning_admission_digest(
    admission: Mapping[str, Any] | GovAdmissionDecision,
) -> str:
    checked = validate_admission_decision(admission)
    return govengine_record_digest(
        checked,
        record_type="govengine.admission.GovAdmissionDecision",
    )


def validate_trigger_planning_admission(
    admission: Mapping[str, Any] | GovAdmissionDecision,
    *,
    request: Mapping[str, Any] | TriggerPlanningRequest,
) -> GovAdmissionDecision:
    checked = validate_admission_decision(admission)
    expected = admit_trigger_planning(request)
    if checked.as_dict() != expected.as_dict():
        raise GovApiError("trigger_planning_admission_drift")
    return checked


def _metadata(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    raw = require_mapping(value, reason_code="invalid_trigger_planning_metadata")
    return dict(raw)


def _reject_forbidden_trigger_metadata(value: Mapping[str, Any]) -> None:
    lowered = {str(key).lower() for key in value}
    for key in FORBIDDEN_TRIGGER_METADATA_KEYS:
        if key in lowered:
            raise GovApiError(f"forbidden_trigger_planning_metadata:{key}")
    for nested in value.values():
        if isinstance(nested, Mapping):
            _reject_forbidden_trigger_metadata(nested)


def _require_digest_ref(value: str, reason_code: str) -> None:
    text = str(value or "").strip()
    prefix, separator, digest = text.partition(":")
    if separator != ":" or prefix != "sha256" or len(digest) != 64:
        raise GovApiError(reason_code)
    if not all(char in hexdigits for char in digest):
        raise GovApiError(reason_code)
