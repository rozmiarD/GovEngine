from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_documentation_hygiene_audit_records_active_roadmap_boundary() -> None:
    text = (ROOT / 'docs' / 'DOCUMENTATION_HYGIENE.md').read_text(encoding='utf-8')

    assert 'docs/roadmaps/ge-governed-runtime-kernel-mvp-seed-manifest.json' in text
    assert 'Removing those files mid-roadmap would break the current' in text
    assert 'Returning to mainline: next task is GE-039' in text


def test_local_only_documentation_patterns_are_ignored() -> None:
    ignore = (ROOT / '.gitignore').read_text(encoding='utf-8')

    for pattern in (
        '.signposter-local/',
        'docs/roadmaps/local/',
        'docs/roadmaps/**/*.local.md',
        'docs/roadmaps/**/*.scratch.md',
        'docs/roadmaps/**/*.private.md',
    ):
        assert pattern in ignore


def test_no_tracked_local_only_documentation_artifacts() -> None:
    tracked_docs = [
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob('*.md')
        if '.git' not in path.parts and '.venv' not in path.parts
    ]

    forbidden_suffixes = ('.local.md', '.scratch.md', '.private.md')
    assert not [path for path in tracked_docs if path.startswith('docs/roadmaps/local/')]
    assert not [path for path in tracked_docs if path.endswith(forbidden_suffixes)]
