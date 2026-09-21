#!/usr/bin/env python3
"""Optional actual Qt Quick + loopback smoke test; never provisions software."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'lib'))
from deckctl import apps, core, setup_window, gaming_options, css_stack, component_options


@unittest.skipUnless(shutil.which('qml6') or shutil.which('qml'), 'Qt Quick runtime unavailable')
class NativeSetup(unittest.TestCase):
    def test_real_window_saves_app_dependencies_without_installing(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            harness = base/'Smoke.qml'
            harness.write_text('''import QtQuick
import "''' + (ROOT/'lib/deckctl/ui').as_uri() + '''" as UI
UI.Setup {
    id: app
    width: 1120; height: 720
    property bool attempted: false
    Timer {
        running: app.loaded; interval: 100; repeat: true
        onTriggered: {
            if (!app.attempted) {
                app.attempted = true
                app.preset(false)
                app.toggle("zed", true)
                app.toggle("gaming", false)
                app.detailPage = "launchers"
                app.toggle("heroic", false)
                app.detailPage = "plugins"
                app.detailPreset(false)
                app.toggle("SDH-CssLoader", false)
                app.detailPage = "css"
                app.detailPreset(false)
                app.toggle("Round", false)
                app.stage = 1
                app.toggle("terminal", false)
                app.detailPage = "terminal"
                app.detailPreset(false)
                app.toggle("ghostty", false)
                app.stage = 4
                app.savePlan(false)
            } else if (app.saved) {
                app.dirty = false
                Qt.exit(app.allModules().indexOf("dev") >= 0 ? 0 : 3)
            }
        }
    }
    Timer { running: true; interval: 8000; onTriggered: { app.dirty=false; Qt.exit(4) } }
}
''')
            run = subprocess.run
            def start(args, **kwargs):
                args[1] = str(harness)
                return run(args, timeout=12, **kwargs).returncode
            env = dict(os.environ, QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software', QT_FORCE_STDERR_LOGGING='1')
            with patch.object(core, 'CONFIG_HOME', base/'config'), patch.object(core, 'STATE', base/'state'), patch.dict(os.environ, env), patch.object(setup_window.subprocess, 'call', side_effect=start), patch.object(setup_window.Session, 'start', side_effect=AssertionError('Smoke test must never install')):
                self.assertEqual(setup_window.launch(), 0)
                self.assertEqual(apps.selection(), ['zed'])
                self.assertEqual(gaming_options.selection(), ['heroic'])
                self.assertEqual(core._decky_selected_folders(), {"SDH-CssLoader"})
                self.assertEqual(css_stack.selection(), ["Round"])
                self.assertEqual(component_options.selection()['terminal'], ['ghostty'])
                self.assertIn('dev', core.enabled_modules())
                self.assertFalse((base/'state').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
