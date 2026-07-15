from __future__ import annotations

from contextlib import contextmanager

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


def test_api_error_separates_dynamic_detail_from_reason_code() -> None:
    err = GovApiError('unknown_control_action:operator-supplied-value')

    assert err.reason_code == 'unknown_control_action'
    assert err.context == {'detail': 'operator-supplied-value'}
    assert err.as_dict()['reason_code'] == 'unknown_control_action'
    assert str(err) == 'unknown_control_action:operator-supplied-value'


def test_api_error_bounds_dynamic_detail_and_context() -> None:
    err = GovApiError(
        'invalid_boundary:' + ('x' * 1024),
        context={'nested': {'values': ['y' * 1024] * 64}},
    )

    payload = err.as_dict()
    assert payload['reason_code'] == 'invalid_boundary'
    assert len(payload['context']['detail']) <= 256
    assert len(payload['context']['nested']['values']) <= 32
    assert len(payload['context']['nested']['values'][0]) <= 256


def test_api_error_propagates_through_context_managers_without_masking() -> None:
    @contextmanager
    def passthrough():
        yield

    with pytest.raises(GovApiError, match='boundary_failed'):
        with passthrough():
            raise GovApiError('boundary_failed')


def test_require_mapping_rejects_unstable_inputs() -> None:
    with pytest.raises(GovApiError, match="invalid_contract"):
        require_mapping(["not", "mapping"], reason_code="invalid_contract")
