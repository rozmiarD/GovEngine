from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from scripts.validate_release_train_truth import (
    ACTIVE_TRAIN_DOCS,
    ROOT,
    _validate_active_docs,
    _validate_cross_repo,
    load_release_train,
    main as release_train_main,
    validate_release_train_truth,
)


def _write_project(
    root: Path,
    *,
    name: str,
    version: str,
    dependencies: tuple[str, ...] = (),
) -> None:
    root.mkdir(parents=True)
    dependency_lines = ',\n'.join(json.dumps(item) for item in dependencies)
    (root / 'pyproject.toml').write_text(
        '\n'.join(
            (
                '[project]',
                f'name = {json.dumps(name)}',
                f'version = {json.dumps(version)}',
                f'dependencies = [{dependency_lines}]',
            )
        ),
        encoding='utf-8',
    )


def test_release_train_truth_matches_current_repository() -> None:
    report = validate_release_train_truth(mode='local')
    assert report == {
        'published_sclite': '2.0.1',
        'published_govengine': '1.0.0rc2',
        'published_rexecop': '1.0.0rc1',
        'source_sclite': '2.0.1',
        'source_govengine': '1.0.0rc2',
        'source_rexecop': '1.0.0rc3.dev0',
        'source_tecrax': '0.4.0rc3',
    }


def test_manifest_separates_published_history_from_source_candidates() -> None:
    manifest = load_release_train()

    assert manifest['published_artifacts']['rexecop'] == {
        'project': 'rexecop',
        'version': '1.0.0rc1',
        'status': 'published_rc',
        'dependencies': {
            'govengine': '1.0.0rc1',
            'sclite-core': '2.0.0',
        },
    }
    assert manifest['source_candidates']['rexecop'] == {
        'project': 'rexecop',
        'version': '1.0.0rc3.dev0',
        'status': 'source_candidate',
        'dependencies': {
            'govengine': '1.0.0rc2',
            'sclite-core': '2.0.1',
        },
    }
    assert manifest['source_candidates']['tecrax'] == {
        'project': 'tecrax',
        'version': '0.4.0rc3',
        'status': 'pending_realignment',
        'dependencies': {
            'govengine': '1.0.0rc2',
            'rexecop': '1.0.0rc2',
            'sclite-core': '2.0.1',
        },
    }


def _copy_active_train_docs(tmp_path: Path) -> None:
    for relative in ACTIVE_TRAIN_DOCS:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        text = (ROOT / relative).read_text(encoding='utf-8')
        target.write_text(text, encoding='utf-8')


def test_active_docs_match_current_manifest() -> None:
    _validate_active_docs(load_release_train())


def test_active_docs_reject_stale_source_runtime(tmp_path: Path) -> None:
    _copy_active_train_docs(tmp_path)
    publishing = tmp_path / 'PUBLISHING.md'
    publishing.write_text(
        publishing.read_text(encoding='utf-8').replace(
            'RExecOp source candidate `1.0.0rc3.dev0`',
            'RExecOp source candidate `0.3.0rc3`',
        ),
        encoding='utf-8',
    )

    with pytest.raises(
        AssertionError,
        match=(
            'release_train_doc_drift:PUBLISHING.md:'
            'RExecOp source candidate `1.0.0rc3.dev0`'
        ),
    ):
        _validate_active_docs(load_release_train(), root=tmp_path)


def test_active_docs_reject_contradictory_alignment_claim(tmp_path: Path) -> None:
    _copy_active_train_docs(tmp_path)
    public_status = tmp_path / 'PUBLIC_STATUS.md'
    public_status.write_text(
        public_status.read_text(encoding='utf-8')
        + '\nTecrax `0.4.0rc3` is source-aligned/unpublished on the rc1 train.\n',
        encoding='utf-8',
    )

    with pytest.raises(
        AssertionError,
        match=(
            'release_train_doc_contradiction:PUBLIC_STATUS.md:'
            'source-aligned/unpublished'
        ),
    ):
        _validate_active_docs(load_release_train(), root=tmp_path)


def test_migration_guide_rejects_current_source_as_historical_rc1(
    tmp_path: Path,
) -> None:
    _copy_active_train_docs(tmp_path)
    migration = tmp_path / 'docs/MIGRATING_TO_1.md'
    migration.write_text(
        migration.read_text(encoding='utf-8')
        + (
            '\nTecrax `0.4.0rc3` current source is aligned to the published '
            'rc1 train.\n'
        ),
        encoding='utf-8',
    )

    with pytest.raises(
        AssertionError,
        match=(
            'release_train_doc_contradiction:docs/MIGRATING_TO_1.md:'
            'current source is aligned to the published rc1 train'
        ),
    ):
        _validate_active_docs(load_release_train(), root=tmp_path)


def test_migration_guide_rejects_current_public_targets_as_unpublished(
    tmp_path: Path,
) -> None:
    _copy_active_train_docs(tmp_path)
    migration = tmp_path / 'docs/MIGRATING_TO_1.md'
    migration.write_text(
        migration.read_text(encoding='utf-8')
        + (
            '\n`govengine==1.0.0rc2` source and `sclite-core==2.0.1` are not '
            'public install targets.\n'
        ),
        encoding='utf-8',
    )

    with pytest.raises(
        AssertionError,
        match=(
            'release_train_doc_contradiction:docs/MIGRATING_TO_1.md:'
            '`govengine==1.0.0rc2` source and `sclite-core==2.0.1` are not '
            'public install targets'
        ),
    ):
        _validate_active_docs(load_release_train(), root=tmp_path)


def test_pending_tecrax_cannot_match_current_runtime(tmp_path: Path) -> None:
    manifest = copy.deepcopy(dict(load_release_train()))
    manifest['source_candidates']['tecrax']['dependencies']['rexecop'] = (
        '1.0.0rc3.dev0'
    )

    roots = {
        'sclite': tmp_path / 'sclite',
        'govengine': ROOT,
        'rexecop': tmp_path / 'rexecop',
        'tecrax': tmp_path / 'tecrax',
    }
    _write_project(roots['sclite'], name='sclite-core', version='2.0.1')
    _write_project(
        roots['rexecop'],
        name='rexecop',
        version='1.0.0rc3.dev0',
        dependencies=('govengine==1.0.0rc2', 'sclite-core==2.0.1'),
    )
    _write_project(
        roots['tecrax'],
        name='tecrax',
        version='0.4.0rc3',
        dependencies=(
            'govengine==1.0.0rc2',
            'rexecop==1.0.0rc3.dev0',
            'sclite-core==2.0.1',
        ),
    )

    with pytest.raises(
        AssertionError,
        match='release_train_pending_component_is_aligned:tecrax',
    ):
        _validate_cross_repo(manifest, roots)


def test_cross_repo_rejects_dependency_drift(tmp_path: Path) -> None:
    manifest = load_release_train()
    roots = {
        'sclite': tmp_path / 'sclite',
        'govengine': tmp_path / 'govengine',
        'rexecop': tmp_path / 'rexecop',
        'tecrax': tmp_path / 'tecrax',
    }
    _write_project(roots['sclite'], name='sclite-core', version='2.0.1')
    _write_project(
        roots['govengine'],
        name='govengine',
        version='1.0.0rc2',
        dependencies=('sclite-core==2.0.1',),
    )
    _write_project(
        roots['rexecop'],
        name='rexecop',
        version='1.0.0rc3.dev0',
        dependencies=('govengine==0.17.0rc2', 'sclite-core==2.0.0'),
    )
    _write_project(
        roots['tecrax'],
        name='tecrax',
        version='0.4.0rc3',
        dependencies=(
            'govengine==1.0.0rc1',
            'rexecop==1.0.0rc2',
            'sclite-core==2.0.1',
        ),
    )

    with pytest.raises(
        AssertionError,
        match=(
            'release_train_dependency_mismatch:rexecop:'
            'govengine:0.17.0rc2!=1.0.0rc2'
        ),
    ):
        _validate_cross_repo(manifest, roots)


def test_release_train_modes_reject_mismatched_root_scope() -> None:
    roots = {
        'sclite': ROOT.parent / 'sclite',
        'govengine': ROOT,
        'rexecop': ROOT.parent / 'rexecop',
        'tecrax': ROOT.parent / 'tecrax',
    }

    with pytest.raises(
        AssertionError,
        match='release_train_local_mode_rejects_cross_repo_roots',
    ):
        validate_release_train_truth(mode='local', cross_repo_roots=roots)
    with pytest.raises(
        AssertionError,
        match='release_train_cross_repo_roots_required',
    ):
        validate_release_train_truth(mode='cross-repo')
    with pytest.raises(SystemExit, match='2'):
        release_train_main(['--local', '--sclite-root', '/tmp/sclite'])


def test_historical_documents_are_outside_active_train_scan() -> None:
    assert 'CHANGELOG.md' not in ACTIVE_TRAIN_DOCS
    assert all('security-review' not in path for path in ACTIVE_TRAIN_DOCS)
