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
STATUSES = frozenset({'published_frozen', 'published_rc', 'pending_realignment'})
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
    if set(value) != {'schema_version', 'checked_at', 'components'}:
        raise AssertionError('release_train_unknown_top_level_field')
    if value.get('schema_version') != 'govengine.release_train.v1':
        raise AssertionError('release_train_schema_version_mismatch')
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', str(value.get('checked_at') or '')):
        raise AssertionError('release_train_checked_at_invalid')
    components = value.get('components')
    if not isinstance(components, Mapping) or tuple(components) != COMPONENTS:
        raise AssertionError('release_train_component_inventory_mismatch')
    for component_id, raw in components.items():
        if not isinstance(raw, Mapping):
            raise AssertionError(f'release_train_component_invalid:{component_id}')
        if set(raw) != {'project', 'version', 'status', 'dependencies'}:
            raise AssertionError(f'release_train_component_fields_invalid:{component_id}')
        if not all(
            isinstance(raw.get(field), str) and str(raw[field]).strip()
            for field in ('project', 'version', 'status')
        ):
            raise AssertionError(f'release_train_component_identity_invalid:{component_id}')
        if raw['status'] not in STATUSES:
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
    return value


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
    components = manifest['components']
    govengine_version = components['govengine']['version']
    sclite_version = components['sclite']['version']
    rexecop_version = components['rexecop']['version']
    tecrax = components['tecrax']
    stale_rexecop_pin = tecrax['dependencies']['rexecop']

    required = {
        'README.md': (
            f'govengine=={govengine_version}',
            f'sclite-core=={sclite_version}',
        ),
        'PUBLIC_STATUS.md': (
            f'govengine=={govengine_version}',
            f'rexecop=={rexecop_version}',
            'pending realignment',
        ),
        'PUBLISHING.md': (
            f'govengine {govengine_version}',
            f'rexecop {rexecop_version}',
            f'tecrax {tecrax["version"]}',
            f'rexecop=={stale_rexecop_pin}',
            'pending realignment',
        ),
        'docs/MIGRATING_TO_1.md': (
            f'govengine=={govengine_version}',
            f'rexecop=={rexecop_version}',
            f'Tecrax `{tecrax["version"]}`',
            f'rexecop=={stale_rexecop_pin}',
        ),
        'docs/README.md': ('release-train.json',),
        'docs/ROADMAP.md': (
            f'govengine {govengine_version}',
            f'rexecop {rexecop_version}',
            f'tecrax {tecrax["version"]}',
            f'rexecop {stale_rexecop_pin}',
            'pending repin',
        ),
        'docs/VALIDATION.md': ('validate_release_train_truth.py',),
    }
    for relative, markers in required.items():
        text = (root / relative).read_text(encoding='utf-8')
        for marker in markers:
            if marker not in text:
                raise AssertionError(f'release_train_doc_drift:{relative}:{marker}')


def _validate_cross_repo(
    manifest: Mapping[str, Any],
    cross_repo_roots: Mapping[str, Path],
) -> None:
    if set(cross_repo_roots) != set(COMPONENTS):
        raise AssertionError('release_train_cross_repo_inventory_mismatch')
    components = manifest['components']
    for component_id in COMPONENTS:
        _validate_component(
            component_id,
            components[component_id],
            cross_repo_roots[component_id],
        )
    current_rexecop = components['rexecop']['version']
    tecrax_rexecop = components['tecrax']['dependencies'].get('rexecop')
    pending = components['tecrax']['status'] == 'pending_realignment'
    if pending and tecrax_rexecop == current_rexecop:
        raise AssertionError('release_train_pending_component_is_aligned:tecrax')
    if not pending and tecrax_rexecop != current_rexecop:
        raise AssertionError('release_train_aligned_component_has_drift:tecrax')


def validate_release_train_truth(
    *,
    root: Path = ROOT,
    manifest_path: Path = MANIFEST_PATH,
    cross_repo_roots: Mapping[str, Path] | None = None,
) -> dict[str, str]:
    manifest = load_release_train(manifest_path)
    components = manifest['components']
    _validate_component('govengine', components['govengine'], root)
    _validate_active_docs(manifest, root=root)

    if cross_repo_roots is not None:
        _validate_cross_repo(manifest, cross_repo_roots)

    return {
        component_id: str(components[component_id]['version'])
        for component_id in COMPONENTS
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--cross-repo', action='store_true')
    parser.add_argument('--sclite-root', type=Path)
    parser.add_argument('--rexecop-root', type=Path)
    parser.add_argument('--tecrax-root', type=Path)
    args = parser.parse_args(argv)

    roots = None
    if args.cross_repo:
        projects = ROOT.parent
        roots = {
            'sclite': args.sclite_root or projects / 'sclite',
            'govengine': ROOT,
            'rexecop': args.rexecop_root or projects / 'rexecop',
            'tecrax': args.tecrax_root or projects / 'tecrax',
        }
    report = validate_release_train_truth(cross_repo_roots=roots)
    mode = 'cross_repo' if roots is not None else 'local'
    print(
        f'release_train_truth_ok:{mode}:'
        + ':'.join(f'{name}={version}' for name, version in report.items())
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
