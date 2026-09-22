#!/usr/bin/env python3
"""Shared appearance choices and truthful installation progress."""
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'lib'))
from deckctl import appearance, core, css_stack, install_log, install_progress, setup_builder, setup_install, setup_plan, setup_window, terminal


class Experience(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        for owner, name, value in [(core, 'CONFIG_HOME', self.home/'config'), (core, 'STATE', self.home/'state'), (terminal, 'HOME', self.home)]:
            p = patch.object(owner, name, value); p.start(); self.addCleanup(p.stop)

    def test_palettes_render_real_configs_and_disabled_theme_preserves_bytes(self):
        source = core.ROOT/'modules/terminal'
        for palette in css_stack.palette_catalog():
            core.save_json(core.CONFIG_HOME/'css-selection.json', {'palette': palette['id'], 'selected': []})
            ff = json.loads(appearance.render((source/'fastfetch.json').read_text()))
            self.assertEqual(ff['logo']['color']['1'], palette['css_palette']['pink'])
            posh = json.loads(appearance.render((source/'bubble-gum-rave.omp.json').read_text()))
            self.assertEqual(posh['blocks'][0]['segments'][0]['background'], palette['css_palette']['pink'])
            terminal._ghostty_config()
            theme = self.home/'.config/ghostty/themes/deckctl-bubble-gum-rave'
            self.assertIn('cursor-color = '+palette['css_palette']['pink'], theme.read_text())
            konsole = appearance.render((source/'BubbleGumRave.colorscheme').read_text())
            rgb = ','.join(str(int(palette['css_palette']['background'][i:i+2], 16)) for i in (1,3,5))
            self.assertIn('[Background]\nColor='+rgb, konsole)
        core.save_json(core.CONFIG_HOME/'appearance.json', {'fastfetch': False, 'ghostty': False})
        folder = self.home/'managed'; folder.mkdir()
        ff = folder/'fastfetch.json'; ff.write_text('personal settings')
        previous = theme.read_bytes()
        with patch.object(terminal, 'TERM_CONFIG', folder), patch.object(terminal, 'SHELL_CONFIG', folder/'shell'), patch.object(terminal, 'KONSOLE_DIR', folder/'konsole'):
            terminal._copy_managed_config({'fastfetch', 'ghostty'})
        self.assertEqual(ff.read_text(), 'personal settings')
        self.assertEqual(theme.read_bytes(), previous)

    def test_appearance_saves_without_installing_tools_and_rejects_invalid_values(self):
        payload = {'modules': ['base'], 'apps': [], 'components': {}, 'css': [], 'plugins': [], 'palette': 'ocean', 'appearance': {'ghostty': False}}
        setup_window.Session().save(payload)
        self.assertEqual(core.enabled_modules(), ['base'])
        self.assertFalse(setup_window.Session().snapshot()['appearance']['ghostty'])
        first = setup_plan.fingerprint(setup_plan.normalize(payload))
        payload['appearance']['ghostty'] = True
        self.assertNotEqual(first, setup_plan.fingerprint(setup_plan.normalize(payload)))
        before = {p.name: p.read_bytes() for p in core.CONFIG_HOME.iterdir()}
        for value in ({'ghostty': 'false'}, {'unknown': True}, []):
            with self.assertRaises(ValueError): setup_builder.save_plan(['base'], [], appearance_choices=value)
        self.assertEqual(before, {p.name: p.read_bytes() for p in core.CONFIG_HOME.iterdir()})

    def test_decky_opt_out_keeps_components_but_disables_palette_writes(self):
        core.save_json(core.CONFIG_HOME/'appearance.json', {'css': False})
        stack = css_stack._stack(unfiltered=True)
        self.assertTrue(stack['required'])
        self.assertTrue(all(not row.get('configure_palette') for group in ('required', 'recommended', 'optional') for row in stack.get(group, [])))

    def test_transfer_bytes_known_and_unknown_and_size_guard(self):
        class Response(io.BytesIO):
            headers = {'Content-Length': '6'}
        rows = []
        with patch.object(terminal.urllib.request, 'urlopen', return_value=Response(b'abcdef')), install_progress.listen(lambda *args: rows.append(args)):
            self.assertEqual(terminal._request('https://example.test/tool'), b'abcdef')
        self.assertEqual(rows[-1][0], 'Downloading')
        self.assertEqual(rows[-1][2:], (6, 6))
        response = Response(b'ab'); response.headers = {}
        with patch.object(terminal.urllib.request, 'urlopen', return_value=response), install_progress.listen(lambda *args: rows.append(args)):
            terminal._request('https://example.test/tool')
        self.assertEqual(rows[-1][2:], (2, None))

    def test_live_phase_elapsed_log_and_failure_preserve_diagnostics(self):
        row = dict(key='terminal:ghostty', name='Ghostty', kind='component', requires=[], visible=True)
        plan = {'test': True}
        seen = []
        def execute(_):
            install_progress.report('Downloading', 'Downloading tool', 5, 10)
            seen.append(setup_window.Session().progress()['items'][0])
            install_progress.report('Extracting', 'Extracting runtime')
            seen.append(setup_window.Session().progress()['items'][0])
            raise RuntimeError('provider failed access_token=secret-value')
        with patch.object(setup_plan, 'items', return_value=(plan, [row])), patch.object(setup_plan, 'storage_budget', return_value=(self.home, None, '')), patch.object(setup_install, 'verify', return_value=True), patch.object(setup_install, 'execute', side_effect=execute):
            self.assertEqual(setup_install.run(), 1)
            self.assertEqual(seen[0]['phase'], 'Downloading')
            self.assertEqual(seen[0]['downloaded'], 5)
            self.assertIsNone(seen[1]['downloaded'])
            self.assertGreaterEqual(seen[1]['elapsedSeconds'], 0)
            text = setup_window.Session().log(row['key'])['text']
            self.assertIn('Extracting runtime', text)
            self.assertIn('provider failed', text)
            self.assertNotIn('secret-value', text)
            with self.assertRaises(ValueError): setup_window.Session().log('../secret')
            path = install_log.path_for(row['key']); path.unlink(); path.symlink_to(self.home/'private')
            with self.assertRaises(OSError): setup_window.Session().log(row['key'])


if __name__ == '__main__': unittest.main(verbosity=2)
