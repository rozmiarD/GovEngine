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
    report = validate_release_train_truth()
    assert report == {
        'sclite': '2.0.1',
        'govengine': '1.0.0rc2',
        'rexecop': '1.0.0rc1',
        'tecrax': '0.4.0rc3',
    }


def test_active_docs_reject_stale_reference_runtime(tmp_path: Path) -> None:
    for relative in ACTIVE_TRAIN_DOCS:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        text = (ROOT / relative).read_text(encoding='utf-8')
        if relative == 'PUBLISHING.md':
            text = text.replace('rexecop 1.0.0rc1', 'rexecop 0.3.0rc3')
        target.write_text(text, encoding='utf-8')

    with pytest.raises(
        AssertionError,
        match='release_train_doc_drift:PUBLISHING.md:rexecop 1.0.0rc1',
    ):
        _validate_active_docs(load_release_train(), root=tmp_path)


def test_pending_tecrax_cannot_match_current_runtime(tmp_path: Path) -> None:
    manifest = copy.deepcopy(dict(load_release_train()))
    manifest['components']['tecrax']['dependencies']['rexecop'] = '1.0.0rc1'

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
        version='1.0.0rc1',
        dependencies=('govengine==1.0.0rc1', 'sclite-core==2.0.0'),
    )
    _write_project(
        roots['tecrax'],
        name='tecrax',
        version='0.4.0rc3',
        dependencies=(
            'govengine==1.0.0rc1',
            'rexecop==1.0.0rc1',
            'sclite-core==2.0.0',
        ),
    )

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
        version='1.0.0rc1',
        dependencies=('govengine==0.17.0rc2', 'sclite-core==2.0.0'),
    )
    _write_project(
        roots['tecrax'],
        name='tecrax',
        version='0.4.0rc3',
        dependencies=(
            'govengine==1.0.0rc1',
            'rexecop==0.3.0rc3',
            'sclite-core==2.0.0',
        ),
    )

    with pytest.raises(
        AssertionError,
        match=(
            'release_train_dependency_mismatch:rexecop:'
            'govengine:0.17.0rc2!=1.0.0rc1'
        ),
    ):
        _validate_cross_repo(manifest, roots)


def test_historical_documents_are_outside_active_train_scan() -> None:
    assert 'CHANGELOG.md' not in ACTIVE_TRAIN_DOCS
    assert all('security-review' not in path for path in ACTIVE_TRAIN_DOCS)
