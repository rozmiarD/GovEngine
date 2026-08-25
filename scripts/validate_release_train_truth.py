#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import tomllib
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / 'docs' / 'release-train.json'
COMPONENTS = ('sclite', 'govengine', 'rexecop', 'tecrax')
PUBLISHED_COMPONENTS = ('sclite', 'govengine', 'rexecop')
PUBLISHED_STATUSES = frozenset({'published_frozen', 'published_rc'})
SOURCE_STATUSES = frozenset({
    'post_published_source',
    'source_candidate',
    'pending_realignment',
})
VALIDATION_MODES = frozenset({'local', 'cross-repo'})
STACK_PROJECTS = frozenset({'sclite-core', 'govengine', 'rexecop', 'tecrax'})
ACTIVE_TRAIN_DOCS = (
    'README.md',
    'PUBLIC_STATUS.md',
    'PUBLISHING.md',
    'docs/MIGRATING_TO_1.md',
    'docs/README.md',
    'docs/ROADMAP.md',
    'docs/VALIDATION.md',
)


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AssertionError(f'release_train_duplicate_key:{key}')
        result[key] = value
    return result


def load_release_train(path: Path = MANIFEST_PATH) -> Mapping[str, Any]:
    value = json.loads(
        path.read_text(encoding='utf-8'),
        object_pairs_hook=_strict_object,
        parse_constant=lambda value: (_ for _ in ()).throw(
            AssertionError(f'release_train_non_finite_number:{value}')
        ),
    )
    if not isinstance(value, Mapping):
        raise AssertionError('release_train_not_mapping')
    if set(value) != {
        'schema_version',
        'checked_at',
        'published_artifacts',
        'source_candidates',
    }:
        raise AssertionError('release_train_unknown_top_level_field')
    if value.get('schema_version') != 'govengine.release_train.v2':
        raise AssertionError('release_train_schema_version_mismatch')
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', str(value.get('checked_at') or '')):
        raise AssertionError('release_train_checked_at_invalid')
    published = value.get('published_artifacts')
    source = value.get('source_candidates')
    if not isinstance(published, Mapping) or tuple(published) != PUBLISHED_COMPONENTS:
        raise AssertionError('release_train_published_inventory_mismatch')
    if not isinstance(source, Mapping) or tuple(source) != COMPONENTS:
        raise AssertionError('release_train_source_inventory_mismatch')
    for collection, statuses in (
        (published, PUBLISHED_STATUSES),
        (source, SOURCE_STATUSES),
    ):
        for component_id, raw in collection.items():
            _validate_manifest_identity(component_id, raw, statuses=statuses)

    for component_id in PUBLISHED_COMPONENTS:
        published_identity = published[component_id]
        source_identity = source[component_id]
        if published_identity['project'] != source_identity['project']:
            raise AssertionError(
                f'release_train_project_identity_drift:{component_id}'
            )
        if source_identity['status'] == 'post_published_source' and (
            source_identity['version'] != published_identity['version']
            or source_identity['dependencies'] != published_identity['dependencies']
        ):
            raise AssertionError(
                f'release_train_published_source_identity_mismatch:{component_id}'
            )
    return value


def _validate_manifest_identity(
    component_id: str,
    raw: Any,
    *,
    statuses: frozenset[str],
) -> None:
    if not isinstance(raw, Mapping):
        raise AssertionError(f'release_train_component_invalid:{component_id}')
    if set(raw) != {'project', 'version', 'status', 'dependencies'}:
        raise AssertionError(f'release_train_component_fields_invalid:{component_id}')
    if not all(
        isinstance(raw.get(field), str) and str(raw[field]).strip()
        for field in ('project', 'version', 'status')
    ):
        raise AssertionError(f'release_train_component_identity_invalid:{component_id}')
    if raw['status'] not in statuses:
        raise AssertionError(f'release_train_component_status_invalid:{component_id}')
    dependencies = raw.get('dependencies')
    if not isinstance(dependencies, Mapping) or any(
        not isinstance(name, str)
        or not isinstance(version, str)
        or not name
        or not version
        for name, version in dependencies.items()
    ):
        raise AssertionError(f'release_train_dependencies_invalid:{component_id}')


def _project_truth(root: Path) -> tuple[str, str, dict[str, str]]:
    path = root / 'pyproject.toml'
    if not path.is_file():
        raise AssertionError(f'release_train_pyproject_missing:{root}')
    project = tomllib.loads(path.read_text(encoding='utf-8')).get('project')
    if not isinstance(project, Mapping):
        raise AssertionError(f'release_train_project_missing:{root}')
    name = str(project.get('name') or '')
    version = str(project.get('version') or '')
    dependencies: dict[str, str] = {}
    for raw in project.get('dependencies', ()):
        item = str(raw)
        match = re.fullmatch(r'([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+!-]+)', item)
        if match:
            dependencies[match.group(1).lower().replace('_', '-')] = match.group(2)
    return name, version, dependencies


def _validate_component(
    component_id: str,
    raw: Mapping[str, Any],
    root: Path,
) -> None:
    name, version, dependencies = _project_truth(root)
    if name != raw['project']:
        raise AssertionError(
            f'release_train_project_name_mismatch:{component_id}:{name}!={raw["project"]}'
        )
    if version != raw['version']:
        raise AssertionError(
            f'release_train_version_mismatch:{component_id}:{version}!={raw["version"]}'
        )
    expected_dependencies = dict(raw['dependencies'])
    for dependency, expected in expected_dependencies.items():
        actual = dependencies.get(dependency)
        if actual != expected:
            raise AssertionError(
                f'release_train_dependency_mismatch:{component_id}:'
                f'{dependency}:{actual}!={expected}'
            )
    actual_stack_dependencies = {
        name: version
        for name, version in dependencies.items()
        if name in STACK_PROJECTS
    }
    if actual_stack_dependencies != expected_dependencies:
        raise AssertionError(
            f'release_train_dependency_inventory_mismatch:{component_id}'
        )


def _validate_active_docs(manifest: Mapping[str, Any], *, root: Path = ROOT) -> None:
    for relative in ACTIVE_TRAIN_DOCS:
        if not (root / relative).is_file():
            raise AssertionError(f'release_train_active_doc_missing:{relative}')
    published = manifest['published_artifacts']
    source = manifest['source_candidates']
    published_govengine_version = published['govengine']['version']
    published_sclite_version = published['sclite']['version']
    govengine_version = source['govengine']['version']
    sclite_version = source['sclite']['version']
    published_rexecop_version = published['rexecop']['version']
    historical_govengine_version = published['rexecop']['dependencies']['govengine']
    source_rexecop_version = source['rexecop']['version']
    tecrax = source['tecrax']
    source_tecrax_rexecop_pin = tecrax['dependencies']['rexecop']

    required = {
        'README.md': (
            f'govengine=={govengine_version}',
            f'sclite-core=={sclite_version}',
        ),
        'PUBLIC_STATUS.md': (
            f'govengine=={govengine_version}',
            (
                '| Published reference runtime | '
                f'`rexecop=={published_rexecop_version}`; immutable rc1 artifact |'
            ),
            (
                '| RExecOp source candidate | '
                f'`rexecop=={source_rexecop_version}`; unpublished |'
            ),
            (
                '| Profile source candidate | '
                f'Tecrax `{tecrax["version"]}`; `pending_realignment`; '
                f'pins `rexecop=={source_tecrax_rexecop_pin}` |'
            ),
        ),
        'PUBLISHING.md': (
            f'govengine {govengine_version}',
            '`published_artifacts`',
            '`source_candidates`',
            f'Published RExecOp `{published_rexecop_version}` remains immutable',
            f'RExecOp source candidate `{source_rexecop_version}`',
            f'Tecrax `{tecrax["version"]}` remains `pending_realignment`',
            f'`rexecop=={source_tecrax_rexecop_pin}`',
        ),
        'docs/MIGRATING_TO_1.md': (
            (
                'Current public GovEngine target: '
                f'`govengine=={published_govengine_version}`.'
            ),
            (
                'Current public SCLite target: '
                f'`sclite-core=={published_sclite_version}`.'
            ),
            (
                'Current RExecOp source candidate: '
                f'`rexecop=={source_rexecop_version}` (unpublished).'
            ),
            (
                f'Tecrax `{tecrax["version"]}` status: `pending_realignment`;'
            ),
            f'`rexecop=={source_tecrax_rexecop_pin}`.',
            (
                'Historical immutable GovEngine artifact: '
                f'`govengine=={historical_govengine_version}`.'
            ),
            (
                'Historical immutable RExecOp artifact: '
                f'`rexecop=={published_rexecop_version}`.'
            ),
        ),
        'docs/README.md': ('release-train.json',),
        'docs/ROADMAP.md': (
            f'govengine=={govengine_version}',
            f'rexecop {published_rexecop_version}',
            f'rexecop {source_rexecop_version}',
            f'tecrax {tecrax["version"]}',
            f'rexecop {source_tecrax_rexecop_pin}',
            'pending realignment',
        ),
        'docs/VALIDATION.md': (
            'validate_release_train_truth.py',
            'published_artifacts',
            'source_candidates',
        ),
    }
    for relative, markers in required.items():
        text = (root / relative).read_text(encoding='utf-8')
        for marker in markers:
            if marker not in text:
                raise AssertionError(f'release_train_doc_drift:{relative}:{marker}')

    contradictory = {
        'PUBLIC_STATUS.md': ('source-aligned/unpublished',),
        'PUBLISHING.md': ('source-aligned/unpublished',),
        'docs/ROADMAP.md': ('source-aligned/unpublished',),
        'docs/VALIDATION.md': ('source-aligned/unpublished',),
        'docs/MIGRATING_TO_1.md': (
            'current source is aligned to the published rc1 train',
            (
                f'`govengine=={published_govengine_version}` source and '
                f'`sclite-core=={published_sclite_version}` are not public '
                'install targets'
            ),
        ),
    }
    for relative, markers in contradictory.items():
        text = (root / relative).read_text(encoding='utf-8')
        normalized_text = ' '.join(text.split()).casefold()
        for marker in markers:
            if ' '.join(marker.split()).casefold() in normalized_text:
                raise AssertionError(
                    f'release_train_doc_contradiction:{relative}:{marker}'
                )


def _validate_cross_repo(
    manifest: Mapping[str, Any],
    cross_repo_roots: Mapping[str, Path],
) -> None:
    if set(cross_repo_roots) != set(COMPONENTS):
        raise AssertionError('release_train_cross_repo_inventory_mismatch')
    components = manifest['source_candidates']
    for component_id in COMPONENTS:
        _validate_component(
            component_id,
            components[component_id],
            cross_repo_roots[component_id],
        )
    component_by_project = {
        raw['project']: component_id
        for component_id, raw in components.items()
    }
    for component_id, raw in components.items():
        drift: list[str] = []
        for project, version in raw['dependencies'].items():
            target_id = component_by_project.get(project)
            if target_id is None:
                continue
            current_version = components[target_id]['version']
            if version != current_version:
                drift.append(f'{project}:{version}!={current_version}')
        pending = raw['status'] == 'pending_realignment'
        if pending and not drift:
            raise AssertionError(
                f'release_train_pending_component_is_aligned:{component_id}'
            )
        if not pending and drift:
            raise AssertionError(
                f'release_train_source_dependency_drift:{component_id}:{drift}'
            )


def validate_release_train_truth(
    *,
    mode: str = 'local',
    root: Path = ROOT,
    manifest_path: Path = MANIFEST_PATH,
    cross_repo_roots: Mapping[str, Path] | None = None,
) -> dict[str, str]:
    if mode not in VALIDATION_MODES:
        raise AssertionError(f'release_train_validation_mode_invalid:{mode}')
    if mode == 'local' and cross_repo_roots is not None:
        raise AssertionError('release_train_local_mode_rejects_cross_repo_roots')
    if mode == 'cross-repo' and cross_repo_roots is None:
        raise AssertionError('release_train_cross_repo_roots_required')
    manifest = load_release_train(manifest_path)
    published = manifest['published_artifacts']
    source = manifest['source_candidates']
    _validate_component('govengine', source['govengine'], root)
    _validate_active_docs(manifest, root=root)

    if mode == 'cross-repo':
        assert cross_repo_roots is not None
        _validate_cross_repo(manifest, cross_repo_roots)

    return {
        **{
            f'published_{component_id}': str(published[component_id]['version'])
            for component_id in PUBLISHED_COMPONENTS
        },
        **{
            f'source_{component_id}': str(source[component_id]['version'])
            for component_id in COMPONENTS
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--local', action='store_true')
    mode.add_argument('--cross-repo', action='store_true')
    parser.add_argument('--sclite-root', type=Path)
    parser.add_argument('--rexecop-root', type=Path)
    parser.add_argument('--tecrax-root', type=Path)
    args = parser.parse_args(argv)

    explicit_roots = (args.sclite_root, args.rexecop_root, args.tecrax_root)
    if not args.cross_repo and any(root is not None for root in explicit_roots):
        parser.error('sibling root arguments require --cross-repo')

    roots = None
    if args.cross_repo:
        projects = ROOT.parent
        roots = {
            'sclite': args.sclite_root or projects / 'sclite',
            'govengine': ROOT,
            'rexecop': args.rexecop_root or projects / 'rexecop',
            'tecrax': args.tecrax_root or projects / 'tecrax',
        }
    selected_mode = 'cross-repo' if args.cross_repo else 'local'
    report = validate_release_train_truth(
        mode=selected_mode,
        cross_repo_roots=roots,
    )
    print(
        f'release_train_truth_ok:{selected_mode}:'
        + ':'.join(f'{name}={version}' for name, version in report.items())
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
