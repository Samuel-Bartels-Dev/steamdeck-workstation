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
        xhr.timeout = 10000
        if (payload !== null) xhr.setRequestHeader("Content-Type", "application/json")
        xhr.onreadystatechange = function() {
            if (xhr.readyState !== XMLHttpRequest.DONE) return
            try {
                var result = JSON.parse(xhr.responseText)
                if (xhr.status !== 200) throw new Error(result.error || "Setup could not complete this action.")
                callback(result)
            } catch (e) { busy = false; problem = e.message || "Setup connection lost. Close and reopen this window." }
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
    function markChanged() { saved = false; dirty = true; notice = ""; problem = "" }
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
        return ({PENDING:"Waiting",RUNNING:"Installing",READY:"Ready",OPTIONAL:"Ready",CONFIG_REQUIRED:"Needs setup",NOT_INSTALLED:"Not installed",DEGRADED:"Needs attention",FAILED:"Failed"})[value] || value
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
        busy = true; problem = ""
        var components = {}
        Object.keys(selectedComponents).forEach(function(key) { components[key] = pageValues(key).slice() })
        request("save", {modules: chosen, apps: selectedApps, launchers: pageValues("launchers"), plugins: pageValues("plugins"), css: pageValues("css"), components: components, palette: paletteId}, function(result) {
            saved = true; dirty = false; busy = false; notice = "Plan saved. You can close this window or install when ready."
            if (install) startOperation("install")
            else if (data.planOnly) window.close()
        })
    }
    function startOperation(name) {
        busy = true; problem = ""
        request("start", {operation: name}, function(result) {
            progress = result; stage = 5; busy = false
        })
    }
    function stateColor(status) {
        if (status === "READY" || status === "OPTIONAL") return accent
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
            data = result; paletteId = result.palette; selectedComponents = result.selectedComponents; selectedCss = result.selectedCss.slice(); selectedLaunchers = result.selectedLaunchers.slice(); selectedPlugins = result.selectedPlugins.slice(); chosen = result.modules.slice(); selectedApps = result.selectedApps.slice(); loaded = true
            if (!result.hasSavedPlan) { preset(false); dirty = false; notice = "Start with only what you need. Nothing installs until you review and confirm." }
        })
    }
    Timer {
        interval: 1500; running: window.loaded && window.stage === 5; repeat: true
        onTriggered: window.request("progress", null, function(result) { window.progress = result })
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
                    text: "Theme palette ▾"
                    enabled: window.loaded
                    Accessible.name: "Theme palette for CSS Loader: " + window.activePalette.name
                    onClicked: paletteMenu.popup()
                    Menu {
                        id: paletteMenu
                        y: -height
                        Repeater {
                            model: window.paletteOptions
                            delegate: MenuItem {
                                required property var modelData
                                text: modelData.name
                                checkable: true
                                checked: window.paletteId === modelData.id
                                onTriggered: window.choosePalette(modelData.id)
                            }
                        }
                    }
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
                Action { text: window.navigationStack.length && window.navigationStack[window.navigationStack.length-1].stage === 4 ? "‹ Return to review" : window.detailPage === "css" ? "‹ Decky plugins" : "‹ " + window.stageNames[window.stage]; onClicked: window.back() }
                TextLabel { Layout.fillWidth: true; text: window.detailPage === "plugins" ? "Choosing a plugin includes Decky Loader." : window.detailPage === "css" ? "Choosing a theme includes CSS Loader and Decky." : "Your edits stay in this plan."; color: window.muted; font.pixelSize: 12 }
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
                        MenuItem { text: "Load full preset…"; onTriggered: { window.pendingPreset = true; presetDialog.open() } }
                        MenuItem { text: "Clear all choices…"; onTriggered: { window.pendingPreset = false; presetDialog.open() } }
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
            ScrollView {
                id: scroll
                Layout.fillWidth: true; Layout.fillHeight: true
                clip: true; contentWidth: availableWidth
                ScrollBar.vertical.policy: ScrollBar.AsNeeded
                ScrollBar.vertical.active: true
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                ColumnLayout {
                    width: scroll.availableWidth; spacing: 14
                    TextLabel {
                        visible: window.detailPage === "css" || window.detailPage === "plugins"
                        text: "Theme palette: " + window.activePalette.name + ". Change it with Theme palette in the sidebar. Colors apply during installation to supported CSS Loader controls; plugins without color settings keep their own appearance."
                        color: window.muted; font.pixelSize: 13; Layout.fillWidth: true
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
                                TextLabel { visible: window.pageValues("css").length > 0; text: "Theme palette: " + window.activePalette.name + " · for selected CSS Loader color controls"; Layout.fillWidth: true; color: window.cyan; font.pixelSize: 14 }
                            }
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
                                            TextLabel { text: modelData.summary; Layout.fillWidth: true; Layout.leftMargin: 20; color: window.muted; font.pixelSize: 12 }
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
                        TextLabel { text: "WHAT HAPPENS NEXT"; font.pixelSize: 11; color: window.muted; font.letterSpacing: 1.2; Layout.topMargin: 6 }
                        TextLabel { text: "1. Download and install your selections.\n2. Complete selected vendor setup, sign-in and pairing in Konsole.\n3. Return here to review anything that still needs attention."; Layout.fillWidth: true; font.pixelSize: 13; color: window.muted }

                    }
                    ColumnLayout {
                        visible: window.stage === 5; Layout.fillWidth: true; spacing: 12
                        TextLabel { text: window.installTitle(); font.pixelSize: 21; font.weight: Font.DemiBold }
                        TextLabel { text: window.progress.running ? "Use the Konsole window for installer prompts. Keep this window open to follow results." : window.progress.operation && window.progress.exitCode !== 0 ? "The operation ended with exit code " + window.progress.exitCode + ". Check its Konsole output, then retry. Completed installs are reused." : "Results are grouped by setup area. Continue with sign-in and pairing for selected apps that need it."; Layout.fillWidth: true; color: window.muted; font.pixelSize: 13 }
                        BusyIndicator { running: window.progress.running; visible: running; implicitWidth: 38; implicitHeight: 38 }
                        Repeater {
                            model: window.progress.modules
                            delegate: Rectangle {
                                required property var modelData
                                Layout.fillWidth: true; implicitHeight: resultColumn.implicitHeight + 26
                                radius: 10; color: window.tone("#1a1128")
                                ColumnLayout {
                                    id: resultColumn; anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 13; spacing: 5
                                    RowLayout {
                                        Layout.fillWidth: true
                                        TextLabel { text: window.featureNames()[modelData.id] || modelData.id; Layout.fillWidth: true; font.pixelSize: 14 }
                                        TextLabel { text: window.statusLabel(modelData.status); color: window.stateColor(modelData.status); font.pixelSize: 12 }
                                    }
                                    TextLabel { visible: !!modelData.message; text: modelData.message || ""; color: window.muted; font.pixelSize: 12; Layout.fillWidth: true }
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
                    text: window.navigationStack.length && window.navigationStack[window.navigationStack.length-1].stage === 4 ? "Return to review →" : window.detailPage ? "Done choosing →" : window.stage < 3 ? "Continue →" : (window.stage === 3 ? "Review setup →" : (window.stage === 4 ? (window.data.planOnly ? "Save & continue" : "Save & install") : (window.progress.operation === "install" && window.progress.exitCode === 0 ? "Continue setup" : window.progress.operation === "accounts" && window.progress.exitCode === 0 ? "Finish" : window.progress.operation === "accounts" ? "Retry setup" : window.progress.operation ? "Retry installation" : "Install selections")))
                    enabled: window.loaded && !window.busy && !window.progress.running && (window.stage !== 5 || !window.data.planOnly)
                    onClicked: {
                        if (window.detailPage || window.navigationStack.length) window.back()
                        else if (window.stage < 4) window.navigate(window.stage + 1)
                        else if (window.stage === 4) window.savePlan(!window.data.planOnly)
                        else if (window.progress.operation === "install" && window.progress.exitCode === 0) window.startOperation("accounts")
                        else if (window.progress.operation === "accounts" && window.progress.exitCode === 0) window.close()
                        else window.startOperation(window.progress.operation === "accounts" ? "accounts" : "install")
                    }
                }
            }
        }
    }
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
