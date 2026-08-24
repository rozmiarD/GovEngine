from __future__ import annotations

from math import inf, nan

import pytest

from govengine.api import GovApiError
from govengine.signing import canonical_govengine_record


RECORD_TYPE = "govengine.admission.RuntimeAdmissionResult"


@pytest.mark.parametrize(
    "value",
    [
        2**53,
        -(2**53),
    ],
)
def test_v1_rejects_unsafe_integers_with_a_typed_reason(value: int) -> None:
    with pytest.raises(GovApiError) as exc_info:
        canonical_govengine_record({"nested": [value]}, record_type=RECORD_TYPE)

    assert exc_info.value.reason_code == "unsupported_govengine_record_unsafe_integer"


def test_v1_rejects_unsafe_integer_subclass_with_overridden_abs() -> None:
    class UnsafeInteger(int):
        def __abs__(self) -> int:
            return 0

    with pytest.raises(GovApiError) as exc_info:
        canonical_govengine_record({"number": UnsafeInteger(2**53)}, record_type=RECORD_TYPE)

    assert exc_info.value.reason_code == "unsupported_govengine_record_unsafe_integer"


@pytest.mark.parametrize("value", [inf, nan])
def test_v1_retains_non_finite_rejection_with_a_typed_reason(value: float) -> None:
    with pytest.raises(GovApiError) as exc_info:
        canonical_govengine_record({"number": value}, record_type=RECORD_TYPE)

    assert exc_info.value.reason_code == "unsupported_govengine_record_value"


@pytest.mark.parametrize("value", [(2**53) - 1, -((2**53) - 1), True])
def test_v1_accepts_safe_integers_and_booleans(value: int | bool) -> None:
    canonical = canonical_govengine_record({"number": value}, record_type=RECORD_TYPE)

    assert '"number":' in canonical
