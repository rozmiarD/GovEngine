from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts.validate_release_record_commit import validate_record_commit


def _git(path: Path, *args: str) -> str:
    return subprocess.check_output(['git', *args], cwd=path, text=True).strip()


def test_record_child_adds_exactly_two_new_paths(tmp_path: Path) -> None:
    _git(tmp_path, 'init', '-q')
    _git(tmp_path, 'config', 'user.name', 'fixture')
    _git(tmp_path, 'config', 'user.email', 'fixture@example.invalid')
    (tmp_path / 'source.txt').write_text('a', encoding='utf-8')
    _git(tmp_path, 'add', 'source.txt')
    _git(tmp_path, 'commit', '-qm', 'A')
    source = _git(tmp_path, 'rev-parse', 'HEAD')
    (tmp_path / 'docs/security-review').mkdir(parents=True)
    (tmp_path / 'docs/rc-window').mkdir(parents=True)
    (tmp_path / 'docs/security-review/rc2-external-review.json').write_text('{}', encoding='utf-8')
    (tmp_path / 'docs/rc-window/1.0.0rc2.json').write_text('{}', encoding='utf-8')
    _git(tmp_path, 'add', 'docs')
    _git(tmp_path, 'commit', '-qm', 'B')
    assert validate_record_commit(tmp_path, 'HEAD') == source


def test_record_child_rejects_non_record_change(tmp_path: Path) -> None:
    _git(tmp_path, 'init', '-q')
    _git(tmp_path, 'config', 'user.name', 'fixture')
    _git(tmp_path, 'config', 'user.email', 'fixture@example.invalid')
    (tmp_path / 'source.txt').write_text('a', encoding='utf-8')
    _git(tmp_path, 'add', 'source.txt')
    _git(tmp_path, 'commit', '-qm', 'A')
    (tmp_path / 'other.txt').write_text('b', encoding='utf-8')
    _git(tmp_path, 'add', 'other.txt')
    _git(tmp_path, 'commit', '-qm', 'B')
    with pytest.raises(ValueError, match='exactly the two record paths'):
        validate_record_commit(tmp_path, 'HEAD')
