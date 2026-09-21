"""On-demand local coding: owned process groups, no services or login autostart."""
from __future__ import annotations
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import signal
import socket
import sys
import re
import subprocess
import tarfile
import tempfile
import time
import urllib.request
from . import core, terminal

MODEL = 'qwen2.5-coder:1.5b'
HOST = '127.0.0.1'
PORT = 11435  # Dedicated endpoint; never borrow/stop another Ollama server.
HOME = Path.home()
BIN = HOME / '.local/bin'
DATA = HOME / '.local/share/deckctl/ollama'
MODELS = DATA / 'models'
CONFIG = HOME / '.config/opencode/config.json'
RECEIPT = core.STATE / 'ollama-install.json'


def runtime_env():
    return {**os.environ, 'OLLAMA_HOST': f'{HOST}:{PORT}', 'OLLAMA_KEEP_ALIVE': '0',
            'OLLAMA_MODELS': str(MODELS), 'OLLAMA_NUM_PARALLEL': '1',
            'OLLAMA_CONTEXT_LENGTH': '2048', 'OLLAMA_NO_CLOUD': '1',
            'OPENCODE_CONFIG': str(CONFIG), 'OPENCODE_CONFIG_CONTENT': json.dumps(config_data()), 'NO_PROXY': '127.0.0.1,localhost', 'no_proxy': '127.0.0.1,localhost'}


def config_data():
    return {'$schema': 'https://opencode.ai/config.json',
            'provider': {
                'local-ollama': {'npm': '@ai-sdk/openai-compatible', 'name': 'Local Ollama',
                                 'options': {'baseURL': f'http://{HOST}:{PORT}/v1'},
                                 'models': {MODEL: {'name': 'Qwen 2.5 Coder 1.5B'}}},
                'openai': {'name': 'ChatGPT Pro (sign in with OpenAI)'}},
            'agent': {'local-coder': {'description': 'Lightweight local coding chat; no tool execution',
                                      'mode': 'primary', 'model': 'local-ollama/' + MODEL,
                                      'tools': {'*': False}}}}


def merge_config(existing, desired):
    """Preserve unrelated keys and fail before writing on conflicting managed values."""
    if not isinstance(existing, dict):
        raise ValueError('OpenCode config must be a JSON object')
    result = dict(existing)
    for key, value in desired.items():
        if key not in result:
            result[key] = value
        elif isinstance(value, dict):
            result[key] = merge_config(result[key], value)
        elif result[key] != value:
            raise ValueError(f'Existing OpenCode setting conflicts with workspace setting: {key}; file preserved')
    return result


def configure():
    existing = json.loads(CONFIG.read_text()) if CONFIG.exists() else {}
    merged = merge_config(existing, config_data())
    if merged != existing:
        core.save_json(CONFIG, merged)


def _download(asset, path):
    expected = asset.get('digest', '')
    if not expected.startswith('sha256:'):
        raise RuntimeError('Ollama release lacks a SHA-256 digest')
    digest = hashlib.sha256()
    total = 0
    req = urllib.request.Request(asset['browser_download_url'], headers={'User-Agent': 'deckctl'})
    with urllib.request.urlopen(req, timeout=120) as response, path.open('wb') as stream:
        while block := response.read(1024 * 1024):
            total += len(block)
            if total > 2 * 1024**3:
                raise RuntimeError('Ollama download exceeds 2 GiB limit')
            digest.update(block); stream.write(block)
    if 'sha256:' + digest.hexdigest() != expected:
        raise RuntimeError('Ollama download SHA-256 mismatch')
    return digest.hexdigest()


def _extract(tf, destination):
    """Stream bounded regular files, then validated internal symlinks; never follow links."""
    total = 0
    seen = set()
    links = []
    for member in tf:
        path = PurePosixPath(member.name)
        if path.is_absolute() or '..' in path.parts or '\\' in member.name:
            raise ValueError('Unsafe Ollama archive path')
        if str(path) in ('.', ''):
            continue
        if path.parts[0] not in ('bin', 'lib') or path in seen:
            raise ValueError(f'Unexpected or duplicate Ollama archive path: {path}')
        seen.add(path)
        total += member.size
        if total > 6 * 1024**3 or len(seen) > 20000:
            raise ValueError('Ollama archive exceeds extraction limits')
        target = destination / str(path)
        if member.isdir():
            target.mkdir(parents=True, exist_ok=True)
        elif member.isfile():
            target.parent.mkdir(parents=True, exist_ok=True)
            with tf.extractfile(member) as source, target.open('xb') as output:
                shutil.copyfileobj(source, output, 1024 * 1024)
            target.chmod(0o755 if member.mode & 0o111 else 0o644)
        elif member.issym():
            link = PurePosixPath(member.linkname)
            if link.is_absolute() or '\\' in member.linkname:
                raise ValueError('Unsafe Ollama archive link')
            links.append((target, member.linkname))
        else:
            raise ValueError('Unsupported Ollama archive entry')
    for target, link in links:
        target.parent.mkdir(parents=True, exist_ok=True)
        resolved = (target.parent / link).resolve()
        if not resolved.is_relative_to(destination.resolve()):
            raise ValueError('Ollama archive link escapes installation')
        target.symlink_to(link)
    # Recheck chains after all links exist, including forward references.
    for target, _ in links:
        if not target.resolve().is_relative_to(destination.resolve()):
            raise ValueError('Ollama archive link chain escapes installation')


def install_ollama():
    binary = BIN / 'ollama'
    receipt = core.load_json(RECEIPT, {}) or {}
    if binary.exists() or binary.is_symlink():
        if receipt.get('binary_sha256') and terminal._sha256_file(binary) == receipt['binary_sha256']:
            library = HOME / '.local/lib/ollama'
            if library.is_dir():
                print('Ollama already installed; retained')
                return
        raise ValueError(f'Existing or incomplete {binary} preserved; inspect before replacing it')
    library = HOME / '.local/lib/ollama'
    if library.exists() or library.is_symlink():
        raise ValueError(f'Existing Ollama libraries preserved: {library}')
    if not shutil.which('zstd'):
        raise RuntimeError('zstd is required to unpack the upstream Ollama archive')
    if shutil.disk_usage(HOME).free < 8 * 1024**3:
        raise RuntimeError('Allow at least 8 GiB free for Ollama download, libraries and model')
    release, asset = terminal._github_asset('ollama/ollama', r'^ollama-linux-amd64\.tar\.zst$')
    DATA.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.install-', dir=DATA) as temporary:
        temp = Path(temporary)
        digest = _download(asset, temp / 'ollama.tar.zst')
        stage = temp / 'runtime'; stage.mkdir()
        with subprocess.Popen(['zstd', '-d', '-c', str(temp / 'ollama.tar.zst')], stdout=subprocess.PIPE) as process:
            try:
                with tarfile.open(fileobj=process.stdout, mode='r|') as tf:
                    _extract(tf, stage)
                # Drain trailing decompressor output before waiting.
                while process.stdout.read(1024 * 1024):
                    pass
                if process.wait():
                    raise RuntimeError('Ollama decompression failed')
            except BaseException:
                process.kill(); process.wait(); raise
        candidate = stage / 'bin/ollama'
        if not candidate.is_file() or candidate.is_symlink() or not (stage / 'lib/ollama').is_dir():
            raise RuntimeError('Upstream Ollama executable/runtime libraries missing')
        result = subprocess.run([str(candidate), '--version'], capture_output=True, timeout=30)
        if result.returncode:
            raise RuntimeError('Ollama executable failed its version check')
        destination = DATA / ('runtime-' + digest)
        if destination.exists():
            raise ValueError(f'Previous incomplete runtime retained: {destination}')
        stage.rename(destination)
        BIN.mkdir(parents=True, exist_ok=True)
        library.parent.mkdir(parents=True, exist_ok=True)
        library.symlink_to(destination / 'lib/ollama')
        shutil.copy2(destination / 'bin/ollama', binary)
        core.save_json(RECEIPT, {'version': release['tag_name'], 'source': asset['browser_download_url'],
                                'archive_sha256': digest, 'binary_sha256': terminal._sha256_file(binary),
                                'runtime': str(destination)})


def model_present():
    manifest = MODELS / 'manifests/registry.ollama.ai/library/qwen2.5-coder/1.5b'
    try:
        data = json.loads(manifest.read_text())
        layers = [data['config'], *data['layers']]
        for layer in layers:
            digest = layer['digest']
            if not isinstance(digest, str) or not re.fullmatch(r'sha256:[a-f0-9]{64}', digest):
                return False
            blob = MODELS / 'blobs' / digest.replace(':', '-')
            if not blob.is_file() or blob.stat().st_size != layer['size']:
                return False
        return bool(layers)
    except (OSError, ValueError, KeyError, TypeError):
        return False


def occupied():
    with socket.socket() as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((HOST, PORT))
            return False
        except OSError:
            return True


def owns_listener(pid):
    """Linux ownership proof: avoid attaching to an unrelated bind-race winner."""
    try:
        sockets = {os.readlink(fd) for fd in Path(f'/proc/{pid}/fd').iterdir()}
        for line in Path('/proc/net/tcp').read_text().splitlines()[1:]:
            fields = line.split()
            if fields[1] == f'0100007F:{PORT:04X}' and fields[3] == '0A':
                if 'socket:[' + fields[9] + ']' in sockets:
                    return True
    except (OSError, IndexError):
        pass
    return False


def stop_group(process):
    if process is None:
        return
    # Even when the leader has exited, its runners may still own the process group.
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait(timeout=3)


@contextlib.contextmanager
def signal_cleanup():
    def interrupted(number, frame):
        raise KeyboardInterrupt(f'workspace interrupted by signal {number}')
    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT)}
    try:
        for sig in previous:
            signal.signal(sig, interrupted)
        yield
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


@contextlib.contextmanager
def server():
    core.STATE.mkdir(parents=True, exist_ok=True)
    lock_path = core.STATE / 'ai-workspace.lock'
    with lock_path.open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('An AI workspace/pull already owns the local engine') from None
        if occupied():
            raise RuntimeError(f'{HOST}:{PORT} is already in use; no existing process was stopped')
        process = None
        with tempfile.TemporaryFile() as log, signal_cleanup():
            try:
                process = subprocess.Popen([str(BIN / 'ollama'), 'serve'], env=runtime_env(),
                                           stdout=log, stderr=log, start_new_session=True)
                deadline = time.monotonic() + 30
                while time.monotonic() < deadline:
                    if process.poll() is not None:
                        raise RuntimeError('Owned Ollama server exited before becoming ready')
                    try:
                        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(f'http://{HOST}:{PORT}/api/version', timeout=0.5) as response:
                            if response.status == 200 and process.poll() is None and owns_listener(process.pid):
                                break
                    except (OSError, ValueError):
                        time.sleep(0.1)
                else:
                    raise RuntimeError('Ollama startup timed out')
                yield process
            finally:
                stop_group(process)


def run_client(command):
    """Give a foreground TUI its own process group and restore the controlling terminal."""
    process = None
    tty = None
    old_group = None
    previous_ttou = signal.getsignal(signal.SIGTTOU)
    try:
        if os.isatty(0):
            tty = 0; old_group = os.tcgetpgrp(tty)
            signal.signal(signal.SIGTTOU, signal.SIG_IGN)
        if tty is not None:
            # Do not let the TUI read before its group owns the terminal (SIGTTIN).
            gate = "import os,sys,time; \nwhile os.tcgetpgrp(0) != os.getpgrp(): time.sleep(0.01)\nos.execvpe(sys.argv[1], sys.argv[1:], os.environ)"
            command = [sys.executable, '-c', gate, *command]
        process = subprocess.Popen(command, env=runtime_env(), process_group=0)
        if tty is not None:
            os.tcsetpgrp(tty, process.pid)
        return process.wait()
    finally:
        try:
            if tty is not None:
                os.tcsetpgrp(tty, old_group)
        except OSError:
            pass  # The terminal may have closed; cleanup must still run.
        finally:
            signal.signal(signal.SIGTTOU, previous_ttou)
            stop_group(process)


def pull():
    with server():
        if run_client([str(BIN / 'ollama'), 'pull', MODEL]):
            raise RuntimeError('Model download failed; retry deckctl ai-workspace install')
    if not model_present():
        raise RuntimeError('Model manifest/blobs are incomplete after download')


def install():
    if os.geteuid() == 0:
        raise ValueError('Run workspace installation as your normal user, without sudo')
    configure()  # Validate user configuration before downloads.
    install_ollama()
    if not model_present():
        pull()
    guide()
    return 0


def guide():
    print('''\nON-DEMAND AI WORKSPACE
Local: deckctl ai-workspace open
ChatGPT Pro setup: run opencode, enter /connect, choose OpenAI -> ChatGPT Plus/Pro, then finish browser sign-in.
Then list models: opencode models openai
Cloud: deckctl ai-workspace open --profile chatgpt-pro --model openai/MODEL_FROM_LIST
Config: ~/.config/opencode/config.json (workspace loads this path explicitly).
Do not paste a ChatGPT browser access token into configuration; OpenCode stores its OAuth credentials.
Local workspace exit stops its owned Ollama server/runners. No startup service is installed.
OLLAMA_KEEP_ALIVE=0 requests model unloading after each response; timing is not instantaneous.
Close the workspace before gaming; deckctl ai-workspace status reports endpoint occupancy.
''')
    return 0


def status(as_json=False):
    config_ok = False
    try:
        config_ok = merge_config(json.loads(CONFIG.read_text()), config_data()) == json.loads(CONFIG.read_text())
    except (OSError, ValueError):
        pass
    tools = {name: os.access(BIN / name, os.X_OK) for name in ('ollama', 'opencode', 'nvim', 'ghostty', 'tmux')}
    loaded = model_present()
    data = {'status': 'READY' if all(tools.values()) and config_ok and loaded else 'NOT_INSTALLED',
            'message': 'On-demand workspace installation; accounts and GUI behavior require separate checks.',
            'tools': tools, 'config_ready': config_ok, 'model_downloaded': loaded,
            'endpoint_in_use': occupied(), 'endpoint': f'http://{HOST}:{PORT}', 'autostart': False}
    print(json.dumps(data, indent=2) if as_json else '\n'.join(f'{k}: {v}' for k, v in data.items()))
    return 0 if data['status'] == 'READY' else 1


def add_parser(subparsers):
    parser = subparsers.add_parser('ai-workspace', help='On-demand local and ChatGPT coding workspace')
    sp = parser.add_subparsers(dest='ai_command', required=True)
    sp.add_parser('install'); sp.add_parser('guide')
    st = sp.add_parser('status'); st.add_argument('--json', action='store_true')
    op = sp.add_parser('open'); op.add_argument('--profile', choices=['local-ollama', 'chatgpt-pro'], default='local-ollama', help='Local owned engine or OpenAI subscription provider.')
    op.add_argument('--model', help='OpenAI model ID from opencode models openai; required for chatgpt-pro.')


def dispatch(args):
    if args.ai_command == 'install':
        return install()
    if args.ai_command == 'guide':
        return guide()
    if args.ai_command == 'status':
        return status(args.json)
    if not CONFIG.is_file():
        raise ValueError('Run deckctl ai-workspace install first')
    if args.profile == 'chatgpt-pro':
        if not args.model or not args.model.startswith('openai/'):
            raise ValueError('Use --model openai/MODEL_FROM_LIST; see opencode models openai after sign-in')
        with signal_cleanup():
            return run_client([str(BIN / 'opencode'), '--model', args.model])
    if args.model:
        raise ValueError('Local profile uses the pre-pulled qwen2.5-coder:1.5b model')
    if not model_present():
        raise ValueError('Local model is missing; run deckctl ai-workspace install')
    with server():
        return run_client([str(BIN / 'opencode'), '--agent', 'local-coder', '--model', 'local-ollama/' + MODEL])
