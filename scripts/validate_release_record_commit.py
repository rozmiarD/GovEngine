from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REVIEW_PATH = Path("docs/security-review/rc2-external-review.json")
WINDOW_PATH = Path("docs/rc-window/1.0.0rc2.json")
EXPECTED_RECORD_CHANGES = (
    ("A", str(WINDOW_PATH)),
    ("M", str(REVIEW_PATH)),
)
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
PENDING_REVIEW: dict[str, Any] = {
    "schema_version": "govengine.rc2_external_security_review.v1",
    "source_commit": "",
    "artifacts": {
        "runner": "github-hosted-runner",
        "wheel_sha256": "",
        "normalized_sdist_sha256": "",
    },
    "confidential_report_sha256": "",
    "reviewer": "",
    "reviewed_at": None,
    "verdict": "pending_external_reviewer",
    "open_p0": None,
    "open_p1": None,
}


@dataclass(frozen=True)
class ReleaseABState:
    mode: str
    source_commit: str
    record_commit: str | None


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()


def _git_bytes(repo: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=repo)


def _load_json(text: str) -> Any:
    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"duplicate JSON key:{key}")
            value[key] = item
        return value

    return json.loads(text, object_pairs_hook=reject_duplicate_keys)


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


def _matches_authentic_record(
    repo: Path,
    commit: str,
    source_commit: str,
    current_review: bytes,
) -> bool:
    try:
        if validate_record_commit(repo, commit) != source_commit:
            return False
        record_review = _git_bytes(repo, "show", f"{commit}:{REVIEW_PATH}")
        record_window = _load_json(
            _git_bytes(repo, "show", f"{commit}:{WINDOW_PATH}").decode("utf-8")
        )
    except (ValueError, subprocess.CalledProcessError, json.JSONDecodeError):
        return False
    record_reference = (
        record_window.get("security_review")
        if isinstance(record_window, dict)
        else None
    )
    return (
        record_review == current_review
        and isinstance(record_reference, dict)
        and record_window.get("source_commit") == source_commit
        and record_reference.get("path") == str(REVIEW_PATH)
        and record_reference.get("sha256")
        == hashlib.sha256(record_review).hexdigest()
    )


def _squash_candidate(repo: Path, head_commit: str, source_commit: str) -> str:
    tree = _git(repo, "rev-parse", f"{head_commit}^{{tree}}")
    return subprocess.check_output(
        [
            "git",
            "-c",
            "user.name=GovEngine release gate",
            "-c",
            "user.email=release-gate@example.invalid",
            "commit-tree",
            tree,
            "-p",
            source_commit,
        ],
        cwd=repo,
        input="Synthetic exact-squash record candidate\n",
        text=True,
    ).strip()


def resolve_release_ab_state(repo: Path) -> ReleaseABState:
    head_commit = _git(repo, "rev-parse", "--verify", "HEAD^{commit}")
    review_path = repo / REVIEW_PATH
    window_path = repo / WINDOW_PATH
    review = _load_json(review_path.read_text(encoding="utf-8"))
    if not isinstance(review, dict):
        raise ValueError("rc2 review record must be a JSON object")

    if review == PENDING_REVIEW:
        if window_path.exists():
            raise ValueError("pending rc2 source must not contain an rc2 window")
        return ReleaseABState("synthetic", head_commit, None)

    if not window_path.exists():
        raise ValueError("approved rc2 review requires an rc2 window")
    window = _load_json(window_path.read_text(encoding="utf-8"))
    if not isinstance(window, dict):
        raise ValueError("rc2 window must be a JSON object")
    source_commit = review.get("source_commit")
    if (
        review.get("verdict") != "approved"
        or not isinstance(source_commit, str)
        or not FULL_SHA.fullmatch(source_commit)
        or window.get("schema_version") != "govengine.rc_window.v2"
        or window.get("version") != "1.0.0rc2"
        or window.get("source_commit") != source_commit
    ):
        raise ValueError("rc2 review and window identity are inconsistent")
    reference = window.get("security_review")
    current_review = review_path.read_bytes()
    if (
        not isinstance(reference, dict)
        or reference.get("path") != str(REVIEW_PATH)
        or reference.get("sha256") != hashlib.sha256(current_review).hexdigest()
    ):
        raise ValueError("rc2 window does not bind the current review record")
    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", source_commit, head_commit],
        cwd=repo,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).returncode != 0:
        raise ValueError("rc2 source is not an ancestor of the checked commit")

    candidates: list[str] = []
    commits = _git(
        repo,
        "rev-list",
        "--reverse",
        "--ancestry-path",
        f"{source_commit}..{head_commit}",
    ).splitlines()
    for commit in commits:
        parents = _git(repo, "rev-list", "--parents", "-n", "1", commit).split()[1:]
        if parents != [source_commit]:
            continue
        if _matches_authentic_record(repo, commit, source_commit, current_review):
            candidates.append(commit)

    expected_changes = [
        f"{status}\t{path}" for status, path in EXPECTED_RECORD_CHANGES
    ]
    aggregate_changes = _git(
        repo, "diff", "--name-status", source_commit, head_commit
    ).splitlines()
    if (
        not candidates
        and window.get("status") == "prepared"
        and aggregate_changes == expected_changes
    ):
        candidate = _squash_candidate(repo, head_commit, source_commit)
        if _matches_authentic_record(repo, candidate, source_commit, current_review):
            candidates.append(candidate)
    if len(candidates) != 1:
        raise ValueError("exactly one authentic rc2 record child must resolve")
    return ReleaseABState("authentic", source_commit, candidates[0])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--review-commit", default="HEAD")
    parser.add_argument("--resolve-ab-state", action="store_true")
    args = parser.parse_args()
    try:
        if args.resolve_ab_state:
            state = resolve_release_ab_state(args.repo)
            print(
                "\t".join(
                    (state.mode, state.source_commit, state.record_commit or "-")
                )
            )
        else:
            print(validate_record_commit(args.repo, args.review_commit))
    except (
        OSError,
        ValueError,
        json.JSONDecodeError,
        subprocess.CalledProcessError,
    ) as error:
        print(f"release_record_commit_invalid:{error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
