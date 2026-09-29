#!/usr/bin/env python3
"""Isolated shared CSS prerequisite and live-connection regression contracts."""
import asyncio
from contextlib import nullcontext
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'lib'))
from deckctl import css_connection as connection, css_live, css_stack, core, setup_install, setup_plan


class ConnectionContracts(unittest.TestCase):
    def test_status_is_read_only_and_checks_actual_backend(self):
        answers = [[], str(css_stack.THEMES_DIR), 9]
        with patch.object(css_stack, '_validate_plugin'), patch.object(css_stack, '_fetch_json', side_effect=[{'success': True, 'res': x} for x in answers]) as fetch, patch.object(css_live, 'enable') as enable:
            self.assertTrue(connection.status()[0])
            self.assertEqual([call.args[1]['method'] for call in fetch.call_args_list], ['get_themes', 'fetch_theme_path', 'get_backend_version'])
            self.assertTrue(all(call.kwargs['timeout'] == 1 for call in fetch.call_args_list))
            enable.assert_not_called()

    def test_failed_status_does_not_activate_or_expose_exception(self):
        with patch.object(css_stack, '_validate_plugin'), patch.object(css_stack, '_fetch_json', side_effect=OSError('private-payload')), patch.object(css_live, 'enable') as enable:
            ready, evidence = connection.status()
            self.assertFalse(ready)
            self.assertEqual(evidence['code'], 'BACKEND_UNREACHABLE')
            self.assertNotIn('private-payload', evidence['message'])
            enable.assert_not_called()

    def test_existing_backend_is_reused_without_activation(self):
        with patch.object(connection, '_validate'), patch.object(connection, '_probe'), patch.object(css_live, 'enable') as enable:
            connection.prepare()
            enable.assert_not_called()

    def test_unreachable_backend_activates_once_then_verifies(self):
        with patch.object(connection, '_validate'), patch.object(connection, '_probe', side_effect=[connection.ConnectionError('BACKEND_UNREACHABLE', 'offline'), None]) as probe, patch.object(css_live, 'enable') as enable:
            connection.prepare()
            enable.assert_called_once_with()
            self.assertEqual(probe.call_count, 2)

    def test_live_failure_preserves_specific_diagnostic_without_blanket_advice(self):
        with patch.object(connection, '_validate'), patch.object(connection, '_probe', side_effect=connection.ConnectionError('BACKEND_UNREACHABLE', 'offline')), patch.object(css_live, 'enable', side_effect=css_live.LiveError('Open Steam Big Picture, then retry.', 'STEAM_CONTEXT')):
            with self.assertRaises(connection.ConnectionError) as caught:
                connection.prepare()
            self.assertEqual(caught.exception.code, 'STEAM_CONTEXT')
            self.assertNotIn('Standalone Backend', str(caught.exception))

    def test_bad_contract_and_response_never_activate(self):
        for error in ('BACKEND_RESPONSE', 'THEME_DIRECTORY', 'BACKEND_VERSION', 'BACKEND_HTTP'):
            with self.subTest(error=error), patch.object(connection, '_validate'), patch.object(connection, '_probe', side_effect=connection.ConnectionError(error, 'rejected')), patch.object(css_live, 'enable') as enable:
                with self.assertRaises(connection.ConnectionError): connection.prepare()
                enable.assert_not_called()

    def test_backend_readiness_is_not_a_port_or_receipt_check(self):
        for values, code in [([{}, '', 9], 'BACKEND_RESPONSE'), ([[], '/wrong/theme/path', 9], 'THEME_DIRECTORY'), ([[], str(css_stack.THEMES_DIR), True], 'BACKEND_VERSION'), ([[], str(css_stack.THEMES_DIR), 8], 'BACKEND_VERSION')]:
            with self.subTest(code=code), patch.object(connection, '_read', side_effect=values):
                with self.assertRaises(connection.ConnectionError) as caught: connection._probe()
                self.assertEqual(caught.exception.code, code)

    def test_activation_has_bounded_readiness_wait(self):
        with patch.object(connection, '_validate'), patch.object(connection, '_probe', side_effect=connection.ConnectionError('BACKEND_UNREACHABLE', 'offline')), patch.object(css_live, 'enable') as enable, patch.object(connection.time, 'monotonic', side_effect=[0, 6]):
            with self.assertRaises(connection.ConnectionError) as caught: connection.prepare()
            self.assertEqual(caught.exception.code, 'BACKEND_NOT_READY')
            enable.assert_called_once_with()

    def test_dispatch_shared_step_never_runs_component_apply(self):
        row = dict(key=connection.KEY, kind='css-connection', owner='decky')
        with patch.object(connection, 'prepare') as prepare, patch.object(css_stack, 'apply') as apply:
            self.assertIn('verified', setup_install.execute(row))
            prepare.assert_called_once_with()
            apply.assert_not_called()

    def test_dispatch_failure_is_retryable(self):
        row = dict(key=connection.KEY, kind='css-connection', owner='decky')
        with patch.object(connection, 'prepare', side_effect=connection.ConnectionError('STEAM_CONTEXT', 'Retry here.')):
            with self.assertRaisesRegex(setup_install.NeedsSetup, 'STEAM_CONTEXT'): setup_install.execute(row)


class PlanContracts(unittest.TestCase):
    def items(self, css=(), plugin=False, installed=False):
        plan = {'modules': ['decky'] if plugin or css else [], 'apps': [], 'components': {}, 'launchers': [], 'plugins': ['SDH-CssLoader'] if plugin or css else [], 'css': list(css), 'appearance': {'css': True}}
        with patch.object(setup_plan, 'normalize', return_value=plan), patch.object(core, 'module_manifests', return_value={'decky': (None, {'name': 'Decky'})}), patch.object(core, 'topo', side_effect=lambda roots: roots), patch.object(setup_plan.component_options, 'catalog', return_value={}), patch.object(setup_plan.setup_builder, 'plugin_items', return_value=[{'id': 'SDH-CssLoader', 'name': 'CSS Loader', 'summary': ''}]), patch.object(css_stack, 'selection_items', return_value=[{'id': name, 'name': name, 'summary': ''} for name in css]), patch.object(css_stack, 'installed_palette_components', return_value=['Round'] if installed else []):
            return setup_plan.items(plan)[1]

    def test_one_shared_parent_precedes_every_theme_and_profile(self):
        rows = self.items(css=('Round', 'Art Hero'))
        keys = [row['key'] for row in rows]
        self.assertEqual(keys.count(connection.KEY), 1)
        self.assertLess(keys.index('plugin:SDH-CssLoader'), keys.index(connection.KEY))
        for row in rows:
            if row['kind'] in ('css', 'css-profile'):
                self.assertIn(connection.KEY, row['requires'])
                self.assertLess(keys.index(connection.KEY), keys.index(row['key']))

    def test_plugin_only_has_no_unrequested_css_setup(self):
        self.assertNotIn(connection.KEY, [row['key'] for row in self.items(plugin=True)])

    def test_installed_only_palette_does_not_reselect_or_install_plugin(self):
        rows = self.items(installed=True)
        self.assertEqual([row['key'] for row in rows], [connection.KEY, 'dependency:css-profile'])
        self.assertEqual(rows[0]['requires'], [])

    def test_css_review_promises_no_sudo_or_restart(self):
        for kind in connection.KINDS:
            notes = ' '.join(setup_plan.review_notes({'key': connection.KEY, 'kind': kind}))
            self.assertIn('without sudo', notes)
            self.assertIn('No Decky restart', notes)
            self.assertNotIn('May restart', notes)


class QueueContracts(unittest.TestCase):
    def test_shared_failure_blocks_dependents_but_resume_rechecks_and_retains_work(self):
        rows = [dict(key=connection.KEY, kind='css-connection', name='CSS Loader connection', requires=[]), dict(key='css:Round', kind='css', name='Round', requires=[connection.KEY]), dict(key='dependency:css-profile', kind='css-profile', name='CSS profile', requires=[connection.KEY, 'css:Round']), dict(key='app:test', kind='flatpak', name='Independent app', requires=[])]
        state = {}
        ready = set()
        attempts = []
        fail = True
        def execute(row):
            attempts.append(row['key'])
            if row['key'] == connection.KEY and fail:
                raise setup_install.NeedsSetup('[STEAM_CONTEXT] Open Steam Big Picture, then Retry here.')
            ready.add(row['key'])
        def save(path, value): state[str(path)] = json.loads(json.dumps(value))
        def load(path, default=None): return json.loads(json.dumps(state.get(str(path), default)))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'VERSION').write_text('0.0.0-test')
            journal = SimpleNamespace(id='test-css', path=root / 'logs')
            with patch.object(core, 'ROOT', root), patch.object(core, 'STATE', root), patch.object(core, 'save_json', side_effect=save), patch.object(core, 'load_json', side_effect=load), patch.object(setup_plan, 'items', return_value=({}, rows)), patch.object(setup_plan, 'storage_budget', return_value=(root, None, '')), patch.object(setup_install, 'lock', return_value=nullcontext()), patch.object(setup_install.privilege, 'Session', return_value=nullcontext()), patch.object(setup_install, 'queue_checkpoint'), patch.object(setup_install, '_nested_decky_change', return_value=False), patch.object(setup_install.privilege, 'needed', return_value=False), patch.object(setup_install, 'execute', side_effect=execute), patch.object(setup_install, 'verify', side_effect=lambda row: row['key'] in ready), patch.object(setup_install.install_log, 'capture', side_effect=lambda *a, **k: nullcontext(None)), patch.object(setup_install.install_progress, 'listen', side_effect=lambda *a: nullcontext()), patch.object(setup_install.install_progress, 'report'), patch.object(setup_install.run_log, 'event'), patch.object(setup_install.run_log, 'archive_item'), patch.dict(os.environ, {'DECKCTL_UI_RUN': '1'}):
                self.assertEqual(setup_install._run_plan(None, False, journal), 2)
                records = load(setup_install.state_path())['items']
                self.assertEqual(records[connection.KEY]['status'], 'NEEDS_SETUP')
                self.assertEqual(records['css:Round']['status'], 'BLOCKED')
                self.assertEqual(records['dependency:css-profile']['status'], 'BLOCKED')
                self.assertEqual(records['app:test']['status'], 'DONE')
                self.assertEqual(attempts, [connection.KEY, 'app:test'])
                fail = False
                attempts.clear()
                self.assertEqual(setup_install._run_plan('css:Round', True, journal), 0)
                self.assertEqual(attempts, [connection.KEY, 'css:Round'])
                attempts.clear()
                self.assertEqual(setup_install._run_plan(None, True, journal), 0)
                self.assertEqual(attempts, ['dependency:css-profile'])
                ready.remove(connection.KEY)
                fail = True
                attempts.clear()
                self.assertEqual(setup_install._run_plan(None, True, journal), 2)
                self.assertEqual(attempts, [connection.KEY])


class LiveContracts(unittest.TestCase):
    def target(self, socket='ws://127.0.0.1:8080/devtools/page/test'):
        return {'title': 'SharedJSContext', 'url': 'https://steamloopback.host/routes/test', 'webSocketDebuggerUrl': socket}

    def test_target_accepts_only_expected_loopback_endpoints(self):
        for host in ('127.0.0.1', 'localhost', '[::1]'):
            url = 'ws://' + host + ':8080/devtools/page/test'
            self.assertEqual(css_live._target([self.target(url)]), url)
        for url in ('ws://example.com:8080/devtools/page/test', 'ws://localhost:1337/ws', 'ws://localhost:8080/devtools/page/test?auth=private', 'ws://user@localhost:8080/devtools/page/test', 'ws://localhost:bad/devtools/page/test'):
            with self.subTest(url=url), self.assertRaises(css_live.LiveError) as caught:
                css_live._target([self.target(url)])
            self.assertNotIn('private', str(caught.exception))

    def test_absent_or_ambiguous_context_is_distinct(self):
        for tabs in ([], [self.target(), self.target()]):
            with self.assertRaises(css_live.LiveError) as caught: css_live._target(tabs)
            self.assertEqual(caught.exception.code, 'STEAM_CONTEXT')

    def test_ipv6_fallback_only_after_connection_failure(self):
        class ConnectorError(Exception): pass
        response = Mock(status=200)
        response.content.read = AsyncMock(side_effect=[json.dumps([self.target('ws://[::1]:8080/devtools/page/test')]).encode(), b''])
        context = AsyncMock()
        context.__aenter__.return_value = response
        client = Mock()
        client.get.side_effect = [ConnectorError(), context]
        result = asyncio.run(css_live._debugger_target(client, SimpleNamespace(ClientConnectorError=ConnectorError)))
        self.assertIn('[::1]', result)
        self.assertEqual([call.args[0] for call in client.get.call_args_list], [css_live.DEBUGGER, css_live.DEBUGGER_IPV6])
        self.assertTrue(all(call.kwargs['allow_redirects'] is False for call in client.get.call_args_list))

    @unittest.skipUnless(shutil.which('node'), 'Node is needed to execute the fixed Steam expression')
    def test_javascript_activation_checks_races_errors_and_noop(self):
        cases = [([True], False, True), ([False, True], True, True), ([False, True], False, True), ([False, False], True, False)]
        for states, enabled, available in cases:
            with self.subTest(states=states, enabled=enabled):
                script = 'const states=' + json.dumps(states) + '; const DeckyBackend={ws:{readyState:1},call:async (route,plugin,method)=>({success:true,result:method==="get_server_state" ? states.shift() : {success:' + json.dumps(enabled) + '}})}; ' + css_live._expression(True) + '.then(x=>console.log(JSON.stringify(x)));'
                result = subprocess.run(['node', '-e', script], text=True, capture_output=True, check=True, timeout=5)
                self.assertEqual(json.loads(result.stdout)['available'], available)
        script = 'const DeckyBackend={ws:{readyState:1},call:async ()=>{throw new Error("private-payload")}}; ' + css_live._expression(True) + '.then(x=>console.log(JSON.stringify(x)));'
        result = subprocess.run(['node', '-e', script], text=True, capture_output=True, check=True, timeout=5)
        self.assertEqual(json.loads(result.stdout)['reason'], 'PLUGIN_CALL_FAILED')
        self.assertNotIn('private-payload', result.stdout)


if __name__ == '__main__': unittest.main()
