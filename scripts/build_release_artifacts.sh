#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 2 ] || [ "$1" != "--outdir" ]; then
  echo "usage: $0 --outdir DIRECTORY" >&2
  exit 2
fi

OUTDIR="$2"
PYTHON_BIN="${PYTHON:-python3}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
umask 0022
export LC_ALL=C
export TZ=UTC
export PYTHONHASHSEED=0
export SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-1704067200}"

mkdir -p "$OUTDIR"
shopt -s nullglob
existing=("$OUTDIR"/*.whl "$OUTDIR"/*.tar.gz)
if [ "${#existing[@]}" -ne 0 ]; then
  echo "refusing nonempty release artifact directory: $OUTDIR" >&2
  exit 1
fi

cd "$REPO_ROOT"
"$PYTHON_BIN" -m build --no-isolation --outdir "$OUTDIR"

readarray -t expected < <("$PYTHON_BIN" - <<'PY'
import re
import tomllib
with open("pyproject.toml", "rb") as source:
    project = tomllib.load(source)["project"]
name = re.sub(r"[-_.]+", "_", project["name"])
version = project["version"]
print(f"{name}-{version}-py3-none-any.whl")
print(f"{name}-{version}.tar.gz")
PY
)
wheel="$OUTDIR/${expected[0]}"
sdist="$OUTDIR/${expected[1]}"
artifacts=("$OUTDIR"/*.whl "$OUTDIR"/*.tar.gz)
if [ "${#artifacts[@]}" -ne 2 ] || [ ! -f "$wheel" ] || [ ! -f "$sdist" ]; then
  echo "build did not produce one exact wheel and root sdist" >&2
  exit 1
fi

bash scripts/normalize_sdist.sh "$sdist"
"$PYTHON_BIN" -m twine check "$wheel" "$sdist"
"$PYTHON_BIN" scripts/validate_distribution_metadata.py --wheel "$wheel" --sdist "$sdist"
