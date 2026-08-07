from __future__ import annotations

from dataclasses import asdict, dataclass, field
from math import isfinite
from string import hexdigits
from typing import Any, Mapping

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
        raw = require_mapping(value or {}, reason_code="invalid_runtime_control_projection")
        item = cls(
            timeout_seconds=float(raw.get("timeout_seconds") or 0.0),
            max_steps=int(raw.get("max_steps") or 0),
            max_output_bytes=int(raw.get("max_output_bytes") or 0),
            receipt_required=bool(raw.get("receipt_required", True)),
            output_digest_required=bool(raw.get("output_digest_required", False)),
            read_only_required=bool(raw.get("read_only_required", False)),
            no_raw_shell=bool(raw.get("no_raw_shell", False)),
            mutation_requires_approval=bool(raw.get("mutation_requires_approval", False)),
            allowed_network_egress=_string_tuple(raw.get("allowed_network_egress") or ()),
            allowed_backend_classes=_string_tuple(raw.get("allowed_backend_classes") or ()),
            typed_execution_control_ids=_string_tuple(
                raw.get("typed_execution_control_ids") or ()
            ),
            control_ids=_string_tuple(raw.get("control_ids") or ()),
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
        item = cls(
            plan_id=str(raw.get("plan_id") or "").strip(),
            subject_ref=str(raw.get("subject_ref") or "").strip(),
            policy_pack_id=str(raw.get("policy_pack_id") or "").strip(),
            policy_pack_version=str(raw.get("policy_pack_version") or "").strip(),
            policy_pack_digest=str(raw.get("policy_pack_digest") or "").strip(),
            verdict_id=str(raw.get("verdict_id") or "").strip(),
            verdict_digest=str(raw.get("verdict_digest") or "").strip(),
            status=str(raw.get("status") or "").strip(),
            reason_code=str(raw.get("reason_code") or "").strip(),
            schema_version=str(raw.get("schema_version") or "").strip(),
            controls=RuntimeControlProjection.from_mapping(
                controls if isinstance(controls, Mapping) else {}
            ),
            blockers=_string_tuple(raw.get("blockers") or ()),
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
    if not isfinite(item.timeout_seconds) or item.timeout_seconds < 0:
        raise GovApiError("invalid_runtime_control_timeout")
    if item.max_steps < 0:
        raise GovApiError("invalid_runtime_control_max_steps")
    if item.max_output_bytes < 0:
        raise GovApiError("invalid_runtime_control_output_limit")
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
        if not _is_sha256_reference(digest):
            raise GovApiError("invalid_policy_enforcement_plan_digest")


def _minimum_positive_float(current: float, value: Any) -> float:
    try:
        candidate = float(value)
    except (TypeError, ValueError) as exc:
        raise GovApiError("invalid_policy_constraint:timeout") from exc
    if not isfinite(candidate) or candidate <= 0:
        raise GovApiError("invalid_policy_constraint:timeout")
    return candidate if current <= 0 else min(current, candidate)


def _minimum_positive_int(current: int, value: Any, kind: str) -> int:
    if isinstance(value, bool):
        raise GovApiError(f"invalid_policy_constraint:{kind}")
    try:
        candidate = int(value)
    except (TypeError, ValueError) as exc:
        raise GovApiError(f"invalid_policy_constraint:{kind}") from exc
    if candidate <= 0 or candidate != value:
        raise GovApiError(f"invalid_policy_constraint:{kind}")
    return candidate if current <= 0 else min(current, candidate)


def _string_list(value: Any, kind: str) -> list[str]:
    if not isinstance(value, (list, tuple, set)):
        raise GovApiError(f"invalid_policy_constraint:{kind}")
    items = [str(item).strip() for item in value if str(item).strip()]
    if not items:
        raise GovApiError(f"invalid_policy_constraint:{kind}")
    return items


def _string_tuple(value: Any) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)):
        return (str(value),) if str(value) else ()
    if not isinstance(value, (list, tuple, set)):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())


def _is_sha256_reference(value: str) -> bool:
    prefix, separator, digest = value.partition(":")
    return (
        separator == ":"
        and prefix == "sha256"
        and len(digest) == 64
        and all(char in hexdigits for char in digest)
    )
