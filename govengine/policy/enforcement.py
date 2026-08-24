from __future__ import annotations

from dataclasses import asdict, dataclass, field
from math import isfinite
from typing import Any, Mapping

from govengine._governance_validation import (
    optional_bool,
    optional_nonnegative_int,
    optional_nonnegative_number,
    optional_text_tuple,
    require_sha256_digest,
    required_nonnegative_int,
    required_nonnegative_number,
    required_text,
    schema_version,
    text_tuple,
)
from govengine.api import GovApiError, require_mapping
from govengine.admission import (
    GovAdmissionDecision,
    admission_decision_from_host_gate,
    validate_admission_decision,
)
from govengine.policy.compiler import (
    CompiledPolicyPack,
    _validated_compiled_policy_pack_snapshot,
)
from govengine.policy.model import PolicyVerdict, validate_policy_verdict
from govengine.signing import govengine_record_digest

POLICY_ENFORCEMENT_PLAN_SCHEMA_VERSION = "v0.1"
POLICY_ENFORCEMENT_PLAN_STATUSES = ("ready", "blocked")
SUPPORTED_POLICY_OBLIGATIONS = frozenset(
    {"receipt", "receipt_required", "output_digest_required"}
)
SUPPORTED_POLICY_CONSTRAINTS = frozenset(
    {
        "allowed_backend_classes",
        "allowed_network_egress",
        "max_steps",
        "mutation_requires_approval",
        "no_raw_shell",
        "output_digest_required",
        "output_limit",
        "read_only_required",
        "receipt_required",
        "timeout",
    }
)


@dataclass(frozen=True)
class RuntimeControlProjection:
    """Domain-neutral controls a host runner can enforce mechanically."""

    timeout_seconds: float = 0.0
    max_steps: int = 0
    max_output_bytes: int = 0
    receipt_required: bool = True
    output_digest_required: bool = False
    read_only_required: bool = False
    no_raw_shell: bool = False
    mutation_requires_approval: bool = False
    allowed_network_egress: tuple[str, ...] = field(default_factory=tuple)
    allowed_backend_classes: tuple[str, ...] = field(default_factory=tuple)
    typed_execution_control_ids: tuple[str, ...] = field(default_factory=tuple)
    control_ids: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any] | None) -> RuntimeControlProjection:
        raw = require_mapping(
            {} if value is None else value,
            reason_code="invalid_runtime_control_projection",
        )
        item = cls(
            timeout_seconds=optional_nonnegative_number(
                raw,
                "timeout_seconds",
                default=0.0,
                reason_code="invalid_runtime_control_timeout",
            ),
            max_steps=optional_nonnegative_int(
                raw,
                "max_steps",
                default=0,
                reason_code="invalid_runtime_control_max_steps",
            ),
            max_output_bytes=optional_nonnegative_int(
                raw,
                "max_output_bytes",
                default=0,
                reason_code="invalid_runtime_control_output_limit",
            ),
            receipt_required=optional_bool(
                raw,
                "receipt_required",
                default=True,
                reason_code="invalid_runtime_control_receipt_required",
            ),
            output_digest_required=optional_bool(
                raw,
                "output_digest_required",
                default=False,
                reason_code="invalid_runtime_control_output_digest_required",
            ),
            read_only_required=optional_bool(
                raw,
                "read_only_required",
                default=False,
                reason_code="invalid_runtime_control_read_only_required",
            ),
            no_raw_shell=optional_bool(
                raw,
                "no_raw_shell",
                default=False,
                reason_code="invalid_runtime_control_no_raw_shell",
            ),
            mutation_requires_approval=optional_bool(
                raw,
                "mutation_requires_approval",
                default=False,
                reason_code="invalid_runtime_control_mutation_requires_approval",
            ),
            allowed_network_egress=optional_text_tuple(
                raw,
                "allowed_network_egress",
                reason_code="invalid_runtime_control_allowed_network_egress",
            ),
            allowed_backend_classes=optional_text_tuple(
                raw,
                "allowed_backend_classes",
                reason_code="invalid_runtime_control_allowed_backend_classes",
            ),
            typed_execution_control_ids=optional_text_tuple(
                raw,
                "typed_execution_control_ids",
                reason_code="invalid_runtime_control_typed_execution_control_ids",
            ),
            control_ids=optional_text_tuple(
                raw,
                "control_ids",
                reason_code="invalid_runtime_control_ids",
            ),
        )
        _validate_projection(item)
        return item

    def as_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["control_ids"] = list(self.control_ids)
        out["allowed_network_egress"] = list(self.allowed_network_egress)
        out["allowed_backend_classes"] = list(self.allowed_backend_classes)
        out["typed_execution_control_ids"] = list(self.typed_execution_control_ids)
        return out


@dataclass(frozen=True)
class PolicyEnforcementPlan:
    """GovEngine-owned control plan for one PolicyEngine verdict.

    Admission remains represented by the existing GovAdmissionDecision. This
    record binds governance inputs and neutral controls only; it does not own
    runner IO, SCLite artifact canonicalization, or domain semantics.
    """

    plan_id: str
    subject_ref: str
    policy_pack_id: str
    policy_pack_version: str
    policy_pack_digest: str
    verdict_id: str
    verdict_digest: str
    status: str
    reason_code: str
    schema_version: str = POLICY_ENFORCEMENT_PLAN_SCHEMA_VERSION
    controls: RuntimeControlProjection = field(default_factory=RuntimeControlProjection)
    blockers: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> PolicyEnforcementPlan:
        raw = require_mapping(value, reason_code="invalid_policy_enforcement_plan")
        controls = raw.get("controls")
        if controls is not None and not isinstance(controls, Mapping):
            raise GovApiError("invalid_runtime_control_projection")
        item = cls(
            plan_id=required_text(raw, "plan_id", "missing_policy_enforcement_plan_plan_id"),
            subject_ref=required_text(
                raw,
                "subject_ref",
                "missing_policy_enforcement_plan_subject_ref",
            ),
            policy_pack_id=required_text(
                raw,
                "policy_pack_id",
                "missing_policy_enforcement_plan_policy_pack_id",
            ),
            policy_pack_version=required_text(
                raw,
                "policy_pack_version",
                "missing_policy_enforcement_plan_policy_pack_version",
            ),
            policy_pack_digest=require_sha256_digest(
                required_text(
                    raw,
                    "policy_pack_digest",
                    "missing_policy_enforcement_plan_policy_pack_digest",
                ),
                "invalid_policy_enforcement_plan_digest",
            ),
            verdict_id=required_text(raw, "verdict_id", "missing_policy_enforcement_plan_verdict_id"),
            verdict_digest=require_sha256_digest(
                required_text(
                    raw,
                    "verdict_digest",
                    "missing_policy_enforcement_plan_verdict_digest",
                ),
                "invalid_policy_enforcement_plan_digest",
            ),
            status=required_text(raw, "status", "unknown_policy_enforcement_plan_status"),
            reason_code=required_text(
                raw,
                "reason_code",
                "missing_policy_enforcement_plan_reason_code",
            ),
            schema_version=schema_version(
                raw,
                default=POLICY_ENFORCEMENT_PLAN_SCHEMA_VERSION,
                reason_code="unknown_policy_enforcement_plan_schema",
            ),
            controls=RuntimeControlProjection.from_mapping(controls),
            blockers=optional_text_tuple(
                raw,
                "blockers",
                reason_code="invalid_policy_enforcement_plan_blockers",
            ),
        )
        _validate_plan_shape(item)
        return item

    @property
    def allowed(self) -> bool:
        return self.status == "ready" and not self.blockers

    def as_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "subject_ref": self.subject_ref,
            "policy_pack_id": self.policy_pack_id,
            "policy_pack_version": self.policy_pack_version,
            "policy_pack_digest": self.policy_pack_digest,
            "verdict_id": self.verdict_id,
            "verdict_digest": self.verdict_digest,
            "status": self.status,
            "reason_code": self.reason_code,
            "schema_version": self.schema_version,
            "controls": self.controls.as_dict(),
            "blockers": list(self.blockers),
        }


def policy_pack_digest(policy_pack: CompiledPolicyPack) -> str:
    policy_pack = _validated_compiled_policy_pack_snapshot(policy_pack)
    return govengine_record_digest(
        policy_pack,
        record_type="govengine.policy.compiler.CompiledPolicyPack",
    )


def policy_verdict_digest(verdict: Mapping[str, Any] | PolicyVerdict) -> str:
    checked = validate_policy_verdict(verdict)
    return govengine_record_digest(
        checked,
        record_type="govengine.policy.model.PolicyVerdict",
    )


def policy_enforcement_plan_digest(
    plan: Mapping[str, Any] | PolicyEnforcementPlan,
) -> str:
    checked = (
        plan
        if isinstance(plan, PolicyEnforcementPlan)
        else PolicyEnforcementPlan.from_mapping(plan)
    )
    return govengine_record_digest(
        checked,
        record_type="govengine.policy.enforcement.PolicyEnforcementPlan",
    )


def policy_enforcement_admission(
    plan: Mapping[str, Any] | PolicyEnforcementPlan,
) -> GovAdmissionDecision:
    checked = (
        plan
        if isinstance(plan, PolicyEnforcementPlan)
        else PolicyEnforcementPlan.from_mapping(plan)
    )
    return admission_decision_from_host_gate(
        decision_id=f"policy-admission:{checked.verdict_id}",
        subject_ref=checked.subject_ref,
        allowed=checked.allowed,
        reason_code=checked.reason_code,
        blockers=checked.blockers,
        signal={
            "policy_enforcement_plan_id": checked.plan_id,
            "policy_enforcement_plan_digest": policy_enforcement_plan_digest(checked),
            "policy_pack_digest": checked.policy_pack_digest,
            "verdict_digest": checked.verdict_digest,
        },
        metadata={
            "source": "policy_enforcement_plan",
            "schema_version": checked.schema_version,
        },
    )


def policy_enforcement_admission_digest(
    admission: Mapping[str, Any] | GovAdmissionDecision,
) -> str:
    checked = validate_admission_decision(admission)
    return govengine_record_digest(
        checked,
        record_type="govengine.admission.GovAdmissionDecision",
    )


def project_runtime_controls(verdict: Mapping[str, Any] | PolicyVerdict) -> RuntimeControlProjection:
    checked = validate_policy_verdict(verdict)
    timeout_seconds = 0.0
    max_steps = 0
    max_output_bytes = 0
    receipt_required = True
    output_digest_required = False
    read_only_required = False
    no_raw_shell = False
    mutation_requires_approval = False
    allowed_network_egress: set[str] = set()
    allowed_backend_classes: set[str] = set()
    control_ids: list[str] = []
    typed_execution_control_ids: list[str] = []

    for obligation in checked.obligations:
        if obligation.kind not in SUPPORTED_POLICY_OBLIGATIONS:
            raise GovApiError(f"unsupported_policy_obligation:{obligation.kind}")
        control_ids.append(obligation.obligation_id)
        if obligation.kind in {"receipt", "receipt_required"}:
            receipt_required = True
            typed_execution_control_ids.append("receipt_required")
        elif obligation.kind == "output_digest_required":
            output_digest_required = True
            typed_execution_control_ids.append("output_digest_required")

    for constraint in checked.constraints:
        if constraint.kind not in SUPPORTED_POLICY_CONSTRAINTS:
            raise GovApiError(f"unsupported_policy_constraint:{constraint.kind}")
        control_ids.append(constraint.constraint_id)
        if constraint.kind == "timeout":
            timeout_seconds = _minimum_positive_float(timeout_seconds, constraint.value)
        elif constraint.kind == "max_steps":
            max_steps = _minimum_positive_int(max_steps, constraint.value, "max_steps")
        elif constraint.kind == "output_limit":
            max_output_bytes = _minimum_positive_int(
                max_output_bytes,
                constraint.value,
                "output_limit",
            )
        elif constraint.kind == "receipt_required":
            if constraint.value is not True:
                raise GovApiError("invalid_policy_constraint:receipt_required")
            receipt_required = True
            typed_execution_control_ids.append("receipt_required")
        elif constraint.kind == "output_digest_required":
            if not isinstance(constraint.value, bool):
                raise GovApiError("invalid_policy_constraint:output_digest_required")
            output_digest_required = output_digest_required or constraint.value
            if constraint.value:
                typed_execution_control_ids.append("output_digest_required")
        elif constraint.kind == "read_only_required":
            if constraint.value is not True:
                raise GovApiError("invalid_policy_constraint:read_only_required")
            read_only_required = True
            typed_execution_control_ids.append("read_only_posture")
        elif constraint.kind == "no_raw_shell":
            if constraint.value is not True:
                raise GovApiError("invalid_policy_constraint:no_raw_shell")
            no_raw_shell = True
            typed_execution_control_ids.append("no_raw_shell")
        elif constraint.kind == "mutation_requires_approval":
            if constraint.value is not True:
                raise GovApiError("invalid_policy_constraint:mutation_requires_approval")
            mutation_requires_approval = True
            typed_execution_control_ids.append("mutation_requires_approval")
        elif constraint.kind == "allowed_network_egress":
            allowed_network_egress.update(
                _string_list(constraint.value, "allowed_network_egress")
            )
            typed_execution_control_ids.append("network_boundary_match")
        elif constraint.kind == "allowed_backend_classes":
            allowed_backend_classes.update(
                _string_list(constraint.value, "allowed_backend_classes")
            )
            typed_execution_control_ids.append("backend_class_supported")

    projection = RuntimeControlProjection(
        timeout_seconds=timeout_seconds,
        max_steps=max_steps,
        max_output_bytes=max_output_bytes,
        receipt_required=receipt_required,
        output_digest_required=output_digest_required,
        read_only_required=read_only_required,
        no_raw_shell=no_raw_shell,
        mutation_requires_approval=mutation_requires_approval,
        allowed_network_egress=tuple(sorted(allowed_network_egress)),
        allowed_backend_classes=tuple(sorted(allowed_backend_classes)),
        typed_execution_control_ids=tuple(sorted(set(typed_execution_control_ids))),
        control_ids=tuple(sorted(set(control_ids))),
    )
    _validate_projection(projection)
    return projection


def admit_policy_execution(
    policy_pack: CompiledPolicyPack,
    verdict: Mapping[str, Any] | PolicyVerdict,
) -> PolicyEnforcementPlan:
    policy_pack = _validated_compiled_policy_pack_snapshot(policy_pack)
    checked = validate_policy_verdict(verdict)
    blockers = list(checked.blockers)
    reason_code = checked.reason_code or checked.decision
    controls = RuntimeControlProjection()

    if checked.metadata.get("policy_pack") != policy_pack.policy_id:
        blockers.append("policy_verdict_pack_mismatch")
    if checked.metadata.get("policy_version") != policy_pack.version:
        blockers.append("policy_verdict_version_mismatch")
    if checked.decision not in {"allow", "allow_with_obligations"}:
        blockers.append(reason_code)
    else:
        try:
            controls = project_runtime_controls(checked)
        except GovApiError as exc:
            reason_code = exc.reason_code
            blockers.append(exc.reason_code)

    blockers_tuple = tuple(dict.fromkeys(item for item in blockers if item))
    status = "blocked" if blockers_tuple else "ready"
    if status == "ready":
        reason_code = "policy_controls_projected"
    plan = PolicyEnforcementPlan(
        plan_id=f"policy-enforcement:{checked.verdict_id}",
        subject_ref=checked.subject_ref,
        policy_pack_id=policy_pack.policy_id,
        policy_pack_version=policy_pack.version,
        policy_pack_digest=policy_pack_digest(policy_pack),
        verdict_id=checked.verdict_id,
        verdict_digest=policy_verdict_digest(checked),
        status=status,
        reason_code=reason_code,
        controls=controls,
        blockers=blockers_tuple,
    )
    _validate_plan_shape(plan)
    return plan


def validate_policy_enforcement_plan(
    plan: Mapping[str, Any] | PolicyEnforcementPlan,
    *,
    policy_pack: CompiledPolicyPack,
    verdict: Mapping[str, Any] | PolicyVerdict,
    require_allowed: bool = True,
) -> PolicyEnforcementPlan:
    checked = (
        plan
        if isinstance(plan, PolicyEnforcementPlan)
        else PolicyEnforcementPlan.from_mapping(plan)
    )
    expected = admit_policy_execution(policy_pack, verdict)
    if checked.as_dict() != expected.as_dict():
        raise GovApiError("policy_enforcement_plan_drift")
    if require_allowed and not checked.allowed:
        raise GovApiError(f"policy_enforcement_not_ready:{checked.reason_code}")
    return checked


def validate_policy_enforcement_admission(
    admission: Mapping[str, Any] | GovAdmissionDecision,
    *,
    plan: Mapping[str, Any] | PolicyEnforcementPlan,
) -> GovAdmissionDecision:
    checked = validate_admission_decision(admission)
    expected = policy_enforcement_admission(plan)
    if checked.as_dict() != expected.as_dict():
        raise GovApiError("policy_enforcement_admission_drift")
    return checked


def _validate_projection(item: RuntimeControlProjection) -> None:
    if (
        isinstance(item.timeout_seconds, bool)
        or not isinstance(item.timeout_seconds, (int, float))
        or not isfinite(item.timeout_seconds)
        or item.timeout_seconds < 0
    ):
        raise GovApiError("invalid_runtime_control_timeout")
    if (
        isinstance(item.max_steps, bool)
        or not isinstance(item.max_steps, int)
        or item.max_steps < 0
    ):
        raise GovApiError("invalid_runtime_control_max_steps")
    if (
        isinstance(item.max_output_bytes, bool)
        or not isinstance(item.max_output_bytes, int)
        or item.max_output_bytes < 0
    ):
        raise GovApiError("invalid_runtime_control_output_limit")
    if not isinstance(item.receipt_required, bool):
        raise GovApiError("invalid_runtime_control_receipt_required")
    if not all(
        isinstance(value, bool)
        for value in (
            item.output_digest_required,
            item.read_only_required,
            item.no_raw_shell,
            item.mutation_requires_approval,
        )
    ):
        raise GovApiError("invalid_runtime_control_boolean")
    for values, reason_code in (
        (item.allowed_network_egress, "invalid_runtime_control_allowed_network_egress"),
        (item.allowed_backend_classes, "invalid_runtime_control_allowed_backend_classes"),
        (
            item.typed_execution_control_ids,
            "invalid_runtime_control_typed_execution_control_ids",
        ),
        (item.control_ids, "invalid_runtime_control_ids"),
    ):
        text_tuple(values, reason_code)
    if not item.receipt_required:
        raise GovApiError("runtime_receipt_required")


def _validate_plan_shape(item: PolicyEnforcementPlan) -> None:
    if item.schema_version != POLICY_ENFORCEMENT_PLAN_SCHEMA_VERSION:
        raise GovApiError("unknown_policy_enforcement_plan_schema")
    for field_name in (
        "plan_id",
        "subject_ref",
        "policy_pack_id",
        "policy_pack_version",
        "policy_pack_digest",
        "verdict_id",
        "verdict_digest",
        "reason_code",
    ):
        if not getattr(item, field_name):
            raise GovApiError(f"missing_policy_enforcement_plan_{field_name}")
    if item.status not in POLICY_ENFORCEMENT_PLAN_STATUSES:
        raise GovApiError("unknown_policy_enforcement_plan_status")
    if item.status == "ready" and item.blockers:
        raise GovApiError("ready_policy_enforcement_plan_with_blockers")
    if item.status == "blocked" and not item.blockers:
        raise GovApiError("blocked_policy_enforcement_plan_without_blockers")
    for digest in (item.policy_pack_digest, item.verdict_digest):
        require_sha256_digest(digest, "invalid_policy_enforcement_plan_digest")


def _minimum_positive_float(current: float, value: Any) -> float:
    candidate = required_nonnegative_number(
        {"value": value},
        "value",
        "invalid_policy_constraint:timeout",
    )
    if candidate <= 0:
        raise GovApiError("invalid_policy_constraint:timeout")
    return candidate if current <= 0 else min(current, candidate)


def _minimum_positive_int(current: int, value: Any, kind: str) -> int:
    candidate = required_nonnegative_int(
        {"value": value},
        "value",
        f"invalid_policy_constraint:{kind}",
    )
    if candidate <= 0:
        raise GovApiError(f"invalid_policy_constraint:{kind}")
    return candidate if current <= 0 else min(current, candidate)


def _string_list(value: Any, kind: str) -> list[str]:
    items = list(text_tuple(value, f"invalid_policy_constraint:{kind}"))
    if not items:
        raise GovApiError(f"invalid_policy_constraint:{kind}")
    return items
