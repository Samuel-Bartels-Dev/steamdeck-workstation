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

    def test_palette_only_changes_selected_components(self):
        backend = self.fake_install()
        self.assertEqual(css.apply(), 0)
        before = {p: p.read_bytes() for p in css.THEMES_DIR.glob('*/config_*.json')}
        self.choose('ocean', ['Chromahon (QAM)'])
        self.assertEqual(css.apply(), 0)
        target = next(t['name'] for t in backend.themes() if t['display_name'] == 'Chromahon (QAM)')
        for path, content in before.items():
            if path.parent.name != target: self.assertEqual(path.read_bytes(), content)

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

    def test_no_css_selection_does_not_start_backend(self):
        self.choose('graphite', [])
        self.assertEqual(css.apply(), 0)
        self.assertFalse(css.THEMES_DIR.exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
