from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any


def build_scope_decision(
    *,
    admission: Mapping[str, Any],
    operation_id: str,
    target: str,
    target_host: str,
    in_scope: bool | None,
) -> dict[str, Any]:
    admission_id = str(
        admission.get("admission_id")
        or (admission.get("details") or {}).get("admission_id")
        or operation_id
    )
    return {
        "artifact_type": "govengine_scope_decision",
        "schema_version": "v0.1",
        "decision_ref": f"govengine-scope:{admission_id}",
        "status": "in_scope" if in_scope is True else "out_of_scope" if in_scope is False else "unknown",
        "authority": "govengine",
        "subject": {"operation_id": operation_id},
        "target": {"target": target, "target_host": target_host},
    }


def scope_decision_digest(decision: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        dict(decision),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def build_scope_assertion(decision: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": str(decision.get("status") or "unknown"),
        "authority": str(decision.get("authority") or ""),
        "decision_ref": str(decision.get("decision_ref") or ""),
        "decision_digest": scope_decision_digest(decision),
        "subject": dict(decision.get("subject") or {}),
        "target": dict(decision.get("target") or {}),
    }
