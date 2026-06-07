from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_no_signposter_roadmap_artifacts_in_docs() -> None:
    """Ensure that Signposter operational artifacts are not present in docs/."""
    docs_dir = ROOT / "docs"

    # The entire roadmaps directory must be gone from the repository
    assert not (docs_dir / "roadmaps").exists(), "docs/roadmaps/ should have been removed"

    # DOCUMENTATION_HYGIENE.md was a Signposter process artifact and must be gone
    assert not (docs_dir / "DOCUMENTATION_HYGIENE.md").exists(), "DOCUMENTATION_HYGIENE.md should have been removed"


def test_no_signposter_references_in_documentation() -> None:
    """Scan docs/ for obvious Signposter / local process leakage."""
    docs_dir = ROOT / "docs"

    forbidden_patterns = [
        "Signposter as the workflow control plane",
        "Returning to mainline",
        "GE-TASK-CONTRACT",
        "seed-manifest",
        "docs/roadmaps/",
        "/home/probo",
        "current roadmap",
        "Signposter-controlled",
    ]

    for md_file in docs_dir.rglob("*.md"):
        # Skip the archive (it lives outside docs/)
        if ".signposter-local" in md_file.parts:
            continue

        text = md_file.read_text(encoding="utf-8", errors="ignore")
        for pattern in forbidden_patterns:
            assert pattern not in text, f"{md_file}: found forbidden pattern '{pattern}'"


def test_no_tracked_local_only_documentation_artifacts() -> None:
    """Legacy guard: no .local.md / .scratch.md / .private.md files tracked under docs/."""
    tracked_docs = [
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("*.md")
        if ".git" not in path.parts and ".venv" not in path.parts
    ]

    forbidden_suffixes = (".local.md", ".scratch.md", ".private.md")
    assert not [path for path in tracked_docs if path.startswith("docs/roadmaps/local/")]
    assert not [path for path in tracked_docs if path.endswith(forbidden_suffixes)]


def test_signposter_local_is_ignored() -> None:
    """The .signposter-local/ directory must be ignored by git."""
    # We only check that the pattern exists in .gitignore.
    # Actual git check-ignore is done manually / in CI if needed.
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".signposter-local/" in ignore
