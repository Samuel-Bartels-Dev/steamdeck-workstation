import QtQuick
import QtTest
import "../../lib/deckctl/ui" as UI
Item {
    id: fixture
    property bool ready: false
    UI.Setup { id: app; width: TEST_WIDTH; height: TEST_HEIGHT; textScale: 1.35; endpoint: TEST_ENDPOINT }
    Timer { interval: 1; running: app.loaded && checks.windowShown; onTriggered: fixture.ready = true }
    TestCase {
        id: checks
        parent: app.contentItem
        name: "LayoutAndContinuousOutput"
        when: fixture.ready
        function find(root,name) {
            if (root.objectName === name && root.visible !== false) return root
            var children = root.children || []
            for (var i=0;i<children.length;i++) { var child=find(children[i],name); if(child) return child }
            return null
        }
        function visibleInside(item, container) {
            verify(item !== null, "Expected control exists")
            var at=item.mapToItem(container,0,0)
            verify(at.x >= -1 && at.y >= -1, item.objectName+" starts inside viewport: "+at)
            verify(at.x+item.width <= container.width+1 && at.y+item.height <= container.height+1, item.objectName+" ends inside viewport: "+at+" size "+item.width+"x"+item.height)
        }
        function waitUntilInside(item, container) {
            var diagnostic="", previousGeometry=""
            try { tryVerify(function() {
                if (!item) { diagnostic="Control missing"; return false }
                var at=item.mapToItem(container,0,0)
                diagnostic=item.objectName+" at "+at+" size "+item.width+"x"+item.height+" in "+container.width+"x"+container.height
                var settled=diagnostic===previousGeometry
                previousGeometry=diagnostic
                return settled && at.x>=-1 && at.y>=-1 && at.x+item.width<=container.width+1 && at.y+item.height<=container.height+1
            },1000,"Focused control must settle inside its viewport") }
            catch(error) { console.log("FOCUS_GEOMETRY: "+diagnostic); throw error }
            visibleInside(item,container)
        }
        function capture(name) {
            if (!TEST_IMAGES) return
            var path=TEST_IMAGES+"/"+name+"-"+app.width+".png"
            if (name.indexOf("queue")===0 || name.indexOf("console")===0) {
                var canvas=find(app.contentItem,"setupCanvas"), warmed=false
                verify(canvas.grabToImage(function(image) { warmed=true }))
                tryVerify(function() { return warmed },5000,"Warmup scene rendered")
                var queue=name.indexOf("queue")===0 ? find(app.contentItem,"queueToggle") : null
                var viewport=find(app.contentItem,"setupScroll")
                if(queue) waitUntilInside(queue,viewport)
                function geometry() {
                    return queue ? [queue.mapToItem(viewport,0,0).y,queue.width,queue.height,viewport.height,viewport.contentItem.contentY].join(",") : ""
                }
                var before=geometry(), captured=false
                verify(canvas.grabToImage(function(image) {
                    verify(image.saveToFile(path)); captured=true
                }))
                tryVerify(function() { return captured },5000,"Final setup scene captured")
                if(queue) { compare(geometry(),before,"Queue geometry remains stable through final capture"); visibleInside(queue,viewport) }
            } else {
                // Popups and drawers live in the window overlay, outside canvas.
                var image=grabImage(app.contentItem)
                image.save(path)
            }
        }
        function test_layout_and_output() {
            compare(app.font.family,"JetBrainsMono Nerd Font Mono","The interface uses the installed Nerd Font family")
            tryCompare(app,"guideVisible",true)
            app.closeGuide(); tryCompare(app,"guideVisible",false)
            app.requestActivate(); tryCompare(app,"active",true)
            app.consolePending=true; app.progressPending=true
            var data=Object.assign({},app.data)
            data.layout=data.layout.map(function(section) { return Object.assign({},section,{items:section.items.map(function(item) { return Object.assign({},item,{name:item.name+" — extended accessible label for testing wrapping",summary:(item.summary+" ").repeat(3)}) }) }) })
            data.appearanceTargets=data.appearanceTargets.map(function(item) { return Object.assign({},item,{name:item.name+" — long appearance preference that must wrap safely",summary:item.summary.repeat(3)}) })
            app.data=data
            for (var stage=0;stage<6;stage++) {
                app.navigate(stage); wait(40)
                visibleInside(find(app.contentItem,"primaryAction"),app.contentItem)
                var scroll=find(app.contentItem,"setupScroll")
                verify(scroll.height>40,"Each stage retains a usable scroll body")
                verify(scroll.contentItem.contentWidth<=scroll.width+1,"No horizontal clipping")
                scroll.contentItem.contentY=Math.max(0,scroll.contentItem.contentHeight-scroll.height)
                visibleInside(find(app.contentItem,"primaryAction"),app.contentItem)
            }
            app.navigate(0)
            for (var page of ["css","plugins"]) { app.browse(page); wait(40); visibleInside(find(app.contentItem,"primaryAction"),app.contentItem); app.back() }
            app.importPreview={files:Array(10).fill("very-long/path/".repeat(20)+"settings.json")}
            for (var name of ["appearanceDialog","importDialog","presetDialog","leaveDialog","cancelRunDialog","forceStopDialog","externalCloseDialog","firstRunGuide"]) {
                var popup=findChild(app,name)
                verify(popup!==null,name+" exists")
                var anchor=find(app.contentItem,"primaryAction"); anchor.forceActiveFocus(); tryCompare(anchor,"activeFocus",true)
                popup.open(); tryCompare(popup,"opened",true)
                verify(popup.width<=app.width && popup.height<=app.height,name+" fits window")
                if (popup.footer) visibleInside(popup.footer,app.contentItem)
                if(name==="appearanceDialog") {
                    var appearanceScroll=find(popup.contentItem,"appearanceScroll")
                    verify(appearanceScroll.contentItem.contentWidth<=appearanceScroll.width+1,"Appearance width follows actual scroll viewport")
                    capture("appearance")
                    var ids=app.data.appearanceTargets.map(function(item){return item.id})
                    var first=find(popup.contentItem,"appearanceChoice_"+ids[0])
                    var lastChoice=find(popup.contentItem,"appearanceChoice_"+ids[ids.length-1])
                    first.forceActiveFocus(); tryCompare(first,"activeFocus",true)
                    for(var tab=0;tab<ids.length-1;tab++) keyClick(Qt.Key_Tab)
                    tryCompare(lastChoice,"activeFocus",true)
                    waitUntilInside(lastChoice,appearanceScroll)
                    verify(lastChoice.contentItem.width<=appearanceScroll.width,"Wrapped preference stays within viewport")
                    keyClick(Qt.Key_Tab,Qt.ShiftModifier); verify(!lastChoice.activeFocus)
                    appearanceScroll.contentItem.contentY=Math.max(0,appearanceScroll.contentItem.contentHeight-appearanceScroll.height)
                    capture("appearance-bottom")
                }
                if(name==="importDialog") capture("import")
                keyClick(Qt.Key_Escape); tryCompare(popup,"visible",false)
                tryCompare(anchor,"activeFocus",true,5000,"Closing modal restores its initiating control")
            }
            var inventory={}
            for(var index=0;index<30;index++) inventory["app:"+index]={name:"Application "+String(index).padStart(2,"0"),status:index<10?"UPDATE":index<20?"CURRENT":"MISSING",label:index<10?"Update available":index<20?"Installed":"Not installed",note:"Long diagnostics ".repeat(30),installedVersion:"verylongversion".repeat(10)}
            inventory["app:z"]={name:"Attention",status:"FAILED",label:"Needs repair"}
            inventory["app:a"]={name:"Zebra",status:"UNKNOWN",label:"Not checked"}
            app.deckInventory={items:inventory,running:false}
            compare(app.statusGroups().map(function(group){return group.id}).join(","),"attention,updates,unknown,installed,optional")
            app.toggleStatus("app:0",false)
            app.deckInventory={items:Object.assign({},inventory),running:false}
            verify(app.statusExpanded["app:0"],"Inventory refresh preserves expanded details")
            var drawer=findChild(app,"statusDrawer"); drawer.open(); tryCompare(drawer,"opened",true)
            visibleInside(find(drawer.contentItem,"statusClose"),app.contentItem)
            capture("status")
            var last=find(drawer.contentItem,"statusItem_app:9")
            verify(last!==null); last.forceActiveFocus(); tryCompare(last,"activeFocus",true); wait(30)
            waitUntilInside(last,find(drawer.contentItem,"statusScroll"))
            keyClick(Qt.Key_Tab,Qt.ShiftModifier); wait(30)
            verify(!last.activeFocus,"Shift+Tab traverses long status list")
            keyClick(Qt.Key_Escape); tryCompare(drawer,"visible",false)
            app.navigate(5); app.finishItems=[]
            app.progress={running:false,operation:"install",modules:[{id:"app:tool",name:"Scheduled tool",status:"PENDING",hasLog:false},{id:"app:failed",name:"Needs attention",status:"FAILED"},{id:"app:done",name:"Completed",status:"DONE"}]}
            verify(!app.queueExpanded)
            compare(app.queueSummary(),"1 attention · 1 scheduled · 1 completed")
            var queue=find(app.contentItem,"queueToggle")
            queue.forceActiveFocus(); waitUntilInside(queue,find(app.contentItem,"setupScroll"))
            console.log("QUEUE_BEFORE_CAPTURE y="+queue.mapToItem(find(app.contentItem,"setupScroll"),0,0).y+" h="+queue.height+" viewport="+find(app.contentItem,"setupScroll").height)
            capture("queue-collapsed")
            console.log("QUEUE_AFTER_CAPTURE y="+queue.mapToItem(find(app.contentItem,"setupScroll"),0,0).y+" h="+queue.height+" viewport="+find(app.contentItem,"setupScroll").height)
            waitUntilInside(queue,find(app.contentItem,"setupScroll"))
            mouseClick(queue); verify(app.queueExpanded)
            app.expandedResult="app:tool"; wait(30)
            var details=find(app.contentItem,"viewInstallLog"); verify(details!==null,"Scheduled item has Details before output exists")
            // Exact marker must not match a longer key or text within a provider line.
            var record="[app:tool-extra] Checking\nprovider [app:tool] is text\n[app:failed] FAILED: sample\n"
            app.applyConsole({sourceId:"run-one",text:record}); wait(30)
            details.forceActiveFocus(); wait(30)
            waitUntilInside(details,find(app.contentItem,"setupScroll"))
            mouseClick(details); wait(30)
            var outer=find(app.contentItem,"setupScroll")
            var panel=find(app.contentItem,"consolePanel")
            var panelY=panel.mapToItem(outer,0,0).y
            verify(panelY>=-1 && panelY<outer.height,"Details reveals the overall console from the deep queue")
            verify(app.pendingConsoleJump); compare(app.displayedConsole,record)
            verify(app.outputContext.indexOf("Waiting")>=0)
            capture("console-waiting")
            var withItem=record+"[app:tool] Checking selected item\nprovider output\n"
            app.applyConsole({sourceId:"run-one",text:withItem}); wait(30)
            var output=find(app.contentItem,"inlineConsole")
            compare(output.selectedText,"[app:tool] Checking selected item")
            var consoleViewport=find(app.contentItem,"consoleScroll")
            var selectionY=output.positionToRectangle(output.selectionStart).y-consoleViewport.contentItem.contentY
            verify(selectionY>=-1 && selectionY<consoleViewport.height,"Details highlight is inside the visible console")
            verify(output.persistentSelection); verify(!app.pendingConsoleJump)
            compare(app.displayedConsole,withItem)
            capture("console-selected")
            app.applyConsole({sourceId:"run-one",text:withItem+"[app:done] Verified\n"}); wait(30)
            compare(output.selectedText,"[app:tool] Checking selected item")
            var full=app.displayedConsole
            app.findNextError(); wait(30); compare(app.displayedConsole,full); verify(output.selectedText.indexOf("FAILED")>=0)
            app.applyConsole({source:"unavailable",outputNotice:"Read interrupted"}); compare(app.displayedConsole,full)
            app.applyConsole({sourceId:"run-one",text:full+"Recovery line\n"})
            verify(app.outputContext.indexOf("temporarily unavailable")<0,"Successful read clears transient warning")
            output.select(0,5)
            wait(30); compare(output.selectedText,full.slice(0,5),"A selection made after response beats deferred restoration")
            queue.forceActiveFocus(); wait(30); mouseClick(queue); verify(!app.queueExpanded)
            mouseClick(queue); verify(app.queueExpanded); compare(app.expandedResult,"app:tool")
            var queueScroll=find(app.contentItem,"setupScroll")
            queueScroll.contentItem.contentY=Math.max(0,queue.mapToItem(queueScroll.contentItem,0,0).y+queueScroll.contentItem.contentY)
            wait(30); capture("queue")
            app.navigate(4); app.navigate(5); verify(app.queueExpanded)
            app.applyConsole({sourceId:"run-one",historyTruncated:true,text:"Retained tail\n"}); wait(30)
            compare(output.selectedText,"","Rotation clears unrelated absolute selection")
            app.showLog("app:old"); verify(app.outputContext.indexOf("retained")>=0)
            app.applyConsole({sourceId:"race",text:"[app:failed] FAILED old record\n"}); wait(30)
            app.findNextError()
            app.applyConsole({sourceId:"replacement",text:"New unrelated record\n"}); wait(30)
            compare(output.selectedText,"","Deferred error jump must not select a replaced record")
            // Near the real 1 MiB cap, measure rendering+append without an FPS claim.
            var large="[app:tool] Beginning\n"+"measured output line 012345678901234567890123456789\n".repeat(19500)
            var started=Date.now()
            app.applyConsole({sourceId:"large",text:large}); wait(100)
            app.applyConsole({sourceId:"large",text:large+"[app:failed] FAILED: final marker\n"}); wait(100)
            app.findNextError(); wait(30)
            compare(output.selectedText,"[app:failed] FAILED: final marker")
            output.forceActiveFocus(); keyClick(Qt.Key_Home,Qt.ControlModifier)
            console.log("LARGE_CONSOLE_MS="+(Date.now()-started)+" BYTES="+app.displayedConsole.length)
            app.consoleItem=""; app.pendingConsoleJump=false
            app.applyConsole({sourceId:"final",text:withItem}); wait(30)
            compare(output.selectedText,"")
            compare(output.cursorPosition,0)
            app.showLog("app:tool"); wait(30)
            compare(output.selectedText,"[app:tool] Checking selected item")
            var finalY=output.positionToRectangle(output.selectionStart).y-find(app.contentItem,"consoleScroll").contentItem.contentY
            verify(finalY>=-1 && finalY<find(app.contentItem,"consoleScroll").height,"New-source output is visible after large record")
            capture("console")
            app.dirty=false; app.allowClose=true; app.close()
        }
    }
}
