from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path
from typing import Iterable
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
ROOT_PUBLIC_DOCS = (
    'README.md',
    'CHANGELOG.md',
    'CONTRIBUTING.md',
    'PUBLISHING.md',
    'PUBLIC_STATUS.md',
    'SECURITY.md',
)
EXTERNAL_SCRIPT_OWNERS = {
    'scripts/run_alpha_signoff_checks.sh': 'RExecOp',
    'scripts/validate_g3_runtime_governance_gate.py': 'RExecOp',
    'scripts/validate_g6_release_candidate_gate.py': 'RExecOp',
    'scripts/validate_governance_conformance.py': 'RExecOp',
    'scripts/validate_release_train_preflight.py': 'RExecOp',
}
REQUIRED_RELEASE_DISCLOSURES = {
    'README.md': (
        'Current source is `1.0.0rc2`;',
        'candidate was published from `v1.0.0rc2`',
        'observation window is elapsed_unclosed',
        '| Source/package version | `1.0.0rc2` published; observation elapsed_unclosed |',
    ),
    'PUBLIC_STATUS.md': (
        'Current source version | `govengine==1.0.0rc2`; published; RC observation elapsed_unclosed',
        'Latest published PyPI package: `govengine==1.0.0rc2`',
    ),
    'PUBLISHING.md': (
        'Current source version: `1.0.0rc2`, published; RC observation is elapsed_unclosed.',
        'govengine 1.0.0rc2 governance; published RC, observation elapsed_unclosed',
        '31254483143',
        'validate_release_readiness.py` intentionally reports '
        'stable promotion as `publishable=false`',
    ),
    'docs/ROADMAP.md': (
        '`1.0.0rc2` is required before stable promotion',
        'observation is elapsed_unclosed',
    ),
    'docs/VALIDATION.md': (
        'Expected result for the current `1.0.0rc2` package line: published release',
        'Observation is elapsed_unclosed',
    ),
    'SECURITY.md': (
        'published `1.0.0rc2` release candidate',
        'elapsed_unclosed',
        'Final `1.0.0`\npromotion requires the candidate observation window to complete',
    ),
}
FORBIDDEN_CURRENT_RC_ACTIVE_CLAIMS = {
    'README.md': ('`1.0.0rc2` published; observation active',),
    'PUBLISHING.md': ('govengine 1.0.0rc2    governance; published RC, observation active',),
}
FORBIDDEN_OWNERSHIP_PATTERNS = (
    re.compile(
        r'\bGovEngine\s+(?:owns|executes|performs|runs|dispatches|schedules)\s+'
        r'(?:the\s+)?(?:operation lifecycle|queues?|leases?|fencing|runtime permits?|'
        r'connectors?|retries|rollback|'
        r'(?:(?:live|connector|network|subprocess)\s+)+I/O)\b',
        re.IGNORECASE,
    ),
    re.compile(
        r'\bGovEngine\s+(?:is|acts as)\s+(?:an?\s+)?'
        r'(?:execution runtime|scheduler|queue|connector runtime|truth layer)\b',
        re.IGNORECASE,
    ),
    re.compile(
        r'\b(?:operation lifecycle|queues?|leases?|fencing|runtime permits?|'
        r'connectors?|retries|rollback|'
        r'(?:(?:live|connector|network|subprocess)\s+)+I/O)\s+'
        r'(?:is|are)\s+(?:owned|executed|performed|run|dispatched|scheduled|handled)\s+'
        r'by\s+GovEngine\b',
        re.IGNORECASE,
    ),
    re.compile(
        r'\bSCLite\s+owns\s+(?:policy|governance|approval|admission|runtime execution)\b',
        re.IGNORECASE,
    ),
    re.compile(
        r'\bRExecOp\s+owns\s+(?:policy|governance|approval|admission decisions?)\b',
        re.IGNORECASE,
    ),
)
FORBIDDEN_RELEASE_PATTERNS = (
    re.compile(r'\bpublishable\s*=\s*true\b', re.IGNORECASE),
    re.compile(r'\bmay\s+be\s+promoted\s+directly\s+to\s+stable\b', re.IGNORECASE),
)
CURRENT_VERSION_CLAIM = re.compile(
    r'\bcurrent\s+(?:GovEngine|source/package|source|package)\s+version\s*[:=]?\s*'
    r'`?(?:govengine==)?'
    r'(?P<version>\d+\.\d+\.\d+(?:[A-Za-z][A-Za-z0-9.-]*)?)`?',
    re.IGNORECASE,
)
MARKDOWN_LINK = re.compile(r'!?\[[^\]]*\]\(([^)\n]+)\)')
PATH_REFERENCE = re.compile(
    r'(?<![\w.-])'
    r'((?:\.github/|docs/|govengine/|scripts/|tests/)'
    r'[A-Za-z0-9_./*-]+\.(?:md|py|json|yaml|yml|sh))'
)
BACKTICK_FILE_REFERENCE = re.compile(r'`([^`\n]+\.(?:md|py|json|yaml|yml|sh))`')
CLI_COMMAND = re.compile(r'\b(govengine-(?:policy|supervisor))\s+([a-z][a-z0-9-]*)')
MARKDOWN_HEADING = re.compile(r'^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$', re.MULTILINE)


def active_markdown_paths(root: Path = ROOT) -> tuple[Path, ...]:
    paths = [root / relative for relative in ROOT_PUBLIC_DOCS]
    paths.extend(
        path
        for path in sorted((root / 'docs').rglob('*.md'))
        if 'archive' not in path.relative_to(root / 'docs').parts
    )
    missing = [path.relative_to(root).as_posix() for path in paths if not path.is_file()]
    if missing:
        raise AssertionError(f'active_documentation_missing:{",".join(missing)}')
    return tuple(paths)


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _link_target(raw: str) -> str:
    target = raw.strip()
    if target.startswith('<') and '>' in target:
        return target[1 : target.index('>')]
    return target.split(maxsplit=1)[0]


def _markdown_heading_anchors(path: Path) -> set[str]:
    anchors: set[str] = set()
    occurrences: dict[str, int] = {}
    for heading in MARKDOWN_HEADING.findall(path.read_text(encoding='utf-8')):
        normalized = re.sub(r'!\[([^\]]*)\]\([^)]+\)', r'\1', heading)
        normalized = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', normalized)
        normalized = re.sub(r'<[^>]+>', '', normalized)
        normalized = normalized.replace('`', '').replace('*', '').replace('_', '')
        normalized = ''.join(
            character
            for character in normalized.lower()
            if character.isalnum() or character in {' ', '-'}
        )
        base = re.sub(r'\s+', '-', normalized.strip())
        if not base:
            continue
        occurrence = occurrences.get(base, 0)
        occurrences[base] = occurrence + 1
        anchors.add(base if occurrence == 0 else f'{base}-{occurrence}')
    return anchors


def validate_markdown_links(paths: Iterable[Path], *, root: Path = ROOT) -> None:
    allowed_schemes = ('https://', 'http://', 'mailto:')
    for path in paths:
        text = path.read_text(encoding='utf-8')
        for raw_target in MARKDOWN_LINK.findall(text):
            target = _link_target(raw_target)
            if not target or target.startswith(allowed_schemes):
                continue
            if re.match(r'^[A-Za-z][A-Za-z0-9+.-]*:', target):
                raise AssertionError(
                    f'{_relative(path, root)}:unsupported_markdown_link_scheme:{target}'
                )
            target_path, separator, fragment = target.partition('#')
            local = path.resolve() if not target_path else (path.parent / target_path).resolve()
            try:
                local.relative_to(root.resolve())
            except ValueError as exc:
                raise AssertionError(
                    f'{_relative(path, root)}:markdown_link_escapes_repository:{target}'
                ) from exc
            if not local.exists():
                raise AssertionError(
                    f'{_relative(path, root)}:broken_markdown_link:{target}'
                )
            if separator and fragment and local.suffix.lower() == '.md':
                anchor = unquote(fragment).lower()
                if anchor not in _markdown_heading_anchors(local):
                    raise AssertionError(
                        f'{_relative(path, root)}:broken_markdown_anchor:{target}'
                    )


def _index_targets(index_path: Path) -> set[str]:
    targets = set()
    for raw_target in MARKDOWN_LINK.findall(index_path.read_text(encoding='utf-8')):
        target = _link_target(raw_target).split('#', 1)[0]
        if target and not target.startswith(('https://', 'http://', 'mailto:', '#')):
            targets.add((index_path.parent / target).resolve().as_posix())
    return targets


def validate_documentation_index(*, root: Path = ROOT) -> None:
    index = root / 'docs' / 'README.md'
    targets = _index_targets(index)
    missing = [
        path.name
        for path in sorted((root / 'docs').glob('*.md'))
        if path.name != 'README.md' and path.resolve().as_posix() not in targets
    ]
    if missing:
        raise AssertionError(f'docs/README.md:unindexed_active_docs:{",".join(missing)}')


def _normalize_reference(value: str) -> str:
    reference = value.strip()
    for prefix in ('.venv/bin/python ', 'python3 ', 'python '):
        if reference.startswith(prefix):
            reference = reference[len(prefix) :]
    return reference


def _current_truth_text(path: Path, text: str) -> str:
    if path.name != 'CHANGELOG.md':
        return text
    match = re.search(
        r'^## Unreleased\s*$(?P<section>.*?)(?=^##\s+|\Z)',
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    return match.group('section') if match else ''


def _reference_path(reference: str, source: Path, root: Path) -> Path | None:
    if reference in EXTERNAL_SCRIPT_OWNERS:
        return None
    if reference == 'publish.yml':
        return root / '.github' / 'workflows' / reference
    if '/' in reference:
        return root / reference
    if reference.startswith('test_') and reference.endswith('.py'):
        return root / 'tests' / reference
    if reference.startswith(('validate_', 'generate_', 'run_')) and reference.endswith(
        ('.py', '.sh')
    ):
        return root / 'scripts' / reference
    candidate = source.parent / reference
    if reference.endswith('.md') and not candidate.is_file():
        root_candidate = root / reference
        if root_candidate.is_file():
            return root_candidate
    return candidate


def validate_document_references(paths: Iterable[Path], *, root: Path = ROOT) -> None:
    for path in paths:
        text = path.read_text(encoding='utf-8')
        text = _current_truth_text(path, text)
        references = set(PATH_REFERENCE.findall(text))
        references.update(
            _normalize_reference(value)
            for value in BACKTICK_FILE_REFERENCE.findall(text)
        )
        for reference in sorted(references):
            if '*' in reference:
                continue
            if reference in EXTERNAL_SCRIPT_OWNERS:
                owner = EXTERNAL_SCRIPT_OWNERS[reference]
                if owner not in text:
                    raise AssertionError(
                        f'{_relative(path, root)}:external_reference_owner_missing:'
                        f'{reference}:{owner}'
                    )
                continue
            target = _reference_path(reference, path, root)
            if target is not None and not target.is_file():
                raise AssertionError(
                    f'{_relative(path, root)}:missing_documented_file:{reference}'
                )


def validate_documented_cli_commands(
    paths: Iterable[Path],
    *,
    supported_commands: Iterable[str],
    root: Path = ROOT,
) -> None:
    supported = set(supported_commands)
    for path in paths:
        text = path.read_text(encoding='utf-8')
        for entrypoint, command in CLI_COMMAND.findall(text):
            documented = f'{entrypoint} {command}'
            if documented not in supported:
                raise AssertionError(
                    f'{_relative(path, root)}:unknown_documented_cli_command:{documented}'
                )


def validate_ownership_claims(paths: Iterable[Path], *, root: Path = ROOT) -> None:
    for path in paths:
        if 'security-review' in path.parts:
            continue
        text = path.read_text(encoding='utf-8')
        text = _current_truth_text(path, text)
        for pattern in FORBIDDEN_OWNERSHIP_PATTERNS:
            match = pattern.search(text)
            if match:
                claim = ' '.join(match.group(0).split())
                raise AssertionError(
                    f'{_relative(path, root)}:forbidden_ownership_claim:{claim}'
                )


def validate_current_version_claims(
    paths: Iterable[Path],
    *,
    expected_version: str,
    root: Path = ROOT,
) -> None:
    for path in paths:
        text = _current_truth_text(path, path.read_text(encoding='utf-8'))
        for match in CURRENT_VERSION_CLAIM.finditer(text):
            claimed = match.group('version')
            if claimed != expected_version:
                raise AssertionError(
                    f'{_relative(path, root)}:stale_current_version:'
                    f'{claimed}:expected={expected_version}'
                )


def validate_release_claims(paths: Iterable[Path], *, root: Path = ROOT) -> None:
    for path in paths:
        if 'security-review' in path.parts:
            continue
        text = _current_truth_text(path, path.read_text(encoding='utf-8'))
        for pattern in FORBIDDEN_RELEASE_PATTERNS:
            match = pattern.search(text)
            if match:
                claim = ' '.join(match.group(0).split())
                raise AssertionError(
                    f'{_relative(path, root)}:contradictory_release_claim:{claim}'
                )


def validate_release_disclosures(*, root: Path = ROOT) -> None:
    for relative, markers in REQUIRED_RELEASE_DISCLOSURES.items():
        text = (root / relative).read_text(encoding='utf-8')
        normalized_text = ' '.join(text.split())
        for marker in markers:
            if ' '.join(marker.split()) not in normalized_text:
                raise AssertionError(f'{relative}:missing_release_disclosure:{marker}')


def validate_current_rc_observation_claims(*, root: Path = ROOT) -> None:
    for relative, stale_claims in FORBIDDEN_CURRENT_RC_ACTIVE_CLAIMS.items():
        normalized_text = ' '.join((root / relative).read_text(encoding='utf-8').split())
        for stale_claim in stale_claims:
            if ' '.join(stale_claim.split()) in normalized_text:
                raise AssertionError(
                    f'{relative}:stale_current_rc_observation_claim:{stale_claim}'
                )


def validate_documentation_antidrift(
    *,
    root: Path = ROOT,
    supported_commands: Iterable[str],
) -> dict[str, int]:
    paths = active_markdown_paths(root)
    validate_markdown_links(paths, root=root)
    validate_documentation_index(root=root)
    validate_document_references(paths, root=root)
    validate_documented_cli_commands(
        paths,
        supported_commands=supported_commands,
        root=root,
    )
    validate_ownership_claims(paths, root=root)
    project = tomllib.loads((root / 'pyproject.toml').read_text(encoding='utf-8'))
    validate_current_version_claims(
        paths,
        expected_version=str(project['project']['version']),
        root=root,
    )
    validate_release_claims(paths, root=root)
    validate_release_disclosures(root=root)
    validate_current_rc_observation_claims(root=root)
    return {'active_markdown_files': len(paths)}


def main() -> int:
    from govengine.cli_contracts import cli_contract_registry

    supported = {
        str(contract['command'])
        for contract in cli_contract_registry()['contracts']
    }
    result = validate_documentation_antidrift(supported_commands=supported)
    print(
        'documentation_antidrift_ok:'
        f"active_docs={result['active_markdown_files']}"
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
