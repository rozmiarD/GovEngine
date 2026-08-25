#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
repo_root="$(pwd)"
python_bin="${PYTHON:-python3}"
if [[ "$python_bin" == */* && "$python_bin" != /* ]]; then
  python_bin="$repo_root/$python_bin"
fi
work="$(mktemp -d)"
cleanup() { rm -rf "$work"; }
trap cleanup EXIT
export SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-1704067200}"
candidate_version="$($python_bin -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])')"
candidate_number="${candidate_version##*rc}"
candidate_label="rc${candidate_number}"
review_relative="docs/security-review/${candidate_label}-external-review.json"
window_relative="docs/rc-window/${candidate_version}.json"

git clone --quiet --no-local "$repo_root" "$work/repo"
git -C "$repo_root" diff --binary --no-ext-diff HEAD -- | \
  git -C "$work/repo" apply --binary
while IFS= read -r -d '' relative; do
  mkdir -p "$work/repo/$(dirname "$relative")"
  cp "$repo_root/$relative" "$work/repo/$relative"
done < <(git -C "$repo_root" ls-files --others --exclude-standard -z)
cd "$work/repo"
if ! git diff --quiet || [ -n "$(git ls-files --others --exclude-standard)" ]; then
  git config user.name "GovEngine release gate"
  git config user.email "release-gate@example.invalid"
  git add --all
  git commit --quiet -m "Synthetic source-A snapshot from current worktree"
fi
IFS=$'\t' read -r gate_mode source_commit record_commit < <(
  "$python_bin" scripts/validate_release_record_commit.py \
    --resolve-ab-state --candidate-version "$candidate_version"
)

if [ "$gate_mode" = "synthetic" ]; then
  PYTHON="$python_bin" bash scripts/build_release_artifacts.sh --outdir "$work/reviewed"
  mkdir -p docs/security-review docs/rc-window
  wheel_sha="$(sha256sum "$work"/reviewed/*.whl | cut -d' ' -f1)"
  sdist_sha="$(sha256sum "$work"/reviewed/*.tar.gz | cut -d' ' -f1)"
  pyproject_sha="$(sha256sum pyproject.toml | cut -d' ' -f1)"
  compat_sha="$(sha256sum govengine/v1_compatibility_manifest.json | cut -d' ' -f1)"
  corpus_sha="$(sha256sum govengine/conformance/v1/manifest.json | cut -d' ' -f1)"
  reason_registry_sha="$(sha256sum govengine/policy/reasons.py | cut -d' ' -f1)"
  "$python_bin" - "$candidate_version" "$source_commit" "$wheel_sha" "$sdist_sha" "$pyproject_sha" "$compat_sha" "$corpus_sha" "$reason_registry_sha" <<'PY'
import hashlib, json, sys
from pathlib import Path
version, source, wheel, sdist, pyproject, compatibility, corpus, reason_registry = sys.argv[1:]
label = "rc" + version.rsplit("rc", 1)[1]
review_path = Path(f"docs/security-review/{label}-external-review.json")
window_path = Path(f"docs/rc-window/{version}.json")
pending_review = json.loads(review_path.read_text(encoding="utf-8"))
if pending_review.get("verdict") != "pending_external_reviewer":
    raise SystemExit("source A must contain the seeded pending external-review form")
if window_path.exists():
    pending_window = json.loads(window_path.read_text(encoding="utf-8"))
    if pending_window.get("status") != "pending_review":
        raise SystemExit("source A candidate record must remain pending_review")
review = {"schema_version": f"govengine.{label}_external_security_review.v1", "source_commit": source, "artifacts": {"runner": "github-hosted-runner", "wheel_sha256": wheel, "normalized_sdist_sha256": sdist}, "confidential_report_sha256": "0" * 64, "reviewer": "synthetic-record-only-gate", "reviewed_at": "2026-01-01T00:00:00Z", "verdict": "approved", "open_p0": 0, "open_p1": 0}
review_path.write_text(json.dumps(review, sort_keys=True) + "\n", encoding="utf-8")
window = {"schema_version": "govengine.rc_window.v2", "status": "prepared", "version": version, "source_commit": source, "prepared_at": "2026-01-01T00:00:00Z", "published_at": None, "observation_ends_at": None, "completed_at": None, "minimum_observation_days": 7, "public_evidence_ref": "", "frozen_inputs": {"pyproject_sha256": pyproject, "v1_compatibility_manifest_sha256": compatibility, "v1_conformance_manifest_sha256": corpus, "policy_reason_registry_sha256": reason_registry}, "security_review": {"path": str(review_path), "sha256": hashlib.sha256(review_path.read_bytes()).hexdigest()}, "facade_exports": 40, "v1_records": 15, "rule": "schema_facade_corpus_or_reason_registry_change_requires_new_rc", "notes": "Synthetic record-only gate."}
window_path.write_text(json.dumps(window, sort_keys=True) + "\n", encoding="utf-8")
PY
  git config user.name "GovEngine release gate"
  git config user.email "release-gate@example.invalid"
  git add "$review_relative" "$window_relative"
  git commit --quiet -m "Synthetic record-only A/B gate child"
  test "$("$python_bin" scripts/validate_release_record_commit.py --review-commit HEAD --candidate-version "$candidate_version")" = "$source_commit"
  "$python_bin" scripts/validate_rc2_release_records.py \
    --allow-synthetic \
    --candidate-version "$candidate_version" \
    --review "$review_relative" \
    --window "$window_relative" \
    --source-commit "$source_commit" \
    --wheel "$work"/reviewed/*.whl \
    --sdist "$work"/reviewed/*.tar.gz
  PYTHON="$python_bin" bash scripts/build_release_artifacts.sh --outdir "$work/published"
elif [ "$gate_mode" = "authentic" ] && [ "$record_commit" != "-" ]; then
  "$python_bin" scripts/validate_rc_window.py \
    --record "$window_relative" \
    --expected-version "$candidate_version" \
    --history-mode
  mkdir -p "$work/records"
  git show "$record_commit:$review_relative" \
    > "$work/records/review.json"
  git show "$record_commit:$window_relative" \
    > "$work/records/window.json"
  git checkout --quiet --detach "$source_commit"
  PYTHON="$python_bin" bash scripts/build_release_artifacts.sh --outdir "$work/reviewed"
  "$python_bin" scripts/validate_rc2_release_records.py \
    --review "$work/records/review.json" \
    --window "$work/records/window.json" \
    --candidate-version "$candidate_version" \
    --source-commit "$source_commit" \
    --wheel "$work"/reviewed/*.whl \
    --sdist "$work"/reviewed/*.tar.gz
  git checkout --quiet --detach "$record_commit"
  PYTHON="$python_bin" bash scripts/build_release_artifacts.sh --outdir "$work/published"
else
  echo "unsupported release A/B gate state: $gate_mode" >&2
  exit 1
fi

"$python_bin" scripts/compare_release_builds.py --reviewed "$work/reviewed" --published "$work/published"
