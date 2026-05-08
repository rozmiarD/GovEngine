from __future__ import annotations

import pytest

from govengine.api import GovApiError, GovApiResult, require_mapping


def test_api_result_has_stable_envelope() -> None:
    result = GovApiResult(status="allowed", reason_code="ok", data={"decision": "allow"}, warnings=("bounded",))

    assert result.ok is True
    assert result.as_dict() == {
        "status": "allowed",
        "ok": True,
        "reason_code": "ok",
        "data": {"decision": "allow"},
        "warnings": ["bounded"],
    }


def test_api_error_is_structured() -> None:
    err = GovApiError("missing_ticket", "ticket required", {"request_id": "r1"})

    assert str(err) == "missing_ticket:ticket required"
    assert err.as_dict() == {
        "reason_code": "missing_ticket",
        "message": "ticket required",
        "context": {"request_id": "r1"},
    }


def test_require_mapping_rejects_unstable_inputs() -> None:
    with pytest.raises(GovApiError, match="invalid_contract"):
        require_mapping(["not", "mapping"], reason_code="invalid_contract")
