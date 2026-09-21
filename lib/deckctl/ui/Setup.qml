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
    color: "#10161f"
    palette.window: "#182330"
    palette.windowText: ink
    palette.text: ink
    palette.button: "#263647"
    palette.buttonText: ink
    palette.base: "#15212e"
    palette.highlight: accent
    font.family: "Noto Sans"
    font.pixelSize: 15

    readonly property color ink: "#eef4f8"
    readonly property color muted: "#9caebe"
    readonly property color accent: "#68e0bf"
    property var data: ({groups: [], apps: [], modules: [], selectedApps: [], dependencies: {}, defaults: []})
    property string detailPage: ""
    property string searchText: ""
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
    readonly property var stageNames: ["Gaming", "Desktop apps", "Coding & work", "Remote & storage", "Review", "Install & finish"]
    readonly property var stageHints: ["Launchers & appearance", "Everyday apps", "Editors & AI tools", "Streaming & backups", "Check your selections", "Setup & sign-in"]
    readonly property var groupStages: [0, 2, 3]
    readonly property var stageGroups: [0, -1, 1, 2]
    readonly property var stageDescriptions: [
        "Choose game launchers, controller tools and Game Mode appearance.",
        "Pick the apps you use for browsing, chat, editing and media.",
        "Build a workspace around the tools you actually use. Each tool is optional.",
        "Connect to other devices, watch streaming services and protect your files.",
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
    function browse(page) { if (page === "desktop-apps") { stage = 1; page = "" }; detailPage = page; searchText = ""; notice = ""; problem = "" }
    function back() {
        if (detailPage) browse(detailPage === "css" ? "plugins" : "")
        else if (stage > 0) stage--
    }
    function categoryPage(key) {
        if (key === "utilities") return "desktop-apps"
        if (key === "gaming") return "launchers"
        if (key !== "ai-workspace" && data.components && data.components[key]) return key
        return ""
    }
    function pageTitle(page) {
        if (page === "launchers") return "Game launchers"
        if (page === "plugins") return "Decky plugins"
        if (page === "css") return "CSS Loader components"
        return featureNames()[page] || page
    }
    function currentItems() {
        var items = detailPage ? pageItems(detailPage) : stage === 1 ? data.apps : stage < 4 ? (data.groups[stageGroups[stage]] || {modules:[]}).modules : []
        var query = searchText.trim().toLowerCase()
        return items.filter(function(x) { return !query || (x.name + " " + x.summary).toLowerCase().indexOf(query) >= 0 })
    }
    function dependencyNotes() {
        var notes = []
        if (chosen.indexOf("ai-workspace") >= 0) {
            if (pageValues("terminal").indexOf("opencode") < 0) notes.push("OpenCode — required by AI workspace")
            if ((pageValues("ai-workspace").indexOf("model") >= 0 || pageValues("ai-workspace").indexOf("model-7b") >= 0) && pageValues("ai-workspace").indexOf("ollama") < 0) notes.push("Ollama — required by the local model")
        }
        if (pageValues("workspace").length || pageValues("media").length) notes.push("Google Chrome — shared by your selected web apps")
        return notes
    }
    function reviewSections() {
        if (!loaded) return []
        var sections = []
        function add(title, page, items, ids, targetStage) {
            var selected = items.filter(function(x) { return ids.indexOf(x.id) >= 0 })
            if (selected.length) sections.push({title:title, page:page, items:selected, targetStage:targetStage})
        }
        data.groups.forEach(function(group, index) {
            var atomic = group.modules.filter(function(x) { return !categoryPage(x.id) })
            add(group.title, "", atomic, chosen, groupStages[index])
            group.modules.forEach(function(m) {
                var page = categoryPage(m.id)
                if (page && page !== "desktop-apps") add(m.name, page, pageItems(page), pageValues(page), groupStages[index])
                if (m.id === "decky") {
                    add("Decky › Plugins", "plugins", pageItems("plugins"), pageValues("plugins"), 0)
                    add("Decky › CSS Loader components", "css", pageItems("css"), pageValues("css"), 0)
                }
            })
        })
        add("AI workspace options", "ai-workspace", pageItems("ai-workspace"), pageValues("ai-workspace"), 2)
        add("Desktop apps", "", data.apps, selectedApps, 1)
        sections.sort(function(a, b) { return a.targetStage - b.targetStage })
        return sections
    }
    function selectionCount() { return reviewSections().reduce(function(total, section) { return total + section.items.length }, 0) }
    function editSection(section) { stage = section.targetStage; browse(section.page) }
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
        saved = false; dirty = true; notice = full ? "Full workstation selected. Make it your own below." : "Starting small. Add only what you need."
    }
    function savePlan(install) {
        busy = true; problem = ""
        var components = {}
        Object.keys(selectedComponents).forEach(function(key) { components[key] = pageValues(key).slice() })
        request("save", {modules: chosen, apps: selectedApps, launchers: pageValues("launchers"), plugins: pageValues("plugins"), css: pageValues("css"), components: components}, function(result) {
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
        if (status === "FAILED" || status === "NOT_INSTALLED") return "#ffa6a1"
        if (status === "RUNNING") return "#8abaff"
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
            data = result; selectedComponents = result.selectedComponents; selectedCss = result.selectedCss.slice(); selectedLaunchers = result.selectedLaunchers.slice(); selectedPlugins = result.selectedPlugins.slice(); chosen = result.modules.slice(); selectedApps = result.selectedApps.slice(); loaded = true
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
            text: action.text; color: action.primary ? "#10251f" : window.ink
            font.pixelSize: 14; font.weight: Font.DemiBold
            horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
            opacity: action.enabled ? 1 : 0.45
        }
        background: Rectangle {
            radius: 10
            color: action.primary ? (action.down ? "#43b99a" : window.accent) : (action.hovered ? "#2a3849" : "#202c3a")
            border.width: action.activeFocus ? 2 : 1
            border.color: action.activeFocus ? "#ffffff" : (action.primary ? window.accent : "#344356")
            opacity: action.enabled ? 1 : 0.5
        }
    }
    component ChoiceCard: AbstractButton {
        id: card
        property string heading
        property string detail
        property string optionsPage: ""
        property bool navigation: false
        property int selectedCount: 0
        property bool selected: false
        implicitHeight: Math.max(104, card.contentItem.implicitHeight + 32) + (optionsPage && selected ? 54 : 0)
        hoverEnabled: true
        bottomPadding: optionsPage && selected ? 54 : 0
        background: Rectangle {
            radius: 13
            color: !card.navigation && card.selected ? "#19342f" : (card.hovered ? "#233142" : "#1a2532")
            border.width: card.activeFocus ? 2 : 1
            border.color: card.activeFocus ? "#ffffff" : (!card.navigation && card.selected ? "#468e7c" : "#304153")
        }
        contentItem: RowLayout {
            spacing: 14
            Rectangle {
                visible: !card.navigation
                Layout.leftMargin: 18; Layout.preferredWidth: 24; Layout.preferredHeight: 24; radius: 7
                color: card.selected ? window.accent : "#101b28"
                border.color: card.selected ? window.accent : "#66798c"
                Text { anchors.centerIn: parent; text: card.selected ? "✓" : ""; color: "#10251f"; font.bold: true; font.pixelSize: 17 }
            }
            ColumnLayout {
                Layout.leftMargin: card.navigation ? 18 : 0
                Layout.fillWidth: true; Layout.rightMargin: 16; spacing: 6
                TextLabel { text: card.heading; font.pixelSize: 15; font.weight: Font.DemiBold; Layout.fillWidth: true }
                TextLabel { text: card.detail; color: !card.navigation && card.selected ? "#b5d2c9" : window.muted; font.pixelSize: 13; Layout.fillWidth: true }
                TextLabel { visible: card.navigation; text: card.selectedCount ? card.selectedCount + " selected · Browse" : "Browse individual options"; color: window.accent; font.pixelSize: 12 }
            }
            TextLabel { visible: card.navigation; text: "›"; color: window.muted; font.pixelSize: 26; Layout.rightMargin: 18 }
        }
        Action {
            visible: !!card.optionsPage && card.selected
            anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.margins: 10
            text: card.optionsPage === "plugins" ? "Choose plugins" : card.optionsPage === "css" ? "Choose components" : "Workspace options"
            onClicked: window.browse(card.optionsPage)
        }
        Accessible.name: heading + ". " + detail
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
            Layout.fillHeight: true; color: "#151f2b"
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 22; spacing: 8
                Rectangle {
                    visible: window.height >= 600; Layout.topMargin: window.height < 620 ? 0 : 10; width: 42; height: 42; radius: 12; color: window.accent
                    Text { anchors.centerIn: parent; text: "W"; color: "#10251f"; font.pixelSize: 24; font.bold: true }
                }
                TextLabel { text: "DECK\nWORKSTATION"; font.pixelSize: 17; font.weight: Font.Bold; lineHeight: 1.18; Layout.topMargin: 10 }
                TextLabel { visible: window.height >= 600; text: "Make it yours."; color: window.muted; font.pixelSize: 13; Layout.bottomMargin: window.height < 620 ? 4 : 16 }
                Repeater {
                    model: window.stageNames
                    delegate: AbstractButton {
                        id: nav
                        required property string modelData
                        required property int index
                        Layout.fillWidth: true; implicitHeight: 58
                        enabled: window.loaded && !window.busy && !window.progress.running && (index !== 5 || window.saved)
                        onClicked: window.stage = index
                        background: Rectangle { radius: 10; color: window.stage === nav.index ? "#263a43" : "transparent"; border.color: nav.activeFocus ? window.accent : "transparent" }
                        contentItem: RowLayout {
                            spacing: 12
                            Text { Layout.leftMargin: 12; text: String(nav.index+1).padStart(2,"0"); color: window.stage === nav.index ? window.accent : "#7790a3"; font.pixelSize: 13 }
                            ColumnLayout {
                                Layout.fillWidth: true; spacing: 4
                                TextLabel { text: nav.modelData; font.pixelSize: 13; font.weight: Font.DemiBold; color: window.stage === nav.index ? window.ink : window.muted; Layout.fillWidth: true }
                                TextLabel { text: window.stageHints[nav.index]; font.pixelSize: 10; color: window.muted; Layout.fillWidth: true; elide: Text.ElideRight; wrapMode: Text.NoWrap }
                            }
                        }
                    }
                }
                Item { Layout.fillHeight: true }
                Rectangle { visible: window.height >= 780; Layout.fillWidth: true; height: 1; color: "#2c3948" }
                TextLabel { visible: window.height >= 780; text: "BUILT FOR YOUR DECK"; font.pixelSize: 10; font.letterSpacing: 1.2; color: "#8ba0b2"; Layout.topMargin: 14 }
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
                TextLabel { text: window.selectionCount() + " selected"; color: window.muted; font.pixelSize: 12 }
            }
            TextLabel { text: window.detailPage ? window.pageTitle(window.detailPage) : window.stageNames[window.stage]; font.pixelSize: window.width < 950 ? 27 : 32; font.weight: Font.Bold; Layout.fillWidth: true }
            TextLabel { text: window.detailPage === "css" ? "Decky › CSS Loader. Choose the components you want to manage." : window.detailPage === "plugins" ? "Add-ons for Decky Loader. CSS Loader has its own component choices." : window.detailPage ? "Check only the items you want. Browsing does not select or install anything." : window.stageDescriptions[window.stage]; color: window.muted; font.pixelSize: 15; Layout.fillWidth: true }
            RowLayout {
                visible: window.stage < 4 && !window.detailPage; spacing: 10; Layout.bottomMargin: 1
                Action { text: "Clear selections"; enabled: window.loaded; onClicked: { window.pendingPreset = false; presetDialog.open() } }
                Action { text: "Load full preset"; enabled: window.loaded; onClicked: { window.pendingPreset = true; presetDialog.open() } }
                Item { Layout.fillWidth: true }
            }
            RowLayout {
                visible: !!window.detailPage
                Layout.fillWidth: true; spacing: 10
                Action { text: window.detailPage === "css" ? "‹ Decky plugins" : "‹ " + window.stageNames[window.stage]; onClicked: window.back() }
                Item { Layout.fillWidth: true }
                TextLabel { text: window.pageValues(window.detailPage).length + " selected"; color: window.muted; font.pixelSize: 12 }
            }
            RowLayout {
                visible: window.stage < 4
                Layout.fillWidth: true; spacing: 10
                TextField {
                    id: search
                    Layout.fillWidth: true; implicitHeight: 48
                    visible: !!window.detailPage || window.stage === 1
                    placeholderText: "Find an app or tool…"; placeholderTextColor: window.muted; color: window.ink
                    text: window.searchText; onTextEdited: window.searchText = text
                    leftPadding: 14; rightPadding: 14
                    background: Rectangle { radius: 10; color: "#15212e"; border.color: search.activeFocus ? window.accent : "#344356" }
                    Accessible.name: "Filter available choices"
                }
                Action { visible: !!window.detailPage; text: "Select none"; onClicked: window.detailPreset(false) }
                Action { visible: window.detailPage === "plugins" || window.detailPage === "css"; text: "Recommended"; onClicked: window.detailPreset(true) }
            }
            Rectangle {
                visible: !!window.problem || !!window.notice
                Layout.fillWidth: true; implicitHeight: banner.implicitHeight + 24; radius: 10
                color: window.problem ? "#432b2f" : "#203633"
                TextLabel { id: banner; anchors.fill: parent; anchors.margins: 12; text: window.problem || window.notice; color: window.problem ? "#ffd0cc" : "#c1e8dc"; font.pixelSize: 13 }
            }
            ScrollView {
                id: scroll
                Layout.fillWidth: true; Layout.fillHeight: true
                clip: true; contentWidth: availableWidth
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                ColumnLayout {
                    width: scroll.availableWidth; spacing: 14
                    GridLayout {
                        visible: window.stage < 4
                        Layout.fillWidth: true; columns: window.width < 1000 ? 1 : 2; columnSpacing: 12; rowSpacing: 12
                        Repeater {
                            model: window.currentItems()
                            delegate: ChoiceCard {
                                required property var modelData
                                Layout.fillWidth: true; Layout.preferredWidth: 1; Layout.fillHeight: true
                                heading: modelData.name; detail: modelData.summary
                                navigation: !window.detailPage && !!window.categoryPage(modelData.id)
                                optionsPage: !window.detailPage && modelData.id === "decky" ? "plugins" : !window.detailPage && modelData.id === "ai-workspace" ? "ai-workspace" : window.detailPage === "plugins" && modelData.id === "SDH-CssLoader" ? "css" : ""
                                selectedCount: navigation ? window.pageValues(window.categoryPage(modelData.id)).length : 0
                                selected: window.detailPage ? window.pageValues(window.detailPage).indexOf(modelData.id) >= 0 : (window.stage === 1 ? window.selectedApps : window.chosen).indexOf(modelData.id) >= 0
                                onClicked: {
                                    if (navigation) window.browse(window.categoryPage(modelData.id))
                                    else window.toggle(modelData.id, window.stage === 1)
                                }
                            }
                        }
                    }
                    TextLabel {
                        visible: window.stage < 4; Layout.fillWidth: true
                        text: window.searchText && window.currentItems().length === 0 ? "No matches. Try another name or clear the search." : window.detailPage ? "Unchecked items stay out of this plan. Existing installations are kept." : "Browse a category to choose individual items. Checkboxes select an install or setup task."
                        font.pixelSize: 12; color: window.muted; Layout.topMargin: 4
                    }
                    ColumnLayout {
                        visible: window.stage === 4; Layout.fillWidth: true; spacing: 14
                        Rectangle {
                            Layout.fillWidth: true; implicitHeight: reviewIntro.implicitHeight + 36; radius: 14; color: "#1b302f"; border.color: "#3d7568"
                            ColumnLayout {
                                id: reviewIntro; anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 18; spacing: 8
                                TextLabel { text: "A setup that fits you"; font.pixelSize: 19; font.weight: Font.DemiBold }
                                TextLabel { text: "Save this plan for later, or install your choices. Existing apps and personal data are kept."; Layout.fillWidth: true; color: "#bfd6ce"; font.pixelSize: 14 }
                            }
                        }
                        TextLabel { visible: window.selectionCount() === 0; text: "No optional installs selected. Only base support will be configured."; Layout.fillWidth: true; color: window.muted }
                        Repeater {
                            model: window.reviewSections()
                            delegate: Rectangle {
                                required property var modelData
                                Layout.fillWidth: true; implicitHeight: reviewGroup.implicitHeight + 28
                                radius: 12; color: "#1a2532"
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
                                            TextLabel { text: "✓  " + modelData.name; Layout.fillWidth: true; font.pixelSize: 14 }
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
                                radius: 10; color: "#1a2532"
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
                        TextLabel { visible: window.allModules().indexOf("dev") >= 0; text: "Docker & Compose runs project databases and services in containers, keeping their dependencies separate from SteamOS. Install it if your projects need containers."; Layout.fillWidth: true; font.pixelSize: 13; color: window.muted }
                        Action { text: "Optional Docker & Compose"; visible: window.allModules().indexOf("dev") >= 0; enabled: !window.progress.running && !window.busy; onClicked: window.startOperation("docker") }
                        Action { text: "Continue setup & sign-in"; enabled: !window.progress.running && !window.busy && !window.data.planOnly; onClicked: window.startOperation("accounts") }
                    }
                }
            }
            Rectangle { Layout.fillWidth: true; height: 1; color: "#2a3848" }
            RowLayout {
                Layout.fillWidth: true; spacing: 10
                Action { text: "Back"; visible: !!window.detailPage || (window.stage > 0 && window.stage < 5); enabled: !window.busy; onClicked: window.back() }
                TextLabel { visible: window.stage < 4; text: "Your choices save at review.\nNothing installs yet."; font.pixelSize: 12; color: window.muted; Layout.fillWidth: true }
                Item { visible: window.stage >= 4; Layout.fillWidth: true }
                Action { text: "Close"; visible: window.stage === 5; enabled: !window.progress.running && !window.busy; onClicked: window.close() }
                Action { text: "Save for later"; visible: window.stage === 4 && !window.data.planOnly; enabled: !window.busy; onClicked: window.savePlan(false) }
                Action {
                    primary: true
                    text: window.detailPage ? "Done choosing →" : window.stage < 3 ? "Continue →" : (window.stage === 3 ? "Review setup →" : (window.stage === 4 ? (window.data.planOnly ? "Save & continue" : "Save & install") : (window.progress.operation === "install" && window.progress.exitCode === 0 ? "Continue setup" : window.progress.operation === "accounts" && window.progress.exitCode === 0 ? "Finish" : window.progress.operation ? "Retry installation" : "Install selections")))
                    enabled: window.loaded && !window.busy && !window.progress.running && (window.stage !== 5 || !window.data.planOnly)
                    onClicked: {
                        if (window.detailPage) window.back()
                        else if (window.stage < 4) { window.stage++; window.notice="" }
                        else if (window.stage === 4) window.savePlan(!window.data.planOnly)
                        else if (window.progress.operation === "install" && window.progress.exitCode === 0) window.startOperation("accounts")
                        else if (window.progress.operation === "accounts" && window.progress.exitCode === 0) window.close()
                        else window.startOperation("install")
                    }
                }
            }
        }
    }
    }
    Dialog {
        id: presetDialog
        title: window.pendingPreset ? "Load the full preset?" : "Clear your selections?"
        anchors.centerIn: parent; modal: true
        width: Math.min(430, window.width-40)
        standardButtons: Dialog.Ok | Dialog.Cancel
        Label { width: parent.width; wrapMode: Text.WordWrap; text: "This replaces your choices in this window. Existing software stays installed. Your saved plan changes only when you save at review." }
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
