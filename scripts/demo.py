#!/usr/bin/env python3
"""Generate an isolated logging demo or check one without installing dependencies."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / 'evals/demo'


def create(stack: str, destination: Path) -> None:
    destination = destination.absolute()
    if destination.exists() or destination.is_symlink():
        raise ValueError(f'Destination already exists: {destination}')
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Prepare the complete project before publishing it to the chosen destination.
    with tempfile.TemporaryDirectory(prefix='.logging-demo-', dir=destination.parent) as temporary:
        prepared = Path(temporary) / 'project'
        shutil.copytree(DEMO / 'template', prepared, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        shutil.copyfile(DEMO / 'backends' / f'{stack}.py', prepared / 'app/observability.py')
        shutil.copyfile(DEMO / f'requirements-{stack}.txt', prepared / 'requirements.txt')
        (prepared / 'demo.json').write_text(json.dumps({'schema_version': 1, 'stack': stack}, indent=2) + '\n')
        destination.mkdir()  # Exclusive reservation: never replace a competing create.
        for source in prepared.iterdir():
            shutil.move(str(source), destination / source.name)
    print(f'Created {stack} demo: {destination}')


def check(project: Path) -> dict:
    project = project.resolve()
    manifest = json.loads((project / 'demo.json').read_text())
    stack = manifest.get('stack')
    if manifest.get('schema_version') != 1 or stack not in ('stdlib', 'structlog'):
        raise ValueError('Unsupported demo manifest')
    python = project / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if not python.is_file():
        raise ValueError(f'Missing virtual environment: {python}. Follow the generated README.')
    environment = {key: value for key, value in os.environ.items() if key not in ('PYTHONPATH', 'PYTHONHOME')}
    environment['PYTHONDONTWRITEBYTECODE'] = '1'
    execution = subprocess.run(
        [str(python), '-I', '-B', str(DEMO / 'runner.py'), str(project)],
        cwd=project, env=environment, capture_output=True, text=True, timeout=60,
    )
    try:
        payload = json.loads(execution.stdout)
    except ValueError as exc:
        raise ValueError(f'Probe did not return JSON (exit {execution.returncode}): {execution.stderr[-4000:]}') from exc
    if execution.returncode or 'error' in payload:
        raise ValueError(payload.get('error', execution.stderr or 'Probe failed'))
    spec = importlib.util.spec_from_file_location('demo_grading', DEMO / 'grading.py')
    grading = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(grading)
    observed = payload['observations']
    observed['runtime'] = {}
    with tempfile.TemporaryDirectory(prefix='logging-runtime-') as temporary:
        for mode in ('server', 'formatter'):
            metadata = Path(temporary) / f'{mode}.json'
            runtime = subprocess.run(
                [str(python), '-I', '-B', str(DEMO / 'runtime_probe.py'),
                 str(project), mode, str(metadata)],
                cwd=project, env=environment, capture_output=True, text=True, timeout=45,
            )
            if runtime.returncode or not metadata.is_file():
                raise ValueError(f'{mode} runtime probe failed (exit {runtime.returncode}): '
                                 f'{runtime.stderr[-4000:]}')
            observed['runtime'][mode] = {
                **json.loads(metadata.read_text(encoding='utf-8')),
                'stdout': runtime.stdout, 'stderr': runtime.stderr,
            }
    criteria = grading.grade(observed, stack)
    return {'schema_version': 1, 'project': str(project), 'stack': stack,
            'checked_at': datetime.now(timezone.utc).isoformat(), 'versions': observed['versions'],
            'passed': all(item['passed'] for item in criteria), 'criteria': criteria,
            'observations': observed}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    generate = commands.add_parser('create')
    generate.add_argument('--stack', choices=('stdlib', 'structlog'), required=True)
    generate.add_argument('--dest', type=Path, required=True)
    verify = commands.add_parser('check')
    verify.add_argument('--project', type=Path, required=True)
    verify.add_argument('--report', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'create':
            create(args.stack, args.dest)
            return 0
        # Reserve output exclusively before executing project code.
        with args.report.open('x', encoding='utf-8') as output:
            try:
                report = check(args.project)
                status = 0 if report['passed'] else 1
            except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
                report = {'schema_version': 1, 'passed': None, 'error': str(exc)}
                status = 2
            json.dump(report, output, indent=2)
            output.write('\n')
        for criterion in report.get('criteria', []):
            print(f"{'PASS' if criterion['passed'] else 'FAIL'} {criterion['id']}")
        if 'error' in report:
            print(report['error'], file=sys.stderr)
        print(f'Report: {args.report}')
        return status
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
