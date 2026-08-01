#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
repo_root="$(pwd)"
python_bin="${PYTHON:-python3}"
work="$(mktemp -d)"
cleanup() { rm -rf "$work"; }
trap cleanup EXIT

"$python_bin" -m venv "$work/build"
build_py="$work/build/bin/python"
"$build_py" -m pip install -r .github/release-build-requirements.txt >/dev/null
mkdir "$work/source"
tar --exclude-vcs --exclude=build --exclude=dist --exclude='*.egg-info' --exclude=.venv -C "$repo_root" -cf - . | tar -C "$work/source" -xf -
(
  cd "$work/source"
  PYTHON="$build_py" bash scripts/build_release_artifacts.sh --outdir "$work/dist"
)
for kind in wheel sdist; do
  "$python_bin" -m venv "$work/$kind"
  install_py="$work/$kind/bin/python"
  "$install_py" -m pip install pip==26.1.2 >/dev/null
  "$install_py" -m pip install "sclite-core==2.0.0" >/dev/null
  if [ "$kind" = wheel ]; then artifact="$work"/dist/*.whl; else artifact="$work"/dist/*.tar.gz; fi
  # The isolated artifact directory is made by mktemp and contains one artifact.
  "$install_py" -m pip install $artifact >/dev/null
  "$install_py" -m pip check
  "$install_py" -c "import importlib.metadata as md, govengine; assert md.version('govengine') == govengine.__version__ == '1.0.0rc1'"
done
echo "govengine_package_smoke_ok:wheel_and_sdist"
