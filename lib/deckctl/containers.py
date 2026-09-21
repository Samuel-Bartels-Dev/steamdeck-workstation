"""Opt-in Docker development tooling; never modifies the SteamOS system image."""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import pwd
import re
import shutil
import subprocess
import tarfile
import tempfile
import time
import urllib.request
import uuid

from . import core

UNIT = 'deckctl-docker.service'
MARKER = '# Managed by deckctl containers\n'
MANIFEST = core.ROOT / 'modules/dev/containers/downloads.json'
MAX_DOWNLOAD = 256 * 1024 * 1024


def paths():
    base = Path.home() / '.local/share/deckctl/containers'
    return base, core.CONFIG_HOME / 'containers.json', Path.home() / '.config/systemd/user' / UNIT


def config():
    value = core.load_json(paths()[1], {})
    if not isinstance(value, dict):
        raise ValueError('Invalid containers configuration')
    return value


def execute(args, *, env=None, timeout=30):
    return subprocess.run(args, env=env, capture_output=True, text=True, timeout=timeout)


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def download(asset, destination):
    url = asset['url']
    if not url.startswith(('https://download.docker.com/', 'https://github.com/docker/compose/releases/download/', 'https://github.com/docker/buildx/releases/download/')):
        raise ValueError('Unapproved Docker asset source')
    size = 0
    with urllib.request.urlopen(url, timeout=60) as response, destination.open('wb') as stream:
        while chunk := response.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_DOWNLOAD:
                raise ValueError('Download exceeds size limit')
            stream.write(chunk)
    if digest(destination) != asset['sha256']:
        raise ValueError('Docker asset checksum mismatch')


def unpack(archive, destination):
    """Only flat regular files below the two documented upstream archive roots."""
    with tarfile.open(archive) as tar:
        members = tar.getmembers()
        if len(members) > 64 or sum(m.size for m in members) > 768 * 1024 * 1024:
            raise ValueError('Archive exceeds extraction budget')
        names = set()
        for member in members:
            parts = member.name.split('/')
            if member.isdir() and member.name.rstrip('/') in {'docker', 'docker-rootless-extras'}:
                continue
            if (not member.isfile() or len(parts) != 2 or
                    parts[0] not in {'docker', 'docker-rootless-extras'} or
                    not re.fullmatch(r'[A-Za-z0-9_.-]+', parts[1]) or parts[1] in {'.', '..'} or
                    parts[1] in names or (destination / parts[1]).exists()):
                raise ValueError('Unexpected or unsafe Docker archive member')
            names.add(parts[1])
        for member in members:
            if member.isdir():
                continue
            target = destination / member.name.split('/')[1]
            with tar.extractfile(member) as source, target.open('xb') as output:
                shutil.copyfileobj(source, output)
            target.chmod(0o755)


def prerequisites():
    problems = []
    if os.geteuid() == 0:
        problems.append('Run as the Desktop user, not root.')
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        problems.append('Managed installation supports Linux x86_64 only.')
    for command in ('newuidmap', 'newgidmap', 'iptables', 'systemctl', 'unshare'):
        if not shutil.which(command):
            problems.append(f'Missing host prerequisite: {command}')
    if not any(shutil.which(c) for c in ('slirp4netns', 'pasta', 'vpnkit', 'gvproxy')):
        problems.append('A rootless network helper is required: slirp4netns, pasta, vpnkit or gvproxy.')
    username = pwd.getpwuid(os.getuid()).pw_name
    for name in ('subuid', 'subgid'):
        try:
            lines = (Path('/etc') / name).read_text().splitlines()
        except OSError:
            lines = []
        valid = False
        for line in lines:
            fields = line.split(':')
            if len(fields) == 3 and fields[0] in (username, str(os.getuid())):
                try:
                    valid |= int(fields[1]) > 0 and int(fields[2]) >= 65536
                except ValueError:
                    pass
        if not valid:
            problems.append(f'/etc/{name} needs an assigned range of at least 65536 IDs for this user.')
    runtime = os.environ.get('XDG_RUNTIME_DIR')
    if not runtime or not Path(runtime).is_dir() or Path(runtime).stat().st_uid != os.getuid():
        problems.append('A user-owned XDG_RUNTIME_DIR from a Desktop login is required.')
    if shutil.which('systemctl') and execute(['systemctl', '--user', 'show-environment']).returncode:
        problems.append('The systemd user session is unavailable.')
    if shutil.which('unshare') and execute(['unshare', '--user', '--map-root-user', 'true']).returncode:
        problems.append('Unprivileged user namespaces are unavailable or restricted.')
    return problems


def clean_env():
    env = os.environ.copy()
    for key in ('DOCKER_HOST', 'DOCKER_CONTEXT', 'DOCKER_TLS_VERIFY', 'DOCKER_CERT_PATH'):
        env.pop(key, None)
    return env


def client(cfg=None):
    cfg = config() if cfg is None else cfg
    env = clean_env()
    if cfg.get('mode') in ('managed', 'remote'):
        base = paths()[0]
        runtime = os.environ.get('XDG_RUNTIME_DIR')
        if not runtime and cfg['mode'] == 'managed':
            raise ValueError('No XDG_RUNTIME_DIR; log into Desktop Mode first.')
        env['DOCKER_CONFIG'] = str(base / 'client')
        binary = base / 'runtime' / cfg['runtime'] / 'docker'
        env['PATH'] = str(binary.parent) + os.pathsep + env.get('PATH', '/usr/bin:/bin')
        endpoint = cfg['remote'] if cfg['mode'] == 'remote' else f'unix://{runtime}/deckctl-docker.sock'
        return [str(binary), '--host', endpoint], env
    if cfg.get('mode') == 'context':
        binary = shutil.which('docker')
        if not binary:
            raise ValueError('Selected Docker context requires the existing docker CLI on PATH.')
        return [binary, '--context', cfg['context']], env
    raise ValueError('Containers are not configured. Run deckctl containers install.')


def docker(arguments, *, timeout=30, cfg=None):
    command, env = client(cfg)
    return execute(command + arguments, env=env, timeout=timeout)


def test_receipt_path():
    return paths()[1].with_name('containers-test.json')


def test_identity(cfg, data):
    """Bind historical test evidence to the selected engine and test fixture."""
    identity = {k: cfg.get(k) for k in ('mode', 'context', 'remote', 'runtime', 'storage_driver')}
    identity.update({k: data.get(k) for k in ('engine_id', 'engine_version', 'storage_driver', 'compose_version', 'rootless')})
    identity['fixture'] = digest(core.ROOT / 'modules/dev/containers/compose-smoke.yaml')
    return hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()


def status_data():
    cfg = config()
    result = {'status': 'NOT_CONFIGURED', 'mode': cfg.get('mode'),
              'api_ready': False, 'test_status': 'NOT_RUN',
              'autostart': False, 'message': 'Optional; run deckctl containers install.'}
    if cfg.get('mode') not in ('managed', 'context', 'remote'):
        return result
    try:
        info = docker(['info', '--format', '{{json .}}'])
        compose = docker(['compose', 'version', '--short'])
        if info.returncode:
            result.update(status='STOPPED_OR_UNREACHABLE', message='Selected engine unavailable; use containers start for a managed local engine.')
        elif compose.returncode:
            result.update(status='CONFIG_REQUIRED', message='Docker responds, but its Compose plugin is unavailable.')
        else:
            data = json.loads(info.stdout)
            rootless = any('rootless' in s for s in data.get('SecurityOptions', []))
            if cfg['mode'] == 'managed' and not rootless:
                result.update(status='CONFIG_REQUIRED', message='Managed endpoint did not report rootless mode.')
            else:
                result.update(status='API_READY', api_ready=True, engine_id=data.get('ID'),
                              engine_version=data.get('ServerVersion'),
                              storage_driver=data.get('Driver'),
                              compose_version=compose.stdout.strip(), rootless=rootless,
                              message='Engine and Compose respond; run deckctl containers test to verify a container launch.')
                result['test_identity'] = test_identity(cfg, result)
                receipt = core.load_json(test_receipt_path(), {})
                if isinstance(receipt, dict) and receipt.get('identity') == result['test_identity']:
                    outcome = receipt.get('result')
                    if outcome in ('PASSED', 'FAILED', 'RUNNING'):
                        result.update(test_status=outcome, last_test_at=receipt.get('at'))
                        if outcome == 'PASSED':
                            result.update(status='READY', message='Engine responds; the last container launch/HTTP/cleanup test passed (see last_test_at).')
                        else:
                            result.update(status='TEST_FAILED' if outcome == 'FAILED' else 'TEST_REQUIRED',
                                          message='The last container test failed or was interrupted; run deckctl containers test to retry.',
                                          test_failure=receipt.get('failure'))
        if cfg['mode'] == 'managed':
            result['autostart'] = execute(['systemctl', '--user', 'is-enabled', UNIT]).stdout.strip() == 'enabled'
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        result.update(status='CONFIG_REQUIRED', message=str(exc))
    return result


def status(as_json=False):
    data = status_data()
    print(json.dumps(data, indent=2) if as_json else '\n'.join(f'{k}: {v}' for k, v in data.items()))
    return 0 if data['status'] == 'READY' else 2


def service(action):
    if config().get('mode') != 'managed':
        raise ValueError('Service control only applies to the project-managed local engine; existing/remote engines are untouched.')
    if action == 'start':
        errors = prerequisites()
        if errors:
            print('\n'.join(errors))
            return 2
    result = execute(['systemctl', '--user', action, UNIT], timeout=60)
    if result.returncode:
        print(result.stderr.strip())
        return 1
    if action == 'start':
        for _ in range(30):
            if status_data()['api_ready']:
                return 0
            time.sleep(1)
        print(f'Engine did not become ready. Inspect: journalctl --user -u {UNIT}')
        return 1
    return 0


def unit_text(directory, storage_driver=None):
    def quote(value):
        if '\n' in value or '\r' in value:
            raise ValueError('Newlines are not supported in container installation paths')
        return '"' + value.replace('\\', '\\\\').replace('"', '\\"').replace('%', '%%').replace('$', '$$') + '"'
    base = paths()[0]
    storage_flags = ''
    if storage_driver == 'fuse-overlayfs':
        storage_flags = ' --feature=containerd-snapshotter=false --storage-driver=fuse-overlayfs'
    elif storage_driver is not None:
        raise ValueError('Unsupported managed storage driver')
    return (MARKER + '[Unit]\nDescription=Steam Deck development Docker (rootless)\n'
            '[Service]\nType=simple\n'
            'Environment=' + quote('PATH=' + str(directory) + ':/usr/local/bin:/usr/bin:/bin') + '\n'
            'Environment=DOCKERD_ROOTLESS_ROOTLESSKIT_STATE_DIR=%t/deckctl-rootlesskit\n'
            'ExecStart=' + quote(str(directory / 'dockerd-rootless.sh')) +
            ' --host=unix://%t/deckctl-docker.sock --data-root=' + quote(str(base / 'data')) + storage_flags + '\n'
            'Restart=on-failure\nRestartSec=3\nTimeoutStartSec=90\nDelegate=yes\n'
            'KillMode=mixed\n[Install]\nWantedBy=default.target\n')


def safe_directory(path):
    for parent in (path, *path.parents):
        if parent.is_symlink():
            raise ValueError(f'Refusing managed storage through a symlink: {parent}')
    path.mkdir(parents=True, exist_ok=True, mode=0o700)


def aliases():
    """Install shell conveniences without shadowing native commands or user aliases."""
    if config().get('mode') not in ('managed', 'remote', 'context'):
        print('Configure Docker first with deckctl containers install.')
        return 2
    mapping = json.loads((core.ROOT / 'modules/dev/containers/aliases.json').read_text())
    lines = ['# Managed Docker aliases. Existing commands, functions and aliases win.']
    for name, command in mapping.items():
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_-]*', name) or not isinstance(command, str):
            raise ValueError('Invalid container alias map')
        quoted = command.replace("'", "'\"'\"'")
        lines.append(f"if ! command -v {name} >/dev/null 2>&1; then alias {name}='{quoted}'; fi")
    shell = Path.home() / '.config/deckctl/shell/containers.sh'
    safe_directory(shell.parent)
    start = '# >>> steamdeck-workstation Docker aliases >>>'
    end = '# <<< steamdeck-workstation Docker aliases <<<'
    block = (start + '\n'
             '[ -f "$HOME/.config/deckctl/shell/containers.sh" ] && . "$HOME/.config/deckctl/shell/containers.sh"\n'
             + end + '\n')
    updates = {shell: '\n'.join(lines) + '\n'}
    for name in ('.bashrc', '.zshrc'):
        rc = Path.home() / name
        if rc.is_symlink():
            raise ValueError(f'Refusing to replace a symlink: {rc}')
        old = rc.read_text() if rc.exists() else ''
        old = re.sub(re.escape(start) + r'.*?' + re.escape(end) + r'\n?', '', old, flags=re.S).rstrip()
        updates[rc] = (old + '\n\n' if old else '') + block
    for target, content in updates.items():
        if target.is_symlink():
            raise ValueError(f'Refusing to replace a symlink: {target}')
        if target.exists() and target.read_text() == content:
            continue
        fd, name = tempfile.mkstemp(prefix='.' + target.name + '-', dir=target.parent)
        temporary = Path(name)
        try:
            with os.fdopen(fd, 'w') as stream:
                stream.write(content)
            if target.exists():
                temporary.chmod(target.stat().st_mode & 0o777)
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
    print('Docker aliases installed: docker, docker-compose, compose, d, dc.\n'
          'Open a new terminal or run: source ~/.config/deckctl/shell/containers.sh')
    return 0


def install(context=None, remote=None, local=False, storage_driver=None):
    if os.geteuid() == 0:
        raise ValueError('Run as the Desktop user, not root.')
    old = config()
    if storage_driver is not None and (context or remote or (old.get('mode') in ('context', 'remote') and not local)):
        raise ValueError('--storage-driver applies only to the managed local engine; select --local explicitly.')
    selected_storage = storage_driver if storage_driver is not None else old.get('storage_driver')
    if selected_storage == 'default':
        selected_storage = None
    if selected_storage not in (None, 'fuse-overlayfs'):
        raise ValueError('Unsupported managed storage driver')
    if remote and not re.fullmatch(r'ssh://[A-Za-z0-9_.-]+@[A-Za-z0-9][A-Za-z0-9.-]*(?::[0-9]{1,5})?', remote):
        raise ValueError('Remote must be ssh://user@hostname[:port], without paths or passwords.')
    if remote and not shutil.which('ssh'):
        raise ValueError('OpenSSH client is required for remote Docker.')
    if context:
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,100}', context):
            raise ValueError('Invalid Docker context name')
        candidate = {'mode': 'context', 'context': context, 'opt_in': True}
        info = docker(['info', '--format', '{{json .}}'], cfg=candidate)
        compose = docker(['compose', 'version', '--short'], cfg=candidate)
        if info.returncode or compose.returncode:
            print('Existing context must have a reachable engine and working Compose plugin. Nothing changed.')
            return 2
        core.save_json(paths()[1], candidate)
        aliases()
        return smoke()
    if old.get('mode') in ('context', 'remote') and not remote and not local:
        aliases()
        return smoke()
    # Do not silently take over another Docker installation or change its context.
    if not old.get('mode') and not remote and shutil.which('docker'):
        print('Existing Docker CLI detected. Reuse with containers install --context NAME; inspect docker context ls.')
        return 2
    errors = [] if remote else prerequisites()
    if not remote and selected_storage == 'fuse-overlayfs' and not shutil.which('fuse-overlayfs'):
        errors.append('Missing host prerequisite: fuse-overlayfs (required by the selected storage driver).')
    if errors:
        print('CONFIG_REQUIRED\n' + '\n'.join(errors) + '\nSteamOS was not unlocked or modified. Existing/remote Docker is an alternative.')
        return 2
    if (not remote and selected_storage != old.get('storage_driver') and
            execute(['systemctl', '--user', 'is-active', UNIT]).returncode == 0):
        print('Stop the managed engine with deckctl containers stop before changing storage drivers. '
              'Existing images/containers remain on disk but are hidden by the other backend.')
        return 2
    base, cfgpath, unit = paths()
    safe_directory(base)
    if shutil.disk_usage(base).free < 2 * 1024**3:
        raise ValueError('At least 2 GiB free space is required; project images will need more.')
    manifest = json.loads(MANIFEST.read_text())
    version = manifest['engine_version'] + '-compose-' + manifest['compose_version'] + '-buildx-' + manifest['buildx_version']
    destination = base / 'runtime' / version
    safe_directory(destination.parent)
    if not remote and (unit.is_symlink() or (unit.exists() and not unit.read_text().startswith(MARKER))):
        raise ValueError('Unmanaged service file exists; refusing to overwrite it.')
    if destination.is_symlink():
        raise ValueError('Managed runtime cannot be a symlink.')
    if destination.exists():
        receipt = core.load_json(destination / 'receipt.json', {})
        if (not receipt or any(not re.fullmatch(r'[A-Za-z0-9_.-]+', n) or n in {'.', '..'} or
                               (destination / n).is_symlink() or not (destination / n).is_file() or
                               digest(destination / n) != sha for n, sha in receipt.items())):
            raise ValueError('Managed tools changed or are incomplete; keep them for investigation before reinstalling.')
    else:
        with tempfile.TemporaryDirectory(prefix='.download-', dir=destination.parent) as tmp:
            work = Path(tmp)
            binaries = work / 'bin'
            binaries.mkdir()
            for name, asset in manifest['assets'].items():
                archive = work / name
                download(asset, archive)
                if name in ('compose', 'buildx'):
                    shutil.copyfile(archive, binaries / ('docker-' + name))
                    (binaries / ('docker-' + name)).chmod(0o755)
                else:
                    unpack(archive, binaries)
            for required in ('docker', 'dockerd', 'rootlesskit', 'dockerd-rootless.sh', 'docker-compose', 'docker-buildx'):
                if not (binaries / required).is_file():
                    raise ValueError(f'Incomplete Docker bundle: {required}')
            core.save_json(binaries / 'receipt.json', {p.name: digest(p) for p in binaries.iterdir()})
            binaries.rename(destination)
    # Private CLI config avoids overwriting ~/.docker or its credentials/plugins.
    safe_directory(base / 'client/cli-plugins')
    for name in ('docker-compose', 'docker-buildx'):
        plugin = base / 'client/cli-plugins' / name
        if plugin.is_symlink() or (plugin.exists() and digest(plugin) != digest(destination / name)):
            raise ValueError('Docker plugin has local changes; refusing to overwrite it.')
        shutil.copy2(destination / name, plugin)
    if remote:
        core.save_json(cfgpath, {'mode': 'remote', 'runtime': version, 'remote': remote, 'opt_in': True})
        aliases()
        return smoke()
    safe_directory(unit.parent)
    content = unit_text(destination, selected_storage)
    if not unit.exists() or unit.read_text() != content:
        temporary = unit.with_suffix('.service.tmp')
        if temporary.exists() or temporary.is_symlink():
            raise ValueError('Unexpected temporary service file; inspect before retrying.')
        temporary.write_text(content)
        temporary.replace(unit)
    settings = {'mode': 'managed', 'runtime': version, 'opt_in': True}
    if selected_storage:
        settings['storage_driver'] = selected_storage
    core.save_json(cfgpath, settings)
    aliases()
    if execute(['systemctl', '--user', 'daemon-reload']).returncode:
        return 1
    # Start for this session only. No enable, linger, sudo, or firewall changes.
    if service('start'):
        return 2
    return install_test()


def install_test():
    """Offer the known storage repair only after this installation's test fails."""
    result = smoke()
    if result == 0:
        return 0
    cfg = config()
    report = status_data()
    if (cfg.get('mode') != 'managed' or cfg.get('storage_driver') == 'fuse-overlayfs'
            or report.get('test_failure') != 'overlay_mount'):
        return result
    if not shutil.which('fuse-overlayfs'):
        print('CONFIG_REQUIRED: the overlay repair needs the host fuse-overlayfs helper. SteamOS was not modified.')
        return 2
    if not os.isatty(0):
        print('CONFIG_REQUIRED: rerun deckctl containers install in a terminal for the guided storage repair.')
        return 2
    print('Docker could not mount a container with its current storage backend.\n'
          'The repair stops this managed engine and switches to fuse-overlayfs.\n'
          'Existing images and containers remain on disk but are hidden by the new backend; no data is migrated or deleted.')
    # Even stopped user containers must not silently disappear from their owner's view.
    inventory = docker(['ps', '--all', '--quiet'])
    if inventory.returncode or inventory.stdout.strip():
        print('Existing containers or an unavailable inventory require manual review. '
              'Stop your workloads, then use containers stop and containers install --storage-driver fuse-overlayfs.')
        return 2
    if input('Apply the fuse-overlayfs repair and rerun the test? [y/N] ').strip().lower() not in ('y', 'yes'):
        return 2
    # Recheck immediately before stopping; never stop a newly started user workload.
    inventory = docker(['ps', '--all', '--quiet'])
    if inventory.returncode or inventory.stdout.strip():
        print('Container inventory changed; leaving the engine unchanged.')
        return 2
    if service('stop'):
        return 1
    return install(storage_driver='fuse-overlayfs')


def smoke():
    """Compose up/inspect/down one uniquely named, volume-free fixture."""
    report = status_data()
    if not report['api_ready']:
        print('Selected engine and Compose must be ready before the launch test.')
        return 2
    name = 'deckctl-test-' + uuid.uuid4().hex[:12]
    fixture = core.ROOT / 'modules/dev/containers/compose-smoke.yaml'
    prefix = ['compose', '--project-name', name, '--file', str(fixture)]
    result = 1
    failure = 'launch'
    def record(outcome):
        core.save_json(test_receipt_path(), {'identity': report['test_identity'], 'result': outcome,
                       'at': datetime.now(timezone.utc).isoformat(),
                       'failure': failure if outcome == 'FAILED' else None})
    # Invalidate previous success before launching, including if this process is interrupted.
    record('RUNNING')
    try:
        started = docker(prefix + ['up', '--detach', '--wait', '--wait-timeout', '60'], timeout=240)
        if started.returncode:
            print('Container test could not start: ' + started.stderr[-2000:])
            if (config().get('mode') == 'managed' and 'fstype: overlay' in started.stderr
                    and 'invalid argument' in started.stderr):
                failure = 'overlay_mount'
                print('Rootless overlay mounts failed. If fuse-overlayfs is available, stop the managed engine '
                      'with deckctl containers stop, then run deckctl containers install --storage-driver fuse-overlayfs. '
                      'This preserves existing data but images/containers from the old backend become hidden.')
        else:
            failure = 'http'
            probe = docker(prefix + ['exec', '-T', 'probe', 'wget', '-qO-', 'http://127.0.0.1:8080'])
            result = 0 if probe.returncode == 0 and probe.stdout.strip() == 'deckctl-container-ok' else 1
            print('Container launch and internal HTTP test: ' + ('PASS' if result == 0 else 'FAIL'))
    except (OSError, subprocess.SubprocessError):
        failure = 'execution'
        raise
    finally:
        try:
            stopped = docker(prefix + ['down', '--timeout', '10'], timeout=60)
            if stopped.returncode:
                print(f'Could not remove smoke-test project {name}; use the reported project name to inspect it.')
                result, failure = 1, 'cleanup'
        except (OSError, subprocess.SubprocessError):
            result, failure = 1, 'cleanup'
            raise
        finally:
            record('PASSED' if result == 0 else 'FAILED')
    return result


def cleanup():
    # No prune: Docker volumes/images/containers may be other projects' data.
    print('No persistent download cache is kept. Temporary downloads are removed automatically.\n'
          'Images, volumes, project containers and databases are preserved. Use docker/Compose explicitly to manage your own stacks.')
    return 0


def provision():
    if 'dev' not in core.topo(core.enabled_modules()):
        print('Optional Docker skipped: Development tools are not selected in this workstation plan.')
        print('Run deckctl setup customize to select Development, or deckctl containers install to opt in directly.')
        return 0
    cfg = config()
    if cfg.get('opt_in') is False:
        return 0
    if cfg.get('opt_in') is not True:
        if not os.isatty(0):
            print('Optional Docker skipped in non-interactive setup; run deckctl containers install to opt in.')
            return 0
        answer = input('Install optional Docker + Compose for dashboard development? [y/N] ').strip().lower()
        if answer not in ('y', 'yes'):
            core.save_json(paths()[1], {'opt_in': False})
            return 0
        core.save_json(paths()[1], {'opt_in': True})
    return install()


def autostart(setting):
    if config().get('mode') != 'managed':
        raise ValueError('Autostart only applies to the managed local engine.')
    result = execute(['systemctl', '--user', 'enable' if setting == 'on' else 'disable', UNIT])
    print('Applies at user login only; linger and system boot configuration are unchanged.')
    return 0 if result.returncode == 0 else 1


def forward(arguments, compose=False):
    if arguments and arguments[0] == '--':
        arguments = arguments[1:]
    if not arguments:
        raise ValueError('Supply a Docker/Compose command after --; see --help.')
    command, env = client()
    # Keep the selected endpoint authoritative. Raw Docker endpoint/config overrides
    # belong in the user's own Docker invocation, not this managed wrapper.
    if not compose and any(a in ('-H', '--host', '--context', '--config') or
                           a.startswith(('--host=', '--context=', '--config=', '-H')) for a in arguments):
        raise ValueError('Endpoint overrides are not accepted by this wrapper.')
    return subprocess.run(command + (['compose'] if compose else []) + arguments, env=env).returncode


def add_parser(subparsers):
    p = subparsers.add_parser('containers', help='Optional Docker/Compose dashboard development')
    children = p.add_subparsers(dest='containers_sub', required=True)
    status_parser = children.add_parser('status')
    status_parser.add_argument('--json', action='store_true')
    install_parser = children.add_parser('install')
    install_parser.add_argument('--storage-driver', choices=('default', 'fuse-overlayfs'),
                                help='Select managed rootless storage: Docker default or classic fuse-overlayfs. Stop the engine before switching; old images/containers are preserved but hidden. Saved for retries.')
    choice = install_parser.add_mutually_exclusive_group()
    choice.add_argument('--local', action='store_true', help='Explicitly select the managed local rootless engine after using a remote/context engine.')
    choice.add_argument('--context', help='Reuse an existing Docker context and its Compose plugin without modifying its engine.')
    choice.add_argument('--remote', help='Install private Docker CLI tools targeting ssh://user@hostname[:port]. Authenticate with SSH first.')
    for name in ('start', 'stop', 'test', 'cleanup', 'provision', 'check', 'aliases'):
        children.add_parser(name)
    start_parser = children.add_parser('autostart')
    start_parser.add_argument('setting', choices=('on', 'off'), help='Enable or disable managed Docker startup at user login; no system boot/linger changes.')
    for name in ('docker', 'compose'):
        command = children.add_parser(name)
        command.add_argument('arguments', nargs=__import__('argparse').REMAINDER,
                             help='Arguments passed to the selected Docker/Compose endpoint; use -- before vendor options.')


def dispatch(args):
    action = args.containers_sub
    if action == 'install':
        return install(args.context, args.remote, args.local, args.storage_driver)
    if action == 'status':
        return status(args.json)
    if action in ('start', 'stop'):
        return service(action)
    if action == 'autostart':
        return autostart(args.setting)
    if action in ('docker', 'compose'):
        return forward(args.arguments, action == 'compose')
    if action == 'check':
        problems = prerequisites()
        print('\n'.join(problems) if problems else 'Local rootless prerequisites: PASS; install/test still required.')
        return 2 if problems else 0
    return {'test': smoke, 'cleanup': cleanup, 'provision': provision, 'aliases': aliases}[action]()


HELP = {
    'containers aliases': ('Install familiar Docker commands and short shell aliases.',
        'Installs docker, docker-compose, compose, d (Docker), and dc (Compose) for Bash and Zsh after Docker is configured. Open a new terminal or source ~/.config/deckctl/shell/containers.sh. Existing executables, functions and aliases take precedence. Arguments and the working directory pass through unchanged; all Docker subcommands including buildx use the selected engine. These are interactive shell aliases, not executables for scripts or sudo. Scripts can use deckctl containers docker/compose --. Does not start the engine or run containers.', 'containers aliases'),
    'containers install': ('Install optional Docker Engine, Compose and Buildx, or reuse an existing engine.',
        'Opt-in user-space setup. With no flags, checks rootless prerequisites without changing SteamOS, downloads pinned SHA-256-verified tools, creates a separate user service/data directory and starts it for this session. Existing Docker requires --context NAME. --local selects the managed local engine after a remote/context selection. --remote installs private CLI tools for an SSH engine; set up SSH trust/authentication first. Never changes the default Docker context, sudo settings or existing engine. Runs a real Compose smoke test. A known rootless overlay failure offers an interactive fuse-overlayfs repair only when the helper exists and no containers remain. Explains storage visibility and asks before stopping/switching; declining or noninteractive setup returns 2. No automatic binary updates.', 'containers install'),
    'containers status': ('Report the selected Docker engine and Compose readiness.',
        'Read-only: queries the selected engine and Compose, then reads the last test result. API_READY means the API responds but no matching successful launch test exists. READY means the API responds and the last matching launch/HTTP/cleanup test passed; last_test_at shows when, not a live application guarantee. TEST_FAILED or TEST_REQUIRED indicates failed or interrupted testing. Engine, version, storage, endpoint or fixture changes invalidate old evidence. Never starts services, pulls images or writes results. Exit 0 only for READY, otherwise 2. Podman/Distrobox are unchanged.', 'containers status --json'),
    'containers check': ('Check host prerequisites for a local rootless Docker engine.',
        'Read-only host checks for Linux x86_64, UID/GID mapping, subordinate ranges, network helper, user namespaces and a systemd user session. No sudo, pacman, sysctl edits or SteamOS unlock. Missing prerequisites return 2; remote Docker may still be usable.', 'containers check'),
    'containers start': ('Start the project-managed local Docker engine for this session.',
        'Checks prerequisites and starts only deckctl-docker.service. Waits for rootless API/Compose readiness. Does not enable startup or affect another engine.', 'containers start'),
    'containers stop': ('Stop the project-managed local Docker engine.',
        'Stops running workloads on this managed engine. Images, containers and volumes remain on disk. Existing/remote engines cannot be stopped through this command.', 'containers stop'),
    'containers autostart': ('Opt in or out of managed Docker startup at user login.',
        'on enables the managed user service; off disables future automatic starts without stopping current workloads. Does not enable linger or boot startup. The default is off.', 'containers autostart on'),
    'containers test': ('Run and remove a uniquely named Compose HTTP smoke test.',
        'Requires a reachable engine and Compose. May download a digest-pinned BusyBox image, creates a disposable service, waits for health, verifies its HTTP response, and removes only that test project. Records timestamped pass/fail evidence for this engine/storage/fixture; interrupted testing invalidates previous success. Publishes no host ports and uses no volumes. Does not certify your dashboard stack or host networking. Leaves the cached image for reuse.', 'containers test'),
    'containers cleanup': ('Explain automatic installer cleanup and preserve project data.',
        'Downloads are temporary and removed on completion/failure. This read-only command never prunes images, volumes or user containers; database cleanup must be explicit in your project.', 'containers cleanup'),
    'containers provision': ('Offer or resume optional Docker setup during the normal installer.',
        'First interactive use asks once; declining records opt-out. Non-interactive setup skips an unselected option. Accepted setup is retried on later installer runs; containers install can opt in after declining. Does not block unrelated modules from provisioning.', 'containers provision'),
    'containers docker': ('Run Docker CLI arguments against the selected development engine.',
        'Pass arguments after --. Normal Docker semantics apply, including destructive operations you explicitly request. Endpoint overrides are rejected. Private tools do not replace the system docker command. Remote bind mounts refer to the remote host.', 'containers docker -- ps'),
    'containers compose': ('Run your Compose project against the selected development engine.',
        'Runs in your current working directory. Pass Compose arguments after --; vendor operations can build images, start services or delete data as requested. No automatic port rewriting: bind local dashboards to 127.0.0.1 explicitly. On SSH engines bind mounts and published ports belong to the remote host.', 'containers compose -- up --build -d'),
}
