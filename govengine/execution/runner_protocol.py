from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Protocol, Sequence

from govengine.api import GovApiError, require_mapping
from govengine.execution.approved_spec import approved_execution_steps

FORBIDDEN_RECEIPT_BINDING_KEYS = {
    "command",
    "commands",
    "credential",
    "credentials",
    "api_key",
    "passphrase",
    "password",
    "private_key",
    "prompt",
    "raw_output",
    "raw_stderr",
    "raw_stdout",
    "secret",
    "stderr",
    "stdout",
    "target",
    "target_url",
    "token",
    "url",
}


@dataclass(frozen=True)
class GovRunnerStep:
    """A normalized, carrier-neutral execution step."""

    index: int
    tool: str
    args: tuple[str, ...] = ()
    stdin: str = ""

    def as_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["args"] = list(self.args)
        return out


@dataclass(frozen=True)
class GovRunnerRequest:
    """The bounded request a host runner may execute or dry-run."""

    request_id: str
    source: str
    steps: tuple[GovRunnerStep, ...]
    approved_execution_spec: Mapping[str, Any] = field(default_factory=dict)
    execution_ticket_gate: Mapping[str, Any] = field(default_factory=dict)
    dry_run: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "source": self.source,
            "steps": [step.as_dict() for step in self.steps],
            "approved_execution_spec": dict(self.approved_execution_spec),
            "execution_ticket_gate": dict(self.execution_ticket_gate),
            "dry_run": self.dry_run,
        }


@dataclass(frozen=True)
class GovRunnerStepResult:
    index: int
    status: str
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""
    reason_code: str = "ok"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GovRunnerReceiptBinding:
    """Bounded admission/ticket/request references for a runner receipt.

    This is a reference envelope only. GovEngine does not store raw evidence,
    own SCLite ticket canonicalization, or grant live execution authority.
    """

    admission_id: str = ""
    admission_digest: str = ""
    ticket_id: str = ""
    ticket_digest: str = ""
    request_id: str = ""
    request_digest: str = ""
    receipt_id: str = ""
    receipt_digest: str = ""
    runner_profile: str = ""
    output_digests: Mapping[str, str] = field(default_factory=dict)
    evidence_refs: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "admission_id", _clean_text(self.admission_id))
        object.__setattr__(self, "admission_digest", _clean_text(self.admission_digest))
        object.__setattr__(self, "ticket_id", _clean_text(self.ticket_id))
        object.__setattr__(self, "ticket_digest", _clean_text(self.ticket_digest))
        object.__setattr__(self, "request_id", _clean_text(self.request_id))
        object.__setattr__(self, "request_digest", _clean_text(self.request_digest))
        object.__setattr__(self, "receipt_id", _clean_text(self.receipt_id))
        object.__setattr__(self, "receipt_digest", _clean_text(self.receipt_digest))
        object.__setattr__(self, "runner_profile", _clean_text(self.runner_profile))
        object.__setattr__(
            self,
            "output_digests",
            _bounded_string_mapping(self.output_digests, allow_output_stream_keys=True),
        )
        object.__setattr__(self, "evidence_refs", _bounded_string_mapping(self.evidence_refs))

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any] | None) -> "GovRunnerReceiptBinding":
        if value is None:
            return cls()
        raw = require_mapping(value, reason_code="invalid_runner_receipt_binding")
        _reject_forbidden_binding(raw)
        return cls(
            admission_id=raw.get("admission_id") or "",
            admission_digest=raw.get("admission_digest") or "",
            ticket_id=raw.get("ticket_id") or "",
            ticket_digest=raw.get("ticket_digest") or "",
            request_id=raw.get("request_id") or "",
            request_digest=raw.get("request_digest") or "",
            receipt_id=raw.get("receipt_id") or "",
            receipt_digest=raw.get("receipt_digest") or "",
            runner_profile=raw.get("runner_profile") or "",
            output_digests=raw.get("output_digests") if isinstance(raw.get("output_digests"), Mapping) else {},
            evidence_refs=raw.get("evidence_refs") if isinstance(raw.get("evidence_refs"), Mapping) else {},
        )

    @property
    def present(self) -> bool:
        return any((
            self.admission_id,
            self.admission_digest,
            self.ticket_id,
            self.ticket_digest,
            self.request_id,
            self.request_digest,
            self.receipt_id,
            self.receipt_digest,
            self.runner_profile,
            bool(self.output_digests),
            bool(self.evidence_refs),
        ))

    def as_dict(self) -> dict[str, Any]:
        return {
            "admission_id": self.admission_id,
            "admission_digest": self.admission_digest,
            "ticket_id": self.ticket_id,
            "ticket_digest": self.ticket_digest,
            "request_id": self.request_id,
            "request_digest": self.request_digest,
            "receipt_id": self.receipt_id,
            "receipt_digest": self.receipt_digest,
            "runner_profile": self.runner_profile,
            "output_digests": dict(self.output_digests),
            "evidence_refs": dict(self.evidence_refs),
        }


@dataclass(frozen=True)
class GovRunnerReceipt:
    status: str
    request_id: str
    source: str
    step_results: tuple[GovRunnerStepResult, ...] = ()
    reason_code: str = "ok"
    control_decisions: tuple[Mapping[str, Any], ...] = ()
    binding: GovRunnerReceiptBinding | Mapping[str, Any] = field(default_factory=GovRunnerReceiptBinding)

    def __post_init__(self) -> None:
        binding = self.binding if isinstance(self.binding, GovRunnerReceiptBinding) else GovRunnerReceiptBinding.from_mapping(self.binding)
        object.__setattr__(self, "binding", binding)

    def as_dict(self) -> dict[str, Any]:
        out = {
            "status": self.status,
            "request_id": self.request_id,
            "source": self.source,
            "reason_code": self.reason_code,
            "step_results": [result.as_dict() for result in self.step_results],
            "control_decisions": [dict(decision) for decision in self.control_decisions],
        }
        if self.binding.present:
            out["binding"] = self.binding.as_dict()
        return out


class GovRunner(Protocol):
    """Host-provided runner port.

    GovEngine prepares and validates the request shape. The host owns concrete
    IO/subprocess behavior and must honor returned control decisions.
    """

    def run(self, request: GovRunnerRequest) -> GovRunnerReceipt:
        ...


def normalize_runner_steps(raw_steps: Sequence[Mapping[str, Any]]) -> tuple[GovRunnerStep, ...]:
    steps: list[GovRunnerStep] = []
    for idx, raw_step in enumerate(raw_steps):
        if not isinstance(raw_step, Mapping):
            raise GovApiError("invalid_runner_step", f"index={idx}")
        tool = str(raw_step.get("tool") or "").strip()
        if not tool:
            raise GovApiError("missing_runner_step_tool", f"index={idx}")
        raw_args = raw_step.get("args") or []
        if not isinstance(raw_args, Sequence) or isinstance(raw_args, (str, bytes)):
            raise GovApiError("invalid_runner_step_args", f"index={idx}")
        steps.append(GovRunnerStep(
            index=idx,
            tool=tool,
            args=tuple(str(arg) for arg in raw_args),
            stdin=str(raw_step.get("stdin") or ""),
        ))
    if not steps:
        raise GovApiError("missing_runner_steps")
    return tuple(steps)


def runner_request_from_approved_spec(
    approved_execution_spec: Mapping[str, Any],
    *,
    request_id: str = "approved-spec-request",
    execution_ticket_gate: Mapping[str, Any] | None = None,
    dry_run: bool = True,
) -> GovRunnerRequest:
    raw_steps = approved_execution_steps(dict(approved_execution_spec))
    return GovRunnerRequest(
        request_id=str(request_id or "approved-spec-request"),
        source="approved_execution_spec",
        steps=normalize_runner_steps(raw_steps),
        approved_execution_spec=dict(approved_execution_spec),
        execution_ticket_gate=dict(execution_ticket_gate or {"status": "not_required"}),
        dry_run=bool(dry_run),
    )


def dry_run_runner_receipt(
    request: GovRunnerRequest,
    *,
    binding: GovRunnerReceiptBinding | Mapping[str, Any] | None = None,
) -> GovRunnerReceipt:
    return GovRunnerReceipt(
        status="dry-run",
        request_id=request.request_id,
        source=request.source,
        step_results=tuple(
            GovRunnerStepResult(index=step.index, status="dry-run", reason_code="dry_run_requested")
            for step in request.steps
        ),
        reason_code="dry_run_requested",
        binding=binding or GovRunnerReceiptBinding(),
    )


def runner_receipt_with_binding(
    receipt: GovRunnerReceipt,
    *,
    admission_id: str,
    admission_digest: str = "",
    ticket_id: str,
    ticket_digest: str = "",
    request_digest: str = "",
    receipt_id: str = "",
    receipt_digest: str = "",
    runner_profile: str = "",
    output_digests: Mapping[str, str] | None = None,
    evidence_refs: Mapping[str, str] | None = None,
) -> GovRunnerReceipt:
    """Return a copy of a runner receipt with bounded binding references."""

    return GovRunnerReceipt(
        status=receipt.status,
        request_id=receipt.request_id,
        source=receipt.source,
        step_results=receipt.step_results,
        reason_code=receipt.reason_code,
        control_decisions=receipt.control_decisions,
        binding=GovRunnerReceiptBinding(
            admission_id=admission_id,
            admission_digest=admission_digest,
            ticket_id=ticket_id,
            ticket_digest=ticket_digest,
            request_id=receipt.request_id,
            request_digest=request_digest,
            receipt_id=receipt_id,
            receipt_digest=receipt_digest,
            runner_profile=runner_profile,
            output_digests=output_digests or {},
            evidence_refs=evidence_refs or {},
        ),
    )


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _bounded_string_mapping(
    value: Mapping[str, Any] | None,
    *,
    allow_output_stream_keys: bool = False,
) -> dict[str, str]:
    raw = value if isinstance(value, Mapping) else {}
    _reject_forbidden_binding(raw, allow_output_stream_keys=allow_output_stream_keys)
    return {str(key): _clean_binding_ref(item) for key, item in raw.items()}


def _reject_forbidden_binding(
    value: Mapping[str, Any],
    *,
    allow_output_stream_keys: bool = False,
) -> None:
    forbidden = set(FORBIDDEN_RECEIPT_BINDING_KEYS)
    if allow_output_stream_keys:
        forbidden -= {"stderr", "stdout"}
    for key in value:
        if str(key).lower() in forbidden:
            raise GovApiError(f"forbidden_runner_receipt_binding:{key}")


def _clean_binding_ref(value: Any) -> str:
    if isinstance(value, Mapping) or isinstance(value, (list, tuple, set)):
        raise GovApiError("invalid_runner_receipt_binding_ref")
    return _clean_text(value)
