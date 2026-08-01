from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def _artifacts(directory: Path) -> dict[str, Path]:
    files = sorted(path for path in directory.iterdir() if path.is_file())
    wheels = [path for path in files if path.suffix == ".whl"]
    sdists = [path for path in files if path.name.endswith(".tar.gz")]
    if len(files) != 2 or len(wheels) != 1 or len(sdists) != 1:
        raise ValueError("release build must contain exactly one wheel and one sdist")
    return {path.name: path for path in files}


def compare_release_builds(reviewed: Path, published: Path) -> None:
    left, right = _artifacts(reviewed), _artifacts(published)
    if left.keys() != right.keys():
        raise ValueError("reviewed and published artifact names differ")
    for name, reviewed_path in left.items():
        digest = hashlib.sha256(reviewed_path.read_bytes()).hexdigest()
        if digest != hashlib.sha256(right[name].read_bytes()).hexdigest():
            raise ValueError(f"reviewed and published artifact bytes differ:{name}")
        print(f"release_build_match:{name}:{digest}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reviewed", type=Path, required=True)
    parser.add_argument("--published", type=Path, required=True)
    args = parser.parse_args()
    try:
        compare_release_builds(args.reviewed, args.published)
    except (OSError, ValueError) as error:
        print(f"release_build_comparison_failed:{error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
