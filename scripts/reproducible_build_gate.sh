#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
left="$(mktemp -d)"
right="$(mktemp -d)"
cleanup() { rm -rf "$left" "$right"; }
trap cleanup EXIT
export SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-1704067200}"
PYTHON="${PYTHON:-python3}" bash scripts/build_release_artifacts.sh --outdir "$left"
PYTHON="${PYTHON:-python3}" bash scripts/build_release_artifacts.sh --outdir "$right"
python_bin="${PYTHON:-python3}"
"$python_bin" scripts/compare_release_builds.py --reviewed "$left" --published "$right"
