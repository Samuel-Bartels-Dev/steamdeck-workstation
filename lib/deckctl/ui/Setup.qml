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
    property var consoleOutput: ({text:""})
    property bool consolePending: false
    property bool showConsole: true
    property bool progressPending: false
    property string consoleItem: ""
    property string displayedConsole: ""
    property bool errorsOnly: false
    property bool closeAfterCancel: false
    property bool closeRequested: false
    property bool allowClose: false
    property bool followConsole: true
    property string expandedResult: ""
    property bool showCompleted: false
    function installRows() {
        if (!progress.operation || (finishItems.length && !progress.running)) return []
        var rows = progress.items || progress.modules || [], output = []
        ;[{name:"ACTIVE",states:["RUNNING"]},{name:"SCHEDULED",states:["PENDING"]},{name:"NEEDS ATTENTION",states:["FAILED","INTERRUPTED","NEEDS_SETUP","BLOCKED"]},{name:"COMPLETED",states:["DONE"]}].forEach(function(group) {
            var items = rows.filter(function(item) { return group.states.indexOf(item.status) >= 0 })
            if (group.name === "COMPLETED" && !showCompleted) return
            items.forEach(function(item,index) { output.push(Object.assign({},item,{queueHeading:index === 0 ? group.name + " · " + items.length : ""})) })
        })
        return output
    }
    function requestRunClose() {
        closeRequested = true
        if (progress.controls && progress.controls.available) {
            if (progress.controls.cancel) { closeAfterCancel = true; notice = "Closing when cancellation finishes. Use Force stop if the provider does not respond." }
            else cancelRunDialog.open()
        } else externalCloseDialog.open()
    }
    onProgressChanged: {
        if (closeAfterCancel && !progress.running) { allowClose = true; Qt.callLater(function() { window.close() }) }
    }
    function controlQueue(action) { request("control", {action:action}, function(result) { progress = result }) }
    function rateLabel(key) {
        var samples = progress.activity || [], sample = samples.length ? samples[samples.length-1] : {}, value = sample[key]
        if (value === null || value === undefined || !sample.time) return "Unknown"
        if (!progress.running) return bytesLabel(value) + "/s · last observed"
        var age = Math.max(0,clockSeconds-sample.time)
        return age > 10 ? "Stale · " + elapsedLabel(Math.floor(age)) + " ago" : bytesLabel(value) + "/s"
    }
    function refreshConsole() {
        if (consolePending) return
        consolePending = true
        request("console", null, function(result) { consolePending = false; consoleOutput = result; if (followConsole && !consoleItem) displayedConsole = result.text || "" })
    }
    function refreshProgress() {
        if (progressPending) return
        progressPending = true
        request("progress", null, function(result) {
            progressPending = false
            var wasRunning = progress.running
            progress = result
            if (wasRunning && !result.running) refreshInventory()
        })
    }
    function displayedOutput() {
        if (!displayedConsole) return "Installer stdout and stderr will appear here. No passwords or interactive input are accepted."
        if (!errorsOnly) return displayedConsole
        var lines = displayedConsole.split("\n"), selected = []
        for (var i=0; i<lines.length; i++) {
            if (/error|fail|traceback|interrupted|needs_setup|blocked/i.test(lines[i])) {
                if (i > 0 && (selected.length === 0 || selected[selected.length-1] !== lines[i-1])) selected.push(lines[i-1])
                selected.push(lines[i])
            }
        }
        return selected.length ? selected.join("\n") : "No error keywords in the displayed output. Check item results for verified status."
    }
    function revealConsole() {
        Qt.callLater(function() {
            if (scroll.contentItem) scroll.contentItem.contentY = Math.max(0, consolePanel.mapToItem(scroll.contentItem, 0, 0).y)
        })
    }
    function networkLabel() {
        var network = progress.network, samples = progress.activity || []
        if (!network) return "Network state unknown · Internet access not checked"
        var stale = network.checkedAt && clockSeconds-network.checkedAt > 10
        return (stale ? "Last known: " : "") + network.message + (stale ? " · stale reading" : "") +
                (samples.length && samples[samples.length-1].network === 0 ? " · no receive traffic measured" : "")
    }
    function storageLabel(storage) {
        if (!storage) return ""
        return storage.path + " · " + (storage.freeBytes === null ? "free space unknown" : bytesLabel(storage.freeBytes) + " free now") + "\n" +
            (storage.allowanceBytes === null ? "Size unknown; provider checks space" : bytesLabel(storage.allowanceBytes) + " original staging allowance") +
            " · " + bytesLabel(storage.reserveBytes) + " reserve" +
            (storage.status === "INSUFFICIENT" ? " · Below original allowance + reserve" : "") +
            ". This is not a remaining-space estimate."
    }
    property var previousRun: ({})
    property bool previousRunDismissed: false
    property int guideStep: 0
    readonly property var guidePages: [
        {title:"Start in Desktop Mode", text:"From Steam’s Power menu, switch to Desktop Mode. Keep your Deck connected to power and the internet for downloads. This guide is optional and does not change your choices."},
        {title:"Check your password", text:"Some vendor installers need administrator access. If setup says your password is missing or locked, open Konsole and run passwd. Typed characters stay invisible. Return here and use Recheck password. Decky plugin and palette changes use a KDE password dialog before installation. Never paste passwords into logs or chat."},
        {title:"Choose storage deliberately", text:"Internal storage holds tools and settings. Optional DECK-GAMES and DECK-EMU cards are for the configured game and emulation paths. Insert the intended card before installing components that use it. Check changes & space on the review page shows known allowances; unknown vendor sizes need extra room."},
        {title:"Make it your setup", text:"Choose individual apps and tools; required dependencies are included automatically. Review new installs, updates and configuration changes, then confirm. Afterward, check results and complete any sign-in or pairing. You can save choices for later and resume unfinished installation work."}
    ]
    readonly property bool guideVisible: guideDialog.visible
    function openGuide() { guideStep = 0; guideDialog.open() }
    function closeGuide() { guideDialog.close(); request("guide-seen", {}, function() {}) }
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
        property bool logPending: false
    function cssPaletteTargets() {
        var installed = (progress.cssPalette || data.cssPalette || {}).installedComponents || []
        return installed.concat(pageValues("css")).filter(function(name, index, all) { return all.indexOf(name) === index })
    }
    function cssSelectionError() {
        return appearanceChoices.css === true && cssPaletteTargets().length === 0 ? "Game Mode theming is enabled but no CSS components are selected. Choose components or turn Game Mode theming off." : ""
    }
    function cssPalettePlanText() {
        if (cssSelectionError()) return "Selection error: " + cssSelectionError()
        if (appearanceChoices.css === false) return "Selected palette: " + activePalette.name + ". Game Mode recoloring is off; existing colors will stay."
        if (cssPaletteTargets().length === 0) return "Selected palette: " + activePalette.name + ". It will not apply to Game Mode: no CSS components selected. Existing colors will stay."
        return "Selected palette: " + activePalette.name + ". Will apply to " + cssPaletteTargets().length + " supported CSS themes when you apply changes. Installed themes are included automatically; no need to select them again."
    }
    function openAppearance() { appearanceDialog.open() }
    function closeAppearance() { appearanceDialog.close() }
    function closeLog() { consoleItem = ""; displayedConsole = consoleOutput.text || "" }
    function appearanceTargetSelected(key) {
        return key === "css" ? cssPaletteTargets().length > 0 : pageValues("terminal").indexOf(key) >= 0
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
        request("log", {item: key}, function(result) { logView = result; consoleItem = key; displayedConsole = result.text || ""; showConsole = true; revealConsole() })
    }
    function refreshLog() {
        if (logPending || !logView.item) return
        logPending = true
        request("log", {item: logView.item}, function(result) { logPending = false; applyLogRefresh(result) })
    }
    function applyLogRefresh(result) {
        if (consoleItem !== result.item) return
        logView = result
        if (followConsole) displayedConsole = result.text || ""
    }
    function logCanRetry() {
        return !progress.running && !busy && (progress.items || progress.modules || []).some(function(item) {
            return item.id === logView.item && ["FAILED", "INTERRUPTED", "NEEDS_SETUP", "BLOCKED"].indexOf(item.status) >= 0
        })
    }
    property double clockSeconds: Date.now()/1000
    function githubLimitText() {
        var limit = progress.githubLimit
        if (!limit) return ""
        if (!limit.resetAt) return "GitHub API is rate limited; no reset time was provided. Independent installs can continue. Retry affected items later."
        var remaining = Math.max(0, Math.ceil(limit.resetAt-clockSeconds))
        return remaining > 0 ? "GitHub API reset expected in " + elapsedLabel(remaining) + " (" + new Date(limit.resetAt*1000).toLocaleTimeString() + "). Independent installs can continue." : "GitHub’s reset time has passed. Retry affected items when ready; availability has not been rechecked."
    }
    Timer { interval: 1000; repeat: true; running: window.stage === 5; onTriggered: window.clockSeconds = Date.now()/1000 }
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
            } catch (e) { busy = false; if (route === "log") logPending = false; if (route === "console") consolePending = false; if (route === "progress") progressPending = false; problem = e.message || "Setup connection lost. Close and reopen this window." }
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
        if (progress.running && progress.controls && progress.controls.cancel) return "Cancelling installation"
        if (progress.running && progress.queueStatus === "AUTHENTICATING") return "Waiting for administrator permission"
        if (progress.controls && progress.controls.cancel && !progress.running) return "Installation cancelled"
        if (progress.running && progress.queueStatus === "PAUSED") return "Queue paused"
        if (progress.running) return "Installing your selections"
        if (!progress.operation) return "Ready to install"
        if (progress.exitCode !== 0) return "Setup needs attention"
        return "Installation pass finished"
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
        if (!full) appearanceChoices = Object.assign({}, appearanceChoices, {css:false})
        selectedOnly = false; searchText = ""; saved = false; dirty = true; notice = full ? "Full workstation selected. Make it your own below." : "Starting small. Add only what you need."
    }
    function savePlan(install) {
        if (cssSelectionError()) { problem = cssSelectionError(); openAppearance(); return }
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
            busy = false; notice = result.confirmed ? "Marked complete by you." : result.terminalRequired ? "Opened the explicitly requested interactive terminal. Complete setup there, then recheck readiness here." : "Opened. Complete setup, then use Recheck readiness."
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
            showConsole = true; consoleItem = ""; followConsole = true; refreshConsole()
        })
    }
    function stateColor(status) {
        if (status === "DONE" || status === "READY" || status === "OPTIONAL") return accent
        if (status === "FAILED" || status === "NOT_INSTALLED") return window.tone("#ff91ba")
        if (status === "RUNNING") return window.tone("#42f5ff")
        return muted
    }
    function sectionCount(section) {
        return section.items.filter(function(item) { return itemSelected(item) }).length
    }
    onClosing: function(event) {
        if (allowClose) return
        if (progress.running) {
            event.accepted = false
            requestRunClose()
        } else if (busy) {
            event.accepted = false
            notice = "Finishing the current request. Try Close again in a moment."
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
            if (!result.guideSeen) Qt.callLater(openGuide)
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
        onTriggered: window.refreshProgress()
    }
    Timer { interval: 1000; running: window.loaded && window.stage === 5; repeat: true; onTriggered: window.refreshConsole() }

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
            radius: 12
            color: action.primary ? (action.down ? window.tone("#df30b6") : window.accent) : (action.hovered ? window.tone("#352046") : window.tone("#261735"))
            border.width: action.activeFocus ? 2 : 1
            border.color: action.activeFocus ? window.cyan : (action.primary ? window.accent : window.tone("#533960"))
            opacity: action.enabled ? 1 : 0.5
        }
    }
    component ActivityChart: ColumnLayout {
        id: chart
        required property string title
        required property var keys
        required property var colors
        required property var samples
        required property string rates
        readonly property real peak: {
            var highest = 0
            samples.forEach(function(sample) { keys.forEach(function(key) { if (sample[key] !== null && sample[key] !== undefined) highest = Math.max(highest, sample[key]) }) })
            return highest
        }
        spacing: 4
        TextLabel { text: chart.title; Layout.fillWidth: true; font.pixelSize: 11; color: window.muted }
        TextLabel { text: chart.rates; Layout.fillWidth: true; font.pixelSize: 13; color: chart.colors[0] }
        TextLabel { text: "Scale 0 – " + window.bytesLabel(chart.peak) + "/s"; Layout.fillWidth: true; font.pixelSize: 11; color: window.muted }
        Canvas {
            objectName: chart.keys[0] === "network" ? "downloadActivityGraph" : "diskActivityGraph"
            Layout.fillWidth: true; Layout.preferredHeight: window.height < 620 ? 45 : 64
            property var samples: chart.samples
            onSamplesChanged: requestPaint()
            onWidthChanged: requestPaint()
            onHeightChanged: requestPaint()
            onPaint: {
                var ctx = getContext("2d"); ctx.clearRect(0,0,width,height)
                ctx.strokeStyle = window.muted; ctx.globalAlpha = .2
                for (var grid=0;grid<3;grid++) { ctx.beginPath(); ctx.moveTo(0,2+(height-4)*grid/2); ctx.lineTo(width,2+(height-4)*grid/2); ctx.stroke() }
                ctx.globalAlpha = 1; ctx.lineWidth = 2
                var last = samples.length ? samples[samples.length-1].time : 0
                var first = samples.length ? samples[0].time : 0
                var duration = Math.max(1, last-first)
                chart.keys.forEach(function(key,index) {
                    ctx.strokeStyle = chart.colors[index]; ctx.beginPath(); var connected = false, previousTime = 0
                    samples.forEach(function(sample) {
                        if (sample[key] === null || sample[key] === undefined || !sample.time) { connected = false; return }
                        if (previousTime && sample.time-previousTime > 5) connected = false
                        var x = width*(sample.time-first)/duration, y = height-2-(height-4)*sample[key]/Math.max(1,chart.peak)
                        if (connected) ctx.lineTo(x,y); else ctx.moveTo(x,y)
                        connected = true; previousTime = sample.time
                    }); ctx.stroke()
                })
            }
        }
        TextLabel { text: chart.samples.length > 1 && chart.samples[0].time ? Math.round(chart.samples[chart.samples.length-1].time-chart.samples[0].time) + "s history · newest at right" : "Waiting for measured samples"; Layout.fillWidth: true; font.pixelSize: 11; color: window.muted }
    }
    component SpaceBudget: ColumnLayout {
        id: budget
        property string destination: ""
        property var freeBytes: null
        property var allowanceBytes: null
        property var reserveBytes: null
        property int unknownSizes: 0
        property bool advisory: false
        readonly property bool known: freeBytes !== null && freeBytes !== undefined && allowanceBytes !== null && allowanceBytes !== undefined
        readonly property real required: (allowanceBytes || 0) + (reserveBytes || 0)
        readonly property bool fits: known && freeBytes >= required
        spacing: 5
        TextLabel { text: budget.destination; Layout.fillWidth: true; color: window.ink; font.pixelSize: 13 }
        TextLabel { text: (budget.freeBytes === null || budget.freeBytes === undefined ? "Free space unknown" : window.bytesLabel(budget.freeBytes) + " free now") + " · " + (budget.known ? window.bytesLabel(budget.allowanceBytes) + " known staging allowance" : "Installation size unknown"); Layout.fillWidth: true; color: window.muted; font.pixelSize: 13 }
        Rectangle {
            Layout.fillWidth: true; implicitHeight: 14; radius: 4; clip: true
            color: window.tone("#35203f"); border.color: window.muted
            Accessible.role: Accessible.ProgressBar
            Accessible.name: budget.known ? (budget.fits ? "Known allowance fits available free space" : "Insufficient space for original allowance") : "Storage requirement unknown"
            Rectangle { height: parent.height; radius: 4; width: budget.known ? parent.width*Math.min(1,budget.required/Math.max(1,budget.freeBytes)) : 0; color: budget.fits ? window.cyan : window.accent }
        }
        TextLabel { text: (budget.known ? (budget.fits ? window.bytesLabel(budget.freeBytes-budget.required) + " above" : window.bytesLabel(budget.required-budget.freeBytes) + " below") + " allowance + " + window.bytesLabel(budget.reserveBytes) + " reserve" : "Provider must check space; no complete capacity estimate") + (budget.unknownSizes > 0 ? " · " + budget.unknownSizes + " sizes unknown" : "") + (budget.advisory ? ". Original allowance, not remaining bytes needed." : ". Allowances are estimates."); Layout.fillWidth: true; color: budget.known && !budget.fits ? window.accent : window.muted; font.pixelSize: 13 }
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
        implicitHeight: Math.max(108, card.contentItem.implicitHeight + 28) + (optionsPage ? 54 : 0)
        hoverEnabled: true
        bottomPadding: optionsPage ? 54 : 0
        ToolTip.visible: hovered && !!inventoryDetail
        ToolTip.delay: 700
        ToolTip.text: inventoryDetail
        background: Rectangle {
            radius: 14
            color: !card.navigation && card.selected ? window.tone("#2a1736") : (card.hovered || card.activeFocus ? window.tone("#2b1c3a") : window.tone("#1a1128"))
            border.width: card.activeFocus ? 3 : 1
            border.color: card.activeFocus ? window.cyan : (!card.navigation && card.selected ? window.tone("#c745a7") : window.tone("#493055"))
            Rectangle {
                visible: card.selected && !card.navigation
                width: 4; radius: 2; height: parent.height - 24
                anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter
                color: window.accent
            }
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
                TextLabel { text: card.heading; font.pixelSize: 16; font.weight: Font.DemiBold; Layout.fillWidth: true }
                TextLabel { text: card.detail; color: !card.navigation && card.selected ? window.tone("#e2c5e6") : window.muted; font.pixelSize: 13; Layout.fillWidth: true }
                TextLabel { visible: !!card.inventoryLabel; text: card.inventoryLabel; color: card.inventoryStatus === "UPDATE" ? window.accent : window.muted; font.pixelSize: 13; Layout.fillWidth: true }

                TextLabel { visible: !!card.requirement; text: "Included · required by " + card.requirement; color: window.cyan; font.pixelSize: 13; Layout.fillWidth: true }
                TextLabel { visible: card.navigation; text: card.selectedCount ? card.selectedCount + " selected · Browse" : "Browse individual options"; color: window.accent; font.pixelSize: 13 }
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
            visible: window.width >= 950
            Layout.preferredWidth: 200
            Layout.fillHeight: true; color: window.tone("#120b1d")
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 16; spacing: 8
                RowLayout {
                    Layout.fillWidth: true; Layout.topMargin: window.height < 620 ? 0 : 10; spacing: 10
                    Rectangle {
                        Layout.preferredWidth: 42; Layout.preferredHeight: 42; radius: 13; color: window.accent
                        Text { anchors.centerIn: parent; text: "W"; color: window.tone("#20091e"); font.pixelSize: 24; font.bold: true }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true; spacing: 1
                        TextLabel { text: "DECK"; font.pixelSize: 16; font.weight: Font.Bold; font.letterSpacing: 1.1 }
                        TextLabel { text: "WORKSTATION"; font.pixelSize: 10; font.weight: Font.DemiBold; font.letterSpacing: 1.3; color: window.muted }
                    }
                }
                TextLabel { visible: window.height >= 600; text: "Build your Deck, your way"; color: window.muted; font.pixelSize: 13; Layout.bottomMargin: window.height < 620 ? 4 : 16 }
                Repeater {
                    model: window.stageNames
                    delegate: AbstractButton {
                        id: nav
                        required property string modelData
                        required property int index
                        Layout.fillWidth: true; implicitHeight: window.height < 620 ? 48 : 58
                        enabled: window.loaded && !window.busy && !window.progress.running && (index !== 5 || window.saved)
                        onClicked: window.navigate(index)
                        background: Rectangle {
                            radius: 12; color: window.stage === nav.index ? window.tone("#35203f") : nav.hovered ? window.tone("#261735") : "transparent"
                            border.width: nav.activeFocus ? 2 : 0; border.color: window.cyan
                            Rectangle { visible: window.stage === nav.index; width: 3; height: parent.height - 16; radius: 2; anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter; color: window.accent }
                        }
                        contentItem: RowLayout {
                            spacing: 12
                            Text { Layout.leftMargin: 12; text: String(nav.index+1).padStart(2,"0"); color: window.stage === nav.index ? window.cyan : window.tone("#ac87be"); font.pixelSize: 13 }
                            ColumnLayout {
                                Layout.fillWidth: true; spacing: 4
                                TextLabel { text: nav.modelData; font.pixelSize: 14; font.weight: Font.DemiBold; color: window.stage === nav.index ? window.ink : window.muted; Layout.fillWidth: true }
                                TextLabel { text: window.stageHints[nav.index]; font.pixelSize: 10; color: window.muted; Layout.fillWidth: true; elide: Text.ElideRight; wrapMode: Text.NoWrap }
                            }
                        }
                    }
                }
                Item { Layout.fillHeight: true }
                Action {
                    id: paletteButton
                    Layout.fillWidth: true
                    text: "Appearance"
                    enabled: window.loaded && !window.busy && !window.progress.running
                    Accessible.name: "Theme and appearance: " + window.activePalette.name
                    onClicked: appearanceDialog.open()
                }
                Rectangle { visible: window.height >= 780; Layout.fillWidth: true; height: 1; color: window.tone("#402c4e") }
                TextLabel { visible: window.height >= 780; text: "BUILT FOR YOUR DECK"; font.pixelSize: 10; font.letterSpacing: 1.2; color: window.tone("#bda8ca"); Layout.topMargin: 14 }
                TextLabel { visible: window.height >= 780; text: "On-demand setup.\nYour choices stay yours."; color: window.muted; font.pixelSize: 13; Layout.topMargin: 4 }
            }
        }
        ColumnLayout {
            Layout.fillWidth: true; Layout.fillHeight: true
            Layout.margins: window.width < 950 ? 14 : 24; spacing: window.stage === 5 ? 8 : 12
            RowLayout {
                Layout.fillWidth: true
                ComboBox {
                    objectName: "compactNavigation"; visible: window.width < 950; model: window.stageNames; currentIndex: window.stage
                    implicitHeight: 44; Layout.preferredWidth: 205; enabled: !window.progress.running
                    Accessible.name: "Setup section"; onActivated: window.navigate(currentIndex)
                }
                Action { visible: window.width < 950; text: "Appearance"; enabled: !window.progress.running; onClicked: window.openAppearance() }
                TextLabel { visible: window.width >= 950; text: "SETUP / " + String(window.stage + 1).padStart(2, "0") + " OF 06"; font.pixelSize: 11; font.letterSpacing: 1.6; color: window.cyan }
                Item { Layout.fillWidth: true }
                Rectangle {
                    visible: window.width >= 950; Layout.preferredWidth: planCount.implicitWidth + 24; Layout.preferredHeight: 32
                    radius: 16; color: window.tone("#261735"); border.color: window.tone("#493055")
                    TextLabel { id: planCount; anchors.centerIn: parent; text: window.selectionCount() + " selected"; color: window.ink; font.pixelSize: 13; font.weight: Font.DemiBold }
                }
                Action { text: window.data.sudoReadiness && window.data.sudoReadiness.status !== "PASS" ? "Setup check" : window.inventoryPending ? "Checking Deck…" : "Deck status"; implicitHeight: 36; onClicked: statusDrawer.open() }
            }
            Rectangle {
                Layout.fillWidth: true; implicitHeight: window.stage === 5 ? 64 : window.height < 620 ? 92 : 110; radius: 18
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0.0; color: window.tone("#35203f") }
                    GradientStop { position: 1.0; color: window.tone("#1a1128") }
                }
                border.color: window.tone("#493055")
                ColumnLayout {
                    anchors.fill: parent; anchors.leftMargin: 22; anchors.rightMargin: 22; anchors.topMargin: 15; anchors.bottomMargin: 17; spacing: 4
                    TextLabel { visible: window.stage !== 5; text: window.stage === 5 ? "INSTALLATION" : window.detailPage ? "FINE TUNE YOUR SETUP" : "YOUR DECK · YOUR CHOICES"; color: window.cyan; font.pixelSize: 10; font.weight: Font.DemiBold; font.letterSpacing: 1.5 }
                    TextLabel { text: window.stage === 5 ? window.installTitle() : window.detailPage ? window.pageTitle(window.detailPage) : window.stageNames[window.stage]; font.pixelSize: window.stage === 5 ? 24 : window.width < 950 ? 26 : 30; font.weight: Font.Bold; Layout.fillWidth: true }
                    TextLabel { visible: window.stage !== 5; text: window.detailPage === "css" ? "Choose the CSS components you want to manage." : window.detailPage === "plugins" ? "Choose your Decky add-ons. CSS Loader has its own options." : window.detailPage ? "Choose only what you want. Nothing installs while browsing." : window.stageDescriptions[window.stage]; color: window.muted; font.pixelSize: 13; Layout.fillWidth: true }
                }
                Rectangle {
                    anchors.bottom: parent.bottom; anchors.left: parent.left; anchors.right: parent.right
                    height: 3; color: window.tone("#402c4e")
                    Rectangle { height: parent.height; width: parent.width * (window.stage + 1) / 6; color: window.accent }
                }
            }
            RowLayout {
                visible: !!window.detailPage || window.navigationStack.length > 0
                Layout.fillWidth: true
                Action { text: window.stage === 5 && window.progress.running ? "Installing…" : window.navigationStack.length && window.navigationStack[window.navigationStack.length-1].stage === 4 ? "‹ Return to review" : window.detailPage === "css" ? "‹ Decky plugins" : "‹ " + window.stageNames[window.stage]; onClicked: window.back() }
                TextLabel { Layout.fillWidth: true; text: window.detailPage === "plugins" ? "Choosing a plugin includes Decky Loader." : window.detailPage === "css" ? "Choosing a theme includes CSS Loader and Decky." : "Your edits stay in this plan."; color: window.muted; font.pixelSize: 13 }
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
                        Flow {
                            visible: window.stage === 5 && window.progress.running; Layout.fillWidth: true; spacing: 8
                            Action { text: window.progress.controls && window.progress.controls.pause ? "Continue queue" : "Pause after item"; enabled: !!window.progress.controls && !!window.progress.controls.available && !window.progress.controls.cancel; onClicked: window.controlQueue(window.progress.controls.pause ? "continue" : "pause") }
                            Action { text: window.progress.controls && window.progress.controls.cancel ? "Cancelling…" : "Cancel run"; enabled: !!window.progress.controls && !!window.progress.controls.available && !window.progress.controls.cancel; onClicked: { window.closeRequested = false; cancelRunDialog.open() } }
                        }
                        Action { text: "Force stop…"; visible: window.stage === 5 && !!window.progress.controls && !!window.progress.controls.forceAvailable; onClicked: forceStopDialog.open() }
                        TextLabel { visible: window.stage === 5 && !!window.progress.controls && (window.progress.controls.pause || window.progress.controls.cancel); text: window.progress.controls && window.progress.controls.cancel ? (window.progress.running ? "Cancellation requested. Waiting for the current provider to stop; unfinished work can be retried." : "Run cancelled. Completed installs are kept. Resume will verify and retry unfinished work.") : window.progress.queueStatus === "PAUSED" ? "Queue paused. No next item will start until you continue." : "Pause requested. The current item will finish before the queue pauses."; Layout.fillWidth: true; color: window.accent; font.pixelSize: 13 }

            ScrollView {
                id: scroll; objectName: "setupScroll"
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
                                        Label { text: (window.paletteId === modelData.id ? "✓ " : "") + modelData.name; color: modelData.colors["#f8e7ff"]; font.pixelSize: 13 }
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
                                        TextLabel { text: "Store"; font.pixelSize: 13 }
                                        TextLabel { text: "Settings"; font.pixelSize: 13 }
                                    }
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true; Layout.fillHeight: true
                                    TextLabel { text: "QUICK ACCESS"; font.pixelSize: 10; color: window.cyan }
                                    TextLabel { text: "Volume"; font.pixelSize: 13 }
                                    Rectangle { Layout.fillWidth: true; height: 5; radius: 3; color: window.accent }
                                    Item { Layout.fillHeight: true }
                                    TextLabel { text: "KEYBOARD"; font.pixelSize: 10; color: window.cyan }
                                    RowLayout {
                                        Layout.fillWidth: true; spacing: 5
                                        Repeater { model: ["Q", "W", "E", "R", "T"]
                                            delegate: Rectangle { required property string modelData; Layout.fillWidth: true; height: 38; radius: 6; color: window.tone("#35203f"); TextLabel { anchors.centerIn: parent; text: modelData; font.pixelSize: 13 } }
                                        }
                                    }
                                }
                            }
                        }
                        TextLabel { text: "Illustration of the selected colors, not a Game Mode screenshot. Actual layouts depend on the CSS components you select. Use the theme authors’ previews to compare layouts."; Layout.fillWidth: true; color: window.muted; font.pixelSize: 13 }
                        Action { text: "Open CSS Loader theme previews ↗"; onClicked: Qt.openUrlExternally("https://deckthemes.com/") }
                        }
                    }
                    Repeater {
                        model: window.currentSections()
                        delegate: ColumnLayout {
                            required property var modelData
                            Layout.fillWidth: true; spacing: 10
                            Layout.topMargin: 10
                            RowLayout {
                                visible: !window.detailPage
                                Layout.fillWidth: true
                                Rectangle { Layout.preferredWidth: 4; Layout.preferredHeight: 22; radius: 2; color: window.cyan }
                                TextLabel { text: modelData.title; color: window.ink; font.pixelSize: 19; font.weight: Font.Bold; Layout.fillWidth: true; Layout.leftMargin: 6 }
                                TextLabel { text: window.sectionCount(modelData) + " / " + modelData.items.length + " selected"; color: window.muted; font.pixelSize: 13 }
                            }
                            TextLabel { visible: !window.detailPage; text: modelData.description; color: window.muted; font.pixelSize: 13; Layout.fillWidth: true }
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
                        font.pixelSize: 13; color: window.muted; Layout.topMargin: 4
                    }
                    ColumnLayout {
                        visible: window.stage < 4 && window.dependencyNotes().length > 0
                        Layout.fillWidth: true
                        TextLabel { text: "Included with your choices"; color: window.cyan; font.pixelSize: 13; font.weight: Font.DemiBold }
                        Repeater {
                            model: window.dependencyNotes()
                            delegate: TextLabel { required property string modelData; text: "↳ " + modelData; color: window.muted; font.pixelSize: 13; Layout.fillWidth: true }
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
                                TextLabel { text: window.cssPalettePlanText(); Layout.fillWidth: true; color: window.cyan; font.pixelSize: 14 }
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
                                            TextLabel { text: modelData.summary + "\n" + window.inventoryFor(modelData).label; Layout.fillWidth: true; Layout.leftMargin: 20; color: window.muted; font.pixelSize: 13 }
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
                        TextLabel { visible: (window.installPreview.unknownSizes || 0) > 0; text: window.installPreview.unknownSizes + " items have unknown sizes. The known allowance is not a complete download estimate."; color: window.accent; Layout.fillWidth: true; font.pixelSize: 13 }
                        TextLabel { visible: !!window.installPreview.sizeNote; text: window.installPreview.sizeNote || ""; Layout.fillWidth: true; font.pixelSize: 13; color: window.muted }
                        Repeater {
                            model: window.installPreview.volumes || []
                            delegate: SpaceBudget { required property var modelData; Layout.fillWidth: true; destination: modelData.path || "Destination"; freeBytes: modelData.freeBytes; allowanceBytes: modelData.requiredBytes === undefined ? null : Math.max(0,modelData.requiredBytes-(modelData.reserveBytes || 0)); reserveBytes: modelData.reserveBytes; unknownSizes: window.installPreview.unknownSizes || 0 }
                        }
                        Repeater {
                            model: window.changeGroups()
                            delegate: ColumnLayout {
                                required property var modelData
                                Layout.fillWidth: true; spacing: 8
                                TextLabel { text: modelData.title + " (" + modelData.items.length + ")"; font.bold: true; Layout.fillWidth: true }
                                Repeater {
                                    model: modelData.items
                                    delegate: TextLabel { required property var modelData; Layout.fillWidth: true; font.pixelSize: 13; color: window.muted; text: modelData.name + " · " + modelData.updateCheck + "\nDownload estimate if needed: " + window.bytesLabel(modelData.downloadBytes) + "\n" + (modelData.reviewNotes || []).join("\n") }
                                }
                            }
                        }
                        TextLabel { text: "WHAT HAPPENS NEXT"; font.pixelSize: 11; color: window.muted; font.letterSpacing: 1.2; Layout.topMargin: 6 }
                        TextLabel { text: "1. Install selections with live output here.\n2. Review results and open sign-in or pairing for the apps that need it.\n3. Interactive vendor tools are clearly marked before opening a terminal."; Layout.fillWidth: true; font.pixelSize: 13; color: window.muted }

                    }
                    ColumnLayout {
                        visible: window.stage === 5; Layout.fillWidth: true; spacing: 12

                        TextLabel {
                            visible: !!window.progress.operation && !!window.progress.summary
                            text: (window.progress.summary ? window.progress.summary.done + " of " + window.progress.summary.total + " verified in this installation record" + (window.progress.summary.attention ? " · " + window.progress.summary.attention + " need attention" : "") : "")
                            Layout.fillWidth: true; font.pixelSize: 13; color: window.cyan
                        }
                        TextLabel { visible: !!window.progress.githubLimit; text: window.githubLimitText(); Layout.fillWidth: true; color: window.cyan; font.pixelSize: 13 }
                        TextLabel { visible: !!window.progress.failureMessage; text: window.progress.failureMessage || ""; Layout.fillWidth: true; color: window.accent; font.pixelSize: 13 }
                        Repeater {
                            model: window.installRows().filter(function(item) { return item.status === "RUNNING" })
                            delegate: installationRowDelegate
                        }
                        Rectangle {
                            id: consolePanel; objectName: "consolePanel"
                            visible: !!window.progress.operation
                            Layout.fillWidth: true; implicitHeight: consoleColumn.implicitHeight + 20
                            radius: 10; color: window.tone("#150d21"); border.color: window.tone("#533960")
                            ColumnLayout {
                                id: consoleColumn; anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 10; spacing: 6
                                Flow {
                                    Layout.fillWidth: true; spacing: 6
                                    Action { objectName: "consoleAllSteps"; text: window.consoleItem ? "All steps" : "Install output"; implicitHeight: 44; onClicked: window.closeLog() }
                                    Action { text: window.followConsole ? "Following latest" : "Follow latest"; implicitHeight: 44; onClicked: { window.followConsole = !window.followConsole; if (window.followConsole) { if (window.consoleItem) window.refreshLog(); else window.displayedConsole = window.consoleOutput.text || "" } } }
                                    Action { objectName: "consoleFindErrors"; text: window.errorsOnly ? "Show all output" : "Find errors"; implicitHeight: 44; onClicked: window.errorsOnly = !window.errorsOnly }
                                    Action { text: "Copy"; implicitWidth: 70; implicitHeight: 44; onClicked: { consoleText.selectAll(); consoleText.copy(); consoleText.deselect() } }
                                }
                                TextLabel { text: window.consoleItem ? "Item: " + window.consoleItem : "All modules · latest 64 KiB"; Layout.fillWidth: true; color: window.cyan; font.pixelSize: 13 }
                                ScrollView {
                                    id: consoleScroll; Layout.fillWidth: true; Layout.preferredHeight: window.height < 620 ? 110 : 150; clip: true
                                    ScrollBar.vertical.policy: ScrollBar.AlwaysOn
                                    TextArea {
                                        id: consoleText; objectName: "inlineConsole"
                                        text: window.displayedOutput(); readOnly: true; selectByMouse: true; activeFocusOnTab: true
                                        Accessible.name: "Installer output. " + (window.consoleItem || "All steps")
                                        textFormat: TextEdit.PlainText; wrapMode: TextEdit.WrapAnywhere
                                        color: window.ink; font.family: "monospace"; font.pixelSize: 13; background: null
                                        onTextChanged: { if (window.followConsole) cursorPosition = length }
                                    }
                                }
                                TextLabel { visible: !window.followConsole; text: "Viewing history · collection continues in the background"; color: window.muted; Layout.fillWidth: true; font.pixelSize: 13 }
                                TextLabel { visible: !!window.consoleOutput.logDirectory; text: "Durable logs: " + (window.consoleOutput.logDirectory || ""); Layout.fillWidth: true; color: window.muted; font.pixelSize: 13 }
                            }
                        }
                        Rectangle {
                            visible: !!window.progress.operation && (window.progress.running || (window.progress.activity || []).length > 0)
                            Layout.fillWidth: true; implicitHeight: activityLayout.implicitHeight + 24; radius: 10; color: window.tone("#150d21")
                            ColumnLayout {
                                id: activityLayout; objectName: "activityPanel"; anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 12; spacing: 8
                                TextLabel { text: "DECK ACTIVITY · includes other apps"; font.pixelSize: 11; color: window.muted; Layout.fillWidth: true }
                                TextLabel { text: window.networkLabel(); Layout.fillWidth: true; color: window.progress.network && window.progress.network.status === "OFFLINE" ? window.accent : window.muted; font.pixelSize: 13 }
                                GridLayout {
                                    Layout.fillWidth: true; columns: 2; columnSpacing: 18
                                    ActivityChart { Layout.fillWidth: true; title: "NETWORK RECEIVE"; keys: ["network"]; colors: [window.accent]; samples: window.progress.activity || []; rates: window.rateLabel("network") }
                                    ActivityChart { Layout.fillWidth: true; title: "DISK READ / WRITE"; keys: ["read", "write"]; colors: [window.cyan, window.violet]; samples: window.progress.activity || []; rates: window.rateLabel("read") + " / " + window.rateLabel("write") }
                                }
                                TextLabel { text: "Separate scales · missing samples leave gaps · 0 means no measured traffic"; color: window.muted; font.pixelSize: 13; Layout.fillWidth: true }
                                SpaceBudget { visible: !!window.progress.storage; Layout.fillWidth: true; destination: (window.progress.storage || {}).path || ""; freeBytes: (window.progress.storage || {}).freeBytes; allowanceBytes: (window.progress.storage || {}).allowanceBytes; reserveBytes: (window.progress.storage || {}).reserveBytes; advisory: true }

                            }
                        }
                        Action { text: "Show installation results"; visible: window.finishItems.length > 0; onClicked: window.finishItems = [] }
                        Action { visible: !!window.progress.operation && !window.progress.running; text: "Recheck readiness"; enabled: !window.busy && !window.progress.running; onClicked: window.checkFinish() }
                        TextLabel { visible: !window.progress.operation; text: window.selectionCount() + " optional choices saved. Start when you're ready; live output and results will appear here."; Layout.fillWidth: true; color: window.muted }
                        Repeater {
                            model: window.finishItems
                            delegate: ColumnLayout {
                                required property var modelData
                                property bool expanded: window.expandedResult === "finish:" + modelData.key
                                Layout.fillWidth: true; spacing: 8
                                AbstractButton {
                                    Layout.fillWidth: true; implicitHeight: 48
                                    Accessible.name: modelData.name + ". " + modelData.status + ". Show setup actions."
                                    onClicked: window.expandedResult = parent.expanded ? "" : "finish:" + modelData.key
                                    background: Rectangle { color: parent.hovered || parent.activeFocus ? window.tone("#1a1128") : "transparent"; radius: 6 }
                                    contentItem: RowLayout {
                                        TextLabel { text: modelData.name; Layout.fillWidth: true; font.pixelSize: 14 }
                                        TextLabel { text: modelData.status + "  ›"; color: window.cyan; font.pixelSize: 13 }
                                    }
                                }
                                TextLabel { visible: parent.expanded; text: modelData.note; Layout.fillWidth: true; color: window.muted; font.pixelSize: 13 }
                                Flow {
                                    visible: parent.expanded; Layout.fillWidth: true; spacing: 8
                                    Action { visible: modelData.canLaunch; text: modelData.terminalRequired ? "Open interactive terminal…" : modelData.status === "Ready" ? "Open" : "Open setup / sign-in"; enabled: !window.busy && !window.progress.running; onClicked: window.finishAction(modelData.key, "launch") }
                                    Action { visible: modelData.canConfirm && modelData.status !== "Ready"; text: modelData.followup === "pairing" ? "I've paired it" : modelData.followup === "setup" ? "I've completed setup" : "I've signed in"; enabled: !window.busy && !window.progress.running; onClicked: window.finishAction(modelData.key, "confirm") }
                                }
                                Rectangle { Layout.fillWidth: true; height: 1; color: window.tone("#402c4e") }
                            }
                        }
                        RowLayout {
                            visible: !!window.progress.operation && !window.finishItems.length
                            Layout.fillWidth: true
                            TextLabel { text: "QUEUE · select an item for details"; Layout.fillWidth: true; color: window.muted; font.pixelSize: 11; font.letterSpacing: .5 }
                            CheckBox { text: "Completed (" + (window.progress.summary ? window.progress.summary.done : 0) + ")"; checked: window.showCompleted; onToggled: window.showCompleted = checked }
                        }
                        Repeater {
                            model: window.installRows().filter(function(item) { return item.status !== "RUNNING" })
                            delegate: installationRowDelegate
                        }

                    }
                }
            }
            Rectangle { Layout.fillWidth: true; height: 1; color: window.tone("#402c4e") }
            RowLayout {
                Layout.fillWidth: true; spacing: 10
                Action { text: "Back"; visible: !!window.detailPage || (window.stage > 0 && window.stage < 5); enabled: !window.busy; onClicked: window.back() }
                TextLabel { visible: window.stage < 4; text: "Your choices save at review.\nNothing installs yet."; font.pixelSize: 13; color: window.muted; Layout.fillWidth: true }
                Item { visible: window.stage >= 4; Layout.fillWidth: true }
                Action { text: "Close"; visible: window.stage === 5; enabled: !window.busy; onClicked: window.close() }
                Action { text: "Save for later"; visible: window.stage === 4 && !window.data.planOnly; enabled: !window.busy; onClicked: window.savePlan(false) }
                Action {
                    objectName: "primaryAction"
                    primary: true
                    text: window.stage === 5 && window.progress.running ? "Installing…" : window.navigationStack.length && window.navigationStack[window.navigationStack.length-1].stage === 4 ? "Return to review →" : window.detailPage ? "Done choosing →" : window.stage < 3 ? "Continue →" : (window.stage === 3 ? "Review setup →" : (window.stage === 4 ? (window.data.planOnly ? "Save & continue" : window.previewPending ? "Checking changes…" : !window.installPreview.items || window.installPreview.error ? "Review changes" : "Save & install") : (window.progress.operation === "install" && window.progress.exitCode === 0 ? (window.finishItems.length ? "Finish" : "Review readiness") : window.progress.operation ? "Resume installation" : "Install selections")))
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
                        else if (window.progress.operation === "install" && window.progress.exitCode === 0) { if (window.finishItems.length) window.close(); else window.checkFinish() }
                        else window.startOperation(window.progress.resumable ? "resume" : "install")
                    }
                }
            }
        }
    }
    }
    Component {
        id: installationRowDelegate
        ColumnLayout {
            id: resultRow
            required property var modelData
            property bool expanded: window.expandedResult === modelData.id
            Layout.fillWidth: true; spacing: 6
            TextLabel { visible: modelData.status !== "RUNNING" && !!modelData.queueHeading; text: modelData.queueHeading || ""; color: window.cyan; font.pixelSize: 13; font.letterSpacing: 1; Layout.topMargin: 8; Layout.fillWidth: true }
            AbstractButton {
                objectName: "installationResultRow"
                Layout.fillWidth: true; implicitHeight: 48
                Accessible.name: (modelData.name || modelData.id) + ". " + (modelData.resultLabel || window.statusLabel(modelData.status)) + ". Show details and actions."
                onClicked: window.expandedResult = resultRow.expanded ? "" : modelData.id
                background: Rectangle { color: parent.hovered || parent.activeFocus ? window.tone("#1a1128") : "transparent"; radius: 6 }
                contentItem: RowLayout {
                    spacing: 12
                    TextLabel { text: modelData.name || modelData.id; Layout.fillWidth: true; font.pixelSize: 14 }
                    TextLabel { text: (modelData.resultLabel || window.statusLabel(modelData.status)) + (resultRow.expanded ? "  ⌄" : "  ›"); color: window.stateColor(modelData.status); font.pixelSize: 13 }
                }
            }
            TextLabel { visible: resultRow.expanded && !!modelData.message; text: modelData.message || ""; color: window.muted; font.pixelSize: 13; Layout.fillWidth: true }
            TextLabel { visible: resultRow.expanded && !!modelData.nextAction; text: modelData.nextAction || ""; color: window.cyan; font.pixelSize: 13; Layout.fillWidth: true }
            TextLabel { visible: !!modelData.activityNotice; text: modelData.activityNotice || ""; color: window.accent; font.pixelSize: 13; Layout.fillWidth: true }
            TextLabel { visible: modelData.status === "RUNNING"; text: (modelData.phase || "Working") + " · " + window.elapsedLabel(modelData.elapsedSeconds) + (modelData.downloaded !== null && modelData.downloaded !== undefined ? " · " + window.bytesLabel(modelData.downloaded) + (modelData.total > 0 ? " / " + window.bytesLabel(modelData.total) + " (" + Math.min(100,Math.floor(modelData.downloaded/modelData.total*100)) + "%)" : " · total unknown") : " · progress total unknown"); color: window.muted; font.pixelSize: 13; Layout.fillWidth: true }
            ProgressBar { visible: modelData.status === "RUNNING"; Layout.fillWidth: true; implicitHeight: 4; indeterminate: !(modelData.total > 0); value: modelData.total > 0 ? Math.min(1, (modelData.downloaded || 0) / modelData.total) : 0; Accessible.name: "Progress for " + modelData.name }
            Flow {
                visible: resultRow.expanded; Layout.fillWidth: true; spacing: 8
                Action { objectName: "viewInstallLog"; text: "Details"; visible: !!modelData.hasLog; onClicked: window.showLog(modelData.id) }
                Action { text: "Retry item"; visible: ["FAILED", "INTERRUPTED", "NEEDS_SETUP", "BLOCKED"].indexOf(modelData.status) >= 0; enabled: !window.progress.running && !window.busy; onClicked: window.startOperation("retry", modelData.id) }
                Action { text: "Continue in terminal"; visible: modelData.terminalRequired === true && ["FAILED", "NEEDS_SETUP"].indexOf(modelData.status) >= 0; enabled: !window.progress.running && !window.busy; onClicked: window.startOperation("interactive", modelData.id) }
            }
            Rectangle { Layout.fillWidth: true; height: 1; color: window.tone("#402c4e") }
        }
    }

    Dialog {
        id: cancelRunDialog
        objectName: "cancelRunDialog"
        title: window.closeRequested ? "Cancel installation and close?" : "Cancel this installation run?"
        anchors.centerIn: parent; width: Math.min(480, window.width-40); modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel
        contentItem: TextLabel { text: "The current provider will be interrupted. Completed items are kept; unfinished items may need repair or retry. This does not uninstall anything."; wrapMode: Text.WordWrap }
        onAccepted: { window.closeAfterCancel = window.closeRequested; window.controlQueue("cancel") }
        onRejected: window.closeRequested = false
    }
    Dialog {
        id: forceStopDialog
        title: "Force stop the current provider?"
        anchors.centerIn: parent; width: Math.min(480, window.width-40); modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel
        contentItem: TextLabel { text: "The provider has not stopped after cancellation. Force stop ends this run immediately. The unfinished item may need repair; completed installs are kept."; wrapMode: Text.WordWrap }
        onAccepted: window.controlQueue("force")
    }
    Dialog {
        id: externalCloseDialog
        title: "Close this viewer?"
        anchors.centerIn: parent; width: Math.min(480, window.width-40); modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel
        contentItem: TextLabel { text: "This installation is controlled by another window or terminal. Closing this viewer will leave it running. Cancel it from the window that started it."; wrapMode: Text.WordWrap }
        onAccepted: { window.allowClose = true; window.close() }
    }
    Drawer {
        id: statusDrawer
        edge: Qt.RightEdge; width: Math.min(430, window.width - 32); height: window.height
        background: Rectangle { color: window.tone("#150d21") }
        ScrollView { anchors.fill: parent; anchors.margins: 20; clip: true; contentWidth: availableWidth
            ColumnLayout { width: parent.width; spacing: 16
                TextLabel { text: "This Deck"; font.pixelSize: 26; font.bold: true; Layout.fillWidth: true }
                TextLabel { text: window.inventoryPending ? "Checking installed tools and available updates… " + (window.deckInventory.completed || 0) + "/" + (window.deckInventory.total || 0) : "Checks are separate from your selections. Nothing updates automatically."; Layout.fillWidth: true; color: window.muted }
                Flow { Layout.fillWidth: true; spacing: 8
                    Action { text: "Refresh status"; enabled: !window.inventoryPending && !window.progress.running; onClicked: window.refreshInventory() }
                    Action { text: "Select updates"; enabled: !window.inventoryPending && !window.progress.running && !window.busy; onClicked: { window.selectUpdates(); statusDrawer.close() } }
                }
                TextLabel { text: "Administrator access"; font.bold: true; Layout.fillWidth: true }
                TextLabel { text: "Workstation " + (window.data.runtimeVersion || "unknown"); Layout.fillWidth: true; color: window.muted }
                TextLabel { text: window.data.sudoReadiness ? window.data.sudoReadiness.message : "Not checked"; Layout.fillWidth: true; color: window.muted; font.pixelSize: 13 }
                Action { text: "Recheck password"; enabled: !window.progress.running; onClicked: window.request("sudo-readiness", null, function(result) { var next = Object.assign({}, window.data); next.sudoReadiness = result; window.data = next }) }
                TextLabel { text: "Installed tools & updates"; font.bold: true; Layout.fillWidth: true }
                Repeater { model: Object.keys(window.deckInventory.items || {})
                    delegate: TextLabel { required property string modelData; property var check: window.deckInventory.items[modelData]; text: (check.name || modelData) + " · " + check.label + (check.note ? "\n" + check.note : "") + (check.installedVersion && check.availableVersion ? "\n" + check.installedVersion + " → " + check.availableVersion : ""); Layout.fillWidth: true; color: check.status === "UPDATE" ? window.accent : window.muted; font.pixelSize: 13 }
                }
                Action { text: "Close"; onClicked: statusDrawer.close() }
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
                TextLabel { text: "Choose a palette for your workstation. Installed supported Game Mode themes follow automatically when you apply changes."; Layout.fillWidth: true; color: window.muted }
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
                TextLabel { text: window.cssPalettePlanText(); Layout.fillWidth: true; color: window.cyan; font.pixelSize: 13 }
                TextLabel { text: "Saved Game Mode status: " + ((window.progress.cssPalette || window.data.cssPalette || {}).message || "Not checked"); Layout.fillWidth: true; color: window.muted; font.pixelSize: 13 }
                Action { visible: !!window.cssSelectionError(); text: "Turn Game Mode theming off"; onClicked: window.setAppearance("css", false) }
                Action { text: "Install additional Game Mode themes"; enabled: !window.progress.running && !window.busy; onClicked: { window.closeAppearance(); window.browse("css") } }
                TextLabel { text: "Appearance preferences"; font.weight: Font.DemiBold; Layout.fillWidth: true }
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
                        TextLabel { text: modelData.summary + (modelData.id === "css" && window.cssSelectionError() ? " · Selection required" : window.appearanceTargetSelected(modelData.id) ? "" : " · Tool not selected; preference only"); Layout.fillWidth: true; Layout.leftMargin: 30; font.pixelSize: 13; color: window.muted }
                    }
                }
                TextLabel { text: "These switches never install extra software. Off keeps the current appearance; it does not reset it. Changes apply when you save and install. Personal Ghostty configuration is preserved; its theme must reference deckctl-bubble-gum-rave to follow this palette. Unsupported Decky plugins keep their own colors."; Layout.fillWidth: true; color: window.muted; font.pixelSize: 13 }
            }
        }
    }
    Timer { interval: 1500; repeat: true; running: window.stage === 5 && !!window.consoleItem && window.followConsole && window.progress.running; onTriggered: window.refreshLog() }
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
