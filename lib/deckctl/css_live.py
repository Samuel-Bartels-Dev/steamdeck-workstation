"""Activate CSS Loader through Steam's existing Decky connection, without reloads.

Never connect to Decky's single-client /ws endpoint: that evicts its frontend.
Only the existing local Steam debugger and CSS Loader's public methods are used.
aiohttp is optional; no package is downloaded or installed by this helper.
"""
import asyncio
import json
from urllib.parse import urlsplit

DEBUGGER = 'http://127.0.0.1:8080/json'
DEBUGGER_IPV6 = 'http://[::1]:8080/json'
MAX_RESPONSE = 256 * 1024
SHARED_TITLES = {'SharedJSContext', 'Steam Shared Context presented by Valve™', 'Steam', 'SP'}
REASONS = {
    'DECKY_UNAVAILABLE': 'Decky is not connected in Steam. Open Steam Big Picture and check that Decky is loaded, then retry here.',
    'PLUGIN_UNAVAILABLE': 'CSS Loader did not provide its server state. Check that the CSS Loader plugin is enabled in Decky, then retry here.',
    'ACTIVATION_FAILED': 'CSS Loader did not enable its local backend. Enable Standalone Backend in CSS Loader settings, then retry here.',
    'PLUGIN_CALL_FAILED': 'The existing Decky connection could not call CSS Loader. Check the plugin in Decky, then retry here.',
}


class LiveError(RuntimeError):
    def __init__(self, message, code='LIVE_UNAVAILABLE'):
        self.code = code
        super().__init__(message)


def _target(tabs):
    if not isinstance(tabs, list) or len(tabs) > 64:
        raise LiveError('Steam debugger returned an unsupported target list.', 'DEBUGGER_RESPONSE')
    matches = []
    for tab in tabs:
        if not isinstance(tab, dict) or not isinstance(tab.get('title'), str) or tab['title'] not in SHARED_TITLES:
            continue
        try:
            if not isinstance(tab.get('url'), str): continue
            page = urlsplit(tab['url'])
            if page.scheme != 'https' or page.hostname != 'steamloopback.host' or page.username or page.password or not (
                    page.path.startswith('/routes/') or page.path == '/index.html'):
                continue
            socket_url = tab.get('webSocketDebuggerUrl', '')
            if not isinstance(socket_url, str): raise ValueError('Invalid socket type')
            url = urlsplit(socket_url)
            if (url.scheme != 'ws' or url.hostname not in ('127.0.0.1', 'localhost', '::1') or
                    url.port != 8080 or url.username or url.password or url.query or url.fragment or
                    not url.path.startswith('/devtools/page/')):
                raise ValueError('Invalid socket endpoint')
        except ValueError as exc:
            raise LiveError('Steam debugger target is not the expected local endpoint.', 'DEBUGGER_TARGET') from exc
        matches.append(socket_url)
    if len(matches) != 1:
        raise LiveError('Steam shared Decky context is unavailable or ambiguous. Open Steam Big Picture, keep setup open, then retry here.', 'STEAM_CONTEXT')
    return matches[0]


def _expression(enable):
    # Fixed operations only. No token retrieval, new Decky socket or arbitrary JS input.
    activation = '''
        if (!state.result) {
            const enabled = await DeckyBackend.call("loader/call_legacy_plugin_method", "CSS Loader", "enable_server", {});
            if (enabled?.success !== true || typeof enabled.result?.success !== "boolean")
                return {available:false, reason:"ACTIVATION_FAILED"};
            // An already-enabled response can race another caller. Verify state,
            // rather than treating the upstream "Nothing to do" result as failure.
            const checked = await DeckyBackend.call("loader/call_legacy_plugin_method", "CSS Loader", "get_server_state", {});
            if (checked?.success !== true || checked.result !== true)
                return {available:false, reason:"ACTIVATION_FAILED"};
        }
    ''' if enable else ''
    return '''(async () => {
        if (typeof DeckyBackend === "undefined" || typeof DeckyBackend.call !== "function" ||
            DeckyBackend.ws?.readyState !== 1) return {available:false, reason:"DECKY_UNAVAILABLE"};
        try {
        const state = await DeckyBackend.call("loader/call_legacy_plugin_method", "CSS Loader", "get_server_state", {});
        if (state?.success !== true || typeof state.result !== "boolean")
            return {available:false, reason:"PLUGIN_UNAVAILABLE"};
    ''' + activation + '''
        return {available:true};
        } catch (_) { return {available:false, reason:"PLUGIN_CALL_FAILED"}; }
    })()'''


async def _debugger_target(client, aiohttp):
    # Steam/CEF may listen on IPv6 localhost only. Never try a non-loopback host.
    for address in (DEBUGGER, DEBUGGER_IPV6):
        try:
            async with client.get(address, allow_redirects=False) as response:
                if response.status != 200:
                    raise LiveError('Steam local debugger returned an unexpected HTTP status.', 'DEBUGGER_HTTP')
                raw = b''
                while chunk := await response.content.read(16384):
                    raw += chunk
                    if len(raw) > MAX_RESPONSE:
                        raise LiveError('Steam debugger response exceeds the size limit.', 'DEBUGGER_RESPONSE')
                try:
                    tabs = json.loads(raw)
                except (ValueError, UnicodeError) as exc:
                    raise LiveError('Steam debugger returned unreadable target data.', 'DEBUGGER_RESPONSE') from exc
                return _target(tabs)
        except aiohttp.ClientConnectorError:
            continue
    raise LiveError('Steam local debugger is not reachable on either loopback address. Open Steam Big Picture, keep setup open, then retry here. This does not prove Standalone Backend is disabled.', 'DEBUGGER_UNREACHABLE')


async def _evaluate(expression):
    try:
        import aiohttp
    except ImportError as exc:
        raise LiveError('Live CSS setup needs the optional Python aiohttp package, or an already enabled CSS Loader standalone backend.', 'PYTHON_DEPENDENCY') from exc
    async def reject_redirect(_client, _context, _params):
        raise LiveError('Steam debugger redirects are not permitted.', 'DEBUGGER_REDIRECT')
    trace = aiohttp.TraceConfig()
    trace.on_request_redirect.append(reject_redirect)
    stage = 'DEBUGGER_UNREACHABLE'
    try:
        async with aiohttp.ClientSession(trust_env=False, timeout=aiohttp.ClientTimeout(total=5), trace_configs=[trace]) as client:
            target = await _debugger_target(client, aiohttp)
            stage = 'DEBUGGER_SOCKET'
            async with client.ws_connect(target, max_msg_size=MAX_RESPONSE) as connection:
                await connection.send_json({'id': 1, 'method': 'Runtime.evaluate', 'params': {
                    'expression': expression, 'awaitPromise': True, 'returnByValue': True}})
                for _ in range(64):
                    message = await connection.receive_json()
                    if not isinstance(message, dict):
                        raise LiveError('Steam debugger returned an unsupported reply.', 'DEBUGGER_RESPONSE')
                    if message.get('id') != 1:
                        continue
                    result = message.get('result')
                    if 'error' in message or not isinstance(result, dict) or 'exceptionDetails' in result:
                        raise LiveError('CSS Loader live request failed in Steam.', 'DEBUGGER_EVALUATION')
                    remote = result.get('result')
                    value = remote.get('value') if isinstance(remote, dict) else None
                    if not isinstance(value, dict):
                        raise LiveError('Steam debugger returned an unsupported CSS result.', 'DEBUGGER_RESPONSE')
                    if value.get('available') is not True:
                        reason = value.get('reason')
                        if not isinstance(reason, str) or reason not in REASONS:
                            raise LiveError('CSS Loader returned an unsupported availability response.', 'DEBUGGER_RESPONSE')
                        raise LiveError(REASONS[reason], reason)
                    return
                raise LiveError('Steam debugger did not return the requested reply.', 'DEBUGGER_RESPONSE')
    except TimeoutError as exc:
        raise LiveError('Steam’s live CSS request timed out; retry here. No restart was requested.', 'LIVE_TIMEOUT') from exc
    except (ValueError, TypeError, AttributeError) as exc:
        raise LiveError('Steam debugger returned data that could not be read safely.', 'DEBUGGER_RESPONSE') from exc
    except (aiohttp.ClientError, OSError) as exc:
        # Never include debugger payloads, URLs or third-party exceptions in logs.
        message = ('Steam local debugger could not be reached. Open Steam Big Picture and retry here.'
                   if stage == 'DEBUGGER_UNREACHABLE' else
                   'Steam debugger WebSocket disconnected or could not be opened. Keep Steam Big Picture open and retry here.')
        raise LiveError(message, stage) from exc


def enable():
    """Enable this session without a persistent CSS server setting or restart.

    Upstream enable_server may create Steam's CEF debugging flag if absent.
    """
    try:
        asyncio.run(asyncio.wait_for(_evaluate(_expression(True)), timeout=5))
    except TimeoutError as exc:
        raise LiveError('Steam’s live CSS request timed out; retry here. No restart was requested.', 'LIVE_TIMEOUT') from exc
