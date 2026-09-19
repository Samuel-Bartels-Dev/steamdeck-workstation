#!/usr/bin/env python3
"""Explicit live test on an existing Docker engine; never starts/stops its daemon."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group()
    target.add_argument('--context', default='default', help='Existing CI/development Docker context with Compose and Buildx.')
    target.add_argument('--managed', action='store_true', help='Test the already configured managed rootless engine without changing its configuration.')
    args = parser.parse_args()
    # Keep this test out of normal install-time offline validation.
    with tempfile.TemporaryDirectory(prefix='deckctl-live-test-') as tmp:
        work = Path(tmp)
        env = {**os.environ, 'DECKCTL_CONFIG': str(work / 'config')}
        if args.managed:
            env = os.environ.copy()
        cli = [str(ROOT / 'bin/deckctl'), 'containers']
        def run(*arguments, check=True):
            return subprocess.run(cli + list(arguments), env=env, check=check, capture_output=True, text=True, timeout=300)
        if args.managed:
            before = json.loads(run('status', '--json', check=False).stdout)
            assert before['mode'] == 'managed' and before.get('rootless') and before.get('api_ready'), before
            run('test')
        else:
            run('install', '--context', args.context)
        data = json.loads(run('status', '--json').stdout)
        assert data['status'] == 'READY', data
        run('docker', '--', 'buildx', 'version')
        fixture = (ROOT / 'modules/dev/containers/compose-smoke.yaml').read_text()
        image = next(line.split('image: ', 1)[1] for line in fixture.splitlines() if 'image: ' in line)
        (work / 'Dockerfile').write_text(f'FROM {image}\nRUN printf "built-for-deckctl\\n" > /build-marker\n')
        compose = work / 'compose.yaml'
        compose.write_text(fixture.replace('    image: ' + image, '    build: .'))
        project = 'deckctl-build-' + uuid.uuid4().hex[:12]
        command = ['compose', '--', '--project-name', project, '--file', str(compose)]
        try:
            run(*command, 'up', '--build', '--detach', '--wait', '--wait-timeout', '60')
            assert run(*command, 'exec', '-T', 'probe', 'cat', '/build-marker').stdout.strip() == 'built-for-deckctl'
            assert run(*command, 'exec', '-T', 'probe', 'wget', '-qO-', 'http://127.0.0.1:8080').stdout.strip() == 'deckctl-container-ok'
        finally:
            run(*command, 'down', '--rmi', 'local', '--timeout', '10')
    print('Live Docker/Compose/Buildx test: PASS; daemon and unrelated projects preserved.')


if __name__ == '__main__':
    main()
