#!/usr/bin/env python3
"""Optional actual Qt Quick + loopback smoke test; never provisions software."""
import os
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'lib'))
from deckctl import apps, core, setup_window, gaming_options, css_stack, component_options, appearance, preflight


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
    property bool capturing: false
    property bool retried: false
    property int experienceStage: 0
    function findObject(root, name) {
        if (root.objectName === name) return root
        var children=root.children || []
        for (var i=0;i<children.length;i++) { var found=findObject(children[i],name); if (found) return found }
        return null
    }
    Timer {
        running: app.loaded; interval: 100; repeat: true
        onTriggered: {
            if (app.capturing) return
            if (!app.attempted) {
                if (!app.deckInventory.items || !app.deckInventory.items["app:discord"]) return
                app.attempted = true
                if (app.dirty || app.selectionCount() !== 0) throw new Error("Fresh setup must start empty")
                app.choosePalette("ocean")
                app.setAppearance("css", true)
                if (!app.cssSelectionError()) throw new Error("Invalid enabled empty theming accepted")
                if (app.cssPalettePlanText().indexOf("no CSS components are selected") < 0) throw new Error("Palette with no targets looks applied")
                app.progress = {running:false,cssPalette:{installedComponents:["Chromahon (QAM)"]}}
                if (app.cssSelectionError() || app.cssPaletteTargets().length !== 1) throw new Error("Installed theme requires reselection")
                if (app.pageValues("css").length !== 0) throw new Error("Palette selected an installation")
                if (app.cssPalettePlanText().indexOf("included automatically") < 0) throw new Error("Automatic palette targets unexplained")
                app.progress = ({running:false})
                app.setAppearance("css", false)
                if (app.cssPalettePlanText().indexOf("recoloring is off") < 0) throw new Error("Disabled Game Mode appearance missing")
                app.setAppearance("css", true)
                app.dirty = false

                app.openGuide()
                app.guideStep = 3
                app.closeGuide()
                if (app.selectionCount() !== 0 || app.dirty) throw new Error("Walkthrough changed choices")
                app.progress = {running:false,modules:[{id:"test",status:"PENDING"}]}
                if (app.installRows().length) throw new Error("Ready-to-install screen shows waiting rows")
                app.restoreProgress({hasHistory:true,resumable:true,unfinished:2,lastRunAt:123,running:false,modules:[]})
                if (app.previousRunText().indexOf("2 items") < 0 || app.stage !== 0) throw new Error("Resume guidance missing or changed navigation")
                app.previousRun = ({})
                if (app.data.sudoReadiness.state !== "PASSWORD_MISSING") throw new Error("Fresh-install password guidance missing")
                if (app.inventoryFor({kind:"app",id:"discord"}).label !== "Update available") return
                app.selectUpdates()
                if (app.selectedApps.indexOf("discord") < 0 || app.inventoryDetails({kind:"app",id:"discord"}).indexOf("1 → 2") < 0) throw new Error("Update selection or versions missing")
                app.toggleItem({kind:"app",id:"discord"})
                app.dirty = false
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
                app.showPalettePreview = true
                choose("Round")
                if (app.pageValues("plugins").indexOf("SDH-CssLoader") < 0 || app.chosen.indexOf("decky") < 0) throw new Error("Theme missing required parents")
                app.back()
                if (app.detailPage !== "plugins" || app.stage !== 0) throw new Error("Theme back did not return to plugins")
                app.back()
                if (app.detailPage !== "" || app.stage !== 0) throw new Error("Plugins back did not return to Gaming")
                app.openAppearance()
                app.setAppearance("ghostty", false)
                app.closeAppearance()
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
                app.progress = {running:true, queueStatus:"AUTHENTICATING", operation:"install", modules:[]}
                if (app.installTitle() !== "Waiting for administrator permission") throw new Error("Password wait looks like a stuck install")
                app.progress.controls = {cancel:true}
                if (app.installTitle() !== "Cancelling installation") throw new Error("Cancellation hidden by password wait")
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
                if (app.experienceStage < 4 && (app.progress.operation !== "accounts" || app.progress.exitCode !== 0)) throw new Error("Retry switched to installing")
                if (app.experienceStage === 0) {
                    app.experienceStage = 1
                    app.navigate(4); app.invalidatePreview()
                    var reviewAction = app.findObject(app.contentItem,"primaryAction")
                    if (reviewAction.text !== "Review changes") throw new Error("Install confirmation bypasses review")
                    reviewAction.clicked()
                    if (!app.previewPending || app.busy) throw new Error("Review started installation")
                    return
                }
                if (app.experienceStage === 1) {
                    if (app.previewPending) return
                    if (!app.installPreview.items || app.installPreview.items[0].action !== "UPDATE") throw new Error("Preview did not render update evidence")
                    if (app.changeGroups()[0].title !== "Updates") throw new Error("Preview did not group changes")
                    app.installPreview = Object.assign({}, app.installPreview, {volumes:[{fits:false}]})
                    app.findObject(app.contentItem,"primaryAction").clicked()
                    if (app.problem.indexOf("Not enough space") < 0) throw new Error("Low-space plan not blocked")
                    app.navigate(5)
                    app.experienceStage = 2; app.checkFinish(); return
                }
                if (app.experienceStage === 2) {
                    if (app.finishItems[0].status !== "Needs sign-in") throw new Error("Installed app incorrectly shown as signed in")
                    app.experienceStage = 3; app.finishAction("app:slack", "confirm"); return
                }
                if (app.experienceStage < 4 && app.finishItems[0].status !== "Ready") throw new Error("Explicit confirmation did not update readiness")
                if (app.experienceStage === 3) {
                    app.experienceStage = 4
                    app.finishItems = []
                    app.progress = {running:true, operation:"install", modules:[{id:"terminal:ghostty",name:"Ghostty",status:"RUNNING",phase:"Downloading",message:"Fetching runtime",elapsedSeconds:65,startedAt:1,total:10000000,downloaded:5000000,hasLog:true}]}
                    app.showLog("terminal:ghostty")
                    app.refreshConsole()
                    return
                }
                if (!app.logView.text || app.logView.text.indexOf("Extracting") < 0) throw new Error("Log viewer did not load diagnostics")
                if (app.experienceStage === 4) {
                    app.experienceStage = 5; app.refreshLog(); return
                }
                if (app.logPending) return
                if (app.logView.text.indexOf("Latest output") < 0) throw new Error("Live details did not refresh")
                if (app.experienceStage === 5) {
                    app.progress = {running:false,operation:"install",exitCode:1,summary:{total:1,done:0,attention:1},modules:[{id:"terminal:ghostty",name:"Ghostty",status:"FAILED",message:"Verification needs attention. Review Details before retrying.",hasLog:true}]}
                    app.closeLog(); app.experienceStage = 6; return
                }
                if (app.consolePending) return
                if (app.consoleOutput.text.indexOf("Checking selected tools") < 0) throw new Error("Inline output did not load")
                var resultRow = app.findObject(app.contentItem,"installationResultRow")
                if (!resultRow) throw new Error("Compact result row missing")
                resultRow.clicked()
                if (app.expandedResult !== "terminal:ghostty") throw new Error("Row did not expand")
                resultRow.clicked()
                if (app.expandedResult !== "") throw new Error("Row did not collapse")
                if (!app.logCanRetry()) throw new Error("Failed item retry unavailable")
                app.closeLog()
                app.dirty = false
                app.progress = {running:true,operation:"install",controls:{available:true,pause:false,cancel:false},summary:{total:3,done:1,attention:0},activity:[{network:1048576,read:2097152,write:1048576},{network:2097152,read:3145728,write:2097152}],modules:[{id:"active",name:"Ghostty",status:"RUNNING",phase:"Updating",message:"Downloading update",elapsedSeconds:10},{id:"queued",name:"Slack",status:"PENDING"},{id:"done",name:"Discord",status:"DONE"}]}
                if (app.installRows().map(function(x) { return x.id }).join(",") !== "active,queued") throw new Error("Queue grouping is incorrect")
                app.showCompleted = true
                if (app.installRows()[2].queueHeading !== "COMPLETED · 1") throw new Error("Completed queue section missing")
                app.progress = Object.assign({},app.progress,{queueStatus:"PAUSED"})
                if (app.installTitle() !== "Queue paused") throw new Error("Pause state not reflected")
                app.progress = Object.assign({},app.progress,{queueStatus:"RUNNING"})
                app.clockSeconds = 1000
                app.progress = Object.assign({},app.progress,{githubLimit:{resetAt:1060}})
                if (app.githubLimitText().indexOf("1m 0s") < 0) throw new Error("GitHub reset countdown missing")
                app.clockSeconds = 1061
                if (app.githubLimitText().indexOf("has not been rechecked") < 0) throw new Error("Expired timer falsely claims API availability")

                // OPTIONAL_SCREENSHOT
                app.close()
                if (!app.visible || !app.closeRequested) throw new Error("Closing an active run did not offer cancellation")
                Qt.exit(app.allModules().indexOf("dev") >= 0 ? 0 : 3)
            }
        }
    }
    Timer { running: true; interval: 8000; onTriggered: { app.dirty=false; Qt.exit(4) } }
}
'''.replace('width: 1120; height: 720', f'width: {width}; height: {height}'))
            if os.environ.get('DECKCTL_UI_SCREENSHOTS'):
                images = Path(os.environ['DECKCTL_UI_SCREENSHOTS']); images.mkdir(parents=True,exist_ok=True)
                capture = 'app.capturing = true; app.paletteId = "bubblegum"; app.findObject(app.contentItem,"setupCanvas").grabToImage(function(image) { image.saveToFile('+json.dumps(str(images/f'install-{width}.png'))+'); app.navigate(1); Qt.callLater(function() { app.findObject(app.contentItem,"setupCanvas").grabToImage(function(choices) { choices.saveToFile('+json.dumps(str(images/f'choices-{width}.png'))+'); Qt.exit(0) }) }) }); return'
                harness.write_text(harness.read_text().replace('// OPTIONAL_SCREENSHOT',capture))
            run = subprocess.run
            def start(args, **kwargs):
                args[1] = str(harness)
                return run(args, timeout=12, **kwargs).returncode
            operations=[]
            def fake_start(session, operation, item=None):
                operations.append(operation)
                self.assertEqual(operation, 'accounts', 'Retry must not install software')
                return dict(running=False, operation=operation, exitCode=0, modules=[])
            confirmed = []
            log_reads = []
            def fake_log(session, item):
                log_reads.append(item)
                return {'item':item,'text':'Extracting runtime: diagnostic test' + (' Latest output' if len(log_reads)>1 else '')}
            def fake_preview(session, payload):
                session.preview_result = {'running': False, 'items': [{'visible': True, 'name': 'Slack', 'action': 'UPDATE', 'updateCheck': 'Checked', 'downloadBytes': 1000000}], 'volumes': [], 'sizeNote': 'Test provider estimate'}
                return session.preview_result
            def fake_finish():
                return [dict(key='app:slack', name='Slack', status='Ready' if confirmed else 'Needs sign-in', note='Test account readiness', canLaunch=True, canConfirm=True, followup='signin')]
            def fake_action(key, operation):
                self.assertEqual((key, operation), ('app:slack', 'confirm'))
                confirmed.append(key)
                return {'confirmed': True}
            env = dict(os.environ, QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software', QT_FORCE_STDERR_LOGGING='1')
            password_check = patch.object(preflight,'sudo_readiness',return_value={'status':'WARN','state':'PASSWORD_MISSING','message':'No account password is set. In Desktop Mode, open Konsole and run passwd to set one before using installers that require sudo. Password entry stays in Konsole; typed characters are not displayed. Then recheck here. User-space installs can continue.'})
            password_check.start()
            self.addCleanup(password_check.stop)
            console_check = patch.object(setup_window.Session,'console',return_value={'text':'Checking selected tools…\nGhostty: verification needs attention.\nInstallation pass complete. Review the results below.'})
            console_check.start()
            self.addCleanup(console_check.stop)
            with patch.object(css_stack, 'THEMES_DIR', base/'themes'), patch.object(core, 'CONFIG_HOME', base/'config'), patch.object(core, 'STATE', base/'state'), patch.dict(os.environ, env), patch.object(setup_window.subprocess, 'call', side_effect=start), patch.object(setup_window.Session, 'inventory', return_value={'items':{'app:discord':{'label':'Update available','status':'UPDATE','installedVersion':'1','availableVersion':'2','checkedAt':1}},'running':False,'completed':1,'total':1}), patch.object(setup_window.Session, 'start', fake_start), patch.object(setup_window.Session, 'preview', fake_preview), patch.object(setup_window.Session, 'log', fake_log), patch.object(setup_window.setup_finish, 'rows', fake_finish), patch.object(setup_window.setup_finish, 'action', fake_action):
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
                self.assertFalse(appearance.selection()['ghostty'])
                self.assertEqual(component_options.selection()['terminal'], ['ghostty'])
                self.assertIn('dev', core.enabled_modules())
                self.assertFalse((base/'state').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
