#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
repo_root="$(pwd)"
python_bin="${PYTHON:-python3}"
work="$(mktemp -d)"
cleanup() { rm -rf "$work"; }
trap cleanup EXIT
export SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-1704067200}"

git clone --quiet --no-local "$repo_root" "$work/repo"
cd "$work/repo"
source_commit="$(git rev-parse HEAD)"
PYTHON="$python_bin" bash scripts/build_release_artifacts.sh --outdir "$work/reviewed"
mkdir -p docs/security-review docs/rc-window
wheel_sha="$(sha256sum "$work"/reviewed/*.whl | cut -d' ' -f1)"
sdist_sha="$(sha256sum "$work"/reviewed/*.tar.gz | cut -d' ' -f1)"
pyproject_sha="$(sha256sum pyproject.toml | cut -d' ' -f1)"
compat_sha="$(sha256sum govengine/v1_compatibility_manifest.json | cut -d' ' -f1)"
corpus_sha="$(sha256sum govengine/conformance/v1/manifest.json | cut -d' ' -f1)"
reason_registry_sha="$(sha256sum govengine/policy/reasons.py | cut -d' ' -f1)"
"$python_bin" - "$source_commit" "$wheel_sha" "$sdist_sha" "$pyproject_sha" "$compat_sha" "$corpus_sha" "$reason_registry_sha" <<'PY'
import hashlib, json, sys
from pathlib import Path
source, wheel, sdist, pyproject, compatibility, corpus, reason_registry = sys.argv[1:]
review_path = Path("docs/security-review/rc2-external-review.json")
window_path = Path("docs/rc-window/1.0.0rc2.json")
pending_review = json.loads(review_path.read_text(encoding="utf-8"))
if pending_review.get("verdict") != "pending_external_reviewer":
    raise SystemExit("source A must contain the seeded pending external-review form")
if window_path.exists():
    raise SystemExit("source A must not contain the rc2 window record")
review = {"schema_version": "govengine.rc2_external_security_review.v1", "source_commit": source, "artifacts": {"runner": "github-hosted-runner", "wheel_sha256": wheel, "normalized_sdist_sha256": sdist}, "confidential_report_sha256": "0" * 64, "reviewer": "synthetic-record-only-gate", "reviewed_at": "2026-01-01T00:00:00Z", "verdict": "approved", "open_p0": 0, "open_p1": 0}
review_path.write_text(json.dumps(review, sort_keys=True) + "\n", encoding="utf-8")
window = {"schema_version": "govengine.rc_window.v2", "status": "prepared", "version": "1.0.0rc2", "source_commit": source, "prepared_at": "2026-01-01T00:00:00Z", "published_at": None, "observation_ends_at": None, "completed_at": None, "minimum_observation_days": 7, "public_evidence_ref": "", "frozen_inputs": {"pyproject_sha256": pyproject, "v1_compatibility_manifest_sha256": compatibility, "v1_conformance_manifest_sha256": corpus, "policy_reason_registry_sha256": reason_registry}, "security_review": {"path": str(review_path), "sha256": hashlib.sha256(review_path.read_bytes()).hexdigest()}, "facade_exports": 40, "v1_records": 15, "rule": "schema_facade_corpus_or_reason_registry_change_requires_new_rc", "notes": "Synthetic record-only gate."}
window_path.write_text(json.dumps(window, sort_keys=True) + "\n", encoding="utf-8")
PY
git config user.name "GovEngine release gate"
git config user.email "release-gate@example.invalid"
git add docs/security-review/rc2-external-review.json docs/rc-window/1.0.0rc2.json
git commit --quiet -m "Synthetic record-only A/B gate child"
test "$("$python_bin" scripts/validate_release_record_commit.py --review-commit HEAD)" = "$source_commit"
"$python_bin" scripts/validate_rc2_release_records.py --allow-synthetic --review docs/security-review/rc2-external-review.json --window docs/rc-window/1.0.0rc2.json --source-commit "$source_commit" --wheel "$work"/reviewed/*.whl --sdist "$work"/reviewed/*.tar.gz
PYTHON="$python_bin" bash scripts/build_release_artifacts.sh --outdir "$work/published"
"$python_bin" scripts/compare_release_builds.py --reviewed "$work/reviewed" --published "$work/published"
