"""Activate CSS Loader through Steam's existing Decky connection, without reloads.

Never connect to Decky's single-client /ws endpoint: that evicts its frontend.
Only the existing local Steam debugger and CSS Loader's public methods are used.
aiohttp is optional; no package is downloaded or installed by this helper.
"""
import asyncio
import json
from urllib.parse import urlsplit

DEBUGGER = 'http://127.0.0.1:8080/json'
MAX_RESPONSE = 256 * 1024
SHARED_TITLES = {'SharedJSContext', 'Steam Shared Context presented by Valve™', 'Steam', 'SP'}


class LiveError(RuntimeError):
    pass


def _target(tabs):
    if not isinstance(tabs, list) or len(tabs) > 64:
        raise LiveError('Steam debugger returned an unsupported target list.')
    matches = []
    for tab in tabs:
        if not isinstance(tab, dict) or tab.get('title') not in SHARED_TITLES:
            continue
        page = urlsplit(tab.get('url', ''))
        if page.scheme != 'https' or page.hostname != 'steamloopback.host' or not (
                page.path.startswith('/routes/') or page.path == '/index.html'):
            continue
        socket_url = tab.get('webSocketDebuggerUrl', '')
        url = urlsplit(socket_url)
        if (url.scheme != 'ws' or url.hostname not in ('127.0.0.1', 'localhost') or
                url.port != 8080 or url.username or url.password or url.query or url.fragment or
                not url.path.startswith('/devtools/page/')):
            raise LiveError('Steam debugger target is not the expected local endpoint.')
        matches.append(socket_url)
    if len(matches) != 1:
        raise LiveError('Steam shared Decky context is unavailable or ambiguous.')
    return matches[0]


def _expression(enable):
    # Fixed operations only. No token retrieval, new Decky socket or arbitrary JS input.
    activation = '''
        if (!state.result) {
            const enabled = await DeckyBackend.call("loader/call_legacy_plugin_method", "CSS Loader", "enable_server", {});
            if (enabled?.success !== true || enabled.result?.success !== true)
                return {available:false};
        }
    ''' if enable else ''
    return '''(async () => {
        if (typeof DeckyBackend === "undefined" || typeof DeckyBackend.call !== "function" ||
            DeckyBackend.ws?.readyState !== 1) return {available:false};
        const state = await DeckyBackend.call("loader/call_legacy_plugin_method", "CSS Loader", "get_server_state", {});
        if (state?.success !== true || typeof state.result !== "boolean") return {available:false};
    ''' + activation + '''
        return {available:true};
    })()'''


async def _evaluate(expression):
    try:
        import aiohttp
    except ImportError as exc:
        raise LiveError('Live CSS setup needs the optional Python aiohttp package, or an already enabled CSS Loader standalone backend.') from exc
    async def reject_redirect(_client, _context, _params):
        raise LiveError('Steam debugger redirects are not permitted.')
    trace = aiohttp.TraceConfig()
    trace.on_request_redirect.append(reject_redirect)
    try:
        async with aiohttp.ClientSession(trust_env=False, timeout=aiohttp.ClientTimeout(total=5), trace_configs=[trace]) as client:
            async with client.get(DEBUGGER, allow_redirects=False) as response:
                if response.status != 200:
                    raise LiveError('Steam local debugger is unavailable.')
                raw = b''
                while chunk := await response.content.read(16384):
                    raw += chunk
                    if len(raw) > MAX_RESPONSE:
                        raise LiveError('Steam debugger response exceeds the size limit.')
                target = _target(json.loads(raw))
            async with client.ws_connect(target, max_msg_size=MAX_RESPONSE) as connection:
                await connection.send_json({'id': 1, 'method': 'Runtime.evaluate', 'params': {
                    'expression': expression, 'awaitPromise': True, 'returnByValue': True}})
                for _ in range(64):
                    message = await connection.receive_json()
                    if not isinstance(message, dict):
                        raise LiveError('Steam debugger returned an unsupported reply.')
                    if message.get('id') != 1:
                        continue
                    result = message.get('result', {})
                    if 'error' in message or 'exceptionDetails' in result:
                        raise LiveError('CSS Loader live request failed in Steam.')
                    value = result.get('result', {}).get('value')
                    if not isinstance(value, dict) or value.get('available') is not True:
                        raise LiveError('CSS Loader is not available through the existing Decky connection.')
                    return
                raise LiveError('Steam debugger did not return the requested reply.')
    except (aiohttp.ClientError, OSError, ValueError, TypeError, AttributeError) as exc:
        # Do not include debugger payloads, URLs or third-party exceptions in logs.
        raise LiveError('Could not reach Steam’s local CSS Loader connection.') from exc


def enable():
    """Enable the current session without a persistent CSS server setting or restart.

    Upstream enable_server may create Steam's CEF debugging flag if absent.
    """
    try:
        asyncio.run(asyncio.wait_for(_evaluate(_expression(True)), timeout=5))
    except TimeoutError as exc:
        raise LiveError('Steam’s live CSS request timed out; no restart was requested.') from exc
