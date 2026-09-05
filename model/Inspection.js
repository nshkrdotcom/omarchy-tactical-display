// Presentation whitelist: identifiers and exact provenance without arbitrary argv or raw rich text.
function text(value) {return String(value===null||value===undefined?'':value).replace(/[\x00-\x1f\x7f-\x9f\u202a-\u202e\u2066-\u2069]/g,'').slice(0,4096);}
function finite(n){return typeof n==='number'&&isFinite(n);}
function bytes(n,rate){if(!finite(n))return 'Unavailable';var units=['B','KiB','MiB','GiB','TiB'],i=0;while(Math.abs(n)>=1024&&i<4){n/=1024;i++;}return (i?n.toFixed(2):Math.round(n))+' '+units[i]+(rate?'/s':'');}
function value(v){if(v===null||v===undefined)return 'Unavailable';if(Array.isArray(v))return v.map(value).join(', ');if(typeof v==='object')return JSON.stringify(v);return text(v);}
function fields(entity, data, privacy, frame) {
    if(!entity)return [];
    var r=data||entity.raw||{},out=[],kind=entity.kind;
    function add(label,v,source,classification,sensitive) {
        if(v===undefined)return;
        out.push({label:label,value:privacy&&sensitive?'Hidden in privacy mode':value(v),source:source||'',classification:classification||'observed'});
    }
    function rate(label,v,source){add(label,bytes(v,true),source,'derived');}
    function exact(label,v,source,sensitive){add(label,v,source,'observed',sensitive);}
    exact('Identity',r.key||entity.key,'Stable instance identifier',true);
    if(r.closed||entity.closed)exact('Lifecycle','Ended; retained briefly for inspection','Bounded snapshot diff');
    exact('Process ID',r.pid,'/proc/<pid>/stat; includes start-time identity',true);
    exact('Process IDs',r.pids,'Readable process membership',true);
    exact('Parent PID',r.ppid,'/proc/<pid>/stat; parent start-time check',true);
    exact('Kernel start ticks',r.startTicks,'/proc/<pid>/stat; ticks since boot',true);
    exact('Executable',r.executable,'/proc/<pid>/exe',true);
    exact('Cgroup',r.cgroup,'/proc/<pid>/cgroup',true);
    add('Grouping',r.groupProvenance||((kind==='application')?r.provenance:undefined),'Cgroup / executable / runtime ancestry','derived');
    exact('State',r.states||r.state,r.proto?'Kernel socket state':'Kernel / PipeWire state');
    if(r.ageMs!==undefined)add('Observed age',(r.ageMs/1000).toFixed(1)+' s','Monotonic first observation in this session','derived');
    if(r.cpuPercent!==undefined)add('CPU work',finite(r.cpuPercent)?r.cpuPercent.toFixed(2)+'% (100% = one core)':'Unavailable until two samples','Monotonic /proc/<pid>/stat CPU delta','derived');
    if(r.rssBytes!==undefined)exact('Resident memory',bytes(r.rssBytes),'/proc/<pid>/stat; shared resident pages can overlap');
    exact('Threads',r.threads,'/proc/<pid>/stat');
    if(r.readBps!==undefined)rate('Read',r.readBps,kind==='device'?'Monotonic diskstats sectors x 512':'Monotonic /proc/<pid>/io read_bytes; storage accounted');
    if(r.writeBps!==undefined)rate('Write',r.writeBps,kind==='device'?'Monotonic diskstats sectors x 512':'Monotonic /proc/<pid>/io write_bytes; storage accounted');
    if(r.readBytes!==undefined)exact('Cumulative read',bytes(r.readBytes),kind==='device'?'diskstats sectors x 512':'/proc/<pid>/io');
    if(r.writeBytes!==undefined)exact('Cumulative write',bytes(r.writeBytes),kind==='device'?'diskstats sectors x 512':'/proc/<pid>/io');
    exact('Protocol',r.proto,'Kernel socket family');
    exact('Local endpoint',r.local,'Kernel address/port tuple',true);
    exact('Remote endpoint',r.remote||r.address,'Kernel address/port tuple',true);
    exact('Address family',r.family===undefined?undefined:'IPv'+r.family,'Kernel socket family');
    if(r.nameSource!==undefined)add('Display-name source',privacy?'Identity hidden':r.nameSource,'Local alias / hosts / optional unverified PTR','enriched',true);
    if(r.nameTrusted!==undefined)add('Name trust',r.nameTrusted?'Local hostname mapping':'Reverse DNS lookup (PTR)','Enrichment policy','enriched');
    if(r.offline && !privacy) {
        add('Offline ASN',r.offline.asn,r.offline.provenance,'enriched',true);
        add('Offline organization',r.offline.organization,r.offline.provenance,'enriched',true);
        add('Approximate country',r.offline.country,r.offline.provenance,'enriched',true);
    }
    exact('Port / service',r.servicePort===undefined?r.port:r.servicePort,'Kernel endpoint tuple');
    add('Service name',r.serviceName||undefined,'/etc/services port mapping','enriched');
    exact('Ports',r.ports||r.listenerPorts,'Observed endpoints');
    exact('Live socket count',r.socketCount,'Aggregated kernel socket records');
    exact('New / closed sockets',r.newCount===undefined?undefined:r.newCount+' / '+r.closedCount,'Bounded monotonic snapshot diff');
    exact('Owners / members',r.processKeys,'Readable fd ownership / application membership',true);
    if(r.queueBytes!==undefined)exact('Kernel queues',bytes(r.queueBytes),'Socket buffer queue occupancy');
    if(r.ackedBps!==undefined)rate('TCP acknowledged goodput',r.ackedBps,'inet_diag tcp_info cumulative bytes_acked delta');
    if(r.receivedBps!==undefined)rate('TCP received goodput',r.receivedBps,'inet_diag tcp_info cumulative bytes_received delta');
    if(r.rttMs!==undefined)exact('TCP RTT',r.rttMs===null?'Unavailable':r.rttMs+' ms','inet_diag tcp_info tcpi_rtt / 1000');
    if(kind==='relationship'&&r.proto)add('Connection origin',r.kind+'; '+(r.provenance||''),'Matched via listener, protocol, and socket owner','inferred');
    if(r.sharedOwnership)exact('Attribution','Shared across groups; per-group goodput suppressed','Readable fd ownership');
    if(r.remoteKeys)exact('Related remotes',r.remoteKeys.length,'Distinct normalized IP identities');
    exact('Mount path',r.path,'/proc/self/mountinfo',true);
    exact('Filesystem',r.fsType,'/proc/self/mountinfo');
    exact('Mount source',r.source&&kind==='mount'?r.source:undefined,'/proc/self/mountinfo',true);
    exact('Major:minor',r.majorMinor,'Kernel device number');
    exact('Mount ID',r.mountId,'/proc/self/mountinfo');
    exact('Backing layers',r.slaves,'sysfs backing devices',true);
    if(r.capacity){exact('Capacity',bytes(r.capacity.totalBytes),'statvfs; local filesystem only');exact('Available',bytes(r.capacity.availableBytes),'statvfs f_bavail x f_frsize');exact('Capacity sampled at',r.capacity.sampledAt,'Monotonic seconds; cached at most 15 s between probes');}
    if(kind==='mount')exact('Per-mount throughput','Not measured','Kernel storage accounting');
    if(r.busyPercent!==undefined)add('Device busy proxy',finite(r.busyPercent)?r.busyPercent.toFixed(2)+'%':'Unavailable','diskstats io_ticks delta','derived');
    exact('I/O in flight',r.inFlight,'diskstats instantaneous request count');
    if(r.readAwaitMs!==undefined)add('Read request latency proxy',finite(r.readAwaitMs)?r.readAwaitMs.toFixed(3)+' ms':'Unavailable','delta read request ms / completed reads','derived');
    if(r.writeAwaitMs!==undefined)add('Write request latency proxy',finite(r.writeAwaitMs)?r.writeAwaitMs.toFixed(3)+' ms':'Unavailable','delta write request ms / completed writes','derived');
    exact('Media class',r.mediaClass,'PipeWire node properties');
    exact('PipeWire object ID',r.objectId,'Current runtime ID; actions revalidate serial',true);
    exact('PipeWire serial',r.serial,'PipeWire object.serial + core epoch',true);
    exact('Default endpoint',r.default,'PipeWire default metadata');
    exact('Mute',r.mute,'PipeWire Props parameter');
    exact('Linear gain',r.volume,'PipeWire node volume properties');
    exact('Sample rate',r.sampleRate===undefined?undefined:r.sampleRate+' Hz','PipeWire node/format metadata when provided');
    exact('Sample format',r.sampleFormat,'PipeWire Format parameter when provided');
    if(r.processKey&&(String(kind).indexOf('audio')===0||kind==='stream'||kind==='sink'||kind==='source'))add('Process association',r.processKey,'PipeWire application.process.id joined to current process instance','reported',true);
    if(kind==='subsystem'){
        exact('Current state',r.value,'Selected resource snapshot');
        add('Meaning',r.scope,'Subsystem resource accounting','derived');
        if(r.pressure!==undefined)exact('PSI some / avg10',finite(r.pressure)?r.pressure+'% stalled':'Unavailable','/proc/pressure; 10-second rolling average');
        var d=r.details||{};
        if(entity.key==='subsystem:cpu'){exact('Logical CPUs',(d.cores||[]).length,'/proc/stat / sysfs topology');exact('Load averages',d.load,'/proc/loadavg');}
        if(entity.key==='subsystem:memory'){
            ['totalBytes','availableBytes','usedBytes','cacheBytes','buffersBytes','swapUsedBytes','swapTotalBytes'].forEach(function(k){if(d[k]!==undefined)add(k,bytes(d[k]),'/proc/meminfo; used = total - available','derived');});
        }
        if(entity.key==='subsystem:network')exact('Counter scope',d.scope,'/proc/net/dev; virtual interfaces can double count');
        if(entity.key==='subsystem:storage')exact('Aggregate scope',(d.summary||{}).aggregateScope,'diskstats; physical whole leaf devices only');
        if(entity.key==='subsystem:gpu')(d.gpus||[]).forEach(function(g){add(privacy?'GPU':g.name,JSON.stringify({utilizationPercent:g.utilizationPercent,memoryUsedBytes:g.memoryUsedBytes,memoryTotalBytes:g.memoryTotalBytes,temperatureC:g.temperatureC}),g.source,'observed');});
        if(entity.key==='subsystem:thermal')(d.thermals||[]).forEach(function(t){exact(privacy?'Thermal sensor':t.name,t.temperatureC+' C',t.source||'hwmon sysfs');});
    }
    if(r.provenance&&kind!=='application'&&kind!=='relationship')add('Provenance',typeof r.provenance==='object'?JSON.stringify(r.provenance):r.provenance,'Provider declaration','source',privacy);
    return out;
}
function socketRows(records, privacy) {
    return (Array.isArray(records)?records:[]).map(function(r,i){
        var title=String(r.proto||'').toUpperCase()+' '+(r.state||'')+' / '+(privacy?'ENDPOINTS HIDDEN':text(r.local)+' -> '+text(r.remote));
        var owner=(r.owners||[]).map(function(o){return privacy?'OWNER':text(o.name||o.process||'process')+' PID '+o.pid;}).join(', ')||'unattributed';
        return {title:title,details:'Owner: '+owner+'\nQueue '+bytes(r.queueBytes)+'; RTT '+(finite(r.rttMs)?r.rttMs+' ms':'unavailable')+'\nAck '+bytes(r.ackedBps,true)+'; received '+bytes(r.receivedBps,true),source:text(r.source||'kernel')+'; '+text(r.directionSource||'direction unavailable')};
    });
}
function related(view, entity) {
    if(!entity)return [];
    var keys={},edgeBy={},nodes={};
    (view.allNodes||[]).forEach(function(n){nodes[n.key]=n;});
    (view.edges||[]).forEach(function(e){if(e.key===entity.key||e.sourceKey===entity.key||e.targetKey===entity.key){keys[e.sourceKey]=true;keys[e.targetKey]=true;edgeBy[e.key]=e;}});
    delete keys[entity.key];
    var out=Object.keys(keys).sort().map(function(k){var n=nodes[k];return n?{key:k,name:n.name,kind:n.kind}:null;}).filter(function(n){return n!==null;});
    Object.keys(edgeBy).sort().forEach(function(k){var e=edgeBy[k];if(e.kind==='relationship'||e.kind==='audio-link')out.push({key:k,name:e.label||'Relationship',kind:e.kind});});
    return out.slice(0,256);
}
function clipboard(entity,data,privacy,frame){return entity?entity.name+'\n'+fields(entity,data,privacy,frame).map(function(r){return r.label+': '+r.value+' ['+r.classification+'; '+r.source+']';}).join('\n'):'';}
if(typeof module!=='undefined')module.exports={fields:fields,socketRows:socketRows,related:related,clipboard:clipboard};
