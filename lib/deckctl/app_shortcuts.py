"""Submit desktop apps through SteamOS; inspect Steam records without editing them."""
from __future__ import annotations

import configparser
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import urllib.parse

from . import core, library

READY = 'READY'
MISSING = 'MISSING'
PENDING = 'PENDING_STEAM_REFRESH'
STEAM_BASE = 76561197960265728
MARKER = Path('/tmp/addnonsteamgamefile')


def _profile():
    root = Path.home()/'.local/share/Steam'
    login = root/'config/loginusers.vdf'
    if login.exists():
        lexer = shlex.shlex(login.read_text(), posix=True, punctuation_chars='{}')
        lexer.whitespace_split = True
        lexer.commenters = ''
        tokens = iter(part for token in lexer for part in (list(token) if token and set(token) <= {'{', '}'} else [token]))
        def object_(closing=False):
            result = {}
            for key in tokens:
                if key == '}':
                    if not closing: raise ValueError('Unexpected Steam login profile terminator')
                    return result
                if key == '{': raise ValueError('Invalid Steam login profile structure')
                value = next(tokens, None)
                if value is None or value == '}': raise ValueError('Truncated Steam login profile')
                result[key] = object_(True) if value == '{' else value
            if closing: raise ValueError('Truncated Steam login profile')
            return result
        users = object_().get('users', {})
        if not isinstance(users, dict): raise ValueError('Invalid Steam login profile')
        recent = [sid for sid, user in users.items() if isinstance(user, dict) and user.get('MostRecent') == '1']
        if len(recent) > 1: raise ValueError('Steam account is ambiguous; sign into the intended account before adding shortcuts.')
        if recent:
            sid = recent[0]
            if not sid.isdigit() or not STEAM_BASE <= int(sid) <= STEAM_BASE+0xffffffff:
                raise ValueError('Invalid Steam account identifier')
            return str(int(sid)-STEAM_BASE)
    accounts = [p.name for p in (root/'userdata').glob('*') if p.is_dir() and p.name.isdigit()]
    if len(accounts) > 1: raise ValueError('Steam account is ambiguous; sign into the intended account before adding shortcuts.')
    return accounts[0] if accounts else None


def _words(value):
    # Desktop Entry string escaping is applied before Exec token quoting.
    value = value.replace('\\\\', '\\').replace('\\s', ' ').replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '\r')
    return shlex.split(value)


def _target(name, desktop_path):
    path = Path(desktop_path).expanduser().absolute()
    if not path.is_file(): raise ValueError(f'{name}: desktop launcher is missing; install the app before adding it to Steam.')
    desktop = configparser.ConfigParser(interpolation=None)
    try: desktop.read_string(path.read_text())
    except configparser.Error as exc: raise ValueError(f'{name}: invalid desktop application launcher; review it before retrying.') from exc
    if not desktop.has_section('Desktop Entry') or desktop.get('Desktop Entry', 'Type', fallback='') != 'Application':
        raise ValueError(f'{name}: invalid desktop application launcher.')
    command = _words(desktop.get('Desktop Entry', 'Exec', fallback=''))
    title = desktop.get('Desktop Entry', 'Name', fallback='')
    if not command or not title: raise ValueError(f'{name}: desktop launcher has no application name or command.')
    return path, command, title


def _identity(command):
    if not command: return None
    executable = str(Path(command[0]).expanduser().resolve()) if '/' in command[0] else shutil.which(command[0])
    if not executable: return None
    if Path(executable).name == 'flatpak' and 'run' in command[1:]:
        args = command[command.index('run')+1:]
        app = next((arg for arg in args if re.fullmatch(r'[A-Za-z][\w-]*(?:\.[\w-]+){2,}', arg)), None)
        return ('flatpak', executable, app) if app else None
    return ('executable', executable)


def _validate_vdf(data):
    # library's audit parser tolerates EOF. Require all object terminators here,
    # so an incomplete Steam write cannot be mistaken for a missing shortcut.
    prefix = b'\x00shortcuts\x00'
    if not data.startswith(prefix): raise ValueError('Unsupported Steam shortcuts root')
    def end(pos, depth=0):
        if depth > 64: raise ValueError('Steam shortcuts nesting exceeds limit')
        while pos < len(data):
            typ = data[pos]; pos += 1
            if typ == 8: return pos
            _, pos = library._cstring(data, pos)
            if typ == 0: pos = end(pos, depth+1)
            elif typ == 1: _, pos = library._cstring(data, pos)
            elif typ in (2, 3, 7):
                pos += 8 if typ == 7 else 4
                if pos > len(data): raise ValueError('Truncated Steam shortcut value')
            else: raise ValueError('Unsupported Steam shortcut value')
        raise ValueError('Truncated Steam shortcuts object')
    tail = data[end(len(prefix)):]
    if tail not in (b'', b'\x08'): raise ValueError('Unexpected Steam shortcuts trailer')


def _present(user, name, path, command):
    vdf = Path.home()/'.local/share/Steam/userdata'/user/'config/shortcuts.vdf'
    if not vdf.exists(): return False
    try:
        data = vdf.read_bytes()
        _validate_vdf(data)
        records = library._read_obj(data, 0)[0]['shortcuts']
    except (ValueError, OSError) as exc: raise ValueError('Steam shortcuts could not be read; retry after Steam finishes saving its library.') from exc
    wanted = _identity(command)
    for entry in records.values():
        if not isinstance(entry, dict): continue
        try:
            if not isinstance(entry.get('exe', ''), str) or not isinstance(entry.get('LaunchOptions', ''), str):
                raise ValueError('Steam shortcut launch fields are not strings')
            executable = shlex.split(entry.get('exe', ''))
            options = shlex.split(entry.get('LaunchOptions', ''))
        except ValueError:
            if entry.get('appname') == name: raise ValueError(f'{name}: existing Steam launch arguments could not be read; inspect the shortcut before retrying.')
            continue
        # Steam can preserve the desktop target or expand its Exec command.
        if len(executable) == 1 and Path(executable[0]).expanduser().absolute() in (path, path.resolve()): return True
        found = _identity(executable+options)
        if wanted is not None and found == wanted: return True
    return False


def _receipt_path():
    return core.STATE/'steam-app-shortcuts.json'


def _steam_generation():
    result = []
    for comm in Path('/proc').glob('[0-9]*/comm'):
        try:
            if comm.parent.stat().st_uid != os.getuid() or comm.read_text().strip().lower() != 'steam': continue
            start = (comm.parent/'stat').read_text().rsplit(')', 1)[1].split()[19]
            result.append(comm.parent.name+':'+start)
        except (OSError, IndexError): continue
    return sorted(result)


def _receipts():
    data = core.load_json(_receipt_path(), {})
    if not isinstance(data, dict): raise ValueError('Saved Steam shortcut submissions are invalid; review them before retrying.')
    return data


def _pending(receipts, signature, user, key, path, generation):
    if signature not in receipts: return False
    receipt = receipts[signature]
    if (not isinstance(receipt, dict) or receipt.get('key') != key or receipt.get('user') != user
            or receipt.get('desktop') != str(path) or receipt.get('outcome') not in ('SUBMITTED', 'UNCONFIRMED')
            or not isinstance(receipt.get('generation'), list) or not receipt['generation']
            or not all(isinstance(item, str) and re.fullmatch(r'\d+:\d+', item) for item in receipt['generation'])):
        raise ValueError('Saved Steam shortcut submission is invalid; review it before retrying.')
    return bool(generation) and receipt['generation'] == generation


def _signature(user, key, path, command, title):
    # Keep the stable input path, not Flatpak deployment symlink destinations.
    return hashlib.sha256(json.dumps([user, key, str(path), command, title]).encode()).hexdigest()


def status(key, name, desktop_path):
    """Return READY only for an exact parsed target in the intended Steam account."""
    if not Path(desktop_path).expanduser().is_file(): return MISSING
    path, command, title = _target(name, desktop_path)
    user = _profile()
    if user is None: return MISSING
    if _present(user, name, path, command): return READY
    return PENDING if _pending(_receipts(), _signature(user, key, path, command, title), user, key, path, _steam_generation()) else MISSING


def ensure(key, name, desktop_path):
    """Submit once per account/target; a handoff is pending until Steam saves it."""
    path, command, title = _target(name, desktop_path)
    user = _profile()
    if user is None: raise ValueError(f'{name}: sign into Steam before adding the shortcut, then retry.')
    core.STATE.mkdir(parents=True, exist_ok=True)
    with (core.STATE/'steam-app-shortcuts.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if _present(user, name, path, command): return READY
        signature = _signature(user, key, path, command, title)
        receipts = _receipts()
        generation = _steam_generation()
        if _pending(receipts, signature, user, key, path, generation): return PENDING
        if not generation: raise ValueError(f'{name}: open Steam and sign in before adding the shortcut, then retry. Steam was not started automatically.')
        helper = shutil.which('steamos-add-to-steam')
        if helper: args = [helper, str(path)]
        else:
            steam = shutil.which('steam')
            if not steam: raise ValueError(f'{name}: Steam shortcut helper is unavailable; open Steam and retry.')
            MARKER.touch(exist_ok=True)
            args = [steam, 'steam://addnonsteamgame/'+urllib.parse.quote(str(path.resolve()), safe='')]
        receipts[signature] = {'key':key, 'user':user, 'desktop':str(path),
                               'generation':generation, 'outcome':'UNCONFIRMED'}
        core.save_json(_receipt_path(), receipts)
        try:
            process = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL, start_new_session=True)
        except OSError as exc:
            receipts.pop(signature, None); core.save_json(_receipt_path(), receipts)
            raise ValueError(f'{name}: Steam shortcut submission could not start; retry.') from exc
        # Persist the in-flight handoff before waiting. Interrupting our wait must
        # not duplicate a request still being processed by the detached Steam client.
        try: rc = process.wait(timeout=5)
        except subprocess.TimeoutExpired: return PENDING
        if rc:
            receipts.pop(signature, None)
            core.save_json(_receipt_path(), receipts)
            raise ValueError(f'{name}: Steam shortcut submission failed or was cancelled (status {rc}); retry.')
        receipts[signature]['outcome'] = 'SUBMITTED'
        core.save_json(_receipt_path(), receipts)
        return READY if _present(user, name, path, command) else PENDING
