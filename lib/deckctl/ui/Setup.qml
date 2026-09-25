import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

ApplicationWindow {
    id: window
    width: Math.min(1120, Screen.width)
    height: Math.min(720, Screen.height)
    minimumWidth: 760
    minimumHeight: 540
    visible: true
    title: "Steam Deck Workstation"
    color: window.tone("#090612")
    palette.window: window.tone("#1a1128")
    palette.windowText: ink
    palette.text: ink
    palette.button: window.tone("#31213f")
    palette.buttonText: ink
    palette.base: window.tone("#150d21")
    palette.highlight: accent
    font.family: "Noto Sans"
    font.pixelSize: 15

    readonly property color ink: window.tone("#f8e7ff")
    readonly property color muted: window.tone("#bda8ca")
    readonly property color accent: window.tone("#ff4fd8")
    readonly property color cyan: window.tone("#42f5ff")
    readonly property color violet: window.tone("#a970ff")
    property string paletteId: "bubblegum"
    property var appearanceChoices: ({})
    property var logView: ({item: "", text: ""})
    property var previousRun: ({})
    property bool previousRunDismissed: false
    property int guideStep: 0
    readonly property var guidePages: [
        {title:"Start in Desktop Mode", text:"From Steam’s Power menu, switch to Desktop Mode. Keep your Deck connected to power and the internet for downloads. This guide is optional and does not change your choices."},
        {title:"Check your password", text:"Some vendor installers need administrator access. If setup says your password is missing or locked, open Konsole and run passwd. Typed characters stay invisible. Return here and use Recheck password. Never paste passwords into logs or this UI."},
        {title:"Choose storage deliberately", text:"Internal storage holds tools and settings. Optional DECK-GAMES and DECK-EMU cards are for the configured game and emulation paths. Insert the intended card before installing components that use it. Check changes & space on the review page shows known allowances; unknown vendor sizes need extra room."},
        {title:"Make it your setup", text:"Choose individual apps and tools; required dependencies are included automatically. Review new installs, updates and configuration changes, then confirm. Afterward, check results and complete any sign-in or pairing. You can save choices for later and resume unfinished installation work."}
    ]
    function openGuide() { guideStep = 0; guideDialog.open() }
    function closeGuide() { guideDialog.close() }
    function restoreProgress(result) { previousRun = result; progress = result; if (result.running) stage = 5 }
    function previousRunText() {
        if (previousRun.historyPlanChanged) return "Your saved choices or installer version differ from the last run. Review this plan; previous results will not be reused as proof."
        var stamp = previousRun.lastRunAt ? " · " + new Date(previousRun.lastRunAt * 1000).toLocaleString() : ""
        return (previousRun.unfinished ? "Unfinished installation: " + previousRun.unfinished + " items remaining" : "Your last installation results are available") + stamp + ". Resume rechecks completed items before skipping them."
    }
    function changeGroups() {
        var categories = [{title:"New installations",actions:["NEW"]},{title:"Updates",actions:["UPDATE"]},{title:"Configuration changes",actions:["CONFIGURE"]},{title:"Existing installations / checks",actions:["INSTALLED","UP_TO_DATE","PRESERVE_SYSTEM"]},{title:"Included support",actions:["SUPPORT"]}]
        return categories.map(function(group) { return {title:group.title,items:(installPreview.items || []).filter(function(item) { return group.actions.indexOf(item.action) >= 0 })} }).filter(function(group) { return group.items.length })
    }
    property bool followLog: true
    property bool logPending: false
    function openAppearance() { appearanceDialog.open() }
    function closeAppearance() { appearanceDialog.close() }
    function closeLog() { logDialog.close() }
    function appearanceTargetSelected(key) {
        return key === "css" ? pageValues("css").length > 0 : pageValues("terminal").indexOf(key) >= 0
    }
    function appearanceSummary() {
        var names = (data.appearanceTargets || []).filter(function(target) {
            return appearanceChoices[target.id] !== false && appearanceTargetSelected(target.id)
        }).map(function(target) { return target.name })
        return names.length ? activePalette.name + " → " + names.join(", ") : "Keep current appearance"
    }
    function setAppearance(key, value) {
        var next = Object.assign({}, appearanceChoices); next[key] = value
        appearanceChoices = next; markChanged()
    }
    function showLog(key) {
        request("log", {item: key}, function(result) { logView = result; logDialog.open() })
    }
    function refreshLog() {
        if (logPending || !logView.item) return
        logPending = true
        request("log", {item: logView.item}, function(result) { logPending = false; if (logDialog.visible) logView = result })
    }
    function logCanRetry() {
        return !progress.running && !busy && (progress.items || progress.modules || []).some(function(item) {
            return item.id === logView.item && ["FAILED", "INTERRUPTED", "NEEDS_SETUP", "BLOCKED"].indexOf(item.status) >= 0
        })
    }
    function elapsedLabel(seconds) {
        var mins = Math.floor((seconds || 0) / 60)
        return mins ? mins + "m " + (seconds % 60) + "s" : (seconds || 0) + "s"
    }
    readonly property var paletteOptions: data.palettes || []
    readonly property var activePalette: paletteOptions.find(function(p) { return p.id === paletteId }) || ({name: "Bubble Gum Rave", colors: {}})
    function tone(original) { return activePalette.colors[original] || original }
    function choosePalette(key) {
        if (paletteId === key) return
        paletteId = key
        markChanged()
    }
    property var data: ({groups: [], apps: [], modules: [], selectedApps: [], dependencies: {}, defaults: []})
    property string detailPage: ""
    property string searchText: ""
    property bool selectedOnly: false
    property var navigationStack: []
    property var selectedLaunchers: []
    property var selectedPlugins: []
    property var selectedCss: []
    property var selectedComponents: ({})
    readonly property bool componentDetail: !!(data.components && data.components[detailPage])
    property var chosen: []
    property var selectedApps: []
    property int planRevision: 0
    property int previewRevision: -1
    function invalidatePreview() { planRevision++; installPreview = ({}); finishItems = [] }
    onChosenChanged: invalidatePreview()
    onSelectedAppsChanged: invalidatePreview()
    onSelectedComponentsChanged: invalidatePreview()
    onSelectedLaunchersChanged: invalidatePreview()
    onSelectedPluginsChanged: invalidatePreview()
    onSelectedCssChanged: invalidatePreview()
    onPaletteIdChanged: invalidatePreview()
    onAppearanceChoicesChanged: invalidatePreview()
    property bool showPalettePreview: false
    property var finishItems: []
    property var importPreview: ({})
    property var deckInventory: ({items: {}, running: false})
    property bool inventoryPending: false
    function refreshInventory() {
        inventoryPending = true
        request("inventory", {}, function(result) { deckInventory = result; inventoryPending = !!result.running })
    }
    function inventoryFor(item) {
        var prefix = item.kind === "component" ? item.group : item.kind
        var key = prefix + ":" + item.id
        return (deckInventory.items || {})[key] || ({label: inventoryPending ? "Checking this Deck…" : "Not checked", status: "UNKNOWN"})
    }
    function inventoryDetails(item) {
        var result = inventoryFor(item), parts = []
        function version(value) { return /^[a-f0-9]{64}$/.test(value) ? value.slice(0, 12) + " (commit)" : value }
        if (result.installedVersion && result.availableVersion) parts.push(version(result.installedVersion) + " → " + version(result.availableVersion))
        if (result.note && result.note !== "Checked") parts.push(result.note)
        if (result.checkedAt) parts.push("Checked " + new Date(result.checkedAt * 1000).toLocaleTimeString())
        return parts.join(" · ")
    }
    function selectUpdates() {
        var items = data.layout.reduce(function(all, section) { return all.concat(section.items) }, [])
        items = items.concat(detailItems("plugins"), detailItems("css"))
        var count = 0
        items.forEach(function(item) {
            if (inventoryFor(item).status === "UPDATE" && !itemSelected(item)) { toggleItem(item); count++ }
        })
        notice = count ? count + " updates added to your choices. Review before installing; existing choices are kept." : "No additional updates to select."
    }
    property var installPreview: ({})
    property bool previewPending: false
    property var progress: ({running: false, modules: [], operation: null})
    property int stage: 0
    property bool loaded: false
    property bool busy: false
    property bool saved: false
    property bool dirty: false
    property bool pendingPreset: false
    property string notice: ""
    property string problem: ""
    property string endpoint: ""
    readonly property var stageNames: ["Gaming", "Apps & media", "Coding & work", "Remote & storage", "Review", "Install & finish"]
    readonly property var stageHints: ["Launchers & appearance", "Chat, browser & video", "Editors & AI tools", "Devices, drives & saves", "Check your selections", "Setup & sign-in"]
    readonly property var stageDescriptions: [
        "Choose game launchers, controller tools and Game Mode appearance.",
        "Choose everyday apps, media players and Game Mode streaming shortcuts.",
        "Build a workspace around the tools you actually use. Each tool is optional.",
        "Choose remote connections, storage tools and backup. Each choice stays on this page.",
        "Check each selected item and its requirements before installing.",
        "Install your choices, then finish setup, account sign-in and pairing."]

    function request(route, payload, callback) {
        var xhr = new XMLHttpRequest()
        xhr.open(payload === null ? "GET" : "POST", endpoint + route)
        xhr.timeout = route === "share" ? 0 : route === "finish" ? 120000 : 10000
        if (payload !== null) xhr.setRequestHeader("Content-Type", "application/json")
        xhr.onreadystatechange = function() {
            if (xhr.readyState !== XMLHttpRequest.DONE) return
            try {
                var result = JSON.parse(xhr.responseText)
                if (xhr.status !== 200) throw new Error(result.error || "Setup could not complete this action.")
                callback(result)
            } catch (e) { busy = false; if (route === "log") logPending = false; problem = e.message || "Setup connection lost. Close and reopen this window." }
        }
        xhr.send(payload === null ? null : JSON.stringify(payload))
    }
    function owner(page) {
        if (page === "launchers") return "gaming"
        if (page === "plugins" || page === "css") return "decky"
        return page
    }
    function pageItems(page) {
        if (page === "desktop-apps") return data.apps || []
        if (page === "launchers") return data.launchers || []
        if (page === "plugins") return data.plugins || []
        if (page === "css") return data.css || []
        return (data.components || {})[page] || []
    }
    function pageValues(page) {
        if (page === "desktop-apps") return selectedApps
        if (chosen.indexOf(owner(page)) < 0) return []
        if (page === "css" && selectedPlugins.indexOf("SDH-CssLoader") < 0) return []
        if (page === "launchers") return selectedLaunchers
        if (page === "plugins") return selectedPlugins
        if (page === "css") return selectedCss
        return selectedComponents[page] || []
    }
    function markChanged() { saved = false; dirty = true; notice = ""; problem = ""; previousRunDismissed = true }
    function setPageValues(page, values) {
        var roots = chosen.slice(), module = owner(page)
        if (values.length && roots.indexOf(module) < 0) roots.push(module)
        if (!values.length && module !== "decky" && module !== "ai-workspace") roots = roots.filter(function(x) { return x !== module })
        chosen = roots
        if (page === "css" && values.length && selectedPlugins.indexOf("SDH-CssLoader") < 0) selectedPlugins = selectedPlugins.concat(["SDH-CssLoader"])
        if (page === "plugins" && values.indexOf("SDH-CssLoader") < 0) selectedCss = []
        if (page === "launchers") selectedLaunchers = values
        else if (page === "plugins") selectedPlugins = values
        else if (page === "css") selectedCss = values
        else { var updated = Object.assign({}, selectedComponents); updated[page] = values; selectedComponents = updated }
        markChanged()
    }
    function toggle(key, isApp) {
        if (detailPage) {
            var values = pageValues(detailPage).slice(), index = values.indexOf(key)
            if (index < 0) values.push(key); else values.splice(index, 1)
            setPageValues(detailPage, values)
            return
        }
        var values = (isApp ? selectedApps : chosen).slice(), index = values.indexOf(key)
        if (index < 0) values.push(key); else values.splice(index, 1)
        if (isApp) selectedApps = values; else chosen = values
        markChanged()
    }
    function detailPreset(defaults) {
        var values = []
        if (defaults) values = detailPage === "plugins" ? data.defaultPlugins.slice() : detailPage === "css" ? data.defaultCss.slice() : pageItems(detailPage).map(function(x) { return x.id })
        setPageValues(detailPage, values)
    }
    function navigate(stageIndex) {
        navigationStack = []
        stage = stageIndex; detailPage = ""; searchText = ""; selectedOnly = false
        notice = ""; problem = ""
    }
    function location() {
        return {stage:stage, page:detailPage, query:searchText, selected:selectedOnly,
                scroll:scroll.contentItem ? scroll.contentItem.contentY : 0}
    }
    function browse(page) {
        if (page === detailPage) return
        navigationStack = navigationStack.concat([location()])
        detailPage = page; selectedOnly = false; notice = ""; problem = ""
    }
    function back() {
        if (navigationStack.length) {
            var trail = navigationStack.slice(), previous = trail.pop()
            navigationStack = trail
            stage = previous.stage; detailPage = previous.page; searchText = previous.query; selectedOnly = previous.selected
            Qt.callLater(function() { if (scroll.contentItem) scroll.contentItem.contentY = previous.scroll })
        } else if (detailPage) {
            detailPage = ""
        } else if (stage > 0) {
            navigate(stage - 1)
        }
    }
    function pageTitle(page) {
        if (page === "plugins") return "Decky plugins"
        if (page === "css") return "CSS Loader themes"
        if (page === "desktop-apps") return "Desktop apps"
        if (page === "launchers") return "Game launchers"
        return featureNames()[page] || page
    }
    function requiredBy(item) {
        if (item.kind === "component" && item.group === "terminal" && item.id === "opencode" && chosen.indexOf("ai-workspace") >= 0) return "AI workspace"
        if (item.kind === "component" && item.group === "ai-workspace" && item.id === "ollama" &&
            pageValues("ai-workspace").some(function(x) { return x === "model" || x === "model-7b" })) return "your selected Qwen model"
        if (item.kind === "module" && item.id === "ai-workspace" && pageValues("ai-workspace").length) return "your local AI choices"
        if (item.kind === "module" && item.id === "decky" && pageValues("plugins").length) return "your selected plugins"
        if (item.kind === "plugin" && item.id === "SDH-CssLoader" && pageValues("css").length) return "your selected themes"
        return ""
    }
    function itemSelected(item) {
        if (requiredBy(item)) return true
        if (item.kind === "app") return selectedApps.indexOf(item.id) >= 0
        if (item.kind === "module") return chosen.indexOf(item.id) >= 0
        var page = item.kind === "launcher" ? "launchers" : item.kind === "plugin" ? "plugins" : item.kind === "css" ? "css" : item.group
        return pageValues(page).indexOf(item.id) >= 0
    }
    function toggleItem(item) {
        var requirement = requiredBy(item)
        if (requirement) { notice = item.name + " is required by " + requirement + ". Remove those choices first."; return }
        if (item.kind === "app" || item.kind === "module") {
            var values = (item.kind === "app" ? selectedApps : chosen).slice(), index = values.indexOf(item.id)
            if (index < 0) values.push(item.id); else values.splice(index, 1)
            if (item.kind === "app") selectedApps = values; else chosen = values
            markChanged(); return
        }
        var page = item.kind === "launcher" ? "launchers" : item.kind === "plugin" ? "plugins" : item.kind === "css" ? "css" : item.group
        var ids = pageValues(page).slice(), at = ids.indexOf(item.id)
        if (at < 0) ids.push(item.id); else ids.splice(at, 1)
        setPageValues(page, ids)
    }
    function detailItems(page) {
        return pageItems(page).map(function(item) {
            return Object.assign({}, item, {kind: page === "plugins" ? "plugin" : page === "css" ? "css" : page === "launchers" ? "launcher" : page === "desktop-apps" ? "app" : "component", group:page})
        })
    }
    function currentSections() {
        if (!loaded || stage >= 4) return []
        var sections = detailPage ? [{title:pageTitle(detailPage), description:"", items:detailItems(detailPage)}] :
                       data.layout.filter(function(section) { return section.stage === stage })
        var query = searchText.trim().toLowerCase()
        return sections.map(function(section) {
            return {title:section.title, description:section.description, items:section.items.filter(function(item) {
                return (!selectedOnly || itemSelected(item)) && (!query || (item.name + " " + item.summary + " " + section.title).toLowerCase().indexOf(query) >= 0)
            })}
        }).filter(function(section) { return section.items.length > 0 })
    }
    function currentItems() {
        return currentSections().reduce(function(items, section) { return items.concat(section.items) }, [])
    }
    function dependencyNotes() {
        var notes = []
        if (chosen.indexOf("ai-workspace") >= 0) {
            if (pageValues("terminal").indexOf("opencode") < 0) notes.push("OpenCode — included for AI workspace")
            if (pageValues("ai-workspace").some(function(x) { return x === "model" || x === "model-7b" }) &&
                pageValues("ai-workspace").indexOf("ollama") < 0) notes.push("Ollama — included for your Qwen model")
        }
        if (pageValues("workspace").length || pageValues("media").length) notes.push("Google Chrome — one shared download for your selected web apps and extensions")
        if (pageValues("plugins").length) notes.push("Decky Loader — included for your selected plugins")
        if (pageValues("css").length) notes.push("CSS Loader — included for your selected themes")
        return notes
    }
    function reviewSections() {
        if (!loaded) return []
        var sections = []
        data.layout.forEach(function(section) {
            var items = section.items.filter(function(item) { return itemSelected(item) })
            if (items.length) sections.push({title:section.title, page:"", items:items, targetStage:section.stage})
        })
        ;[["plugins","Decky plugins"],["css","CSS Loader themes"]].forEach(function(entry) {
            var items = detailItems(entry[0]).filter(function(item) { return itemSelected(item) })
            if (items.length) sections.push({title:entry[1], page:entry[0], items:items, targetStage:0})
        })
        sections.sort(function(a,b) { return a.targetStage - b.targetStage })
        return sections
    }
    function selectionCount() { return reviewSections().reduce(function(total, section) { return total + section.items.length }, 0) }
    function editSection(section) {
        navigationStack = [location()]
        stage = section.targetStage; detailPage = section.page; searchText = ""; selectedOnly = false
        if (!detailPage) searchText = section.title
    }
    function installTitle() {
        if (progress.running) return progress.operation === "accounts" ? "Finish setup in Konsole" : "Installing your selections"
        if (!progress.operation) return "Ready to install"
        if (progress.exitCode !== 0) return "Setup needs attention"
        return progress.operation === "accounts" ? "Guided setup finished" : "Installation pass finished"
    }
    function statusLabel(value) {
        return ({PENDING:"Waiting",RUNNING:"Installing",DONE:"Installed",BLOCKED:"Waiting on dependency",INTERRUPTED:"Interrupted",NEEDS_SETUP:"Needs setup",READY:"Ready",OPTIONAL:"Ready",CONFIG_REQUIRED:"Needs setup",NOT_INSTALLED:"Not installed",DEGRADED:"Needs attention",FAILED:"Failed"})[value] || value
    }
    function selectedNames(items, values) {
        return (items || []).filter(function(x) { return values.indexOf(x.id) >= 0 }).map(function(x) { return x.name }).join(" · ") || "None selected"
    }
    function featureNames() {
        var names = {}
        data.groups.forEach(function(group) { group.modules.forEach(function(m) { names[m.id] = m.name }) })
        names.base = "Base support"
        return names
    }
    function allModules() {
        var result = ["base"]
        function include(key) {
            if (result.indexOf(key) >= 0) return
            result.push(key)
            ;(data.dependencies[key] || []).forEach(include)
        }
        chosen.forEach(include)
        data.apps.forEach(function(app) { if (selectedApps.indexOf(app.id) >= 0) include(app.module) })
        return result
    }
    function preset(full) {
        chosen = full ? data.defaults.slice() : ["base"]
        selectedApps = full ? data.apps.map(function(app) { return app.id }) : []
        selectedLaunchers = full ? data.launchers.map(function(x) { return x.id }) : []
        selectedPlugins = full ? data.defaultPlugins.slice() : []
        selectedCss = full ? data.defaultCss.slice() : []
        var components = {}
        Object.keys(data.defaultComponents).forEach(function(key) { components[key] = full ? data.defaultComponents[key].slice() : [] })
        selectedComponents = components
        selectedOnly = false; searchText = ""; saved = false; dirty = true; notice = full ? "Full workstation selected. Make it your own below." : "Starting small. Add only what you need."
    }
    function savePlan(install) {
        busy = true; problem = ""; notice = ""
        var components = {}
        Object.keys(selectedComponents).forEach(function(key) { components[key] = pageValues(key).slice() })
        request("save", {modules: chosen, apps: selectedApps, launchers: pageValues("launchers"), plugins: pageValues("plugins"), css: pageValues("css"), components: components, palette: paletteId, appearance: appearanceChoices}, function(result) {
            saved = true; dirty = false; busy = false; notice = "Plan saved. You can close this window or install when ready."
            if (install) startOperation("install")
            else if (data.planOnly) window.close()
        })
    }
    function sharePlan(operation) {
        busy = true; problem = ""; notice = ""
        request("share", {operation: operation}, function(result) {
            busy = false
            if (result.exported) notice = "Setup saved to " + result.exported
            if (result.files) { importPreview = result; importDialog.open() }
            if (result.imported) request("catalog", null, function(catalog) {
                data = catalog; paletteId = catalog.palette; appearanceChoices = catalog.appearance; selectedComponents = catalog.selectedComponents
                selectedCss = catalog.selectedCss; selectedLaunchers = catalog.selectedLaunchers
                selectedPlugins = catalog.selectedPlugins; chosen = catalog.modules; selectedApps = catalog.selectedApps
                saved = true; dirty = false; installPreview = ({}); stage = 4
                notice = "Setup imported. Review or remove any choices before installing."
            })
        })
    }
    function checkFinish() {
        busy = true; problem = ""; notice = ""
        request("finish", null, function(result) { finishItems = result.items; busy = false })
    }
    function finishAction(key, operation) {
        busy = true; problem = ""; notice = ""
        request("finish", {item: key, operation: operation}, function(result) {
            busy = false; notice = result.confirmed ? "Marked complete by you." : "Opened. Complete setup, then use Recheck readiness."
            if (result.confirmed) checkFinish()
        })
    }
    function previewPlan() {
        var components = {}
        Object.keys(selectedComponents).forEach(function(key) { components[key] = pageValues(key).slice() })
        problem = ""; previewPending = true; previewRevision = planRevision
        request("preview", {modules: chosen, apps: selectedApps, launchers: pageValues("launchers"), plugins: pageValues("plugins"), css: pageValues("css"), components: components, palette: paletteId, appearance: appearanceChoices}, function(result) { if (previewRevision === planRevision) installPreview = result })
    }
    function bytesLabel(value) {
        if (value === null || value === undefined) return "Provider checks size"
        if (value < 1024 * 1024 * 1024) return (value / (1024 * 1024)).toFixed(1) + " MiB"
        return (value / (1024 * 1024 * 1024)).toFixed(1) + " GiB"
    }
    function startOperation(name, item) {
        busy = true; problem = ""; notice = ""
        request("start", {operation: name, item: item || null}, function(result) {
            finishItems = []; progress = result; stage = 5; busy = false
        })
    }
    function stateColor(status) {
        if (status === "DONE" || status === "READY" || status === "OPTIONAL") return accent
        if (status === "FAILED" || status === "NOT_INSTALLED") return window.tone("#ff91ba")
        if (status === "RUNNING") return window.tone("#42f5ff")
        return muted
    }
    onClosing: function(event) {
        if (progress.running || busy) {
            event.accepted = false
            notice = "Finish or close the installer terminal before closing setup."
        } else if (dirty && loaded && !leaveDialog.visible) {
            event.accepted = false
            leaveDialog.open()
        }
    }
    onDetailPageChanged: { searchText = ""; if (scroll.contentItem) scroll.contentItem.contentY = 0 }
    onStageChanged: { searchText = ""; detailPage = ""; if (scroll.contentItem) scroll.contentItem.contentY = 0 }
    Component.onCompleted: {
        var args = Qt.application.arguments
        for (var i=0; i<args.length; i++) if (args[i].indexOf("http://127.0.0.1:") === 0) endpoint = args[i]
        if (!endpoint) { problem = "Open this app with deckctl setup customize."; return }
        request("catalog", null, function(result) {
            saved = result.hasSavedPlan; data = result; paletteId = result.palette; appearanceChoices = result.appearance; selectedComponents = result.selectedComponents; selectedCss = result.selectedCss.slice(); selectedLaunchers = result.selectedLaunchers.slice(); selectedPlugins = result.selectedPlugins.slice(); chosen = result.modules.slice(); selectedApps = result.selectedApps.slice(); loaded = true
            if (!result.hasSavedPlan) { preset(false); dirty = false; notice = "Start with only what you need. Nothing installs until you review and confirm." }
            if (result.hasSavedPlan) request("progress", null, function(state) { restoreProgress(state) })
            else openGuide()
            refreshInventory()
        })
    }
    Timer {
        interval: 1000; running: window.inventoryPending; repeat: true
        onTriggered: window.request("inventory", null, function(result) { window.deckInventory = result; window.inventoryPending = !!result.running })
    }
    Timer {
        interval: 1000; running: window.previewPending; repeat: true
        onTriggered: window.request("preview", null, function(result) {
            if (window.previewRevision === window.planRevision) window.installPreview = result
            if (!result.running) { window.previewPending = false; if (result.error) window.problem = result.error }
        })
    }
    Timer {
        interval: 1500; running: window.loaded && window.stage === 5; repeat: true
        onTriggered: window.request("progress", null, function(result) { var wasRunning = window.progress.running; window.progress = result; if (wasRunning && !result.running) window.refreshInventory() })
    }

    component TextLabel: Label {
        color: window.ink
        wrapMode: Text.WordWrap
    }
    component Action: Button {
        id: action
        property bool primary: false
        implicitHeight: 48
        implicitWidth: Math.max(110, label.implicitWidth + 34)
        hoverEnabled: true
        contentItem: Text {
            id: label
            text: action.text; color: action.primary ? window.tone("#20091e") : window.ink
            font.pixelSize: 14; font.weight: Font.DemiBold
            horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
            opacity: action.enabled ? 1 : 0.45
        }
        background: Rectangle {
            radius: 10
            color: action.primary ? (action.down ? window.tone("#df30b6") : window.accent) : (action.hovered ? window.tone("#352046") : window.tone("#261735"))
            border.width: action.activeFocus ? 2 : 1
            border.color: action.activeFocus ? window.cyan : (action.primary ? window.accent : window.tone("#533960"))
            opacity: action.enabled ? 1 : 0.5
        }
    }
    component ChoiceCard: AbstractButton {
        id: card
        property string heading
        property string detail
        property string optionsPage: ""
        property bool navigation: false
        property string requirement: ""
        property string inventoryLabel: ""
        property string inventoryStatus: ""
        property string inventoryDetail: ""
        property int selectedCount: 0
        property bool selected: false
        implicitHeight: Math.max(104, card.contentItem.implicitHeight + 32) + (optionsPage ? 54 : 0)
        hoverEnabled: true
        bottomPadding: optionsPage ? 54 : 0
        background: Rectangle {
            radius: 13
            color: !card.navigation && card.selected ? window.tone("#35182f") : (card.hovered ? window.tone("#2b1c3a") : window.tone("#1a1128"))
            border.width: card.activeFocus ? 2 : 1
            border.color: card.activeFocus ? window.cyan : (!card.navigation && card.selected ? window.tone("#c745a7") : window.tone("#493055"))
        }
        contentItem: RowLayout {
            spacing: 14
            Rectangle {
                visible: !card.navigation
                Layout.leftMargin: 18; Layout.preferredWidth: 24; Layout.preferredHeight: 24; radius: 7
                color: card.selected ? window.accent : window.tone("#100a1b")
                border.color: card.selected ? window.accent : window.tone("#9c7aae")
                Text { anchors.centerIn: parent; text: card.selected ? "✓" : ""; color: window.tone("#20091e"); font.bold: true; font.pixelSize: 17 }
            }
            ColumnLayout {
                Layout.leftMargin: card.navigation ? 18 : 0
                Layout.fillWidth: true; Layout.rightMargin: 16; spacing: 6
                TextLabel { text: card.heading; font.pixelSize: 15; font.weight: Font.DemiBold; Layout.fillWidth: true }
                TextLabel { text: card.detail; color: !card.navigation && card.selected ? window.tone("#e2c5e6") : window.muted; font.pixelSize: 13; Layout.fillWidth: true }
                TextLabel { visible: !!card.inventoryLabel; text: card.inventoryLabel; color: card.inventoryStatus === "UPDATE" ? window.accent : window.cyan; font.pixelSize: 12; Layout.fillWidth: true }
                TextLabel { visible: !!card.inventoryDetail; text: card.inventoryDetail; color: window.muted; font.pixelSize: 11; Layout.fillWidth: true }
                TextLabel { visible: !!card.requirement; text: "Included · required by " + card.requirement; color: window.cyan; font.pixelSize: 12; Layout.fillWidth: true }
                TextLabel { visible: card.navigation; text: card.selectedCount ? card.selectedCount + " selected · Browse" : "Browse individual options"; color: window.accent; font.pixelSize: 12 }
            }
            TextLabel { visible: card.navigation; text: "›"; color: window.muted; font.pixelSize: 26; Layout.rightMargin: 18 }
        }
        Action {
            visible: !!card.optionsPage
            anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.margins: 10
            text: card.optionsPage === "plugins" ? "Choose plugins ›" : "Choose themes ›"
            onClicked: window.browse(card.optionsPage)
        }
        Accessible.name: heading + ". " + detail + (requirement ? ". Included for " + requirement : selected ? ". Selected" : ". Not selected")
        Accessible.role: navigation ? Accessible.Button : Accessible.CheckBox
        Accessible.checkable: !navigation
        Accessible.checked: !navigation && selected
    }

    Rectangle {
        objectName: "setupCanvas"
        enabled: !window.busy
        anchors.fill: parent
        color: window.color
    RowLayout {
        anchors.fill: parent; spacing: 0
        Rectangle {
            Layout.preferredWidth: window.width < 950 ? 210 : 246
            Layout.fillHeight: true; color: window.tone("#120b1d")
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 22; spacing: 8
                Rectangle {
                    visible: window.height >= 600; Layout.topMargin: window.height < 620 ? 0 : 10; width: 42; height: 42; radius: 12; color: window.accent
                    Text { anchors.centerIn: parent; text: "W"; color: window.tone("#20091e"); font.pixelSize: 24; font.bold: true }
                }
                TextLabel { text: "DECK\nWORKSTATION"; font.pixelSize: 17; font.weight: Font.Bold; lineHeight: 1.18; Layout.topMargin: 10 }
                TextLabel { visible: window.height >= 600; text: "Choose your tools"; color: window.muted; font.pixelSize: 13; Layout.bottomMargin: window.height < 620 ? 4 : 16 }
                Repeater {
                    model: window.stageNames
                    delegate: AbstractButton {
                        id: nav
                        required property string modelData
                        required property int index
                        Layout.fillWidth: true; implicitHeight: window.height < 620 ? 48 : 58
                        enabled: window.loaded && !window.busy && !window.progress.running && (index !== 5 || window.saved)
                        onClicked: window.navigate(index)
                        background: Rectangle { radius: 10; color: window.stage === nav.index ? window.tone("#35203f") : "transparent"; border.color: nav.activeFocus ? window.accent : "transparent" }
                        contentItem: RowLayout {
                            spacing: 12
                            Text { Layout.leftMargin: 12; text: String(nav.index+1).padStart(2,"0"); color: window.stage === nav.index ? window.cyan : window.tone("#ac87be"); font.pixelSize: 13 }
                            ColumnLayout {
                                Layout.fillWidth: true; spacing: 4
                                TextLabel { text: nav.modelData; font.pixelSize: 13; font.weight: Font.DemiBold; color: window.stage === nav.index ? window.ink : window.muted; Layout.fillWidth: true }
                                TextLabel { text: window.stageHints[nav.index]; font.pixelSize: 10; color: window.muted; Layout.fillWidth: true; elide: Text.ElideRight; wrapMode: Text.NoWrap }
                            }
                        }
                    }
                }
                Item { Layout.fillHeight: true }
                Action {
                    id: paletteButton
                    Layout.fillWidth: true
                    text: "Theme & appearance"
                    enabled: window.loaded && !window.busy && !window.progress.running
                    Accessible.name: "Theme and appearance: " + window.activePalette.name
                    onClicked: appearanceDialog.open()
                }
                Rectangle { visible: window.height >= 780; Layout.fillWidth: true; height: 1; color: window.tone("#402c4e") }
                TextLabel { visible: window.height >= 780; text: "BUILT FOR YOUR DECK"; font.pixelSize: 10; font.letterSpacing: 1.2; color: window.tone("#bda8ca"); Layout.topMargin: 14 }
                TextLabel { visible: window.height >= 780; text: "Setup runs only while open.\nYour choices stay yours."; color: window.muted; font.pixelSize: 12; Layout.topMargin: 4 }
            }
        }
        ColumnLayout {
            Layout.fillWidth: true; Layout.fillHeight: true
            Layout.margins: window.width < 950 ? 22 : 34; spacing: 15
            RowLayout {
                Layout.fillWidth: true
                TextLabel { text: window.stage < 4 ? "BUILD YOUR SETUP" : "YOUR WORKSTATION"; font.pixelSize: 11; font.letterSpacing: 1.8; color: window.accent }
                Item { Layout.fillWidth: true }
                TextLabel { text: window.selectionCount() + " in your plan"; color: window.muted; font.pixelSize: 12 }
            }
            TextLabel { text: window.detailPage ? window.pageTitle(window.detailPage) : window.stageNames[window.stage]; font.pixelSize: window.width < 950 ? 27 : 32; font.weight: Font.Bold; Layout.fillWidth: true }
            TextLabel { text: window.detailPage === "css" ? "Decky › CSS Loader. Choose the components you want to manage." : window.detailPage === "plugins" ? "Add-ons for Decky Loader. CSS Loader has its own component choices." : window.detailPage ? "Check only the items you want. Browsing does not select or install anything." : window.stageDescriptions[window.stage]; color: window.muted; font.pixelSize: 15; Layout.fillWidth: true }
            RowLayout {
                visible: !!window.detailPage || window.navigationStack.length > 0
                Layout.fillWidth: true
                Action { text: window.stage === 5 && window.progress.running ? (window.progress.operation === "accounts" ? "Setup in progress…" : "Installing…") : window.navigationStack.length && window.navigationStack[window.navigationStack.length-1].stage === 4 ? "‹ Return to review" : window.detailPage === "css" ? "‹ Decky plugins" : "‹ " + window.stageNames[window.stage]; onClicked: window.back() }
                TextLabel { Layout.fillWidth: true; text: window.detailPage === "plugins" ? "Choosing a plugin includes Decky Loader." : window.detailPage === "css" ? "Choosing a theme includes CSS Loader and Decky." : "Your edits stay in this plan."; color: window.muted; font.pixelSize: 12 }
            }
            RowLayout {
                visible: !!window.data.sudoReadiness && window.data.sudoReadiness.status !== "PASS"
                Layout.fillWidth: true
                TextLabel { Layout.fillWidth: true; text: window.data.sudoReadiness ? window.data.sudoReadiness.message : ""; color: window.accent; font.pixelSize: 12 }
                Action { text: "Recheck password"; enabled: !window.progress.running; onClicked: window.request("sudo-readiness", null, function(result) { var next = Object.assign({}, window.data); next.sudoReadiness = result; window.data = next }) }
            }
            RowLayout {
                visible: window.stage < 4
                Layout.fillWidth: true; spacing: 10
                TextField {
                    id: search
                    Layout.fillWidth: true; implicitHeight: 48
                    placeholderText: "Search this section…"; placeholderTextColor: window.muted; color: window.ink
                    text: window.searchText; onTextEdited: window.searchText = text
                    leftPadding: 14; rightPadding: 14
                    background: Rectangle { radius: 10; color: window.tone("#150d21"); border.color: search.activeFocus ? window.cyan : window.tone("#533960") }
                    Accessible.name: "Search choices in this section"
                }
                Action { text: window.selectedOnly ? "✓ Selected only" : "Selected only"; primary: window.selectedOnly; implicitWidth: 136; onClicked: window.selectedOnly = !window.selectedOnly; Accessible.name: "Toggle showing selected choices only" }
                Action {
                    id: moreButton; text: "More"; implicitWidth: 72
                    onClicked: choicesMenu.open()
                    Menu {
                        id: choicesMenu
                        MenuItem { text: "Export saved setup…"; enabled: window.saved && !window.dirty && !window.busy; onTriggered: window.sharePlan("export") }
                        MenuItem { text: "Import setup…"; enabled: !window.busy && !window.progress.running; onTriggered: window.sharePlan("import") }
                        MenuSeparator {}
                        MenuItem { text: "Load full preset…"; onTriggered: { window.pendingPreset = true; presetDialog.open() } }
                        MenuItem { text: "Clear all choices…"; onTriggered: { window.pendingPreset = false; presetDialog.open() } }
                        MenuItem { text: "First-run guide…"; onTriggered: window.openGuide() }
                        MenuSeparator { visible: !!window.detailPage }
                        MenuItem { visible: !!window.detailPage; text: "Clear this list"; onTriggered: window.detailPreset(false) }
                        MenuItem { visible: window.detailPage === "plugins" || window.detailPage === "css"; text: "Use recommended choices"; onTriggered: window.detailPreset(true) }
                    }
                }
            }
            Rectangle {
                visible: !!window.problem || !!window.notice
                Layout.fillWidth: true; implicitHeight: banner.implicitHeight + 24; radius: 10
                color: window.problem ? window.tone("#442035") : window.tone("#281d3e")
                TextLabel { id: banner; anchors.fill: parent; anchors.margins: 12; text: window.problem || window.notice; color: window.problem ? window.tone("#ffd0e9") : window.tone("#e3d0fa"); font.pixelSize: 13 }
            }
            RowLayout {
                Layout.fillWidth: true
                TextLabel { Layout.fillWidth: true; font.pixelSize: 12; color: window.muted; text: window.inventoryPending ? "Checking this Deck and available updates… " + (window.deckInventory.completed || 0) + "/" + (window.deckInventory.total || 0) : "Device status is separate from your selections. Sign-in may still be needed." }
                Action { text: "Refresh status"; enabled: !window.inventoryPending && !window.progress.running; onClicked: window.refreshInventory() }
                Action { text: "Select updates"; enabled: !window.inventoryPending && !window.progress.running && !window.busy; onClicked: window.selectUpdates() }
            }
            ScrollView {
                id: scroll
                Layout.fillWidth: true; Layout.fillHeight: true
                clip: true; contentWidth: availableWidth
                ScrollBar.vertical.policy: ScrollBar.AsNeeded
                ScrollBar.vertical.active: true
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                ColumnLayout {
                    width: scroll.availableWidth; spacing: 14
                    ColumnLayout {
                        visible: !window.previousRunDismissed && !window.dirty && window.stage < 5 && (!!window.previousRun.hasHistory || !!window.previousRun.historyPlanChanged)
                        Layout.fillWidth: true
                        TextLabel { text: window.previousRunText(); Layout.fillWidth: true; color: window.cyan; font.pixelSize: 13 }
                        Flow {
                            Layout.fillWidth: true; spacing: 8
                            Action { text: "Resume installation"; visible: !!window.previousRun.resumable && window.previousRun.unfinished > 0 && !window.data.planOnly; enabled: !window.busy && !window.progress.running; onClicked: window.startOperation("resume") }
                            Action { text: "Review choices"; enabled: !window.progress.running; onClicked: { window.previousRunDismissed = true; window.navigate(4) } }
                            Action { text: "View last results"; visible: !!window.previousRun.hasHistory; onClicked: window.navigate(5) }
                        }
                    }
                    TextLabel { visible: window.stage === 4; text: "Appearance: " + window.appearanceSummary(); Layout.fillWidth: true; font.pixelSize: 13; color: window.cyan }
                    TextLabel {
                        visible: window.detailPage === "css" || window.detailPage === "plugins"
                        text: "Theme palette: " + window.activePalette.name + ". Choose where to apply it using Theme & appearance in the sidebar. Enabled appearance targets follow this palette during installation; plugins without color settings keep their own appearance."
                        color: window.muted; font.pixelSize: 13; Layout.fillWidth: true
                    }
                    ColumnLayout {
                        visible: window.detailPage === "css"; Layout.fillWidth: true; spacing: 12
                        TextLabel { text: "Choose your colors"; font.pixelSize: 18; font.weight: Font.DemiBold }
                        Flow {
                            Layout.fillWidth: true; spacing: 10
                            Repeater {
                                model: window.paletteOptions
                                delegate: AbstractButton {
                                    id: paletteCard
                                    required property var modelData
                                    width: 180; height: 76
                                    Accessible.name: modelData.name + (window.paletteId === modelData.id ? ", selected" : "")
                                    onClicked: window.choosePalette(modelData.id)
                                    background: Rectangle { radius: 12; color: modelData.colors["#1a1128"]; border.width: 2; border.color: window.paletteId === modelData.id || parent.activeFocus ? modelData.colors["#ff4fd8"] : window.tone("#402c4e") }
                                    contentItem: Column {
                                        padding: 12; spacing: 8
                                        Row {
                                            spacing: 6
                                            Repeater { model: ["#ff4fd8", "#42f5ff", "#a970ff", "#f8e7ff"]
                                                delegate: Rectangle { required property string modelData; width: 22; height: 12; radius: 6; color: paletteCard.modelData.colors[modelData] }
                                            }
                                        }
                                        Label { text: (window.paletteId === modelData.id ? "✓ " : "") + modelData.name; color: modelData.colors["#f8e7ff"]; font.pixelSize: 12 }
                                    }
                                }
                            }
                        }
                        Action { text: window.showPalettePreview ? "Hide color preview" : "Preview menus & keyboard"; onClicked: window.showPalettePreview = !window.showPalettePreview }
                        ColumnLayout {
                            visible: window.showPalettePreview; Layout.fillWidth: true; spacing: 10
                        TextLabel { text: "Menu & keyboard color study"; font.pixelSize: 14; font.weight: Font.DemiBold }
                        Rectangle {
                            Layout.fillWidth: true; implicitHeight: 190; radius: 14; color: window.tone("#090612"); border.color: window.tone("#402c4e")
                            RowLayout {
                                anchors.fill: parent; anchors.margins: 14; spacing: 12
                                Rectangle {
                                    Layout.fillHeight: true; Layout.preferredWidth: 140; radius: 10; color: window.tone("#1a1128")
                                    Column { anchors.fill: parent; anchors.margins: 12; spacing: 11
                                        TextLabel { text: "STEAM MENU"; font.pixelSize: 10; color: window.cyan }
                                        TextLabel { text: "Library"; color: window.accent; font.bold: true }
                                        TextLabel { text: "Store"; font.pixelSize: 12 }
                                        TextLabel { text: "Settings"; font.pixelSize: 12 }
                                    }
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true; Layout.fillHeight: true
                                    TextLabel { text: "QUICK ACCESS"; font.pixelSize: 10; color: window.cyan }
                                    TextLabel { text: "Volume"; font.pixelSize: 12 }
                                    Rectangle { Layout.fillWidth: true; height: 5; radius: 3; color: window.accent }
                                    Item { Layout.fillHeight: true }
                                    TextLabel { text: "KEYBOARD"; font.pixelSize: 10; color: window.cyan }
                                    RowLayout {
                                        Layout.fillWidth: true; spacing: 5
                                        Repeater { model: ["Q", "W", "E", "R", "T"]
                                            delegate: Rectangle { required property string modelData; Layout.fillWidth: true; height: 38; radius: 6; color: window.tone("#35203f"); TextLabel { anchors.centerIn: parent; text: modelData; font.pixelSize: 12 } }
                                        }
                                    }
                                }
                            }
                        }
                        TextLabel { text: "Illustration of the selected colors, not a Game Mode screenshot. Actual layouts depend on the CSS components you select. Use the theme authors’ previews to compare layouts."; Layout.fillWidth: true; color: window.muted; font.pixelSize: 12 }
                        Action { text: "Open CSS Loader theme previews ↗"; onClicked: Qt.openUrlExternally("https://deckthemes.com/") }
                        }
                    }
                    Repeater {
                        model: window.currentSections()
                        delegate: ColumnLayout {
                            required property var modelData
                            Layout.fillWidth: true; spacing: 10
                            RowLayout {
                                visible: !window.detailPage
                                Layout.fillWidth: true
                                TextLabel { text: modelData.title; color: window.cyan; font.pixelSize: 17; font.weight: Font.DemiBold; Layout.fillWidth: true }
                            }
                            TextLabel { visible: !window.detailPage; text: modelData.description; color: window.muted; font.pixelSize: 12; Layout.fillWidth: true }
                            GridLayout {
                                Layout.fillWidth: true; columns: window.width < 1000 ? 1 : 2; columnSpacing: 12; rowSpacing: 12
                                Repeater {
                                    model: modelData.items
                                    delegate: ChoiceCard {
                                        required property var modelData
                                        objectName: "choice-" + modelData.id
                                        Layout.fillWidth: true; Layout.preferredWidth: 1; Layout.fillHeight: true
                                        heading: modelData.name; detail: modelData.summary
                                        inventoryLabel: window.inventoryFor(modelData).label
                                        inventoryStatus: window.inventoryFor(modelData).status
                                        inventoryDetail: window.inventoryDetails(modelData)
                                        requirement: window.requiredBy(modelData)
                                        optionsPage: modelData.kind === "module" && modelData.id === "decky" ? "plugins" : modelData.kind === "plugin" && modelData.id === "SDH-CssLoader" ? "css" : ""
                                        selected: window.itemSelected(modelData)
                                        onClicked: window.toggleItem(modelData)
                                    }
                                }
                            }
                            Item { implicitHeight: 8 }
                        }
                    }
                    TextLabel {
                        visible: window.stage < 4; Layout.fillWidth: true
                        text: window.currentItems().length === 0 ? "No choices match this view. Clear the search or turn off Selected only." : "Unchecked items are skipped. Deselecting keeps any apps already installed."
                        font.pixelSize: 12; color: window.muted; Layout.topMargin: 4
                    }
                    ColumnLayout {
                        visible: window.stage < 4 && window.dependencyNotes().length > 0
                        Layout.fillWidth: true
                        TextLabel { text: "Included with your choices"; color: window.cyan; font.pixelSize: 13; font.weight: Font.DemiBold }
                        Repeater {
                            model: window.dependencyNotes()
                            delegate: TextLabel { required property string modelData; text: "↳ " + modelData; color: window.muted; font.pixelSize: 12; Layout.fillWidth: true }
                        }
                    }
                    ColumnLayout {
                        visible: window.stage === 4; Layout.fillWidth: true; spacing: 14
                        Rectangle {
                            Layout.fillWidth: true; implicitHeight: reviewIntro.implicitHeight + 36; radius: 14; color: window.tone("#2a1736"); border.color: window.tone("#a970ff")
                            ColumnLayout {
                                id: reviewIntro; anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 18; spacing: 8
                                TextLabel { text: "A setup that fits you"; font.pixelSize: 19; font.weight: Font.DemiBold }
                                TextLabel { text: "Save this plan for later, or install your choices. Existing apps and personal data are kept."; Layout.fillWidth: true; color: window.tone("#e2c5e6"); font.pixelSize: 14 }
                                TextLabel { visible: window.pageValues("css").length > 0; text: window.appearanceChoices.css === false ? "CSS colors: keep current appearance" : "Theme palette: " + window.activePalette.name + " · for selected CSS Loader color controls"; Layout.fillWidth: true; color: window.cyan; font.pixelSize: 14 }
                            }
                        }
                        Flow {
                            Layout.fillWidth: true; spacing: 8
                            Action { text: "Export saved setup…"; enabled: window.saved && !window.dirty && !window.busy; onClicked: window.sharePlan("export") }
                            Action { text: "Import setup…"; enabled: !window.busy; onClicked: window.sharePlan("import") }
                        }
                        TextLabel { visible: window.selectionCount() === 0; text: "No optional installs selected. Only base support will be configured."; Layout.fillWidth: true; color: window.muted }
                        Repeater {
                            model: window.reviewSections()
                            delegate: Rectangle {
                                required property var modelData
                                Layout.fillWidth: true; implicitHeight: reviewGroup.implicitHeight + 28
                                radius: 12; color: window.tone("#1a1128")
                                ColumnLayout {
                                    id: reviewGroup
                                    anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 14
                                    spacing: 9
                                    RowLayout {
                                        Layout.fillWidth: true
                                        TextLabel { text: modelData.title; font.pixelSize: 15; font.weight: Font.DemiBold; Layout.fillWidth: true }
                                        Action { text: "Edit"; implicitWidth: 76; onClicked: window.editSection(modelData) }
                                    }
                                    Repeater {
                                        model: modelData.items
                                        delegate: ColumnLayout {
                                            required property var modelData
                                            Layout.fillWidth: true; spacing: 4
                                            TextLabel { text: "✓  " + modelData.name + (window.requiredBy(modelData) ? " · included" : ""); Layout.fillWidth: true; font.pixelSize: 14 }
                                            TextLabel { text: modelData.summary + "\n" + window.inventoryFor(modelData).label; Layout.fillWidth: true; Layout.leftMargin: 20; color: window.muted; font.pixelSize: 12 }
                                        }
                                    }
                                }
                            }
                        }
                        TextLabel { text: "INCLUDED SUPPORT"; font.pixelSize: 11; color: window.muted; font.letterSpacing: 1.2; Layout.topMargin: 6 }
                        TextLabel { text: "Base support and the dependencies needed by your selections are included automatically."; Layout.fillWidth: true; color: window.muted; font.pixelSize: 13 }
                        Repeater {
                            model: window.dependencyNotes()
                            delegate: TextLabel { required property string modelData; text: "↳  " + modelData; Layout.fillWidth: true; font.pixelSize: 13; color: window.muted }
                        }
                        Action { text: window.previewPending ? "Checking installation details…" : "Check changes & space"; enabled: !window.previewPending; onClicked: window.previewPlan() }
                        TextLabel { visible: !!window.installPreview.sizeNote; text: window.installPreview.sizeNote || ""; Layout.fillWidth: true; font.pixelSize: 12; color: window.muted }
                        Repeater {
                            model: window.installPreview.volumes || []
                            delegate: TextLabel { required property var modelData; Layout.fillWidth: true; text: window.bytesLabel(modelData.freeBytes) + " free · " + window.bytesLabel(modelData.requiredBytes) + " known allowance" + (modelData.fits ? "" : " · Not enough space"); color: modelData.fits ? window.muted : window.accent }
                        }
                        Repeater {
                            model: window.changeGroups()
                            delegate: ColumnLayout {
                                required property var modelData
                                Layout.fillWidth: true; spacing: 8
                                TextLabel { text: modelData.title + " (" + modelData.items.length + ")"; font.bold: true; Layout.fillWidth: true }
                                Repeater {
                                    model: modelData.items
                                    delegate: TextLabel { required property var modelData; Layout.fillWidth: true; font.pixelSize: 12; color: window.muted; text: modelData.name + " · " + modelData.updateCheck + "\nDownload estimate if needed: " + window.bytesLabel(modelData.downloadBytes) + "\n" + (modelData.reviewNotes || []).join("\n") }
                                }
                            }
                        }
                        TextLabel { text: "WHAT HAPPENS NEXT"; font.pixelSize: 11; color: window.muted; font.letterSpacing: 1.2; Layout.topMargin: 6 }
                        TextLabel { text: "1. Download and install your selections.\n2. Complete selected vendor setup, sign-in and pairing in Konsole.\n3. Return here to review anything that still needs attention."; Layout.fillWidth: true; font.pixelSize: 13; color: window.muted }

                    }
                    ColumnLayout {
                        visible: window.stage === 5; Layout.fillWidth: true; spacing: 12
                        TextLabel { text: window.installTitle(); font.pixelSize: 21; font.weight: Font.DemiBold }
                        TextLabel {
                            visible: !!window.progress.operation && !!window.progress.summary
                            text: (window.progress.summary ? window.progress.summary.done + " of " + window.progress.summary.total + " verified in this installation record" + (window.progress.summary.attention ? " · " + window.progress.summary.attention + " need attention" : "") : "")
                            Layout.fillWidth: true; font.pixelSize: 13; color: window.cyan
                        }
                        Action { text: "Show installation results"; visible: window.finishItems.length > 0; onClicked: window.finishItems = [] }
                        Action { visible: !window.progress.running; text: "Recheck readiness"; enabled: !window.busy && !window.progress.running; onClicked: window.checkFinish() }
                        Repeater {
                            model: window.finishItems
                            delegate: Rectangle {
                                required property var modelData
                                Layout.fillWidth: true; implicitHeight: finishColumn.implicitHeight + 28; radius: 12; color: window.tone("#1a1128")
                                ColumnLayout {
                                    id: finishColumn; anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 14; spacing: 7
                                    TextLabel { text: modelData.name + " · " + modelData.status; Layout.fillWidth: true; font.weight: Font.DemiBold }
                                    TextLabel { text: modelData.note; Layout.fillWidth: true; color: window.muted; font.pixelSize: 12 }
                                    Flow {
                                        Layout.fillWidth: true; spacing: 8
                                        Action { visible: modelData.canLaunch; text: modelData.status === "Ready" ? "Open" : "Open setup / sign-in"; enabled: !window.busy && !window.progress.running; onClicked: window.finishAction(modelData.key, "launch") }
                                        Action { visible: modelData.canConfirm && modelData.status !== "Ready"; text: modelData.followup === "pairing" ? "I've paired it" : modelData.followup === "setup" ? "I've completed setup" : "I've signed in"; enabled: !window.busy && !window.progress.running; onClicked: window.finishAction(modelData.key, "confirm") }
                                    }
                                }
                            }
                        }

                        TextLabel { text: window.progress.running ? "Use the Konsole window for installer prompts. Keep this window open to follow results." : window.progress.operation && window.progress.exitCode !== 0 ? "Some selections still need attention. Review their results or logs, then resume. Completed installs are reused." : "Each selection has its own result. Resume checks completed items again and retries unfinished work."; Layout.fillWidth: true; color: window.muted; font.pixelSize: 13 }
                        Repeater {
                            model: window.finishItems.length && !window.progress.running ? [] : window.progress.modules
                            delegate: Rectangle {
                                required property var modelData
                                Layout.fillWidth: true; implicitHeight: resultColumn.implicitHeight + 26
                                radius: 10; color: window.tone("#1a1128")
                                ColumnLayout {
                                    id: resultColumn; anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 13; spacing: 5
                                    RowLayout {
                                        Layout.fillWidth: true
                                        TextLabel { text: modelData.name || window.featureNames()[modelData.id] || modelData.id; Layout.fillWidth: true; font.pixelSize: 14 }
                                        TextLabel { text: modelData.resultLabel || window.statusLabel(modelData.status); color: window.stateColor(modelData.status); font.pixelSize: 12 }
                                    }
                                    TextLabel { visible: !!modelData.message; text: modelData.message || ""; color: window.muted; font.pixelSize: 12; Layout.fillWidth: true }
                                    TextLabel { visible: !!modelData.nextAction; text: "Next: " + (modelData.nextAction || ""); color: window.cyan; font.pixelSize: 12; Layout.fillWidth: true }
                                    TextLabel { visible: !!modelData.activityNotice; text: modelData.activityNotice || ""; color: window.accent; font.pixelSize: 12; Layout.fillWidth: true }
                                    TextLabel { visible: modelData.status === "RUNNING"; text: "Last activity " + window.elapsedLabel(modelData.quietSeconds) + " ago"; color: window.muted; font.pixelSize: 12; Layout.fillWidth: true }
                                    TextLabel {
                                        visible: modelData.status === "RUNNING" || !!modelData.startedAt
                                        text: (modelData.status === "RUNNING" ? (modelData.phase || "Installing") + " · " : "Elapsed · ") + window.elapsedLabel(modelData.elapsedSeconds)
                                        color: window.cyan; font.pixelSize: 12; Layout.fillWidth: true
                                    }
                                    BusyIndicator { visible: modelData.status === "RUNNING" && !(modelData.total > 0); running: visible; implicitWidth: 28; implicitHeight: 28 }
                                    ProgressBar {
                                        id: transferProgress
                                        visible: modelData.status === "RUNNING" && modelData.total > 0; Layout.fillWidth: true
                                        implicitHeight: 6
                                        background: Rectangle { color: window.tone("#31213f"); radius: 3 }
                                        contentItem: Item { Rectangle { width: transferProgress.visualPosition * parent.width; height: parent.height; color: window.accent; radius: 3 } }
                                        indeterminate: !(modelData.total > 0)
                                        value: modelData.total > 0 ? Math.min(1, (modelData.downloaded || 0) / modelData.total) : 0
                                        Accessible.name: "Progress for " + modelData.name
                                    }
                                    TextLabel {
                                        visible: modelData.status === "RUNNING" && modelData.downloaded !== null && modelData.downloaded !== undefined
                                        text: window.bytesLabel(modelData.downloaded) + (modelData.total > 0 ? " of " + window.bytesLabel(modelData.total) : " downloaded · total size unavailable")
                                        font.pixelSize: 12; color: window.muted; Layout.fillWidth: true
                                    }
                                    Action { objectName: "viewInstallLog"; text: "Details / live output"; visible: !!modelData.hasLog; onClicked: window.showLog(modelData.id) }
                                    Action { text: "Retry this item"; visible: ["FAILED", "INTERRUPTED", "NEEDS_SETUP", "BLOCKED"].indexOf(modelData.status) >= 0; enabled: !window.progress.running && !window.busy; onClicked: window.startOperation("retry", modelData.id) }
                                }
                            }
                        }
                    }
                }
            }
            Rectangle { Layout.fillWidth: true; height: 1; color: window.tone("#402c4e") }
            RowLayout {
                Layout.fillWidth: true; spacing: 10
                Action { text: "Back"; visible: !!window.detailPage || (window.stage > 0 && window.stage < 5); enabled: !window.busy; onClicked: window.back() }
                TextLabel { visible: window.stage < 4; text: "Your choices save at review.\nNothing installs yet."; font.pixelSize: 12; color: window.muted; Layout.fillWidth: true }
                Item { visible: window.stage >= 4; Layout.fillWidth: true }
                Action { text: "Close"; visible: window.stage === 5; enabled: !window.progress.running && !window.busy; onClicked: window.close() }
                Action { text: "Save for later"; visible: window.stage === 4 && !window.data.planOnly; enabled: !window.busy; onClicked: window.savePlan(false) }
                Action {
                    objectName: "primaryAction"
                    primary: true
                    text: window.stage === 5 && window.progress.running ? (window.progress.operation === "accounts" ? "Setup in progress…" : "Installing…") : window.navigationStack.length && window.navigationStack[window.navigationStack.length-1].stage === 4 ? "Return to review →" : window.detailPage ? "Done choosing →" : window.stage < 3 ? "Continue →" : (window.stage === 3 ? "Review setup →" : (window.stage === 4 ? (window.data.planOnly ? "Save & continue" : window.previewPending ? "Checking changes…" : !window.installPreview.items || window.installPreview.error ? "Review changes" : "Save & install") : (window.progress.operation === "install" && window.progress.exitCode === 0 ? "Continue setup" : window.progress.operation === "accounts" && window.progress.exitCode === 0 ? "Finish" : window.progress.operation === "accounts" ? "Retry setup" : window.progress.operation ? "Resume installation" : "Install selections")))
                    enabled: window.loaded && !window.busy && !window.progress.running && (window.stage !== 5 || !window.data.planOnly)
                    onClicked: {
                        if (window.detailPage || window.navigationStack.length) window.back()
                        else if (window.stage < 4) window.navigate(window.stage + 1)
                        else if (window.stage === 4) {
                            if (window.data.planOnly) window.savePlan(false)
                            else if (window.previewPending) window.notice = "Wait for the installation review to finish."
                            else if (!window.installPreview.items || window.installPreview.error) { window.previewPlan(); window.notice = "Review the changes and space checks below, then choose Save & install again to confirm." }
                            else if ((window.installPreview.volumes || []).some(function(volume) { return !volume.fits })) window.problem = "Not enough space for the known allowance. Free space or reduce your choices, then check again."
                            else window.savePlan(true)
                        }
                        else if (window.progress.operation === "install" && window.progress.exitCode === 0) window.startOperation("accounts")
                        else if (window.progress.operation === "accounts" && window.progress.exitCode === 0) window.close()
                        else window.startOperation(window.progress.operation === "accounts" ? "accounts" : window.progress.resumable ? "resume" : "install")
                    }
                }
            }
        }
    }
    }
    Dialog {
        id: guideDialog
        objectName: "firstRunGuide"
        title: "Quick start · " + (window.guideStep + 1) + " of " + window.guidePages.length
        modal: true; anchors.centerIn: parent
        width: Math.min(560, window.width - 40); height: Math.min(420, window.height - 40)
        background: Rectangle { color: window.tone("#1a1128"); radius: 14; border.color: window.violet }
        contentItem: ColumnLayout {
            TextLabel { text: window.guidePages[window.guideStep].title; font.pixelSize: 21; font.bold: true; Layout.fillWidth: true }
            ScrollView { Layout.fillWidth: true; Layout.fillHeight: true; clip: true; contentWidth: availableWidth
                TextLabel { width: parent.width; text: window.guidePages[window.guideStep].text; font.pixelSize: 15 }
            }
            Flow { Layout.fillWidth: true; spacing: 8
                Action { text: "Skip guide"; onClicked: window.closeGuide() }
                Action { text: "Back"; visible: window.guideStep > 0; onClicked: window.guideStep-- }
                Action { text: window.guideStep === 3 ? "Choose my apps" : "Next"; primary: true; onClicked: { if (window.guideStep < 3) window.guideStep++; else window.closeGuide() } }
            }
        }
    }
    Dialog {
        id: appearanceDialog
        objectName: "appearanceDialog"
        title: "Theme & appearance"
        background: Rectangle { color: window.tone("#1a1128"); radius: 14; border.color: window.violet }
        anchors.centerIn: parent; width: Math.min(560, window.width - 40); height: Math.min(620, window.height - 40)
        modal: true; standardButtons: Dialog.Close
        contentItem: ScrollView {
            clip: true; contentWidth: availableWidth
            ColumnLayout {
                width: appearanceDialog.availableWidth; spacing: 12
                TextLabel { text: "Choose one palette, then where it applies."; Layout.fillWidth: true; color: window.muted }
                ComboBox {
                    Layout.fillWidth: true; model: window.paletteOptions; textRole: "name"
                    currentIndex: window.paletteOptions.findIndex(function(p) { return p.id === window.paletteId })
                    Accessible.name: "Shared color palette"
                    onActivated: window.choosePalette(window.paletteOptions[currentIndex].id)
                }
                Row {
                    spacing: 10
                    Repeater {
                        model: ["#090612", "#ff4fd8", "#42f5ff", "#a970ff", "#f8e7ff"]
                        delegate: Rectangle { required property string modelData; width: 36; height: 20; radius: 6; color: window.tone(modelData); border.color: window.muted }
                    }
                }
                TextLabel { text: "Apply to selected tools"; font.weight: Font.DemiBold; Layout.fillWidth: true }
                Repeater {
                    model: window.data.appearanceTargets || []
                    delegate: ColumnLayout {
                        required property var modelData
                        Layout.fillWidth: true; spacing: 1
                        CheckBox {
                            id: appearanceSwitch
                            implicitHeight: 44
                            indicator: Rectangle {
                                x: 6; y: (parent.height - height) / 2; width: 24; height: 24; radius: 7
                                color: appearanceSwitch.checked ? window.accent : window.tone("#100a1b")
                                border.width: appearanceSwitch.activeFocus ? 2 : 1
                                border.color: appearanceSwitch.activeFocus ? window.cyan : window.muted
                                Text { anchors.centerIn: parent; text: appearanceSwitch.checked ? "✓" : ""; color: window.tone("#20091e"); font.bold: true; font.pixelSize: 17 }
                            }
                            text: modelData.name; Layout.fillWidth: true
                            checked: window.appearanceChoices[modelData.id] !== false
                            onClicked: window.setAppearance(modelData.id, checked)
                        }
                        TextLabel { text: modelData.summary + (window.appearanceTargetSelected(modelData.id) ? "" : " · Tool not selected; preference only"); Layout.fillWidth: true; Layout.leftMargin: 30; font.pixelSize: 12; color: window.muted }
                    }
                }
                TextLabel { text: "These switches never install extra software. Off keeps the current appearance; it does not reset it. Changes apply when you save and install. Personal Ghostty configuration is preserved; its theme must reference deckctl-bubble-gum-rave to follow this palette. Unsupported Decky plugins keep their own colors."; Layout.fillWidth: true; color: window.muted; font.pixelSize: 12 }
            }
        }
    }
    Dialog {
        id: logDialog
        objectName: "installLogDialog"
        title: "Installation details · " + window.logView.item
        background: Rectangle { color: window.tone("#1a1128"); radius: 14; border.color: window.violet }
        anchors.centerIn: parent; width: Math.min(760, window.width - 40); height: Math.min(540, window.height - 40)
        modal: true; standardButtons: Dialog.Close
        contentItem: ColumnLayout {
            TextLabel { text: "Phases, installer errors and diagnostics. Prompts remain in Konsole. Review before sharing."; Layout.fillWidth: true; font.pixelSize: 12; color: window.muted }
            TextLabel { visible: !!window.logView.truncated; text: "Showing the last 64 KiB."; font.pixelSize: 12 }
            ScrollView {
                Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                TextArea { id: logText; objectName: "liveLogText"; text: window.logView.text || "No diagnostic output yet."; readOnly: true; textFormat: TextEdit.PlainText; selectByMouse: true; wrapMode: TextEdit.WrapAnywhere; font.family: "monospace"; font.pixelSize: 12 }
            }
            CheckBox { text: "Live refresh (pause to select text)"; checked: window.followLog; onToggled: window.followLog = checked }
            Flow {
                Layout.fillWidth: true; spacing: 8
                Action { text: "Refresh"; enabled: !window.logPending; onClicked: window.refreshLog() }
                Action { text: "Copy output"; onClicked: { logText.selectAll(); logText.copy(); logText.deselect() } }
                Action { text: "Retry this item"; enabled: window.logCanRetry(); onClicked: { window.closeLog(); window.startOperation("retry", window.logView.item) } }
            }
        }
    }
    Timer { interval: 1500; repeat: true; running: logDialog.visible && window.followLog && window.progress.running; onTriggered: window.refreshLog() }
    Dialog {
        id: importDialog
        title: "Import this setup?"
        anchors.centerIn: parent; width: Math.min(500, window.width - 40); modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel
        contentItem: Label { wrapMode: Text.WordWrap; text: "Replace your saved choices with this shared setup? Nothing installs yet. Review and deselect anything afterward. Your current configuration is backed up.\n\nIncluded files:\n" + (window.importPreview.files || []).slice(0, 10).join("\n") + ((window.importPreview.files || []).length > 10 ? "\n… plus " + (window.importPreview.files.length - 10) + " more files" : "") }
        onAccepted: window.sharePlan("import-confirm")
        onRejected: window.sharePlan("import-cancel")
    }
    Dialog {
        id: presetDialog
        title: window.pendingPreset ? "Select everything in the full preset?" : "Clear all choices?"
        anchors.centerIn: parent; modal: true
        width: Math.min(430, window.width-40)
        standardButtons: Dialog.Ok | Dialog.Cancel
        Label { width: parent.width; wrapMode: Text.WordWrap; text: (window.pendingPreset ? "This selects all tools, including both local AI models. Review the individual choices before installing. " : "This clears every section of your plan. ") + "Existing software stays installed. Your saved plan changes only when you save at review." }
        onAccepted: window.preset(window.pendingPreset)
    }
    Dialog {
        id: leaveDialog
        title: "Leave setup?"
        anchors.centerIn: parent
        modal: true
        width: Math.min(430, window.width-40)
        standardButtons: Dialog.Discard | Dialog.Cancel
        Label { width: parent.width; wrapMode: Text.WordWrap; text: "Your unsaved choices will be discarded. Your previously saved setup stays unchanged." }
        onDiscarded: { window.saved = true; window.dirty = false; window.close() }
    }
}
