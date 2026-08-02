from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


EXPECTED_RECORD_CHANGES = (
    ("A", "docs/rc-window/1.0.0rc2.json"),
    ("M", "docs/security-review/rc2-external-review.json"),
)


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()


def validate_record_commit(repo: Path, review_commit: str) -> str:
    parents = _git(repo, "rev-list", "--parents", "-n", "1", review_commit).split()
    if len(parents) != 2:
        raise ValueError("rc2 review record commit must have exactly one parent")
    source_commit = parents[1]
    changes = _git(repo, "diff", "--name-status", source_commit, review_commit).splitlines()
    expected = [f"{status}\t{path}" for status, path in EXPECTED_RECORD_CHANGES]
    if changes != expected:
        raise ValueError(
            "rc2 review record commit must add the window and modify the seeded review form"
        )
    return source_commit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--review-commit", default="HEAD")
    args = parser.parse_args()
    try:
        print(validate_record_commit(args.repo, args.review_commit))
    except (ValueError, subprocess.CalledProcessError) as error:
        print(f"release_record_commit_invalid:{error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
