from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts.validate_release_record_commit import validate_record_commit


def _git(path: Path, *args: str) -> str:
    return subprocess.check_output(['git', *args], cwd=path, text=True).strip()


def _source_with_seeded_review(tmp_path: Path) -> str:
    _git(tmp_path, 'init', '-q')
    _git(tmp_path, 'config', 'user.name', 'fixture')
    _git(tmp_path, 'config', 'user.email', 'fixture@example.invalid')
    (tmp_path / 'source.txt').write_text('a', encoding='utf-8')
    review = tmp_path / 'docs/security-review/rc2-external-review.json'
    review.parent.mkdir(parents=True)
    review.write_text('{"verdict":"pending_external_reviewer"}', encoding='utf-8')
    _git(tmp_path, 'add', 'source.txt', str(review.relative_to(tmp_path)))
    _git(tmp_path, 'commit', '-qm', 'A')
    return _git(tmp_path, 'rev-parse', 'HEAD')


def test_record_child_modifies_seeded_review_and_adds_window(tmp_path: Path) -> None:
    source = _source_with_seeded_review(tmp_path)
    (tmp_path / 'docs/rc-window').mkdir(parents=True)
    (tmp_path / 'docs/security-review/rc2-external-review.json').write_text(
        '{"verdict":"approved"}', encoding='utf-8'
    )
    (tmp_path / 'docs/rc-window/1.0.0rc2.json').write_text('{}', encoding='utf-8')
    _git(tmp_path, 'add', 'docs')
    _git(tmp_path, 'commit', '-qm', 'B')
    assert validate_record_commit(tmp_path, 'HEAD') == source


def test_record_child_rejects_added_review_and_window(tmp_path: Path) -> None:
    _git(tmp_path, 'init', '-q')
    _git(tmp_path, 'config', 'user.name', 'fixture')
    _git(tmp_path, 'config', 'user.email', 'fixture@example.invalid')
    (tmp_path / 'source.txt').write_text('a', encoding='utf-8')
    _git(tmp_path, 'add', 'source.txt')
    _git(tmp_path, 'commit', '-qm', 'A')
    (tmp_path / 'docs/security-review').mkdir(parents=True)
    (tmp_path / 'docs/rc-window').mkdir(parents=True)
    (tmp_path / 'docs/security-review/rc2-external-review.json').write_text(
        '{"verdict":"approved"}', encoding='utf-8'
    )
    (tmp_path / 'docs/rc-window/1.0.0rc2.json').write_text('{}', encoding='utf-8')
    _git(tmp_path, 'add', 'docs')
    _git(tmp_path, 'commit', '-qm', 'B')
    with pytest.raises(ValueError, match='add the window and modify the seeded review form'):
        validate_record_commit(tmp_path, 'HEAD')


def test_record_child_rejects_non_record_change(tmp_path: Path) -> None:
    _source_with_seeded_review(tmp_path)
    (tmp_path / 'other.txt').write_text('b', encoding='utf-8')
    _git(tmp_path, 'add', 'other.txt')
    _git(tmp_path, 'commit', '-qm', 'B')
    with pytest.raises(ValueError, match='add the window and modify the seeded review form'):
        validate_record_commit(tmp_path, 'HEAD')


def test_record_child_rejects_multiple_parents(tmp_path: Path) -> None:
    source = _source_with_seeded_review(tmp_path)
    tree = _git(tmp_path, 'rev-parse', f'{source}^{{tree}}')
    other = _git(tmp_path, 'commit-tree', tree, '-p', source, '-m', 'other')
    merge = _git(
        tmp_path,
        'commit-tree',
        tree,
        '-p',
        source,
        '-p',
        other,
        '-m',
        'merge',
    )
    with pytest.raises(ValueError, match='exactly one parent'):
        validate_record_commit(tmp_path, merge)
