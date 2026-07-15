#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
INSTALLED_SURFACE_SMOKE = """\
import importlib.util
from importlib.resources import files
import govengine
import govengine.v1 as govengine_v1
from govengine import public_surface_index
from govengine.policy import baseline_policy_pack, validate_policy_pack

expected = [
    'artifact_governance_core',
    'planning_contracts_core',
    'admission_policy_core',
    'evidence_review_core',
    'domain_profile_sdk',
    'runtime_contract_proofs',
    'controlled_execution_core',
]
retired = [
    'govengine.sclite_adapter',
    'govengine.security_profile',
    'govengine.scope',
    'govengine.action_schema',
    'govengine.action_validators',
    'govengine.action_compiler',
    'govengine.capability_recipes',
    'govengine.tool_registry',
    'govengine.semantic_loss_policy',
    'govengine.policy.core',
    'govengine.policy.gateway',
    'govengine.contracts.signal',
    'govengine.contracts.analysis',
    'govengine.contracts.evidence_policy',
]
def absent(module):
    try:
        return importlib.util.find_spec(module) is None
    except ModuleNotFoundError:
        return True

assert govengine.__version__ == '0.17.0rc2'
assert len(govengine_v1.__all__) == 32
assert govengine_v1.PolicyEngine is govengine.PolicyEngine
assert [surface.name for surface in public_surface_index()] == expected
assert all(absent(module) for module in retired)
assert validate_policy_pack(baseline_policy_pack('governed-runtime')).ok
assert not files('govengine').joinpath('capability_recipes.yaml').is_file()
assert not files('govengine').joinpath('tool_registry.yaml').is_file()
print('installed_surface_smoke_ok:govengine==0.17.0rc2:surfaces=7:policy_authoring=ok')
"""


def _run(command: list[str], *, cwd: Path = ROOT, dry_run: bool = False) -> dict[str, Any]:
    if dry_run:
        return {
            'command': command,
            'cwd': str(cwd),
            'returncode': 0,
            'status': 'planned',
            'stdout': '',
            'stderr': '',
        }
    env = dict(os.environ)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    proc = subprocess.run(command, cwd=str(cwd), text=True, capture_output=True, check=False, env=env)
    return {
        'command': command,
        'cwd': str(cwd),
        'returncode': proc.returncode,
        'status': 'passed' if proc.returncode == 0 else 'failed',
        'stdout': proc.stdout.strip(),
        'stderr': proc.stderr.strip(),
    }


def _python(venv: Path) -> Path:
    return venv / ('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')


def build_plan(
    *,
    venv: Path,
    dev: bool,
    sclite_source: Path | None,
    editable: bool,
    python_bin: str,
) -> list[list[str]]:
    venv_python = str(_python(venv))
    target = '.[dev]' if dev else '.'
    install = ['-m', 'pip', 'install', '-e', target] if editable else ['-m', 'pip', 'install', target]
    commands: list[list[str]] = [
        [python_bin, '-m', 'venv', str(venv)],
        [venv_python, '-m', 'pip', 'install', '--upgrade', 'pip'],
    ]
    if sclite_source is not None:
        commands.append([venv_python, '-m', 'pip', 'install', str(sclite_source.resolve())])
    commands.append([venv_python, *install])
    commands.extend(
        [
            [venv_python, '-I', '-c', INSTALLED_SURFACE_SMOKE],
            [venv_python, 'scripts/validate_public_truth.py'],
            [venv_python, 'scripts/validate_alpha_readiness.py'],
        ]
    )
    if dev:
        commands.append([venv_python, '-m', 'pytest', '-q', '-o', f'cache_dir={venv}/pytest-cache'])
    commands.append([venv_python, '-m', 'pip', 'check'])
    return commands


def validate_clean_install(
    *,
    venv: Path,
    dev: bool,
    sclite_source: Path | None,
    editable: bool,
    dry_run: bool,
    python_bin: str,
) -> dict[str, Any]:
    if venv.exists() and not dry_run:
        return {
            'artifact_type': 'govengine_clean_package_install_validation',
            'schema_version': 'v0.1',
            'status': 'failed',
            'venv': str(venv),
            'error': 'venv_already_exists_choose_new_path',
            'steps': [],
        }

    steps = []
    for command in build_plan(
        venv=venv,
        dev=dev,
        sclite_source=sclite_source,
        editable=editable,
        python_bin=python_bin,
    ):
        step = _run(command, dry_run=dry_run)
        steps.append(step)
        if step['returncode'] != 0:
            break

    failed = [step for step in steps if step['returncode'] != 0]
    return {
        'artifact_type': 'govengine_clean_package_install_validation',
        'schema_version': 'v0.1',
        'status': 'planned' if dry_run else ('passed' if not failed else 'failed'),
        'mode': 'dev' if dev else 'runtime',
        'venv': str(venv),
        'editable': bool(editable),
        'sclite_source': str(sclite_source.resolve()) if sclite_source else None,
        'steps': steps,
        'non_claims': [
            'Does not authorize live target execution.',
            'Does not prove package publication or production readiness.',
            'Uses a disposable virtual environment so pip check is scoped to the install under validation.',
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description='Validate GovEngine source/package readiness in a clean virtual environment.')
    parser.add_argument('--venv', required=True, type=Path, help='New virtualenv path. The path must not already exist.')
    parser.add_argument('--dev', action='store_true', help='Install development extras and run pytest.')
    parser.add_argument('--sclite-source', type=Path, help='Optional local SCLite source tree to install before GovEngine.')
    parser.add_argument('--no-editable', action='store_true', help='Install GovEngine from the current tree non-editably.')
    parser.add_argument('--python', default=sys.executable, help='Python interpreter used to create the virtualenv.')
    parser.add_argument('--dry-run', action='store_true', help='Emit the command plan without creating the virtualenv.')
    parser.add_argument('--json', action='store_true', help='Emit machine-readable JSON only.')
    args = parser.parse_args()

    report = validate_clean_install(
        venv=args.venv,
        dev=args.dev,
        sclite_source=args.sclite_source,
        editable=not args.no_editable,
        dry_run=args.dry_run,
        python_bin=args.python,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(
            f"govengine_clean_package_install_validation:{report.get('mode', '-')}:"
            f"{report['status']}:venv={report['venv']}"
        )
        if report.get('error'):
            print(f"error {report['error']}")
        for step in report.get('steps', []):
            print(f"{step['status']} {' '.join(step['command'])}")
            if step['status'] == 'failed':
                if step.get('stdout'):
                    print(step['stdout'])
                if step.get('stderr'):
                    print(step['stderr'], file=sys.stderr)
    return 0 if report['status'] in {'passed', 'planned'} else 1


if __name__ == '__main__':
    raise SystemExit(main())
