from __future__ import annotations

import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLISHED_VERSION = '0.16.10'


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding='utf-8')


def _project_version() -> str:
    return str(tomllib.loads(_read('pyproject.toml'))['project']['version'])


def test_current_public_docs_track_package_version() -> None:
    version = _project_version()
    docs = {
        'README.md': _read('README.md'),
        'PUBLIC_STATUS.md': _read('PUBLIC_STATUS.md'),
        'docs/ROADMAP.md': _read('docs/ROADMAP.md'),
        'docs/VALIDATION.md': _read('docs/VALIDATION.md'),
    }

    assert f'govengine=={version}' in docs['docs/ROADMAP.md']
    assert f'govengine=={version}' in docs['PUBLIC_STATUS.md']
    assert f'Expected result for the current `{version}` package line' in docs['docs/VALIDATION.md']
    assert f'Current supported stack line: `govengine=={version}`' in docs['README.md']
    assert f'python -m pip install govengine=={PUBLISHED_VERSION}' in docs['README.md']
    assert 'Current 0.12.x alpha line' not in docs['docs/ROADMAP.md']
    assert 'published `0.12` alpha line' not in docs['README.md']


def test_docs_pin_canonical_lifecycle_vocabulary_and_legacy_alias_status() -> None:
    docs = '\n'.join((
        _read('README.md'),
        _read('docs/SCLITE_INTEGRATION.md'),
        _read('docs/API_STABILITY_MATRIX.md'),
        _read('docs/VALIDATION.md'),
    ))

    assert 'verified_chain' in docs
    assert 'verified_lifecycle' in docs
    assert 'chain_verified' in docs
    assert 'lifecycle_verified' in docs
    assert 'migration aliases' in docs or 'migration shims' in docs


def test_docs_keep_runtime_shell_projection_separate_from_state_machine() -> None:
    state_machine = _read('docs/STATE_MACHINE.md')
    runtime_shell = _read('docs/RUNTIME_SHELL.md')

    assert 'host projection state only' in state_machine
    assert 'must not be copied into' in state_machine
    assert 'projection states' in runtime_shell
    assert 'running_live' in state_machine
    assert 'running_live' in runtime_shell


def test_docs_classify_contract_proofs_as_conformance_artifacts_not_authority() -> None:
    matrix = _read('docs/API_STABILITY_MATRIX.md')
    boundary = _read('docs/API_BOUNDARY.md')

    assert 'conformance artifacts' in boundary or 'proof fixtures' in boundary
    assert 'fixture' in matrix
    assert 'not production authority' in matrix or 'not production authority' in boundary or 'Non-claims' in boundary
