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
LOCAL_MODELS = {
    MODEL: {'name': 'Qwen 2.5 Coder 1.5B', 'component': 'model', 'space_bytes': 1536 * 1024**2},
    'qwen2.5-coder:7b': {'name': 'Qwen 2.5 Coder 7B', 'component': 'model-7b', 'space_bytes': 6 * 1024**3},
}


def selected_models():
    from . import component_options
    selected = component_options.effective('ai-workspace')
    return [model for model, item in LOCAL_MODELS.items() if item['component'] in selected]

HOST = '127.0.0.1'
PORT = 11435  # Dedicated endpoint; never borrow/stop another Ollama server.
HOME = Path.home()
BIN = HOME / '.local/bin'
DATA = HOME / '.local/share/deckctl/ollama'
MODELS = DATA / 'models'
CONFIG = HOME / '.config/opencode/config.json'
RECEIPT = core.STATE / 'ollama-install.json'



def _storage_info(path):
    # Resolve the destination first so moved/symlinked model stores use their
    # actual filesystem. Inspect an existing ancestor without creating files.
    anchor = path.resolve()
    while not anchor.exists():
        anchor = anchor.parent
    return anchor, anchor.stat().st_dev, shutil.disk_usage(anchor).free


def check_space(models=(), runtime=False, upgrading=()):
    """Conservative download/staging budgets, combined per destination filesystem."""
    requirements = []
    if runtime:
        requirements.extend([(DATA, 8 * 1024**3, 'Ollama runtime staging'),
                             (BIN, 256 * 1024**2, 'Ollama executable')])
    for model in models:
        if model in upgrading or not model_present(model):
            requirements.append((MODELS, LOCAL_MODELS[model]['space_bytes'], model))
    volumes = {}
    for path, amount, label in requirements:
        anchor, device, free = _storage_info(path)
        volume = volumes.setdefault(device, {'path': anchor, 'free': free, 'needed': 1024**3, 'items': []})
        volume['free'] = min(volume['free'], free)
        volume['needed'] += amount
        volume['items'].append(label)
    failures = []
    for volume in volumes.values():
        needed, free = volume['needed'], volume['free']
        detail = (f"{volume['path']}: need {needed / 1024**3:.2f} GiB free "
                  f"(including 1 GiB headroom), available {free / 1024**3:.2f} GiB "
                  f"for {', '.join(volume['items'])}")
        print('Storage check: ' + detail)
        if free < needed:
            failures.append(detail + f"; free at least {(needed-free) / 1024**3:.2f} GiB more")
    if failures:
        raise RuntimeError('Not enough disk space. ' + ' | '.join(failures) +
                           '. Free space or select fewer models, then retry; this download has not started.')
    return volumes


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
                                 'models': {model: {'name': item['name']} for model, item in LOCAL_MODELS.items()}},
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



def model_update_needed(model):
    if not model_present(model):
        return True
    try:
        name, tag = model.split(':')
        remote = json.loads(terminal._request(
            f'https://registry.ollama.ai/v2/library/{name}/manifests/{tag}', 20))
        if not isinstance(remote, dict) or not isinstance(remote.get('layers'), list) or 'config' not in remote:
            raise ValueError('invalid upstream manifest')
        local = json.loads((MODELS/'manifests/registry.ollama.ai/library'/model.replace(':','/')).read_text())
        return remote != local
    except (OSError, ValueError) as exc:
        print(f'WARN: Cannot check {model} for updates; keeping installed model: {exc}')
        return False


def ollama_release_plan():
    binary = BIN/'ollama'
    receipt = core.load_json(RECEIPT, {}) or {}
    existing = binary.exists() or binary.is_symlink()
    library = HOME/'.local/lib/ollama'
    if existing:
        if not receipt.get('binary_sha256') or terminal._sha256_file(binary) != receipt['binary_sha256'] or not library.is_dir():
            raise ValueError(f'Existing or incomplete {binary} preserved; inspect before replacing it')
    elif library.exists() or library.is_symlink():
        raise ValueError(f'Existing Ollama libraries preserved: {library}')
    try:
        release, asset = terminal._github_asset('ollama/ollama', r'^ollama-linux-amd64\.tar\.zst$')
    except (OSError, ValueError, RuntimeError) as exc:
        if not existing:
            raise
        print(f'WARN: Cannot check Ollama updates; keeping installed runtime: {exc}')
        return None
    if existing:
        newer = terminal.newer_version(release.get('tag_name'), receipt.get('version'))
        if newer is not True:
            print('Ollama retained; no newer comparable release' if newer is None else 'Ollama up to date; download skipped')
            return None
    return release, asset


def install_ollama(release_plan=None):
    plan = release_plan if release_plan is not None else ollama_release_plan()
    if plan is None:
        return
    release, asset = plan
    binary = BIN/'ollama'
    library = HOME/'.local/lib/ollama'
    if not shutil.which('zstd'):
        raise RuntimeError('zstd is required to unpack the upstream Ollama archive')
    check_space(runtime=True)
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
        # Prepare both replacements before touching the working runtime. Retain
        # old runtime payloads for recovery; only the owned link changes.
        old_target = os.readlink(library) if library.is_symlink() else None
        if library.exists() and old_target is None:
            raise ValueError(f'Existing Ollama library directory preserved: {library}')
        fd, staged_name = tempfile.mkstemp(prefix='.ollama-', dir=BIN)
        os.close(fd)
        staged = Path(staged_name)
        link = library.with_name('ollama-new-' + str(os.getpid()))
        try:
            shutil.copy2(destination/'bin/ollama', staged)
            link.symlink_to(destination/'lib/ollama')
            link.replace(library)
            try:
                staged.replace(binary)
            except OSError:
                library.unlink()
                if old_target is not None:
                    library.symlink_to(old_target)
                raise
        finally:
            staged.unlink(missing_ok=True)
            link.unlink(missing_ok=True)
        core.save_json(RECEIPT, {'version': release['tag_name'], 'source': asset['browser_download_url'],
                                'archive_sha256': digest, 'binary_sha256': terminal._sha256_file(binary),
                                'runtime': str(destination)})


def model_present(model=MODEL):
    if model not in LOCAL_MODELS:
        raise ValueError('Unknown local model: ' + model)
    manifest = MODELS / 'manifests/registry.ollama.ai/library' / model.replace(':', '/')
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


def pull(model=MODEL):
    if model not in LOCAL_MODELS:
        raise ValueError('Unknown local model: ' + model)
    check_space([model], upgrading=[model])
    with server():
        if run_client([str(BIN / 'ollama'), 'pull', model]):
            raise RuntimeError('Model download failed; retry deckctl ai-workspace install')
    if not model_present(model):
        raise RuntimeError('Model manifest/blobs are incomplete after download')


def install():
    if os.geteuid() == 0:
        raise ValueError('Run workspace installation as your normal user, without sudo')
    from . import component_options
    models = [model for model in selected_models() if model_update_needed(model)]
    plan = ollama_release_plan() if component_options.selected('ai-workspace', 'ollama') else None
    check_space(models, runtime=plan is not None, upgrading=models)
    configure()  # Validate user configuration before downloads.
    if plan is not None:
        install_ollama(plan)
    for model in models:
        pull(model)
    guide()
    return 0


def guide():
    print('''\nON-DEMAND AI WORKSPACE
Local (uses your selected model; prefers lightweight if both selected): deckctl ai-workspace open
Lightweight: deckctl ai-workspace open --model qwen2.5-coder:1.5b
Higher quality: deckctl ai-workspace open --model qwen2.5-coder:7b
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
    from . import component_options
    required = ['opencode'] + (['ollama'] if component_options.selected('ai-workspace','ollama') else [])
    tools = {name: os.access(BIN / name, os.X_OK) for name in required}
    models = {model: model_present(model) for model in selected_models()}
    loaded = bool(models) and all(models.values())
    data = {'status': 'READY' if all(tools.values()) and config_ok and all(models.values()) else 'NOT_INSTALLED',
            'message': 'On-demand workspace installation; accounts and GUI behavior require separate checks.',
            'tools': tools, 'config_ready': config_ok, 'model_downloaded': loaded, 'selected_models': models,
            'endpoint_in_use': occupied(), 'endpoint': f'http://{HOST}:{PORT}', 'autostart': False}
    print(json.dumps(data, indent=2) if as_json else '\n'.join(f'{k}: {v}' for k, v in data.items()))
    return 0 if data['status'] == 'READY' else 1


def add_parser(subparsers):
    parser = subparsers.add_parser('ai-workspace', help='On-demand local and ChatGPT coding workspace')
    sp = parser.add_subparsers(dest='ai_command', required=True)
    sp.add_parser('install'); sp.add_parser('guide')
    st = sp.add_parser('status'); st.add_argument('--json', action='store_true')
    op = sp.add_parser('open'); op.add_argument('--profile', choices=['local-ollama', 'chatgpt-pro'], default='local-ollama', help='Local owned engine or OpenAI subscription provider.')
    op.add_argument('--model', help='Local: qwen2.5-coder:1.5b or qwen2.5-coder:7b. Cloud: openai/MODEL_FROM_LIST (required).')


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
    choices = selected_models()
    model = args.model or (choices[0] if choices else MODEL)
    if model.startswith('local-ollama/'):
        model = model.removeprefix('local-ollama/')
    if model not in LOCAL_MODELS:
        raise ValueError('Choose qwen2.5-coder:1.5b or qwen2.5-coder:7b for the local profile')
    if not model_present(model):
        raise ValueError(f'{model} is missing; select it in setup, then run deckctl ai-workspace install')
    with server():
        return run_client([str(BIN / 'opencode'), '--agent', 'local-coder', '--model', 'local-ollama/' + model])
