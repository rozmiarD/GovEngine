from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest

from scripts.validate_release_record_commit import (
    PENDING_REVIEW,
    resolve_release_ab_state,
    validate_record_commit,
)


def _git(path: Path, *args: str) -> str:
    return subprocess.check_output(['git', *args], cwd=path, text=True).strip()


def _source_with_seeded_review(tmp_path: Path) -> str:
    _git(tmp_path, 'init', '-q')
    _git(tmp_path, 'config', 'user.name', 'fixture')
    _git(tmp_path, 'config', 'user.email', 'fixture@example.invalid')
    (tmp_path / 'source.txt').write_text('a', encoding='utf-8')
    review = tmp_path / 'docs/security-review/rc2-external-review.json'
    review.parent.mkdir(parents=True)
    review.write_text(json.dumps(PENDING_REVIEW) + '\n', encoding='utf-8')
    _git(tmp_path, 'add', 'source.txt', str(review.relative_to(tmp_path)))
    _git(tmp_path, 'commit', '-qm', 'A')
    return _git(tmp_path, 'rev-parse', 'HEAD')


def _source_with_seeded_candidate_review(
    tmp_path: Path,
    *,
    candidate_version: str,
) -> str:
    candidate_label = f"rc{candidate_version.rsplit('rc', 1)[1]}"
    _git(tmp_path, 'init', '-q')
    _git(tmp_path, 'config', 'user.name', 'fixture')
    _git(tmp_path, 'config', 'user.email', 'fixture@example.invalid')
    (tmp_path / 'source.txt').write_text('a', encoding='utf-8')
    review = tmp_path / f'docs/security-review/{candidate_label}-external-review.json'
    review.parent.mkdir(parents=True)
    pending = dict(PENDING_REVIEW)
    pending['schema_version'] = (
        f'govengine.{candidate_label}_external_security_review.v1'
    )
    review.write_text(json.dumps(pending) + '\n', encoding='utf-8')
    window = tmp_path / f'docs/rc-window/{candidate_version}.json'
    window.parent.mkdir(parents=True)
    window.write_text(
        json.dumps(
            {
                'schema_version': 'govengine.rc_window.v2',
                'status': 'pending_review',
                'version': candidate_version,
                'source_commit': None,
                'security_review': {
                    'path': str(review.relative_to(tmp_path)),
                    'sha256': hashlib.sha256(review.read_bytes()).hexdigest(),
                },
            }
        )
        + '\n',
        encoding='utf-8',
    )
    _git(tmp_path, 'add', 'source.txt', 'docs')
    _git(tmp_path, 'commit', '-qm', 'A')
    return _git(tmp_path, 'rev-parse', 'HEAD')


def _authentic_record_child(tmp_path: Path, source: str) -> str:
    review_path = tmp_path / 'docs/security-review/rc2-external-review.json'
    review = {
        'schema_version': 'govengine.rc2_external_security_review.v1',
        'source_commit': source,
        'artifacts': {
            'runner': 'github-hosted-runner',
            'wheel_sha256': 'a' * 64,
            'normalized_sdist_sha256': 'b' * 64,
        },
        'confidential_report_sha256': 'c' * 64,
        'reviewer': 'reviewer@example.invalid',
        'reviewed_at': '2026-01-01T00:00:00Z',
        'verdict': 'approved',
        'open_p0': 0,
        'open_p1': 0,
    }
    review_path.write_text(json.dumps(review) + '\n', encoding='utf-8')
    window_path = tmp_path / 'docs/rc-window/1.0.0rc2.json'
    window_path.parent.mkdir(parents=True)
    window_path.write_text(
        json.dumps(
            {
                'schema_version': 'govengine.rc_window.v2',
                'status': 'prepared',
                'version': '1.0.0rc2',
                'source_commit': source,
                'security_review': {
                    'path': 'docs/security-review/rc2-external-review.json',
                    'sha256': hashlib.sha256(review_path.read_bytes()).hexdigest(),
                },
            }
        )
        + '\n',
        encoding='utf-8',
    )
    _git(tmp_path, 'add', 'docs')
    _git(tmp_path, 'commit', '-qm', 'B')
    return _git(tmp_path, 'rev-parse', 'HEAD')


def _split_record_pr_merge(
    tmp_path: Path,
    source: str,
    *,
    status: str = 'prepared',
    extra_path: bool = False,
) -> None:
    review_path = tmp_path / 'docs/security-review/rc2-external-review.json'
    review = {
        'schema_version': 'govengine.rc2_external_security_review.v1',
        'source_commit': source,
        'artifacts': {
            'runner': 'github-hosted-runner',
            'wheel_sha256': 'a' * 64,
            'normalized_sdist_sha256': 'b' * 64,
        },
        'confidential_report_sha256': 'c' * 64,
        'reviewer': 'reviewer@example.invalid',
        'reviewed_at': '2026-01-01T00:00:00Z',
        'verdict': 'approved',
        'open_p0': 0,
        'open_p1': 0,
    }
    review_path.write_text(json.dumps(review) + '\n', encoding='utf-8')
    _git(tmp_path, 'add', str(review_path.relative_to(tmp_path)))
    _git(tmp_path, 'commit', '-qm', 'PR review record')
    window = tmp_path / 'docs/rc-window/1.0.0rc2.json'
    window.parent.mkdir(parents=True)
    window.write_text(
        json.dumps(
            {
                'schema_version': 'govengine.rc_window.v2',
                'status': status,
                'version': '1.0.0rc2',
                'source_commit': source,
                'security_review': {
                    'path': 'docs/security-review/rc2-external-review.json',
                    'sha256': hashlib.sha256(review_path.read_bytes()).hexdigest(),
                },
            }
        )
        + '\n',
        encoding='utf-8',
    )
    paths = [str(window.relative_to(tmp_path))]
    if extra_path:
        extra = tmp_path / 'unexpected.txt'
        extra.write_text('unexpected', encoding='utf-8')
        paths.append(str(extra.relative_to(tmp_path)))
    _git(tmp_path, 'add', *paths)
    _git(tmp_path, 'commit', '-qm', 'PR window record')
    pr_head = _git(tmp_path, 'rev-parse', 'HEAD')
    _git(tmp_path, 'checkout', '--detach', '-q', source)
    _git(tmp_path, 'merge', '--no-ff', '-qm', 'synthetic PR merge', pr_head)


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


def test_release_ab_state_accepts_pending_source_a(tmp_path: Path) -> None:
    source = _source_with_seeded_review(tmp_path)
    state = resolve_release_ab_state(tmp_path)
    assert state.mode == 'synthetic'
    assert state.source_commit == source
    assert state.record_commit is None


def test_release_ab_state_accepts_candidate_bound_rc3_pending_source_a(
    tmp_path: Path,
) -> None:
    source = _source_with_seeded_candidate_review(
        tmp_path,
        candidate_version='1.0.0rc3',
    )

    state = resolve_release_ab_state(
        tmp_path,
        candidate_version='1.0.0rc3',
    )

    assert state.mode == 'synthetic'
    assert state.source_commit == source
    assert state.record_commit is None


def test_release_ab_state_finds_authentic_record_child(tmp_path: Path) -> None:
    source = _source_with_seeded_review(tmp_path)
    record = _authentic_record_child(tmp_path, source)
    state = resolve_release_ab_state(tmp_path)
    assert state.mode == 'authentic'
    assert state.source_commit == source
    assert state.record_commit == record


def test_release_ab_state_preserves_record_child_for_descendant(tmp_path: Path) -> None:
    source = _source_with_seeded_review(tmp_path)
    record = _authentic_record_child(tmp_path, source)
    window = tmp_path / 'docs/rc-window/1.0.0rc2.json'
    value = json.loads(window.read_text(encoding='utf-8'))
    value['status'] = 'active'
    window.write_text(json.dumps(value) + '\n', encoding='utf-8')
    _git(tmp_path, 'add', str(window.relative_to(tmp_path)))
    _git(tmp_path, 'commit', '-qm', 'start observation')
    state = resolve_release_ab_state(tmp_path)
    assert state.mode == 'authentic'
    assert state.source_commit == source
    assert state.record_commit == record


def test_release_ab_state_constructs_exact_squash_for_pr_merge(tmp_path: Path) -> None:
    source = _source_with_seeded_review(tmp_path)
    _split_record_pr_merge(tmp_path, source)

    state = resolve_release_ab_state(tmp_path)
    assert state.mode == 'authentic'
    assert state.source_commit == source
    assert state.record_commit is not None
    assert validate_record_commit(tmp_path, state.record_commit) == source
    ancestor = subprocess.run(
        ['git', 'merge-base', '--is-ancestor', state.record_commit, 'HEAD'],
        cwd=tmp_path,
        check=False,
    )
    assert ancestor.returncode != 0


def test_release_ab_state_rejects_squash_candidate_with_extra_path(
    tmp_path: Path,
) -> None:
    source = _source_with_seeded_review(tmp_path)
    _split_record_pr_merge(tmp_path, source, extra_path=True)
    with pytest.raises(ValueError, match='exactly one authentic rc2 record child'):
        resolve_release_ab_state(tmp_path)


def test_release_ab_state_rejects_active_candidate_without_record_child(
    tmp_path: Path,
) -> None:
    source = _source_with_seeded_review(tmp_path)
    _split_record_pr_merge(tmp_path, source, status='active')
    with pytest.raises(ValueError, match='exactly one authentic rc2 record child'):
        resolve_release_ab_state(tmp_path)


def test_release_ab_state_rejects_pending_source_with_window(tmp_path: Path) -> None:
    _source_with_seeded_review(tmp_path)
    window = tmp_path / 'docs/rc-window/1.0.0rc2.json'
    window.parent.mkdir(parents=True)
    window.write_text('{}\n', encoding='utf-8')
    with pytest.raises(ValueError, match='pending rc2 source must not contain'):
        resolve_release_ab_state(tmp_path)


def test_release_ab_state_rejects_duplicate_pending_field(tmp_path: Path) -> None:
    _source_with_seeded_review(tmp_path)
    review = tmp_path / 'docs/security-review/rc2-external-review.json'
    text = review.read_text(encoding='utf-8').rstrip()
    review.write_text(
        text[:-1] + ', "verdict": "pending_external_reviewer"}\n',
        encoding='utf-8',
    )
    with pytest.raises(ValueError, match='duplicate JSON key:verdict'):
        resolve_release_ab_state(tmp_path)


def test_release_ab_state_rejects_approved_review_without_window(
    tmp_path: Path,
) -> None:
    source = _source_with_seeded_review(tmp_path)
    review = tmp_path / 'docs/security-review/rc2-external-review.json'
    value = json.loads(review.read_text(encoding='utf-8'))
    value['verdict'] = 'approved'
    value['source_commit'] = source
    review.write_text(json.dumps(value) + '\n', encoding='utf-8')
    with pytest.raises(ValueError, match='approved rc2 review requires'):
        resolve_release_ab_state(tmp_path)


def test_release_ab_state_rejects_review_window_source_mismatch(
    tmp_path: Path,
) -> None:
    source = _source_with_seeded_review(tmp_path)
    _authentic_record_child(tmp_path, source)
    window = tmp_path / 'docs/rc-window/1.0.0rc2.json'
    value = json.loads(window.read_text(encoding='utf-8'))
    value['source_commit'] = 'd' * 40
    window.write_text(json.dumps(value) + '\n', encoding='utf-8')
    with pytest.raises(ValueError, match='review and window identity'):
        resolve_release_ab_state(tmp_path)


def test_release_ab_state_rejects_review_changed_after_record_child(
    tmp_path: Path,
) -> None:
    source = _source_with_seeded_review(tmp_path)
    _authentic_record_child(tmp_path, source)
    review = tmp_path / 'docs/security-review/rc2-external-review.json'
    value = json.loads(review.read_text(encoding='utf-8'))
    value['reviewer'] = 'replacement@example.invalid'
    review.write_text(json.dumps(value) + '\n', encoding='utf-8')
    with pytest.raises(ValueError, match='window does not bind the current review'):
        resolve_release_ab_state(tmp_path)


def test_release_ab_state_rejects_missing_source_history(tmp_path: Path) -> None:
    origin = tmp_path / 'origin'
    origin.mkdir()
    source = _source_with_seeded_review(origin)
    _authentic_record_child(origin, source)
    shallow = tmp_path / 'shallow'
    subprocess.check_call(
        ['git', 'clone', '--quiet', '--depth', '1', f'file://{origin}', str(shallow)]
    )
    with pytest.raises(ValueError, match='source is not an ancestor'):
        resolve_release_ab_state(shallow)


def test_release_ab_gate_skips_empty_patch_and_preserves_dirty_overlay(
    tmp_path: Path,
) -> None:
    root = Path(__file__).parents[1]
    source = tmp_path / 'source'
    source.mkdir()
    script = source / 'scripts/release_ab_repro_gate.sh'
    script.parent.mkdir()
    script.write_bytes((root / 'scripts/release_ab_repro_gate.sh').read_bytes())
    script.chmod(0o755)
    tracked = source / 'tracked.txt'
    tracked.write_text('clean\n', encoding='utf-8')
    _git(source, 'init', '-q')
    _git(source, 'config', 'user.name', 'fixture')
    _git(source, 'config', 'user.email', 'fixture@example.invalid')
    _git(source, 'add', 'scripts/release_ab_repro_gate.sh', 'tracked.txt')
    _git(source, 'commit', '-qm', 'source')

    python_stub = tmp_path / 'python-stub'
    python_stub.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
if [ "${1:-}" = "-c" ]; then
  printf '1.0.0rc3\\n'
  exit 0
fi
if [ "${1:-}" = "scripts/validate_release_record_commit.py" ]; then
  if [ "${EXPECT_DIRTY:-0}" = "1" ]; then
    test "$(cat tracked.txt)" = "dirty"
    test "$(cat untracked.txt)" = "untracked"
  else
    test "$(cat tracked.txt)" = "clean"
    test ! -e untracked.txt
  fi
  printf 'regression-sentinel\\t-\\t-\\n'
  exit 0
fi
exit 97
""",
        encoding='utf-8',
    )
    python_stub.chmod(0o755)
    env = os.environ.copy()
    env['PYTHON'] = str(python_stub)

    clean = subprocess.run(
        ['bash', 'scripts/release_ab_repro_gate.sh'],
        cwd=source,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert clean.returncode == 1
    assert clean.stderr == (
        'unsupported release A/B gate state: regression-sentinel\n'
    )

    tracked.write_text('dirty\n', encoding='utf-8')
    (source / 'untracked.txt').write_text('untracked\n', encoding='utf-8')
    env['EXPECT_DIRTY'] = '1'
    dirty = subprocess.run(
        ['bash', 'scripts/release_ab_repro_gate.sh'],
        cwd=source,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert dirty.returncode == 1
    assert dirty.stderr == (
        'unsupported release A/B gate state: regression-sentinel\n'
    )
