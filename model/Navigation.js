// Immutable UI state transitions: no telemetry reads, no shell side effects.
function fresh(instrument) {
    return {instrument:instrument || 'connection', selectedKey:'', selectedRecord:null, focusKey:'',
        context:null, history:[], expanded:[], collapsed:[], query:'', filters:{}, isolated:false, frozen:false,
        showSearch:false, showHelp:false, showSettings:false, showPicker:false, showCapabilities:false, showIntro:false,
        showAllDetails:false, trend:false, notice:'', privacyOverride:null};
}
function clone(s) { return JSON.parse(JSON.stringify(s)); }
function contextFor(n) {
    if (!n) return null;
    var r=n.raw || n;
    var c={key:n.key, type:n.kind};
    if (n.kind === 'process') { c.processKey=n.key; c.groupKey=r.groupKey; }
    else if (n.kind === 'application') c.groupKey=n.key;
    else if (n.kind === 'remote') c.remoteKey=n.key;
    else if (n.kind === 'mount') c.mountKey=n.key;
    else if (n.kind === 'device') c.deviceKey=n.key;
    else if (n.kind === 'subsystem') c.subsystem=n.key;
    else if (n.kind.indexOf('audio') === 0 || ['stream','sink','source'].indexOf(n.kind) >= 0) {
        c.audioKey=n.key; c.processKey=r.processKey; c.groupKey=r.groupKey;
    } else if (n.kind === 'relationship' || n.kind === 'listener') {
        c.groupKey=r.groupKey || (String(r.processKey||'').indexOf('process:')===0 ? undefined : r.processKey);
        if(String(r.processKey||'').indexOf('process:')===0) c.processKey=r.processKey;
        c.remoteKey=r.remoteKey;
    }
    return c;
}
function select(s,n) {
    var out=clone(s);
    out.selectedKey=n ? n.key : '';
    out.selectedRecord=n || null;
    if(n) out.context=contextFor(n);
    out.notice='';
    return out;
}
function focus(s,n) {
    if(!n) return s;
    var out=select(s,n);
    out.history=out.history.concat([{instrument:s.instrument,focusKey:s.focusKey,selectedKey:s.selectedKey,
        context:s.context,expanded:s.expanded,collapsed:s.collapsed,isolated:s.isolated}]).slice(-24);
    out.focusKey=n.key;
    if(s.instrument==='processes' && n.kind === 'application' && out.expanded.indexOf(n.key)<0) out.expanded.push(n.key);
    out.showSearch=false; out.showPicker=false;
    return out;
}
function switchTo(s,instrument) {
    var out=clone(s);
    if(out.instrument===instrument) {out.showPicker=false;return out;}
    out.history=out.history.concat([{instrument:s.instrument,focusKey:s.focusKey,selectedKey:s.selectedKey,
        context:s.context,expanded:s.expanded,collapsed:s.collapsed,isolated:s.isolated}]).slice(-24);
    out.instrument=instrument;out.focusKey='';out.selectedKey='';out.selectedRecord=null;
    out.query='';out.filters={};out.expanded=[];out.collapsed=[];out.isolated=false;
    out.showSearch=false;out.showPicker=false;out.showAllDetails=false;
    // Context transfers by process instance/group identity, never by PID alone.
    return out;
}
function resolveContext(s,nodes) {
    if(s.selectedKey) return s;
    if(!s.context) return s;
    var c=s.context, preferred=[c.processKey,c.audioKey,c.remoteKey,c.mountKey,c.deviceKey,c.groupKey,c.subsystem,c.key];
    for(var p=0;p<preferred.length;p++) {
        if(!preferred[p]) continue;
        for(var i=0;i<nodes.length;i++) {
            var n=nodes[i], r=n.raw||{};
            if(n.key===preferred[p] || (c.processKey && r.processKey===c.processKey) || (p===5 && c.groupKey && r.groupKey===c.groupKey)) {
                var out=select(s,n);out.focusKey=n.key;
                if(s.instrument==='processes' && n.kind==='application' && out.expanded.indexOf(n.key)<0) out.expanded.push(n.key);
                return out;
            }
        }
    }
    var missing=clone(s);missing.notice='Selected context is not present in this instrument; showing available state.';
    return missing;
}
function back(s) {
    var out=clone(s);
    var panels=['showAllDetails','showSettings','showCapabilities','showHelp','showIntro','showPicker','showSearch'];
    for(var i=0;i<panels.length;i++) if(out[panels[i]]) {out[panels[i]]=false; return {state:out,close:false};}
    if(out.query) {out.query=''; return {state:out,close:false};}
    if(Object.keys(out.filters).length) {out.filters={};return {state:out,close:false};}
    if(out.history.length) {
        var prev=out.history.pop();
        Object.keys(prev).forEach(function(k){out[k]=prev[k];});
        out.selectedRecord=null;out.query='';return {state:out,close:false};
    }
    if(out.focusKey || out.selectedKey || out.isolated) {
        out.focusKey='';out.selectedKey='';out.selectedRecord=null;out.context=null;out.isolated=false;out.expanded=[];out.collapsed=[];
        return {state:out,close:false};
    }
    return {state:out,close:true};
}
function reset(s) {
    var out=fresh(s.instrument);out.frozen=s.frozen;out.privacyOverride=s.privacyOverride;return out;
}
function toggleGroup(s,key,currentlyExpanded) {
    var out=clone(s), index=out.expanded.indexOf(key);
    out.collapsed=out.collapsed||[];
    if(currentlyExpanded===true||index>=0){if(index>=0)out.expanded.splice(index,1);if(out.collapsed.indexOf(key)<0)out.collapsed.push(key);}
    else {out.expanded.push(key);out.collapsed=out.collapsed.filter(function(k){return k!==key;});}
    return out;
}
function traverse(s,nodes,delta) {
    if(!nodes.length) return s;
    var at=-1;
    for(var i=0;i<nodes.length;i++) if(nodes[i].key===s.selectedKey) {at=i;break;}
    return select(s,nodes[at<0?(delta<0?nodes.length-1:0):(at+delta+nodes.length)%nodes.length]);
}
if(typeof module!=='undefined') module.exports={fresh:fresh,select:select,focus:focus,switchTo:switchTo,resolveContext:resolveContext,back:back,reset:reset,toggleGroup:toggleGroup,traverse:traverse,contextFor:contextFor};
