"""One retryable CSS prerequisite shared by the installer queue.

Status is read-only. Prepare may enable CSS Loader through the existing Steam
connection. Normal Desktop may use a temporary upstream server flag and Decky
restart; Nested Desktop never takes that fallback.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
import os
import subprocess
import time
import urllib.error
from . import css_live, css_stack, decky_installer, privilege, user_session

KEY = 'dependency:css-connection'
KINDS = ('css-connection', 'css', 'css-profile')


class ConnectionError(RuntimeError):
    def __init__(self, code, message):
        self.code = code
        super().__init__('[' + code + '] ' + message)


def _validate():
    try:
        css_stack._validate_plugin()
    except (OSError, ValueError, SyntaxError, KeyError, TypeError, css_stack.CSSError) as exc:
        raise ConnectionError('PLUGIN_CONTRACT', 'CSS Loader is missing, unreadable or has an unsupported backend interface. Check the plugin in Decky, then choose Retry here.') from exc


def _read(method):
    try:
        envelope = css_stack._fetch_json(css_stack.BACKEND_URL, {'method': method, 'args': {}}, timeout=1)
    except urllib.error.HTTPError as exc:
        raise ConnectionError('BACKEND_HTTP', 'CSS Loader rejected the local status request. Check the plugin in Decky, then retry here.') from exc
    except (OSError, TimeoutError) as exc:
        raise ConnectionError('BACKEND_UNREACHABLE', 'CSS Loader\'s local backend is not reachable. Choose Retry here to reconnect in Desktop Mode.') from exc
    except (ValueError, TypeError, css_stack.CSSError) as exc:
        raise ConnectionError('BACKEND_RESPONSE', 'CSS Loader returned an unreadable local response. Check the plugin in Decky, then retry here.') from exc
    if not isinstance(envelope, dict) or envelope.get('success') is not True or 'res' not in envelope:
        raise ConnectionError('BACKEND_RESPONSE', 'CSS Loader returned an unsupported local response. Check the plugin in Decky, then retry here.')
    return envelope['res']


def _probe():
    themes = _read('get_themes')
    if not isinstance(themes, list) or any(not isinstance(item, dict) or not isinstance(item.get('name'), str) or not isinstance(item.get('patches'), list) for item in themes):
        raise ConnectionError('BACKEND_RESPONSE', 'CSS Loader returned an unsupported theme list.')
    path = _read('fetch_theme_path')
    if not isinstance(path, str) or Path(path).resolve() != css_stack.THEMES_DIR.resolve():
        raise ConnectionError('THEME_DIRECTORY', 'CSS Loader uses a different theme directory. No themes were changed.')
    version = _read('get_backend_version')
    if type(version) is not int or version < 9:
        raise ConnectionError('BACKEND_VERSION', 'CSS Loader backend version 9 or newer is required for configurable colors.')


def status():
    """Observe the installed backend; never activate it or trust a saved receipt."""
    try:
        _validate()
        _probe()
    except ConnectionError as exc:
        return False, {'configuration': True, 'code': exc.code, 'message': str(exc)}
    return True, {'configuration': True, 'code': 'READY', 'message': 'CSS Loader connection verified.'}


_scope = ContextVar('css_bridge_scope', default=None)


@contextmanager
def session(permission=None):
    """Own only our temporary flag; close it before run authorization expires."""
    if _scope.get() is not None:
        yield
        return
    if permission is None:
        with privilege.Session() as owned_permission, session(owned_permission):
            yield
        return
    state = {'created': False, 'permission': permission}
    token = _scope.set(state)
    try:
        yield
    finally:
        try:
            if state['created']:
                state['sentinel'].unlink(missing_ok=True)
                if not decky_installer._restart_decky():
                    raise ConnectionError('BRIDGE_CLEANUP', 'Temporary CSS flag removed, but Decky could not close the bridge. Settings are saved; Retry here in normal Desktop Mode.')
        finally:
            _scope.reset(token)


def _wait(seconds):
    deadline = time.monotonic() + seconds
    while True:
        try:
            _probe()
            return
        except ConnectionError as exc:
            if exc.code != 'BACKEND_UNREACHABLE':
                raise
            if time.monotonic() >= deadline:
                raise ConnectionError('BACKEND_NOT_READY', 'CSS Loader did not become reachable. Retry the connection here; completed work is saved.') from exc
            time.sleep(.2)


def _desktop_bridge():
    if user_session.nested_desktop():
        raise ConnectionError('NESTED_DESKTOP', user_session.NESTED_DESKTOP_NOTICE)
    state = _scope.get()
    if state is None:
        raise ConnectionError('BRIDGE_SCOPE', 'Retry CSS setup from the installation window.')
    if os.environ.get('DECKCTL_UI_RUN') == '1':
        permission = state['permission']
        try:
            if permission is None:
                raise RuntimeError('Retry CSS setup from the installation window.')
            if not permission.attempted:
                permission.prepare()
            privilege.command([])
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            raise ConnectionError('AUTHORIZATION', str(exc)) from exc
    sentinel = css_stack.THEMES_DIR / 'SERVER'
    css_stack.THEMES_DIR.mkdir(parents=True, exist_ok=True)
    try:
        sentinel.touch(exist_ok=False)
        state.update(created=True, sentinel=sentinel)
    except FileExistsError:
        pass  # An existing user setting is never removed.
    print('Starting temporary CSS Loader bridge in normal Desktop Mode (Decky restart).', flush=True)
    if not decky_installer._restart_decky():
        raise ConnectionError('BRIDGE_RESTART', 'Decky could not start the CSS bridge. Retry here; selections are saved.')
    _wait(30)


def prepare():
    """Prefer the live path; repair only within a managed setup session."""
    _validate()
    try:
        _probe()
        return
    except ConnectionError as exc:
        if exc.code != 'BACKEND_UNREACHABLE':
            raise
    print('Opening CSS Loader live connection through Steam; no Decky restart.', flush=True)
    try:
        css_live.enable()
        _wait(5)
        return
    except css_live.LiveError as exc:
        if exc.code not in ('DEBUGGER_UNREACHABLE', 'STEAM_CONTEXT', 'PYTHON_DEPENDENCY', 'DECKY_UNAVAILABLE'):
            raise ConnectionError(exc.code, str(exc)) from exc
    except ConnectionError as exc:
        if exc.code != 'BACKEND_NOT_READY':
            raise
    _desktop_bridge()
