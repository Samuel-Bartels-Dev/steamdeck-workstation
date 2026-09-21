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
    property string notice: ""
    property string problem: ""
    property string endpoint: ""
    readonly property var stageNames: ["Play & personalize", "Work & create", "Everyday essentials", "Desktop apps", "Review your setup", "Installation"]
    readonly property var stageDescriptions: [
        "Make room for the way you play.",
        "A capable workstation, on your terms.",
        "Connect, organize, and look after your Deck.",
        "Your everyday favorites, ready to go.",
        "One last look before you make it yours.",
        "Follow your setup, one feature at a time."]

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
    function toggle(key, isApp) {
        var values = (componentDetail ? selectedComponents[detailPage] : detailPage === "css" ? selectedCss : detailPage === "launchers" ? selectedLaunchers : detailPage === "plugins" ? selectedPlugins : isApp ? selectedApps : chosen).slice()
        var index = values.indexOf(key)
        if (index < 0) values.push(key); else values.splice(index, 1)
        if (componentDetail) {
            var updated = Object.assign({}, selectedComponents)
            updated[detailPage] = values
            selectedComponents = updated
        }
        else if (detailPage === "css") selectedCss = values
        else if (detailPage === "launchers") selectedLaunchers = values
        else if (detailPage === "plugins") selectedPlugins = values
        else if (isApp) selectedApps = values; else chosen = values
        saved = false; dirty = true; notice = ""; problem = ""
    }
    function detailPreset(defaults) {
        if (componentDetail) {
            var updated = Object.assign({}, selectedComponents)
            updated[detailPage] = defaults ? data.defaultComponents[detailPage].slice() : []
            selectedComponents = updated
        }
        else if (detailPage === "css") selectedCss = defaults ? data.defaultCss.slice() : []
        else if (detailPage === "plugins") selectedPlugins = defaults ? data.defaultPlugins.slice() : []
        else selectedLaunchers = defaults ? data.launchers.map(function(x) { return x.id }) : []
        saved = false; dirty = true
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
        request("save", {modules: chosen, apps: selectedApps, launchers: selectedLaunchers, plugins: selectedPlugins, css: selectedCss, components: selectedComponents}, function(result) {
            saved = true; dirty = false; busy = false; notice = "Your setup plan is saved."
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
    onDetailPageChanged: { if (scroll.contentItem) scroll.contentItem.contentY = 0 }
    onStageChanged: { detailPage = ""; if (scroll.contentItem) scroll.contentItem.contentY = 0 }
    Component.onCompleted: {
        var args = Qt.application.arguments
        for (var i=0; i<args.length; i++) if (args[i].indexOf("http://127.0.0.1:") === 0) endpoint = args[i]
        if (!endpoint) { problem = "Open this app with deckctl setup customize."; return }
        request("catalog", null, function(result) {
            data = result; selectedComponents = result.selectedComponents; selectedCss = result.selectedCss.slice(); selectedLaunchers = result.selectedLaunchers.slice(); selectedPlugins = result.selectedPlugins.slice(); chosen = result.modules.slice(); selectedApps = result.selectedApps.slice(); loaded = true
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
        property bool selected: false
        implicitHeight: Math.max(100, card.contentItem.implicitHeight + 30) + (optionsPage ? 56 : 0)
        hoverEnabled: true
        background: Rectangle {
            radius: 13
            color: card.selected ? "#19342f" : (card.hovered ? "#233142" : "#1a2532")
            border.width: card.activeFocus ? 2 : 1
            border.color: card.activeFocus ? "#ffffff" : (card.selected ? "#468e7c" : "#304153")
        }
        bottomPadding: optionsPage ? 56 : 0
        contentItem: RowLayout {
            spacing: 14
            Rectangle {
                Layout.leftMargin: 18; Layout.preferredWidth: 24; Layout.preferredHeight: 24; radius: 7
                color: card.selected ? window.accent : "#101b28"
                border.color: card.selected ? window.accent : "#66798c"
                Text { anchors.centerIn: parent; text: card.selected ? "✓" : ""; color: "#10251f"; font.bold: true; font.pixelSize: 17 }
            }
            ColumnLayout {
                Layout.fillWidth: true; Layout.rightMargin: 16; spacing: 5
                TextLabel { text: card.heading; font.pixelSize: 15; font.weight: Font.DemiBold; Layout.fillWidth: true }
                TextLabel { text: card.detail; color: card.selected ? "#b5d2c9" : window.muted; font.pixelSize: 13; Layout.fillWidth: true }
            }
        }
        Action {
            visible: !!card.optionsPage
            anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.margins: 12
            implicitHeight: 48; implicitWidth: 110; text: "Choose tools"
            onClicked: { if (!card.selected) window.toggle(card.optionsPage, false); window.detailPage = card.optionsPage }
        }
        Accessible.name: heading + ". " + detail
        Accessible.role: Accessible.CheckBox
        Accessible.checkable: true
        Accessible.checked: selected
    }

    Rectangle {
        objectName: "setupCanvas"
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
                    Layout.topMargin: window.height < 620 ? 0 : 10; width: 42; height: 42; radius: 12; color: window.accent
                    Text { anchors.centerIn: parent; text: "W"; color: "#10251f"; font.pixelSize: 24; font.bold: true }
                }
                TextLabel { text: "DECK\nWORKSTATION"; font.pixelSize: 17; font.weight: Font.Bold; lineHeight: 1.18; Layout.topMargin: 10 }
                TextLabel { text: "Make it yours."; color: window.muted; font.pixelSize: 13; Layout.bottomMargin: window.height < 620 ? 10 : 26 }
                Repeater {
                    model: window.stageNames
                    delegate: AbstractButton {
                        id: nav
                        required property string modelData
                        required property int index
                        Layout.fillWidth: true; implicitHeight: window.height < 620 ? 44 : 49
                        enabled: window.loaded && !window.busy && !window.progress.running && (index !== 5 || window.saved)
                        onClicked: window.stage = index
                        background: Rectangle { radius: 10; color: window.stage === nav.index ? "#263a43" : "transparent"; border.color: nav.activeFocus ? window.accent : "transparent" }
                        contentItem: RowLayout {
                            spacing: 12
                            Text { Layout.leftMargin: 12; text: String(nav.index+1).padStart(2,"0"); color: window.stage === nav.index ? window.accent : "#7790a3"; font.pixelSize: 13 }
                            TextLabel { text: nav.modelData; font.pixelSize: 13; color: window.stage === nav.index ? window.ink : window.muted; Layout.fillWidth: true }
                        }
                    }
                }
                Item { Layout.fillHeight: true }
                Rectangle { visible: window.height >= 680; Layout.fillWidth: true; height: 1; color: "#2c3948" }
                TextLabel { visible: window.height >= 680; text: "BUILT FOR YOUR DECK"; font.pixelSize: 10; font.letterSpacing: 1.2; color: "#8ba0b2"; Layout.topMargin: 14 }
                TextLabel { visible: window.height >= 680; text: "Setup runs only while open.\nYour choices stay yours."; color: window.muted; font.pixelSize: 12; Layout.topMargin: 4 }
            }
        }
        ColumnLayout {
            Layout.fillWidth: true; Layout.fillHeight: true
            Layout.margins: window.width < 950 ? 22 : 34; spacing: 15
            RowLayout {
                Layout.fillWidth: true
                TextLabel { text: window.stage < 4 ? "BUILD YOUR SETUP" : "YOUR WORKSTATION"; font.pixelSize: 11; font.letterSpacing: 1.8; color: window.accent }
                Item { Layout.fillWidth: true }
                TextLabel { text: window.selectedApps.length + " apps  ·  " + Math.max(0,window.allModules().length-1) + " features"; color: window.muted; font.pixelSize: 12 }
            }
            TextLabel { text: window.componentDetail ? window.featureNames()[window.detailPage] : window.detailPage === "css" ? "Choose your CSS components" : window.detailPage === "launchers" ? "Choose your launchers" : window.detailPage === "plugins" ? "Choose your Decky plugins" : window.stageNames[window.stage]; font.pixelSize: window.width < 950 ? 27 : 32; font.weight: Font.Bold; Layout.fillWidth: true }
            TextLabel { text: window.detailPage ? "Every item is optional. Leaving it unchecked keeps it out of your installation plan." : window.stageDescriptions[window.stage]; color: window.muted; font.pixelSize: 15; Layout.fillWidth: true }
            RowLayout {
                visible: window.stage < 4 && !window.detailPage; spacing: 10; Layout.bottomMargin: 1
                Action { text: "Start small"; enabled: window.loaded; onClicked: window.preset(false) }
                Action { text: "Full workstation"; enabled: window.loaded; onClicked: window.preset(true) }
                Item { Layout.fillWidth: true }
            }
            Flow {
                Layout.fillWidth: true; spacing: 10
                visible: window.stage < 3
                Action { visible: window.stage === 0 && !window.detailPage && window.chosen.indexOf("gaming") >= 0; text: "Choose launchers · " + window.selectedLaunchers.length; onClicked: window.detailPage = "launchers" }
                Action { visible: window.stage === 0 && !window.detailPage && window.chosen.indexOf("decky") >= 0; text: "Choose plugins · " + window.selectedPlugins.length; onClicked: window.detailPage = "plugins" }
                Action { visible: window.detailPage === "plugins" && window.selectedPlugins.indexOf("SDH-CssLoader") >= 0; text: "CSS components · " + window.selectedCss.length; onClicked: window.detailPage = "css" }
                Action { visible: !!window.detailPage; text: "Clear all"; onClicked: window.detailPreset(false) }
                Action { visible: !!window.detailPage; text: window.componentDetail || window.detailPage === "launchers" ? "Select all" : "Use recommended"; onClicked: window.detailPreset(true) }
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
                            model: window.componentDetail ? window.data.components[window.detailPage] : window.detailPage === "css" ? window.data.css : window.detailPage === "launchers" ? window.data.launchers : window.detailPage === "plugins" ? window.data.plugins : window.stage < 3 ? (window.data.groups[window.stage] || {modules:[]}).modules : (window.stage === 3 ? window.data.apps : [])
                            delegate: ChoiceCard {
                                required property var modelData
                                Layout.fillWidth: true
                                heading: modelData.name; detail: modelData.summary
                                optionsPage: !window.detailPage && window.data.components && window.data.components[modelData.id] ? modelData.id : ""
                                selected: (window.componentDetail ? window.selectedComponents[window.detailPage] : window.detailPage === "css" ? window.selectedCss : window.detailPage === "launchers" ? window.selectedLaunchers : window.detailPage === "plugins" ? window.selectedPlugins : window.stage === 3 ? window.selectedApps : window.chosen).indexOf(modelData.id) >= 0
                                onClicked: window.toggle(modelData.id, window.stage === 3)
                            }
                        }
                    }
                    TextLabel {
                        visible: window.stage < 4; Layout.fillWidth: true
                        text: window.detailPage ? "Changing selections never removes existing installations." : "Base support is always included. Required dependencies are added in your review."
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
                        TextLabel { text: "FEATURES & REQUIREMENTS"; color: window.muted; font.pixelSize: 11; font.letterSpacing: 1.2 }
                        Repeater {
                            model: window.allModules()
                            delegate: RowLayout {
                                required property string modelData
                                Layout.fillWidth: true
                                TextLabel { text: "✓"; color: window.accent; Layout.preferredWidth: 22 }
                                TextLabel { text: window.featureNames()[modelData] || modelData; Layout.fillWidth: true; font.pixelSize: 14 }
                                TextLabel { text: modelData === "base" ? "Required" : (window.chosen.indexOf(modelData) < 0 ? "Included dependency / app owner" : "Selected"); color: window.muted; font.pixelSize: 12 }
                            }
                        }
                        Repeater {
                            model: window.loaded ? Object.keys(window.data.components).filter(function(key) { return window.allModules().indexOf(key) >= 0 }) : []
                            delegate: ColumnLayout {
                                required property string modelData
                                Layout.fillWidth: true
                                TextLabel { text: window.featureNames()[modelData].toUpperCase(); color: window.muted; font.pixelSize: 11 }
                                TextLabel { text: window.selectedNames(window.data.components[modelData], window.selectedComponents[modelData] || []); Layout.fillWidth: true; font.pixelSize: 14 }
                            }
                        }
                        TextLabel {
                            visible: window.allModules().indexOf("ai-workspace") >= 0
                            text: "AI workspace requires OpenCode. Selecting the local model also includes Ollama. Ghostty, tmux and Neovim are optional."
                            Layout.fillWidth: true; font.pixelSize: 13; color: window.muted
                        }
                        TextLabel { text: "DESKTOP APPS"; color: window.muted; font.pixelSize: 11; font.letterSpacing: 1.2; Layout.topMargin: 10 }
                        TextLabel { text: window.data.apps.filter(function(app) { return window.selectedApps.indexOf(app.id)>=0 }).map(function(app) { return app.name }).join("  ·  ") || "No desktop apps selected"; Layout.fillWidth: true; font.pixelSize: 14 }
                        TextLabel { text: "LAUNCHERS & TOOLS"; visible: window.allModules().indexOf("gaming") >= 0; color: window.muted; font.pixelSize: 11 }
                        TextLabel { visible: window.allModules().indexOf("gaming") >= 0; text: window.selectedNames(window.data.launchers, window.selectedLaunchers); Layout.fillWidth: true }
                        TextLabel { text: "DECKY PLUGINS"; visible: window.allModules().indexOf("decky") >= 0; color: window.muted; font.pixelSize: 11 }
                        TextLabel { visible: window.allModules().indexOf("decky") >= 0; text: window.selectedNames(window.data.plugins, window.selectedPlugins); Layout.fillWidth: true }
                        TextLabel { visible: window.allModules().indexOf("decky") >= 0 && window.selectedPlugins.indexOf("SDH-CssLoader") >= 0; text: "CSS COMPONENTS"; color: window.muted; font.pixelSize: 11 }
                        TextLabel { visible: window.allModules().indexOf("decky") >= 0 && window.selectedPlugins.indexOf("SDH-CssLoader") >= 0; text: window.selectedNames(window.data.css, window.selectedCss); Layout.fillWidth: true }
                        TextLabel { text: "Some features download software or models and open their own setup prompts. Account sign-in and device pairing happen afterward. You can skip those stages."; color: window.muted; Layout.fillWidth: true; font.pixelSize: 13; Layout.topMargin: 10 }
                    }
                    ColumnLayout {
                        visible: window.stage === 5; Layout.fillWidth: true; spacing: 12
                        TextLabel { text: window.progress.running ? "Setup is running" : (window.progress.operation ? "Installation process finished" : "Your plan is ready"); font.pixelSize: 21; font.weight: Font.DemiBold }
                        TextLabel { text: "Interactive prompts open in Konsole. Module results appear here as the installer records them. Ready means the module check passed; accounts may still need sign-in."; Layout.fillWidth: true; color: window.muted; font.pixelSize: 13 }
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
                                        TextLabel { text: modelData.status.replace(/_/g," "); color: window.stateColor(modelData.status); font.pixelSize: 12 }
                                    }
                                    TextLabel { visible: !!modelData.message; text: modelData.message || ""; color: window.muted; font.pixelSize: 12; Layout.fillWidth: true }
                                }
                            }
                        }
                        Action { text: "Optional Docker & Compose"; visible: window.allModules().indexOf("dev") >= 0; enabled: !window.progress.running && !window.busy; onClicked: window.startOperation("docker") }
                        Action { text: "Continue sign-in & pairing"; enabled: !window.progress.running && !window.busy && !window.data.planOnly; onClicked: window.startOperation("accounts") }
                    }
                }
            }
            Rectangle { Layout.fillWidth: true; height: 1; color: "#2a3848" }
            RowLayout {
                Layout.fillWidth: true; spacing: 10
                Action { text: "Back"; visible: !!window.detailPage || (window.stage > 0 && window.stage < 5); enabled: !window.busy; onClicked: {if (window.detailPage) window.detailPage=window.detailPage === "css" ? "plugins" : ""; else window.stage--; window.problem=""} }
                TextLabel { visible: window.stage < 4; text: "Choose what you need.\nEverything else can wait."; font.pixelSize: 12; color: window.muted; Layout.fillWidth: true }
                Item { visible: window.stage >= 4; Layout.fillWidth: true }
                Action { text: "Save for later"; visible: window.stage === 4 && !window.data.planOnly; enabled: !window.busy; onClicked: window.savePlan(false) }
                Action {
                    primary: true
                    text: window.detailPage ? "Done choosing →" : window.stage < 3 ? "Continue →" : (window.stage === 3 ? "Review setup →" : (window.stage === 4 ? (window.data.planOnly ? "Save & continue" : "Save & install") : "Install / retry"))
                    enabled: window.loaded && !window.busy && !window.progress.running && (window.stage !== 5 || !window.data.planOnly)
                    onClicked: {
                        if (window.detailPage) window.detailPage = window.detailPage === "css" ? "plugins" : ""
                        else if (window.stage < 4) { window.stage++; window.notice="" }
                        else if (window.stage === 4) window.savePlan(!window.data.planOnly)
                        else window.startOperation("install")
                    }
                }
            }
        }
    }
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
