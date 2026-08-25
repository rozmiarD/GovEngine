from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
RC_VERSION = re.compile(r"^1\.0\.0rc(?P<candidate>[1-9][0-9]*)$")


def _load(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError(f"record_not_mapping:{path}")
    return value


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _candidate_identity(candidate_version: str) -> tuple[str, str, str]:
    match = RC_VERSION.fullmatch(candidate_version)
    if match is None:
        raise ValueError("candidate_version_invalid")
    label = f"rc{match.group('candidate')}"
    return (
        label,
        f"govengine.{label}_external_security_review.v1",
        f"docs/security-review/{label}-external-review.json",
    )


def _sha(value: object, field: str, *, label: str) -> None:
    if not isinstance(value, str) or not SHA256.fullmatch(value):
        raise ValueError(f"{label}_record_invalid_sha256:{field}")


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
    candidate_version: str = "1.0.0rc2",
) -> None:
    label, review_schema, review_record_path = _candidate_identity(candidate_version)
    if not FULL_SHA.fullmatch(source_commit):
        raise ValueError(f"{label}_source_commit_invalid")
    security, candidate = _load(review), _load(window)
    security_fields = {"schema_version", "source_commit", "artifacts", "confidential_report_sha256", "reviewer", "reviewed_at", "verdict", "open_p0", "open_p1"}
    if set(security) != security_fields:
        raise ValueError(f"{label}_security_review_fields_invalid")
    if security["schema_version"] != review_schema or security["source_commit"] != source_commit:
        raise ValueError(f"{label}_security_review_identity_invalid")
    artifacts = security["artifacts"]
    if not isinstance(artifacts, Mapping) or set(artifacts) != {"runner", "wheel_sha256", "normalized_sdist_sha256"} or artifacts["runner"] != "github-hosted-runner":
        raise ValueError(f"{label}_security_review_artifacts_invalid")
    if artifacts["wheel_sha256"] != _digest(wheel) or artifacts["normalized_sdist_sha256"] != _digest(sdist):
        raise ValueError(f"{label}_security_review_artifact_hash_mismatch")
    _sha(
        security["confidential_report_sha256"],
        "confidential_report_sha256",
        label=label,
    )
    if not isinstance(security["reviewer"], str) or not security["reviewer"].strip() or not _aware(security["reviewed_at"]):
        raise ValueError(f"{label}_security_review_reviewer_or_date_invalid")
    if not allow_synthetic and security["confidential_report_sha256"] == "0" * 64:
        raise ValueError(f"{label}_security_review_synthetic_report_rejected")
    if not allow_synthetic and security["reviewer"] == "synthetic-record-only-gate":
        raise ValueError(f"{label}_security_review_synthetic_reviewer_rejected")
    if security["verdict"] != "approved":
        raise ValueError(f"{label}_security_review_not_approved")
    if any(
        type(security[field]) is not int or security[field] != 0
        for field in ("open_p0", "open_p1")
    ):
        raise ValueError(f"{label}_security_review_open_counter_invalid")

    window_fields = {
        "schema_version", "status", "version", "source_commit", "prepared_at",
        "published_at", "observation_ends_at", "completed_at",
        "minimum_observation_days", "public_evidence_ref", "frozen_inputs",
        "security_review", "facade_exports", "v1_records", "rule", "notes",
    }
    if set(candidate) != window_fields:
        raise ValueError(f"{label}_window_fields_invalid")
    if (
        candidate["schema_version"] != "govengine.rc_window.v2"
        or candidate["status"] != "prepared"
        or candidate["version"] != candidate_version
        or candidate["source_commit"] != source_commit
    ):
        raise ValueError(f"{label}_window_identity_invalid")
    if (
        not _aware(candidate["prepared_at"])
        or any(candidate[field] is not None for field in ("published_at", "observation_ends_at", "completed_at"))
        or candidate["public_evidence_ref"] != ""
        or type(candidate["minimum_observation_days"]) is not int
        or candidate["minimum_observation_days"] != 7
        or type(candidate["facade_exports"]) is not int
        or candidate["facade_exports"] != 40
        or type(candidate["v1_records"]) is not int
        or candidate["v1_records"] != 15
        or candidate["rule"] != "schema_facade_corpus_or_reason_registry_change_requires_new_rc"
        or not isinstance(candidate["notes"], str)
        or not candidate["notes"].strip()
    ):
        raise ValueError(f"{label}_window_prepared_lifecycle_invalid")
    frozen = candidate["frozen_inputs"]
    expected_frozen = {
        "pyproject_sha256",
        "v1_compatibility_manifest_sha256",
        "v1_conformance_manifest_sha256",
        "policy_reason_registry_sha256",
    }
    if not isinstance(frozen, Mapping) or set(frozen) != expected_frozen:
        raise ValueError(f"{label}_window_frozen_inputs_invalid")
    for field, value in frozen.items():
        _sha(value, field, label=label)
    frozen_paths = {
        "pyproject_sha256": ROOT / "pyproject.toml",
        "v1_compatibility_manifest_sha256": ROOT / "govengine/v1_compatibility_manifest.json",
        "v1_conformance_manifest_sha256": ROOT / "govengine/conformance/v1/manifest.json",
        "policy_reason_registry_sha256": ROOT / "govengine/policy/reasons.py",
    }
    if any(frozen[field] != _digest(path) for field, path in frozen_paths.items()):
        raise ValueError(f"{label}_window_frozen_input_hash_mismatch")
    reference = candidate["security_review"]
    if not isinstance(reference, Mapping) or set(reference) != {"path", "sha256"} or reference["path"] != review_record_path or reference["sha256"] != _digest(review):
        raise ValueError(f"{label}_window_security_binding_invalid")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--window", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--sdist", type=Path, required=True)
    parser.add_argument("--allow-synthetic", action="store_true")
    parser.add_argument("--candidate-version", default="1.0.0rc2")
    args = parser.parse_args()
    try:
        validate_rc2_release_records(
            review=args.review,
            window=args.window,
            source_commit=args.source_commit,
            wheel=args.wheel,
            sdist=args.sdist,
            allow_synthetic=args.allow_synthetic,
            candidate_version=args.candidate_version,
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"candidate_release_records_invalid:{error}")
        return 1
    print(
        f"candidate_release_records_ok:{args.candidate_version}:"
        f"{args.source_commit}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
