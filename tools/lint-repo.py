#!/usr/bin/env python3
"""Run read-only correctness checks for tracked repository source files."""
import argparse
from collections import defaultdict
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
# Narrow exceptions preserve known release behavior. See docs/CONTRIBUTING.md.
SHELL_EXCEPTIONS = {
    'modules/terminal/terminal.sh': ('SC2120', 'SC2164'),
    'modules/dev/install-codex.sh': ('SC2034',),
    'modules/backup/verify.sh': ('SC2088',),
}


def run(command):
    subprocess.run(command, cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''REQUIREMENTS
  Git checkout, Python 3.12+, Bash, Ruff 0.11.13, ShellCheck 0.10.0,
  and actionlint 1.7.7 on PATH. See docs/CONTRIBUTING.md for setup.
BEHAVIOR
  Checks tracked Python and shell files, workflow definitions, local Markdown
  links and generated command documentation. Stage new files before running.
  Does not install tools, execute provisioning, modify files or auto-fix code.
EXIT STATUS
  0  All checks passed.
  1  A check failed.
  2  Invalid arguments, missing tools, or an unavailable Git checkout.
EXAMPLES
  python3 tools/lint-repo.py
  python3 tools/lint-repo.py --help''',
    )
    parser.parse_args()
    missing = [name for name in ('git', 'bash', 'ruff', 'shellcheck', 'actionlint')
               if shutil.which(name) is None]
    if missing:
        parser.error('Missing development tools: ' + ', '.join(missing))
    listing = subprocess.run(['git', 'ls-files', '-z'], cwd=ROOT,
                             capture_output=True, check=False)
    if listing.returncode:
        parser.error('Run from a Git checkout; see docs/CONTRIBUTING.md')
    paths = [Path(p.decode()) for p in listing.stdout.split(b'\0') if p]
    python_files = []
    shell_groups = defaultdict(list)
    for path in paths:
        full = ROOT / path
        if not full.is_file() or full.is_symlink():
            continue
        with full.open('rb') as stream:
            first = stream.readline(256).decode('utf-8', errors='replace').strip()
        if path.suffix == '.py' or (first.startswith('#!') and 'python' in first):
            python_files.append(str(path))
        if path.suffix == '.sh' or first in ('#!/bin/bash', '#!/usr/bin/env bash',
                                             '#!/bin/sh', '#!/usr/bin/env sh'):
            # .sh snippets without a shebang in this project are Bash snippets.
            shell = 'sh' if first in ('#!/bin/sh', '#!/usr/bin/env sh') else 'bash'
            run([shell, '-n', str(path)])
            shell_groups[(shell, SHELL_EXCEPTIONS.get(str(path), ()))].append(str(path))
    if not python_files or not shell_groups:
        parser.error('No tracked Python/shell files found; stage source files first')
    run(['ruff', 'check', '--no-cache', '--config', 'ruff.toml', *python_files])
    for (shell, exceptions), files in shell_groups.items():
        command = ['shellcheck', '--severity=warning', '--shell=' + shell]
        if exceptions:
            command += ['--exclude=' + ','.join(exceptions)]
        run(command + files)
    workflows = [str(p) for p in paths if p.parent == Path('.github/workflows')
                 and p.suffix in ('.yml', '.yaml')]
    if not workflows:
        parser.error('No tracked GitHub workflows found')
    run(['actionlint', '-color', *workflows])
    run([sys.executable, 'tools/check-docs.py'])
    run([sys.executable, 'tools/render-command-docs.py', '--check'])
    print(f'PR static checks: PASS ({len(python_files)} Python, '
          f'{sum(map(len, shell_groups.values()))} shell, {len(workflows)} workflows)')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f'Lint failed: {exc.cmd[0]} exited {exc.returncode}', file=sys.stderr)
        raise SystemExit(1) from exc
