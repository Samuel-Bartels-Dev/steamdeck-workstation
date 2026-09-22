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
        for width, height in ((1120,720),(800,600),(760,540)):
            with self.subTest(size=(width,height)):
                self.check_flow(width,height)

    def check_flow(self, width, height):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            harness = base/'Smoke.qml'
            harness.write_text('''import QtQuick
import "''' + (ROOT/'lib/deckctl/ui').as_uri() + '''" as UI
UI.Setup {
    id: app
    width: 1120; height: 720
    property bool attempted: false
    property bool retried: false
    function findObject(root, name) {
        if (root.objectName === name) return root
        var children=root.children || []
        for (var i=0;i<children.length;i++) { var found=findObject(children[i],name); if (found) return found }
        return null
    }
    Timer {
        running: app.loaded; interval: 100; repeat: true
        onTriggered: {
            if (!app.attempted) {
                app.attempted = true
                if (app.dirty || app.selectionCount() !== 0) throw new Error("Fresh setup must start empty")
                function choose(id) {
                    var item=app.currentItems().filter(function(x) { return x.id === id })[0]
                    if (!item) throw new Error("Missing choice " + id)
                    app.toggleItem(item)
                    return item
                }
                function ids() { return app.currentItems().map(function(x) { return x.id }) }
                if (ids().indexOf("heroic") < 0 || ids().indexOf("gaming") >= 0) throw new Error("Gaming still hides installs behind categories")
                var original = JSON.stringify(app.chosen)
                app.browse("plugins")
                app.browse("css")
                if (app.dirty || JSON.stringify(app.chosen) !== original) throw new Error("Browsing changed selections")
                choose("Round")
                if (app.pageValues("plugins").indexOf("SDH-CssLoader") < 0 || app.chosen.indexOf("decky") < 0) throw new Error("Theme missing required parents")
                app.back()
                if (app.detailPage !== "plugins" || app.stage !== 0) throw new Error("Theme back did not return to plugins")
                app.back()
                if (app.detailPage !== "" || app.stage !== 0) throw new Error("Plugins back did not return to Gaming")
                app.choosePalette("ocean")
                choose("heroic")
                app.navigate(3)
                if (ids().indexOf("utilities") >= 0 || ids().indexOf("parsec") < 0 || ids().indexOf("moonlight") < 0) throw new Error("Remote has a redirect or missing individual apps")
                choose("parsec")
                if (app.stage !== 3) throw new Error("Choosing a remote app changed sidebar sections")
                app.navigate(1)
                if (ids().indexOf("zed") >= 0 || ids().indexOf("parsec") >= 0) throw new Error("App choices duplicated across sections")
                choose("slack"); choose("whatsapp"); choose("telegram"); choose("plex")
                app.navigate(2)
                choose("zed"); choose("ghostty")
                if (app.pageValues("terminal").join(",") !== "ghostty") throw new Error("Ghostty enabled a bundle")
                choose("model-7b")
                if (app.pageValues("ai-workspace").indexOf("model") >= 0) throw new Error("7B unexpectedly selected 1.5B")
                var engine=app.currentItems().filter(function(x) { return x.id === "ollama" })[0]
                if (!app.itemSelected(engine) || !app.requiredBy(engine)) throw new Error("Required engine is not shown as included")
                choose("ollama")
                if (!app.itemSelected(engine)) throw new Error("Model dependency was removed")
                choose("docker"); choose("claude-code")
                app.searchText="ghostty"
                if (app.currentItems().length !== 1) throw new Error("Search did not narrow choices")
                app.searchText=""
                app.selectedOnly=true
                if (ids().indexOf("tmux") >= 0 || ids().indexOf("opencode") < 0) throw new Error("Selected filter misses dependency or shows unselected item")
                app.navigate(4)
                var names = app.reviewSections().reduce(function(out, section) { return out.concat(section.items.map(function(x) { return x.name })) }, [])
                if (names.indexOf("Ghostty") < 0 || names.indexOf("tmux") >= 0 || names.indexOf("Docker & Compose") < 0) throw new Error("Review is not the actual item selection")
                var remoteSection=app.reviewSections().filter(function(x) { return x.title === "Remote connections" })[0]
                app.editSection(remoteSection)
                if (app.stage !== 3 || ids().indexOf("parsec") < 0) throw new Error("Review edit did not open the right group")
                app.back()
                if (app.stage !== 4) throw new Error("Done editing did not return to review")
                app.progress = {running:false, operation:"install", exitCode:1, modules:[]}
                if (app.installTitle() !== "Setup needs attention") throw new Error("Failure shown as successful")
                app.savePlan(false)
            } else if (app.saved && !app.busy) {
                if (!app.retried) {
                    app.retried=true
                    app.navigate(5)
                    app.progress={running:false,operation:"accounts",exitCode:1,modules:[]}
                    var action=app.findObject(app.contentItem,"primaryAction")
                    if (!action || action.text !== "Retry setup") throw new Error("Failed account phase has wrong action")
                    action.clicked()
                    return
                }
                if (app.paletteId !== "ocean" || app.activePalette.name !== "Midnight Ocean") throw new Error("Palette did not apply")
                if (app.progress.operation !== "accounts" || app.progress.exitCode !== 0) throw new Error("Retry switched to installing")
                app.dirty = false
                Qt.exit(app.allModules().indexOf("dev") >= 0 ? 0 : 3)
            }
        }
    }
    Timer { running: true; interval: 8000; onTriggered: { app.dirty=false; Qt.exit(4) } }
}
'''.replace('width: 1120; height: 720', f'width: {width}; height: {height}'))
            run = subprocess.run
            def start(args, **kwargs):
                args[1] = str(harness)
                return run(args, timeout=12, **kwargs).returncode
            operations=[]
            def fake_start(session, operation):
                operations.append(operation)
                self.assertEqual(operation, 'accounts', 'Retry must not install software')
                return dict(running=False, operation=operation, exitCode=0, modules=[])
            env = dict(os.environ, QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software', QT_FORCE_STDERR_LOGGING='1')
            with patch.object(core, 'CONFIG_HOME', base/'config'), patch.object(core, 'STATE', base/'state'), patch.dict(os.environ, env), patch.object(setup_window.subprocess, 'call', side_effect=start), patch.object(setup_window.Session, 'start', fake_start):
                self.assertEqual(setup_window.launch(), 0)
                self.assertEqual(operations, ['accounts'])
                self.assertEqual(apps.selection(), ['parsec', 'plex', 'slack', 'telegram', 'whatsapp', 'zed'])
                self.assertEqual(component_options.selection()['remote'], [])
                self.assertEqual(component_options.selection()['dev'], ['claude-code', 'docker'])
                self.assertEqual(component_options.selection()['ai-workspace'], ['model-7b'])
                self.assertEqual(gaming_options.selection(), ['heroic'])
                self.assertEqual(core._decky_selected_folders(), {"SDH-CssLoader"})
                self.assertEqual(css_stack.selection(), ["Round"])
                self.assertEqual(css_stack.palette_id(), 'ocean')
                self.assertEqual(component_options.selection()['terminal'], ['ghostty'])
                self.assertIn('dev', core.enabled_modules())
                self.assertFalse((base/'state').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
