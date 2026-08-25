from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
RC_VERSION = re.compile(r"^1\.0\.0rc(?P<candidate>[1-9][0-9]*)$")


def _candidate_paths(candidate_version: str) -> tuple[str, Path, Path]:
    match = RC_VERSION.fullmatch(candidate_version)
    if match is None:
        raise ValueError("candidate_version_invalid")
    label = f"rc{match.group('candidate')}"
    return (
        label,
        Path(f"docs/security-review/{label}-external-review.json"),
        Path(f"docs/rc-window/{candidate_version}.json"),
    )


def _pending_review(candidate_version: str) -> dict[str, Any]:
    label, _, _ = _candidate_paths(candidate_version)
    return {
        "schema_version": f"govengine.{label}_external_security_review.v1",
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


# Backward-compatible fixture name for the immutable rc2 A/B history.
PENDING_REVIEW = _pending_review("1.0.0rc2")


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


def _source_has_path(repo: Path, source_commit: str, path: Path) -> bool:
    return subprocess.run(
        ["git", "cat-file", "-e", f"{source_commit}:{path}"],
        cwd=repo,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).returncode == 0


def _expected_record_changes(
    repo: Path,
    source_commit: str,
    *,
    review_path: Path,
    window_path: Path,
) -> list[str]:
    window_status = "M" if _source_has_path(repo, source_commit, window_path) else "A"
    return [f"{window_status}\t{window_path}", f"M\t{review_path}"]


def validate_record_commit(
    repo: Path,
    review_commit: str,
    *,
    candidate_version: str = "1.0.0rc2",
) -> str:
    label, review_path, window_path = _candidate_paths(candidate_version)
    parents = _git(repo, "rev-list", "--parents", "-n", "1", review_commit).split()
    if len(parents) != 2:
        raise ValueError(f"{label} review record commit must have exactly one parent")
    source_commit = parents[1]
    changes = _git(repo, "diff", "--name-status", source_commit, review_commit).splitlines()
    expected = _expected_record_changes(
        repo,
        source_commit,
        review_path=review_path,
        window_path=window_path,
    )
    if changes != expected:
        if _source_has_path(repo, source_commit, window_path):
            action = "modify the window and seeded review form"
        else:
            action = "add the window and modify the seeded review form"
        raise ValueError(
            f"{label} review record commit must {action}"
        )
    return source_commit


def _matches_authentic_record(
    repo: Path,
    commit: str,
    source_commit: str,
    current_review: bytes,
    candidate_version: str,
    review_path: Path,
    window_path: Path,
) -> bool:
    try:
        if validate_record_commit(
            repo,
            commit,
            candidate_version=candidate_version,
        ) != source_commit:
            return False
        record_review = _git_bytes(repo, "show", f"{commit}:{review_path}")
        record_window = _load_json(
            _git_bytes(repo, "show", f"{commit}:{window_path}").decode("utf-8")
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
        and record_window.get("version") == candidate_version
        and record_window.get("source_commit") == source_commit
        and record_reference.get("path") == str(review_path)
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


def resolve_release_ab_state(
    repo: Path,
    *,
    candidate_version: str = "1.0.0rc2",
) -> ReleaseABState:
    label, review_relative, window_relative = _candidate_paths(candidate_version)
    head_commit = _git(repo, "rev-parse", "--verify", "HEAD^{commit}")
    review_path = repo / review_relative
    window_path = repo / window_relative
    review = _load_json(review_path.read_text(encoding="utf-8"))
    if not isinstance(review, dict):
        raise ValueError(f"{label} review record must be a JSON object")

    if review == _pending_review(candidate_version):
        if window_path.exists():
            if candidate_version == "1.0.0rc2":
                raise ValueError("pending rc2 source must not contain an rc2 window")
            pending_window = _load_json(window_path.read_text(encoding="utf-8"))
            reference = (
                pending_window.get("security_review")
                if isinstance(pending_window, dict)
                else None
            )
            if (
                not isinstance(pending_window, dict)
                or pending_window.get("status") != "pending_review"
                or pending_window.get("version") != candidate_version
                or pending_window.get("source_commit") is not None
                or not isinstance(reference, dict)
                or reference.get("path") != str(review_relative)
                or reference.get("sha256")
                != hashlib.sha256(review_path.read_bytes()).hexdigest()
            ):
                raise ValueError(f"pending {label} source record is inconsistent")
        return ReleaseABState("synthetic", head_commit, None)

    if not window_path.exists():
        raise ValueError(f"approved {label} review requires a candidate window")
    window = _load_json(window_path.read_text(encoding="utf-8"))
    if not isinstance(window, dict):
        raise ValueError(f"{label} window must be a JSON object")
    source_commit = review.get("source_commit")
    if (
        review.get("verdict") != "approved"
        or not isinstance(source_commit, str)
        or not FULL_SHA.fullmatch(source_commit)
        or window.get("schema_version") != "govengine.rc_window.v2"
        or window.get("version") != candidate_version
        or window.get("source_commit") != source_commit
    ):
        raise ValueError(f"{label} review and window identity are inconsistent")
    reference = window.get("security_review")
    current_review = review_path.read_bytes()
    if (
        not isinstance(reference, dict)
        or reference.get("path") != str(review_relative)
        or reference.get("sha256") != hashlib.sha256(current_review).hexdigest()
    ):
        raise ValueError(f"{label} window does not bind the current review record")
    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", source_commit, head_commit],
        cwd=repo,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).returncode != 0:
        raise ValueError(f"{label} source is not an ancestor of the checked commit")

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
        if _matches_authentic_record(
            repo,
            commit,
            source_commit,
            current_review,
            candidate_version,
            review_relative,
            window_relative,
        ):
            candidates.append(commit)

    expected_changes = _expected_record_changes(
        repo,
        source_commit,
        review_path=review_relative,
        window_path=window_relative,
    )
    aggregate_changes = _git(
        repo, "diff", "--name-status", source_commit, head_commit
    ).splitlines()
    if (
        not candidates
        and window.get("status") == "prepared"
        and aggregate_changes == expected_changes
    ):
        candidate = _squash_candidate(repo, head_commit, source_commit)
        if _matches_authentic_record(
            repo,
            candidate,
            source_commit,
            current_review,
            candidate_version,
            review_relative,
            window_relative,
        ):
            candidates.append(candidate)
    if len(candidates) != 1:
        raise ValueError(f"exactly one authentic {label} record child must resolve")
    return ReleaseABState("authentic", source_commit, candidates[0])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--review-commit", default="HEAD")
    parser.add_argument("--resolve-ab-state", action="store_true")
    parser.add_argument("--candidate-version", default="1.0.0rc2")
    args = parser.parse_args()
    try:
        if args.resolve_ab_state:
            state = resolve_release_ab_state(
                args.repo,
                candidate_version=args.candidate_version,
            )
            print(
                "\t".join(
                    (state.mode, state.source_commit, state.record_commit or "-")
                )
            )
        else:
            print(
                validate_record_commit(
                    args.repo,
                    args.review_commit,
                    candidate_version=args.candidate_version,
                )
            )
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
