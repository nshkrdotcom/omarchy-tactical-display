// Pure instrument view models. Raw observations never enter drawing code.
// All geometry classes have semantic meaning, shared across the five instruments.
var catalog = [
    {id:'connection',name:'Connection Field',shortName:'Connections',purpose:'Local programs, remote systems, and what changed.',key:'1',providers:['network','processes','machine'],
     legend:['Near plane: local applications. Horizon: remote systems. Inner field: loopback.', 'Squares are programs; diamonds are hosts; boundary apertures are listeners.', 'Arrowheads indicate connection direction. Line width indicates socket count.', 'Solid links are present. Dashed fading links ended. Width encodes socket count.', 'Enter focuses. X expands/collapses a program into its process instances. Queue size and TCP goodput appear when reported by the kernel.']},
    {id:'processes',name:'Process Topology',shortName:'Processes',purpose:'What spawned what, and which application groups consume resources.',key:'2',providers:['processes','network'],
     legend:['Application islands group cgroup/executable identities; branches follow observed parentage.', 'Enter expands a group. A focused process reveals ancestors and descendants.', 'CPU is sampled work: one logical core equals 100%. RSS includes shared resident pages.', 'The emphasis lens ranks CPU, memory, threads, I/O or group socket count.', 'Process identity tracks PID and start time across process lifecycles.']},
    {id:'machine',name:'Machine Anatomy',shortName:'Machine',purpose:'Which resource is under pressure, and who contributes to it.',key:'3',providers:['machine','processes','storage'],
     legend:['The cutaway separates compute, memory, storage, network and optional hardware.', 'Contributor lines connect processes to active subsystem resources.', 'Network links associate active socket owners with the network.', 'Resource pressure uses Linux PSI (Pressure Stall Information) when available.', 'T toggles the 60-second aggregate trend. Unavailable counters display an em dash.']},
    {id:'storage',name:'Storage / I/O Flow',shortName:'Storage',purpose:'Processes doing I/O, mounted filesystems, and their real backing devices.',key:'4',providers:['storage','processes'],
     legend:['Top plane: process I/O. Middle: mounts. Lower plane: block devices and backing layers.', 'Dashed links indicate open file descriptors between processes and mounts.', 'Solid mount/device and device/lower-device links are observed kernel topology.', 'Read and write arrows reflect measured device and process throughput.', 'Capacity is a timestamped statvfs sample on safe local filesystems. Virtual mounts may have no visible block device.']},
    {id:'audio',name:'Audio Routing',shortName:'Audio',purpose:'Which stream is routed where, through which active device.',key:'5',providers:['audio','processes'],
     legend:['Playback streams are on the left, routing nodes in the middle, endpoints on the right.', 'Capture runs from source toward recording stream. Arrows follow actual PipeWire links.', 'Dashed paths are paused, muted or non-active. A double outline identifies a default endpoint.', 'Volume indicates configured linear gain. Routes follow PipeWire links.', 'Mute/default actions are opt-in, require confirmation, revalidate serials, and offer Undo.']}
];
function info(id) {for(var i=0;i<catalog.length;i++)if(catalog[i].id===id)return catalog[i];return catalog[0];}
function array(a) {return Array.isArray(a)?a:[];}
function obj(o) {return o && typeof o==='object' && !Array.isArray(o)?o:{};}
function finite(v) {return typeof v==='number' && isFinite(v);}
function clean(v,n) {return String(v===null || v===undefined?'':v).replace(/[\x00-\x1f\x7f-\x9f\u202a-\u202e\u2066-\u2069]/g,'').slice(0,n||512);}
function bytes(n,rate) {
    if(!finite(n))return '\u2014';
    var units=['B','KiB','MiB','GiB','TiB'],i=0;
    while(Math.abs(n)>=1024 && i<4){n/=1024;i++;}
    return (i?n.toFixed(n>=100?0:1):Math.round(n))+' '+units[i]+(rate?'/s':'');
}
function percent(n) {return finite(n)?n.toFixed(1)+'%':'\u2014';}
function hash(s) {var h=2166136261;for(var i=0;i<s.length;i++){h^=s.charCodeAt(i);h=Math.imul(h,16777619);}return h>>>0;}
function alias(kind,key) {
    var prefix={application:'APP',process:'PROC',remote:'HOST',mount:'MOUNT',device:'DISK',stream:'STREAM',sink:'SINK',source:'SOURCE','audio-device':'DEVICE',listener:'PORT'}[kind]||'ENTITY';
    return prefix+'-'+('00000000'+hash(String(key)).toString(16).toUpperCase()).slice(-8);
}
function match(text,query) {
    query=clean(query,160).toLowerCase().trim();
    if(!query)return true;
    text=clean(text,12000).toLowerCase();
    return query.split(/\s+/).every(function(token){
        if(text.indexOf(token)>=0)return true;
        if(token.length<3 || token.length>24)return false;
        var at=0;for(var i=0;i<text.length && at<token.length;i++)if(text[i]===token[at])at++;
        return at===token.length;
    });
}
function searchable(r) {
    var fields=['name','pid','pids','executable','cgroup','address','path','source','local','remote','servicePort','serviceName','proto','ports','listenerPorts','nodeName','mediaClass','model'];
    return fields.map(function(f){var v=r[f];return Array.isArray(v)?v.join(' '):(typeof v==='string'||typeof v==='number'?String(v):'');}).join(' ');
}
function node(r,kind,zone,subtitle,priority) {
    return {key:String(r.key),name:clean(r.name || r.path || r.address || r.key),kind:kind,zone:zone,
        subtitle:subtitle || '',priority:finite(priority)?priority:0,raw:r,
        event:r.event || (r.closed?'closed':'steady'),closed:r.closed===true || r.active===false,
        topologyDepth:0,groupKey:r.groupKey || '',searchText:searchable(r),lod:false,related:true,match:true};
}
function edge(r,kind,source,target,label) {
    return {key:String(r.key),sourceKey:source || r.sourceKey,targetKey:target || r.targetKey,kind:kind,
        label:label || '',raw:r,direction:r.direction || 'out',weight:Math.max(1,Math.min(24,Number(r.socketCount)||1)),
        closed:r.closed===true || r.active===false,event:r.event || 'steady',muted:r.mute===true,
        state:r.state || '',related:true,match:true};
}
function indexed(rows) {var out={};array(rows).forEach(function(r){if(r && r.key)out[r.key]=r;});return out;}
function connection(frame,state,settings) {
    var data=obj(frame.network),nodes=[],edges=[],filter=obj(state.filters), expanded=array(state.expanded), processes=array(data.processes),
        instances=array(data.instances), instanceLinks=array(data.instanceLinks), links=array(data.links), listeners=array(data.listeners);
    var useInstances={};expanded.forEach(function(k){useInstances[k]=true;});
    if(state.context && state.context.processKey) {
        var instance=instances.filter(function(n){return n.key===state.context.processKey;})[0];
        if(instance)useInstances[instance.groupKey]=true;
    }
    function allowLink(l) {
        if(!settings.loopback && l.kind==='loopback')return false;
        if(filter.direction && filter.direction!=='any' && l.kind!==filter.direction)return false;
        if(filter.protocol && filter.protocol!=='any' && l.proto!==filter.protocol)return false;
        if(filter.state==='live' && !l.active)return false;
        if(filter.state==='closed' && l.active)return false;
        if(filter.state==='listeners')return false;
        return true;
    }
    var activeLinks=links.filter(function(l){return !useInstances[l.processKey] && allowLink(l);});
    instanceLinks.forEach(function(l){if(useInstances[l.groupKey] && allowLink(l))activeLinks.push(l);});
    var used={},remoteUsed={},freshEndpoints={};
    activeLinks.forEach(function(l){
        used[l.processKey]=true;remoteUsed[l.remoteKey]=true;
        // A newly observed relationship must remain visually discoverable even
        // when its application/remote already existed or has low socket count.
        // Propagate the finite acquisition event onto both endpoint nodes so the
        // layout rank protects them from density-budget suppression.
        if(l.event==='opened') {freshEndpoints[l.processKey]=true;freshEndpoints[l.remoteKey]=true;}
    });
    function markFresh(n) {
        if(freshEndpoints[n.key]) {n.event='opened';n.priority=Math.max(n.priority,100000);}
        return n;
    }
    var allowedListeners=settings.listeners?listeners.filter(function(l){return (!filter.protocol || filter.protocol==='any'||filter.protocol===l.proto) && (!filter.state||filter.state==='listeners'||filter.state==='live'&&l.active||filter.state==='closed'&&!l.active);}):[];
    allowedListeners.forEach(function(l){used[l.processKey]=true;});
    processes.forEach(function(p){
        if(!useInstances[p.key] && (used[p.key] || p.key===state.selectedKey || p.key===state.focusKey)) {
            nodes.push(markFresh(node(p,'application','near',p.socketCount+' sockets / '+array(p.pids).length+' processes',p.socketCount)));
        }
        if(useInstances[p.key]) {
            var group=markFresh(node(p,'application','core',array(p.pids).length+' processes',2));group.lod=true;
            nodes.push(group);
        }
    });
    instances.forEach(function(p){if(useInstances[p.groupKey] && (used[p.key]||p.key===state.selectedKey||state.context && p.key===state.context.processKey)){
        var pid=p.pid||array(p.pids)[0],n=markFresh(node(p,'process','near',(pid?'PID '+pid:'PID unavailable')+' / '+p.socketCount+' sockets',p.socketCount));n.groupKey=p.groupKey;nodes.push(n);edges.push(edge({key:'net-member:'+p.key,sourceKey:p.groupKey,targetKey:p.key},'membership'));
    }});
    array(data.remotes).forEach(function(r){if(remoteUsed[r.key]){
        nodes.push(markFresh(node(r,'remote',r.scope==='loopback'?'local':'horizon',array(r.processKeys).length+' apps / '+array(r.ports).slice(0,4).join(', '),r.socketCount)));
    }});
    allowedListeners.forEach(function(l){
        // An expanded application still has an explicit boundary aperture; the group is retained for this structural link.
        if(useInstances[l.processKey] && !nodes.some(function(n){return n.key===l.processKey;})) {
            var p=processes.filter(function(p){return p.key===l.processKey;})[0];if(p)nodes.push(node(p,'application','core',array(p.pids).length+' processes',1));
        }
        nodes.push(node(l,'listener','boundary',l.role==='bound-datagram'?'UDP binding':'Listening',1));
        edges.push(edge({key:'aperture:'+l.key,sourceKey:l.processKey,targetKey:l.key,active:l.active},'listener'));
    });
    activeLinks.forEach(function(l){edges.push(edge(l,'relationship',l.processKey,l.remoteKey,String(l.proto||'').toUpperCase()+' / '+l.servicePort+' \u00d7 '+l.socketCount));});
    var s=obj(data.summary),sys=obj(frame.system);
    return {nodes:nodes,edges:edges,status:[['relationships',s.relationships],['applications',s.processes],['remote systems',s.remoteSystems],['listeners / bindings',s.listeners],['RX',bytes(sys.netRxBps,true)],['TX',bytes(sys.netTxBps,true)]],
        empty:'No visible remote relationships. Local listeners and loopback remain meaningful; change lenses or open a connection.',
        note:'Direction estimated from listeners · Line width indicates socket count · RX/TX is host-wide'};
}
function processTopology(frame,state,settings) {
    var rows=array(frame.processes),groups=array(frame.groups),byPid=indexed(rows), nodes=[],edges=[],emphasis=state.filters.emphasis||'cpu',expanded=array(state.expanded),context=state.context||{};
    var wanted=context.processKey || (String(state.focusKey).indexOf('process:')===0?state.focusKey:'');
    var memberOf={};groups.forEach(function(g){array(g.processKeys).forEach(function(k){memberOf[k]=g.key;});});
    var expandSet={};expanded.forEach(function(k){expandSet[k]=true;});
    if(wanted && memberOf[wanted])expandSet[memberOf[wanted]]=true;
    function score(r){return emphasis==='memory'?(r.rssBytes||0):emphasis==='threads'?(r.threads||0):emphasis==='network'?(r.networkSockets||r.groupNetworkSockets||0):emphasis==='io'?((r.readBps||0)+(r.writeBps||0)):(r.cpuPercent||0);}
    function sub(r){return emphasis==='memory'?bytes(r.rssBytes):emphasis==='threads'?r.threads+' threads':emphasis==='network'?(finite(r.networkSockets)?r.networkSockets:finite(r.groupNetworkSockets)?r.groupNetworkSockets:'unavailable')+' group sockets':emphasis==='io'?'R '+bytes(r.readBps,true)+' / W '+bytes(r.writeBps,true):percent(r.cpuPercent)+' CPU';}
    groups.forEach(function(g){nodes.push(node(g,'application','island',sub(g)+' / '+array(g.pids).length+' processes',score(g)));});
    var groupEdges={};
    rows.forEach(function(p){
        if(state.filters.lens==='active' && !(score(p)>0) && p.key!==wanted)return;
        var n=node(p,'process','branch','PID '+p.pid+' / '+sub(p),score(p));
        n.groupKey=p.groupKey;n.lod=(!expandSet[p.groupKey] && (rows.length>72 || array(state.collapsed).indexOf(p.groupKey)>=0)) && !state.query;
        var ancestor=p,seen={},depth=0;
        while(ancestor && ancestor.parentKey && byPid[ancestor.parentKey] && byPid[ancestor.parentKey].groupKey===p.groupKey && !seen[ancestor.parentKey] && depth<12){seen[ancestor.parentKey]=true;depth++;ancestor=byPid[ancestor.parentKey];}
        n.topologyDepth=depth;
        nodes.push(n);
        if(p.parentKey && byPid[p.parentKey]){
            edges.push(edge({key:'parent:'+p.key,sourceKey:p.parentKey,targetKey:p.key,provenance:'/proc/pid/stat PPID + validated start time'},'parent'));
            var parentGroup=byPid[p.parentKey].groupKey;
            if(parentGroup!==p.groupKey){
                var gk=parentGroup+'>'+p.groupKey;
                if(!groupEdges[gk])groupEdges[gk]=edge({key:'group-parent:'+gk,sourceKey:parentGroup,targetKey:p.groupKey},'group-parent',null,null,'spawned');
            }
        }
        edges.push(edge({key:'member:'+p.key,sourceKey:p.groupKey,targetKey:p.key},'membership'));
    });
    Object.keys(groupEdges).forEach(function(k){edges.push(groupEdges[k]);});
    return {nodes:nodes,edges:edges,status:[['process instances',rows.filter(function(p){return !p.closed;}).length],['application groups',groups.length],['emphasis',emphasis],['load 1m',array(obj(frame.system).load)[0]]],
        empty:'No readable process instances. Check the process capability for procfs permissions.',note:'Branches show parentage · Groups cluster by cgroup, executable, and ancestry'};
}
function machineAnatomy(frame,state,settings) {
    var sys=obj(frame.system),mem=obj(sys.memory),storage=obj(frame.storage),summary=obj(storage.summary),groups=array(frame.groups),hardware=obj(frame.hardware),nodes=[],edges=[];
    var resources=[
        {key:'subsystem:cpu',name:'COMPUTE',value:percent(sys.cpuPercent),subtitle:array(sys.cores).length+' logical CPUs',metric:'cpuPercent',scope:'CPU work / one core=100% for contributors',zone:'compute'},
        {key:'subsystem:memory',name:'MEMORY',value:bytes(mem.usedBytes),subtitle:bytes(mem.availableBytes)+' available',metric:'rssBytes',scope:'resident memory; shared pages can overlap',zone:'memory'},
        {key:'subsystem:storage',name:'STORAGE',value:'R '+bytes(summary.readBps,true),subtitle:'W '+bytes(summary.writeBps,true),metric:'io',scope:'Process storage I/O accounting',zone:'storage'},
        {key:'subsystem:network',name:'NETWORK',value:'RX '+bytes(sys.netRxBps,true),subtitle:'TX '+bytes(sys.netTxBps,true),metric:'networkSockets',scope:'Active socket associations',zone:'network'}
    ];
    if(array(hardware.gpus).length)resources.push({key:'subsystem:gpu',name:'GPU',value:percent(hardware.gpus[0].utilizationPercent),subtitle:bytes(hardware.gpus[0].memoryUsedBytes)+' VRAM',metric:'',scope:hardware.gpus[0].source,zone:'gpu'});
    if(array(hardware.thermals).length) {
        var hot=hardware.thermals.slice().sort(function(a,b){return b.temperatureC-a.temperatureC;})[0];
        resources.push({key:'subsystem:thermal',name:'THERMAL',value:hot.temperatureC.toFixed(1)+' \u00b0C',subtitle:'Highest observed sensor',metric:'',scope:'Hardware monitoring sensors (hwmon)',zone:'thermal'});
    }
    var contributors={},focusedResource=state.focusKey||state.selectedKey||(state.context||{}).subsystem;
    resources.forEach(function(r){
        var psiName=r.metric==='cpuPercent'?'cpu':r.metric==='rssBytes'?'memory':r.metric==='io'?'io':'';
        var psi=obj(obj(obj(sys.pressure)[psiName]).some);
        var raw={key:r.key,name:r.name,value:r.value,scope:r.scope,pressure:psi.avg10,details:r.key==='subsystem:cpu'?sys:r.key==='subsystem:memory'?mem:r.key==='subsystem:storage'?storage:r.key==='subsystem:network'?{interfaces:sys.interfaces,scope:sys.networkScope}:hardware};
        var n=node(raw,'subsystem',r.zone,r.value+' / '+r.subtitle,100);n.value=r.value;n.pressure=psi.avg10;
        if(finite(psi.avg10)&&psi.avg10>=5){n.name+=' / PRESSURE';n.subtitle='PSI '+psi.avg10.toFixed(1)+'% stalled / '+r.value;}
        nodes.push(n);
        if(!r.metric)return;
        function val(g){return r.metric==='io'?(g.readBps||0)+(g.writeBps||0):Number(g[r.metric])||0;}
        var candidates=groups.slice().sort(function(a,b){return val(b)-val(a);}).filter(function(g){return val(g)>0 || state.context && state.context.groupKey===g.key;}).slice(0,6);
        if(state.context && state.context.groupKey){var chosen=groups.filter(function(g){return g.key===state.context.groupKey;})[0];if(chosen && !candidates.some(function(g){return g.key===chosen.key;}))candidates.push(chosen);}
        candidates.forEach(function(g){
            var label=r.metric==='cpuPercent'?percent(g.cpuPercent):r.metric==='rssBytes'?bytes(g.rssBytes):r.metric==='io'?'R '+bytes(g.readBps,true)+' / W '+bytes(g.writeBps,true):g.networkSockets+' sockets';
            if(!contributors[g.key]){var c=node(g,'application','contributor',label,val(g));c.resourceZone=r.zone;contributors[g.key]=c;nodes.push(c);}
            if(r.key===focusedResource){contributors[g.key].subtitle=label;contributors[g.key].resourceZone=r.zone;contributors[g.key].importance=val(g);}
            edges.push(edge({key:'contributes:'+g.key+':'+r.key,sourceKey:g.key,targetKey:r.key,provenance:r.scope,value:val(g)},'contribution',null,null,label));
        });
    });
    return {nodes:nodes,edges:edges,status:[['CPU',percent(sys.cpuPercent)],['memory',bytes(mem.usedBytes)],['cache',bytes(mem.cacheBytes)],['swap',bytes(mem.swapUsedBytes)],['trend',state.trend?'last 60 seconds':'instant state']],
        empty:'Kernel resource counters are unavailable. Inspect capabilities for the reason.',note:'Resource utilization and contributors · PSI measures stall pressure'};
}
function storageFlow(frame,state,settings) {
    var data=obj(frame.storage),nodes=[],edges=[],filter=obj(state.filters),lens=filter.lens||'all',rows=array(data.contributors);
    rows.forEach(function(p){
        var reading=(p.readBps||0)>0,writing=(p.writeBps||0)>0;
        if(lens==='reads'&&!reading||lens==='writes'&&!writing)return;
        var n=node(p,'process','io-process','R '+bytes(p.readBps,true)+' / W '+bytes(p.writeBps,true),(p.readBps||0)+(p.writeBps||0));
        n.lod=lens==='mounts'||lens==='devices';nodes.push(n);
    });
    array(data.mounts).forEach(function(m){
        var sub=m.fsType+' / '+(m.capacity?bytes(m.capacity.availableBytes)+' free':'capacity unavailable');
        var n=node(m,'mount','mount',sub,m.path==='/'?100:1);n.lod=lens==='devices';nodes.push(n);
    });
    array(data.devices).forEach(function(d){
        var n=node(d,'device',d.partition||array(d.slaves).length?'logical-device':'device','R '+bytes(d.readBps,true)+' / W '+bytes(d.writeBps,true),(d.readBps||0)+(d.writeBps||0));
        n.lod=lens==='mounts';nodes.push(n);
    });
    array(data.links).forEach(function(l){edges.push(edge(l,l.kind));});
    var s=obj(data.summary);
    return {nodes:nodes,edges:edges,status:[['mounts',array(data.mounts).length],['block devices',array(data.devices).length],['read',bytes(s.readBps,true)],['write',bytes(s.writeBps,true)],['process I/O',rows.length+' readable contributors']],
        empty:'No storage topology is available in this namespace. Virtual mounts may not expose block devices.',
        note:'Dashed links indicate open file descriptors · Rates reflect process and disk I/O'};
}
function audioRouting(frame,state,settings) {
    var data=obj(frame.audio),nodes=[],edges=[],lens=state.filters.lens||'all';
    array(data.nodes).forEach(function(a){
        var media=a.mediaClass||'',kind=media==='Audio/Sink'?'sink':media==='Audio/Source'?'source':media.indexOf('Stream/')===0?'stream':'audio-node';
        var capture=media==='Audio/Source'||media.indexOf('Stream/Input')===0;
        var zone=kind==='sink'||kind==='source'?'audio-endpoint':kind==='stream'?(capture?'audio-capture':'audio-playback'):'audio-route';
        var n=node(a,kind,zone,(a.default?'DEFAULT / ':'')+(a.mute===true?'MUTED':a.state)+(finite(a.volume)?' / gain '+a.volume.toFixed(2):''),a.state==='running'?10:1);
        n.filtered=lens==='playback'&&capture || lens==='capture'&&!capture || lens==='muted'&&a.mute!==true || lens==='devices'&&kind==='stream';
        nodes.push(n);
        if(a.deviceKey)edges.push(edge({key:'audio-device:'+a.key,sourceKey:a.key,targetKey:a.deviceKey,provenance:'PipeWire device.id'},'device-link'));
    });
    array(data.devices).forEach(function(d){nodes.push(node(d,'audio-device','audio-hardware','Physical device / PipeWire identity',2));});
    var byKey=indexed(array(data.nodes));
    var aggregate={};
    array(data.links).forEach(function(l){
        var source=byKey[l.sourceKey]||{},target=byKey[l.targetKey]||{},k=l.sourceKey+'>'+l.targetKey;
        if(!aggregate[k]){
            var e=edge(l,'audio-link',null,null,'');e.muted=source.mute===true||target.mute===true;e.channels=0;aggregate[k]=e;
        }
        aggregate[k].channels++;aggregate[k].weight=aggregate[k].channels;
        aggregate[k].label=aggregate[k].channels+' channel link'+(aggregate[k].channels===1?'':'s')+' / '+l.state;
    });
    Object.keys(aggregate).forEach(function(k){edges.push(aggregate[k]);});
    return {nodes:nodes,edges:edges,status:[['audio nodes',array(data.nodes).length],['routing links',array(data.links).length],['devices',array(data.devices).length],['levels','not measured']],
        empty:'No live PipeWire audio graph. The audio capability explains missing tools, session access, or an empty graph.',
        note:'Active signal paths via PipeWire · Dashed paths indicate muted or dormant routes'};
}
function build(frame,state,settings) {
    frame=obj(frame);state=state||{};state.filters=obj(state.filters);settings=settings||{};
    var mode=state.instrument||'connection',view;
    if(mode==='processes')view=processTopology(frame,state,settings);
    else if(mode==='machine')view=machineAnatomy(frame,state,settings);
    else if(mode==='storage')view=storageFlow(frame,state,settings);
    else if(mode==='audio')view=audioRouting(frame,state,settings);
    else view=connection(frame,state,settings);
    view.instrument=mode;view.info=info(mode);view.frame=frame;
    var lookup=indexed(view.nodes),focus=state.focusKey||state.selectedKey,adj={},related={};
    view.edges.forEach(function(e){
        if(!adj[e.sourceKey])adj[e.sourceKey]=[];if(!adj[e.targetKey])adj[e.targetKey]=[];
        adj[e.sourceKey].push(e.targetKey);adj[e.targetKey].push(e.sourceKey);
    });
    if(focus){
        related[focus]=true;
        var selectedEdge=view.edges.filter(function(e){return e.key===focus;})[0];
        if(selectedEdge){related[selectedEdge.sourceKey]=true;related[selectedEdge.targetKey]=true;}

        (adj[focus]||[]).forEach(function(k){related[k]=true;});
        if(mode==='connection' && lookup[focus] && lookup[focus].kind==='application'){
            // Follow membership, never traverse back through shared remotes into unrelated apps.
            view.nodes.forEach(function(n){if(n.groupKey===focus){related[n.key]=true;(adj[n.key]||[]).forEach(function(k){related[k]=true;});}});
        }
        if(mode==='connection' && lookup[focus] && lookup[focus].kind==='listener'){
            var listener=lookup[focus].raw,owner=listener.processKey;
            related[owner]=true;
            view.edges.forEach(function(e){if(e.kind==='relationship' && (e.raw.processKey===owner||e.raw.groupKey===owner) && e.raw.kind==='inbound' && e.raw.servicePort===listener.port)related[e.targetKey]=true;});
        }
        if(mode==='audio' && lookup[focus]){
            // Follow actual directed signal paths in each direction separately.
            // Never hop sideways through a shared mixer into unrelated streams.
            var forward={},backward={},seeds=[focus];
            view.edges.forEach(function(e){
                if(e.kind==='audio-link'){
                    if(!forward[e.sourceKey])forward[e.sourceKey]=[];forward[e.sourceKey].push(e.targetKey);
                    if(!backward[e.targetKey])backward[e.targetKey]=[];backward[e.targetKey].push(e.sourceKey);
                } else if(e.kind==='device-link' && e.targetKey===focus) seeds.push(e.sourceKey);
            });
            [forward,backward].forEach(function(graph){
                var queue=seeds.slice(),visited={},i=0;
                while(i<queue.length && i<24000){var key=queue[i++];if(visited[key])continue;visited[key]=true;related[key]=true;(graph[key]||[]).forEach(function(k){queue.push(k);});}
            });
            view.edges.forEach(function(e){if(e.kind==='device-link' && related[e.sourceKey])related[e.targetKey]=true;});
        }
        if(mode==='processes' && state.focusKey){
            // Parent/descendant focus excludes unrelated siblings while preserving an application's context.
            var tree={};view.edges.filter(function(e){return e.kind==='parent';}).forEach(function(e){if(!tree[e.sourceKey])tree[e.sourceKey]=[];tree[e.sourceKey].push(e.targetKey);});
            var todo=[focus],seen={},qi=0;
            while(qi<todo.length && qi<16384){var at=todo[qi++];if(seen[at])continue;seen[at]=true;related[at]=true;(tree[at]||[]).forEach(function(k){todo.push(k);});}
            var current=lookup[focus],hops=0;
            while(current && current.raw.parentKey && hops++<128){related[current.raw.parentKey]=true;current=lookup[current.raw.parentKey];}
        }
    }
    view.nodes.forEach(function(n){
        n.selected=n.key===state.selectedKey;n.focused=n.key===state.focusKey;
        n.related=!focus||!!related[n.key];n.match=match(n.searchText,state.query||'');
        if(settings.privacy && n.kind!=='subsystem'){
            n.name=alias(n.kind,n.key);
            n.match=n.match||match(n.name,state.query||'');
            // Never leave PID/path/address-bearing subtitles in screen-share mode.
            n.subtitle=n.kind==='remote'?array(n.raw.processKeys).length+' related applications':n.kind==='listener'?String(n.raw.proto || '').toUpperCase()+' '+n.raw.port:n.kind==='process'?'CPU '+percent(n.raw.cpuPercent)+' / RSS '+bytes(n.raw.rssBytes):n.kind==='application'?array(n.raw.pids).length+' processes':'Identity hidden / topology retained';
        }
        if(n.selected || n.focused || (state.query && n.match) || (state.focusKey && n.related))n.lod=false;
    });
    view.edges.forEach(function(e){e.related=!focus||!!related[e.sourceKey]&&!!related[e.targetKey];e.match=!!(lookup[e.sourceKey]&&lookup[e.sourceKey].match||lookup[e.targetKey]&&lookup[e.targetKey].match);});
    view.allNodes=view.nodes;
    view.visibleNodes=view.nodes.filter(function(n){return !n.lod && (!n.filtered || n.selected) && (!state.isolated||n.related) && (!state.query||n.match||n.selected||state.focusKey&&n.related);});
    var pickedEdge=view.edges.filter(function(e){return e.key===state.selectedKey;})[0];
    view.selection=lookup[state.selectedKey] || (pickedEdge ? {key:pickedEdge.key,kind:'relationship',name:pickedEdge.label||'Observed relationship',subtitle:pickedEdge.kind,raw:pickedEdge.raw,event:pickedEdge.event} : null);
    view.edges.forEach(function(e){e.selected=e.key===state.selectedKey;});
    view.results=view.nodes.filter(function(n){return !n.filtered && n.match && (!state.isolated||n.related);}).sort(function(a,b){return a.kind.localeCompare(b.kind)||a.key.localeCompare(b.key);});
    view.capabilities=view.info.providers.map(function(id){return obj(obj(frame.capabilities)[id]);});
    view.degraded=view.capabilities.filter(function(c){return ['available','inactive'].indexOf(c.status)<0;});
    view.hiddenCount=view.nodes.length-view.visibleNodes.length;
    return view;
}
if(typeof module!=='undefined') module.exports={catalog:catalog,info:info,build:build,match:match,bytes:bytes,percent:percent,alias:alias,clean:clean,hash:hash};
