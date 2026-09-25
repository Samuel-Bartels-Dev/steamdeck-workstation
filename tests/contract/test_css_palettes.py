#!/usr/bin/env python3
"""Palette changes must reach native CSS state, without redownloads or collateral edits."""
import copy
import json
import unittest

from test_v0219 import Isolated, css, core, upstream_themes, write_json


class CSSPalettes(Isolated):
    def choose(self, key, names=None):
        write_json(core.CONFIG_HOME / 'css-selection.json',
                   {'selected': css.selection() if names is None else names, 'palette': key})

    def test_switch_updates_native_colors_and_profile_without_redownload(self):
        backend = self.fake_install()
        self.assertEqual(css.apply(), 0)
        original = copy.deepcopy(backend.loaded)
        downloads = len([c for c in backend.calls if c[0] == 'download_theme_from_url'])
        for key in ('ocean', 'graphite', 'bubblegum'):
            self.choose(key)
            self.assertFalse(css.readiness()[0])
            self.assertEqual(css.apply(), 0)
            self.assertTrue(css.readiness()[0])
            stack = css._stack()
            self.assertIn(stack['palette_name'], css.readiness()[1])
            profile = css.THEMES_DIR / (stack['preset'] + '.profile/theme.json')
            self.assertTrue(profile.is_file())
            theme = next(t for t in backend.themes() if t['display_name'] == 'Chromahon (QAM)')
            desired = css.palette_plan(theme, stack['palette'], stack['named_presets'])
            css._verify_live(theme, desired)
            config = json.loads((css.THEMES_DIR / theme['name'] / 'config_USER.json').read_text())
            self.assertTrue(css._matches_config(config, desired))
            if key != 'bubblegum': self.assertNotEqual(original[theme['name']], theme)
            self.assertEqual(downloads, len([c for c in backend.calls if c[0] == 'download_theme_from_url']))
            calls = copy.deepcopy(backend.calls)
            self.assertEqual(css.apply(), 0)
            self.assertEqual(calls, backend.calls)

    def test_palette_discovers_installed_themes_with_empty_install_selection(self):
        from deckctl import setup_builder, setup_plan
        backend = self.fake_install()
        self.assertEqual(css.apply(), 0)
        downloads = sum(c[0] == 'download_theme_from_url' for c in backend.calls)
        disabled = next(t for t in backend.loaded.values() if t['display_name'] == 'Chromahon (QAM)')
        disabled['enabled'] = False
        backend.persist(disabled)
        unrelated = css.THEMES_DIR / 'Personal theme/config_USER.json'
        write_json(unrelated, {'active': True, 'color': 'mine'})
        write_json(unrelated.parent/'theme.json', {'name':'Personal theme'})
        before = unrelated.read_bytes()
        original = copy.deepcopy(backend.loaded)
        self.choose('ocean', [])
        write_json(core.CONFIG_HOME/'appearance.json', {'css':True})
        setup_builder.save_plan(['base'], [], css=[], appearance_choices={'css':True})
        self.assertIn('dependency:css-profile', {row['key'] for row in setup_plan.items()[1]})
        self.assertIsNone(css.selection_error())
        self.assertEqual(css.apply(), 0)
        self.assertEqual(css.selection(), [])
        self.assertTrue(css.readiness()[0])
        self.assertFalse(backend.loaded[disabled['name']]['enabled'])
        self.assertEqual(unrelated.read_bytes(), before)
        self.assertEqual(downloads, sum(c[0] == 'download_theme_from_url' for c in backend.calls))
        for name in css.installed_palette_components():
            theme = css._live_theme(backend.themes(), name)
            stack = css._stack()
            desired = css.palette_plan(theme, stack['palette'], stack['named_presets'])
            css._verify_live(theme, desired, theme['enabled'])
            for patch in theme['patches']:
                if patch['name'] not in desired:
                    self.assertIn(patch, original[theme['name']]['patches'])
        calls = copy.deepcopy(backend.calls)
        self.choose('graphite', [])
        write_json(core.CONFIG_HOME/'appearance.json', {'css':False})
        self.assertEqual(css.apply(), 0)
        self.assertEqual(backend.calls, calls)

    def test_missing_live_installed_theme_never_downloads_unselected_theme(self):
        backend = self.fake_install()
        self.assertEqual(css.apply(), 0)
        self.choose('ocean', [])
        write_json(core.CONFIG_HOME/'appearance.json', {'css':True})
        backend.loaded.clear()
        backend.calls.clear()
        self.assertEqual(css.apply(), 2)
        self.assertFalse(any(c[0] == 'download_theme_from_url' for c in backend.calls))

    def test_each_palette_uses_advertised_controls_and_matching_named_colors(self):
        for palette in css.palette_catalog():
            for theme in upstream_themes():
                plan = css.palette_plan(theme, palette['css_palette'], palette['named_presets'])
                values = [value for patch in plan.values() for value in patch['components'].values()]
                self.assertTrue(values)
                self.assertTrue(set(values).issubset(set(palette['css_palette'].values())))
        theme = {'name': 'Keyboard', 'patches': [{'name': 'Color', 'options': ['Pink', 'Cyan', 'Grey'], 'components': []}]}
        for key, expected in [('bubblegum', 'Pink'), ('ocean', 'Cyan'), ('graphite', 'Grey')]:
            palette = next(p for p in css.palette_catalog() if p['id'] == key)
            self.assertEqual(css.palette_plan(theme, palette['css_palette'], palette['named_presets'])['Color']['value'], expected)
        with self.assertRaises(css.CSSError):
            css.palette_plan(theme, palette['css_palette'], ['unsupported'])

    def test_individual_components_preserve_receipts_and_final_profile(self):
        backend = self.fake_install()
        names = ['Chromahon (QAM)', 'Chromahon (Steam Menu)']
        self.choose('ocean', names)
        self.assertEqual(css.apply(only=names[0]), 0)
        self.assertTrue(css.component_ready(names[0]))
        self.assertFalse(css.component_ready(names[1]))
        self.assertFalse(css.readiness()[0])
        self.assertEqual(css.apply(only=names[1]), 0)
        self.assertTrue(all(css.component_ready(name) for name in names))
        calls = copy.deepcopy(backend.calls)
        self.assertEqual(css.apply(only=names[0]), 0)
        self.assertEqual(calls, backend.calls)
        self.assertEqual(css.apply(), 0)
        self.assertTrue(css.readiness()[0])
        write_json(core.STATE/'ui-safe.json', {'active': True})
        self.assertFalse(css.component_ready(names[0]))

    def test_empty_selection_never_reports_palette_applied(self):
        import contextlib
        import io
        self.choose('ocean', [])
        from deckctl import appearance
        self.assertFalse(appearance.enabled('css'))
        status = css.palette_status()
        self.assertEqual(status['state'], 'NO_TARGETS')
        self.assertIn('not applied to Game Mode', status['message'])
        output = io.StringIO()
        with contextlib.redirect_stdout(output): self.assertEqual(css.status(), 0)
        self.assertTrue(output.getvalue().startswith('UNCHANGED'))
        self.assertNotIn('READY', output.getvalue())

    def test_explicit_enabled_empty_selection_is_an_error(self):
        from deckctl import setup_builder
        self.choose('ocean', [])
        write_json(core.CONFIG_HOME/'appearance.json', {'css':True})
        self.assertFalse(css.readiness()[0])
        self.assertEqual(css.palette_status()['state'], 'INVALID')
        self.assertEqual(css.apply(), 2)
        self.assertFalse(css.THEMES_DIR.exists())
        before = (core.CONFIG_HOME/'css-selection.json').read_bytes()
        with self.assertRaisesRegex(ValueError, 'no CSS components'):
            setup_builder.save_plan(['base'], [], css=[], appearance_choices={'css':True})
        with self.assertRaisesRegex(ValueError, 'no CSS components'):
            setup_builder.save_plan(['base'], [], css=[])
        self.assertEqual((core.CONFIG_HOME/'css-selection.json').read_bytes(),before)
        write_json(core.CONFIG_HOME/'appearance.json', {'css':False})
        self.assertTrue(css.readiness()[0])

    def test_no_css_selection_does_not_start_backend(self):
        self.choose('graphite', [])
        self.assertEqual(css.apply(), 0)
        self.assertFalse(css.THEMES_DIR.exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
