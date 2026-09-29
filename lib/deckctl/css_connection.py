"""One retryable CSS prerequisite shared by the installer queue.

Status is read-only. Prepare may enable CSS Loader through the existing Steam
connection, but never installs packages, changes sessions or restarts services.
"""
from pathlib import Path
import time
import urllib.error
from . import css_live, css_stack

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
        raise ConnectionError('BACKEND_UNREACHABLE', 'CSS Loader\'s local backend is not reachable. Choose Retry to attempt live activation; no restart is required by the installer.') from exc
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


def prepare():
    """Activate once for this queue prerequisite, then verify the real backend."""
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
    except css_live.LiveError as exc:
        raise ConnectionError(exc.code, str(exc)) from exc
    deadline = time.monotonic() + 5
    while True:
        try:
            _probe()
            return
        except ConnectionError as exc:
            if exc.code != 'BACKEND_UNREACHABLE':
                raise
            if time.monotonic() >= deadline:
                raise ConnectionError('BACKEND_NOT_READY', 'CSS Loader did not become reachable after live activation. Check Standalone Backend in CSS Loader settings, then Retry here. No restart was requested.') from exc
            time.sleep(.2)
