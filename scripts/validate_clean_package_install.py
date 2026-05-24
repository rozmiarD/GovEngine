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
