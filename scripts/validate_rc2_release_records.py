from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
REVIEW_RECORD_PATH = "docs/security-review/rc2-external-review.json"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _load(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError(f"record_not_mapping:{path}")
    return value


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha(value: object, field: str) -> None:
    if not isinstance(value, str) or not SHA256.fullmatch(value):
        raise ValueError(f"rc2_record_invalid_sha256:{field}")


def _aware(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def validate_rc2_release_records(
    *,
    review: Path,
    window: Path,
    source_commit: str,
    wheel: Path,
    sdist: Path,
    allow_synthetic: bool = False,
) -> None:
    if not FULL_SHA.fullmatch(source_commit):
        raise ValueError("rc2_source_commit_invalid")
    security, candidate = _load(review), _load(window)
    security_fields = {"schema_version", "source_commit", "artifacts", "confidential_report_sha256", "reviewer", "reviewed_at", "verdict", "open_p0", "open_p1"}
    if set(security) != security_fields:
        raise ValueError("rc2_security_review_fields_invalid")
    if security["schema_version"] != "govengine.rc2_external_security_review.v1" or security["source_commit"] != source_commit:
        raise ValueError("rc2_security_review_identity_invalid")
    artifacts = security["artifacts"]
    if not isinstance(artifacts, Mapping) or set(artifacts) != {"runner", "wheel_sha256", "normalized_sdist_sha256"} or artifacts["runner"] != "github-hosted-runner":
        raise ValueError("rc2_security_review_artifacts_invalid")
    if artifacts["wheel_sha256"] != _digest(wheel) or artifacts["normalized_sdist_sha256"] != _digest(sdist):
        raise ValueError("rc2_security_review_artifact_hash_mismatch")
    _sha(security["confidential_report_sha256"], "confidential_report_sha256")
    if not isinstance(security["reviewer"], str) or not security["reviewer"].strip() or not _aware(security["reviewed_at"]):
        raise ValueError("rc2_security_review_reviewer_or_date_invalid")
    if not allow_synthetic and security["confidential_report_sha256"] == "0" * 64:
        raise ValueError("rc2_security_review_synthetic_report_rejected")
    if not allow_synthetic and security["reviewer"] == "synthetic-record-only-gate":
        raise ValueError("rc2_security_review_synthetic_reviewer_rejected")
    if security["verdict"] != "approved":
        raise ValueError("rc2_security_review_not_approved")
    if any(
        type(security[field]) is not int or security[field] != 0
        for field in ("open_p0", "open_p1")
    ):
        raise ValueError("rc2_security_review_open_counter_invalid")

    window_fields = {"schema_version", "status", "source_commit", "frozen_inputs", "security_review"}
    if set(candidate) != window_fields:
        raise ValueError("rc2_window_fields_invalid")
    if candidate["schema_version"] != "govengine.rc2_window.v1" or candidate["status"] != "prepared" or candidate["source_commit"] != source_commit:
        raise ValueError("rc2_window_identity_invalid")
    frozen = candidate["frozen_inputs"]
    expected_frozen = {
        "pyproject_sha256",
        "v1_compatibility_manifest_sha256",
        "v1_conformance_manifest_sha256",
        "policy_reason_registry_sha256",
    }
    if not isinstance(frozen, Mapping) or set(frozen) != expected_frozen:
        raise ValueError("rc2_window_frozen_inputs_invalid")
    for field, value in frozen.items():
        _sha(value, field)
    frozen_paths = {
        "pyproject_sha256": ROOT / "pyproject.toml",
        "v1_compatibility_manifest_sha256": ROOT / "govengine/v1_compatibility_manifest.json",
        "v1_conformance_manifest_sha256": ROOT / "govengine/conformance/v1/manifest.json",
        "policy_reason_registry_sha256": ROOT / "govengine/policy/reasons.py",
    }
    if any(frozen[field] != _digest(path) for field, path in frozen_paths.items()):
        raise ValueError("rc2_window_frozen_input_hash_mismatch")
    reference = candidate["security_review"]
    if not isinstance(reference, Mapping) or set(reference) != {"path", "sha256"} or reference["path"] != REVIEW_RECORD_PATH or reference["sha256"] != _digest(review):
        raise ValueError("rc2_window_security_binding_invalid")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--window", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--sdist", type=Path, required=True)
    parser.add_argument("--allow-synthetic", action="store_true")
    args = parser.parse_args()
    try:
        validate_rc2_release_records(
            review=args.review,
            window=args.window,
            source_commit=args.source_commit,
            wheel=args.wheel,
            sdist=args.sdist,
            allow_synthetic=args.allow_synthetic,
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"rc2_release_records_invalid:{error}")
        return 1
    print(f"rc2_release_records_ok:{args.source_commit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
