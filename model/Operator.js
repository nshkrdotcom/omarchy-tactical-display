// Pure, bounded operator evidence. No provider reads, side effects or raw-frame history.
function finite(v) { return typeof v === 'number' && isFinite(v); }
function measured(v) { return finite(v) && v >= 0 ? v : null; }
function rows(v) { return Array.isArray(v) ? v : []; }
function clean(v) { return String(v || '').replace(/[\x00-\x1f\x7f-\x9f\u202a-\u202e\u2066-\u2069]/g, '').slice(0,240); }
function displayName(row, privacy) {
    if (!privacy || row.kind === 'subsystem') return clean(row.name || row.kind || 'Observed entity');
    var key = String(row.entityKey || row.key || ''), hash = 2166136261;
    for (var i=0; i<key.length; i++) { hash ^= key.charCodeAt(i); hash = Math.imul(hash,16777619); }
    // This identity vocabulary is shared with InstrumentModel.alias; parity is tested.
    var prefix={application:'APP',process:'PROC',remote:'HOST',mount:'MOUNT',device:'DISK',stream:'STREAM',sink:'SINK',source:'SOURCE','audio-device':'DEVICE',listener:'PORT'}[row.kind]||'ENTITY';
    return prefix + '-' + ('00000000'+(hash>>>0).toString(16).toUpperCase()).slice(-8);
}
function providerState(frame, id, now) {
    var c = (frame.capabilities || {})[id];
    if (!c) return 'unavailable';
    if (c.status !== 'available' && c.status !== 'partial') return c.status === 'inactive' ? 'inactive' : c.status === 'stale' ? 'stale' : 'unavailable';
    now = finite(now) ? now : frame.monotonic;
    if (!finite(now) || !finite(c.sampledAt) || c.sampledAt > now + 1 || now-c.sampledAt > Math.max(3.5, (measured(c.intervalSeconds) || 1)*4)) return 'stale';
    return c.status;
}
function usable(state) { return state === 'available' || state === 'partial'; }
function assess(frame, options) {
    frame = frame || {}; options = options || {};
    var out=[], now=finite(options.now)?options.now:frame.monotonic;
    var system=frame.system||{}, pressure=system.pressure||{}, machine=providerState(frame,'machine',now);
    function add(id,severity,title,evidence,next,instrument,key,source) {
        out.push({id:id,severity:severity,title:title,evidence:evidence,next:next,instrument:instrument,entityKey:key||'',source:source});
    }
    if (usable(machine)) {
        ['cpu','memory','io'].forEach(function(resource) {
            var p=pressure[resource]||{}, some=measured((p.some||{}).avg10), full=resource==='cpu'?null:measured((p.full||{}).avg10);
            var isFull=full!==null && full>=2, value=isFull?full:some;
            if (value===null || value>100 || value<(isFull?2:5)) return;
            var name={cpu:'CPU',memory:'Memory',io:'I/O'}[resource];
            add('psi:'+resource,value>=(isFull?10:20)?'high':'watch',name+' stall pressure',
                value.toFixed(1)+'% of time '+(isFull?'all non-idle tasks':'some tasks')+' stalled; PSI avg10 (10 seconds)'+(machine==='partial'?' · partial provider':''),
                'Inspect '+name.toLowerCase()+' contributors and the pressure trend; usage alone does not establish a cause.',
                'machine','subsystem:'+(resource==='io'?'storage':resource),'/proc/pressure/'+resource+' · attention threshold is a triage heuristic');
        });
        var mem=system.memory||{}, total=measured(mem.totalBytes), available=measured(mem.availableBytes);
        if (total>0 && available!==null && available/total<0.10) {
            var share=available/total*100;
            add('memory:headroom',share<5?'high':'watch','Low available memory',share.toFixed(1)+'% available to new work'+(machine==='partial'?' · partial provider':''),
                'Inspect memory contributors and PSI before deciding whether to reduce workload. Shared RSS pages can overlap.',
                'machine','subsystem:memory','/proc/meminfo · MemAvailable / MemTotal');
        }
    }
    var storage=providerState(frame,'storage',now);
    if (usable(storage)) {
        rows((frame.storage||{}).mounts).slice(0,4096).forEach(function(m) {
            var c=m.capacity||{}, total=measured(c.totalBytes), available=measured(c.availableBytes);
            if (m.closed || !(total>0) || available===null || available/total>=0.10 || !finite(c.sampledAt) || c.sampledAt>now+1 || now-c.sampledAt>30) return;
            var name=displayName({key:m.key,kind:'mount',name:m.path||m.name},options.privacy);
            add('capacity:'+m.key,available/total<0.03?'high':'watch','Low filesystem space',name+' · '+(available/total*100).toFixed(1)+'% available · sampled '+Math.max(0,now-c.sampledAt).toFixed(0)+'s ago'+(storage==='partial'?' · partial provider':''),
                'Inspect the mount and backing device. Capacity does not measure per-mount throughput.',
                'storage',m.key,'statvfs · safe local filesystem capacity, cached up to 15 seconds');
        });
    }
    ['processes','network','machine','storage','audio','gpu','thermal','enrichment'].forEach(function(id) {
        if (!(frame.capabilities||{})[id]) return;
        var state=providerState(frame,id,now);
        if (state==='available' || state==='inactive') return;
        if ((id==='gpu' || id==='thermal') && state==='unavailable') return;
        add('provider:'+id,'info','Check '+id+' data',id+' provider is '+state,
            'Open data sources for collection scope, sample age and recovery details.', 'capabilities','', 'Provider capability and timestamp');
    });
    var rank={high:0,watch:1,info:2};
    return out.sort(function(a,b){return rank[a.severity]-rank[b.severity] || a.id.localeCompare(b.id);}).slice(0,24);
}

var domains = {process:'processes',relationship:'connection',remote:'connection',listener:'connection',mount:'storage','audio-node':'audio','audio-link':'audio',pressure:'machine'};
function scalarSummary(row) {
    var parts=[];
    if (measured(row.cpuPercent)!==null) parts.push(format(row.cpuPercent,'percent')+' CPU (100% = one core)');
    if (measured(row.rssBytes)!==null) parts.push(format(row.rssBytes,'bytes')+' RSS');
    if (measured(row.socketCount)!==null) parts.push(row.socketCount+' sockets');
    if (measured(row.readBps)!==null) parts.push('R '+format(row.readBps,'rate'));
    if (measured(row.writeBps)!==null) parts.push('W '+format(row.writeBps,'rate'));
    if (measured((row.capacity||{}).availableBytes)!==null) parts.push(format(row.capacity.availableBytes,'bytes')+' available');
    if (typeof row.mute==='boolean') parts.push(row.mute?'Muted':'Unmuted');
    return parts.join(' · ') || 'No comparable scalar metrics';
}
function entityIndex(frame, wanted) {
    var out=Object.create(null), n=frame.network||{}, s=frame.storage||{}, a=frame.audio||{};
    var collections=[[frame.processes,'process'],[frame.groups,'application'],[n.processes,'application'],[n.instances,'process'],[n.remotes,'remote'],[n.links,'relationship'],[n.instanceLinks,'relationship'],[n.listeners,'listener'],[s.mounts,'mount'],[s.devices,'device'],[s.contributors,'process'],[a.nodes,'audio-node'],[a.devices,'audio-device'],[a.links,'audio-link']];
    collections.forEach(function(pair) {
        rows(pair[0]).slice(0,48000).forEach(function(r) {
            if (!r || !wanted[r.key]) return;
            var kind=pair[1], name=r.name||r.path;
            if (kind==='remote') name=name||r.address;
            if (kind==='relationship') name=name||'Network relationship';
            if (kind==='audio-link') name='Audio route';
            if (kind==='audio-node') kind=r.kind||kind;
            if (!out[r.key]) out[r.key]={key:r.key,kind:kind,name:clean(name||kind),closed:r.closed===true,groupKey:r.groupKey||'',metrics:scalarSummary(r)};
        });
    });
    ['cpu','memory','storage','network','gpu','thermal'].forEach(function(id) {
        var key='subsystem:'+id;
        if (wanted[key]) out[key]={key:key,kind:'subsystem',name:id.toUpperCase(),closed:false};
    });
    return out;
}
function freshSession() { return {at:null,sequence:null,events:[],seen:[]}; }
function ingest(session, frame) {
    session=session||freshSession();
    if (!finite(frame.monotonic)) return session;
    if (finite(session.at) && (frame.monotonic<session.at || finite(frame.sequence) && finite(session.sequence) && frame.sequence<session.sequence)) session=freshSession();
    var now=frame.monotonic, wanted=Object.create(null), incoming=rows(frame.events).slice(0,2048);
    incoming.forEach(function(e) { if(e && typeof e.entityKey==='string') wanted[e.entityKey]=true; });
    var index=entityIndex(frame,wanted), seen=Object.create(null), names=Object.create(null);
    var retained=rows(session.events).filter(function(e){return now-e.at<=300 && e.at<=now;});
    retained.forEach(function(e){names[e.entityKey]=e;});
    var seenRows=rows(session.seen).filter(function(e){return now-e.at<=300;});
    seenRows.forEach(function(e){seen[e.key]=true;});
    incoming.forEach(function(e) {
        if (!e || typeof e.key!=='string' || e.key.length>512 || typeof e.entityKey!=='string' || e.entityKey.length>512 || !Object.prototype.hasOwnProperty.call(domains,e.domain) || ['opened','changed','closed'].indexOf(e.kind)<0 || !finite(e.at) || e.at>now || now-e.at>300 || seen[e.key]) return;
        seen[e.key]=true; seenRows.push({key:e.key,at:e.at});
        var r=index[e.entityKey]||names[e.entityKey]||{kind:e.domain,name:'Entity no longer in collected scope'};
        retained.push({key:e.key,entityKey:e.entityKey,domain:e.domain,kind:e.kind,entityKind:r.entityKind||r.kind,name:r.name,at:e.at,instrument:domains[e.domain],groupKey:r.groupKey||''});
    });
    retained.sort(function(a,b){return b.at-a.at || a.key.localeCompare(b.key);});
    return {at:now,sequence:frame.sequence,events:retained.slice(0,120),seen:seenRows.slice(-2048)};
}
function freezeSession(session, frame) {
    // Freeze replies can arrive after newer live frames. Trim by the pinned time
    // without interpreting that intentional rewind as a helper restart.
    var held={at:frame.monotonic,sequence:frame.sequence,
        events:rows(session.events).filter(function(e){return e.at<=frame.monotonic;}),
        seen:rows(session.seen).filter(function(e){return e.at<=frame.monotonic;})};
    return ingest(held,frame);
}
function activity(session, options) {
    options=options||{};
    return rows((session||{}).events).filter(function(e) {
        return (!options.instrument || options.instrument==='all' || e.instrument===options.instrument) && (!options.kind || options.kind==='all' || e.kind===options.kind);
    }).map(function(e) {
        return {key:e.key,entityKey:e.entityKey,domain:e.domain,kind:e.kind,instrument:e.instrument,at:e.at,groupKey:e.groupKey||'',
            name:displayName({entityKey:e.entityKey,kind:e.entityKind,name:e.name},options.privacy),
            age:Math.max(0,((session||{}).at||e.at)-e.at).toFixed(0)+'s ago'};
    });
}
function togglePin(pins, entity, instrument) {
    pins=rows(pins);
    if (!entity || !entity.key) return pins;
    if (pins.some(function(p){return p.key===entity.key;})) return pins.filter(function(p){return p.key!==entity.key;});
    if (pins.length>=8) return pins;
    var raw=entity.raw||{};
    return pins.concat([{key:entity.key,name:clean(raw.name||raw.path||raw.address||entity.name),kind:entity.kind||'entity',instrument:instrument,groupKey:raw.groupKey||entity.groupKey||''}]);
}
function pinRows(pins, frame, privacy, now) {
    var wanted=Object.create(null); rows(pins).forEach(function(p){wanted[p.key]=true;});
    var index=entityIndex(frame||{},wanted);
    return rows(pins).map(function(p) {
        var r=index[p.key];
        var provider=p.kind==='subsystem'?'machine':['process','application'].indexOf(p.kind)>=0?'processes':p.instrument==='connection'?'network':p.instrument==='audio'?'audio':'storage';
        var quality=providerState(frame||{},provider,now), status=!r?'not observed':r.closed?'ended':quality==='available'?'observed':quality;
        return {key:p.key,entityKey:p.key,name:displayName(r||p,privacy),kind:p.kind,instrument:p.instrument,groupKey:p.groupKey||'',status:status,
            metrics:r && !r.closed && usable(quality)?r.metrics||'No comparable scalar metrics':'Metrics unavailable'};
    });
}

var metricSpecs = [
    {id:'cpu',label:'Host CPU',path:'system.cpuPercent',unit:'percent',provider:'machine'},
    {id:'memory',label:'Used memory',path:'system.memory.usedBytes',unit:'bytes',provider:'machine'},
    {id:'available',label:'Available memory',path:'system.memory.availableBytes',unit:'bytes',provider:'machine'},
    {id:'cpuPsi',label:'CPU stall / avg10',path:'system.pressure.cpu.some.avg10',unit:'percent',provider:'machine'},
    {id:'memoryPsi',label:'Memory stall / avg10',path:'system.pressure.memory.some.avg10',unit:'percent',provider:'machine'},
    {id:'ioPsi',label:'I/O stall / avg10',path:'system.pressure.io.some.avg10',unit:'percent',provider:'machine'},
    {id:'rx',label:'Host receive',path:'system.netRxBps',unit:'rate',provider:'machine'},
    {id:'tx',label:'Host transmit',path:'system.netTxBps',unit:'rate',provider:'machine'},
    {id:'read',label:'Storage read',path:'storage.summary.readBps',unit:'rate',provider:'storage'},
    {id:'write',label:'Storage write',path:'storage.summary.writeBps',unit:'rate',provider:'storage'}
];
function valueAt(frame, path) { return path.split('.').reduce(function(value,key){return value && value[key];},frame); }
function format(value,unit,delta) {
    if (!finite(value)) return '\u2014';
    var sign=delta && value>0?'+':'';
    if (unit==='percent') return sign+value.toFixed(1)+(delta?' pp':'%');
    var units=['B','KiB','MiB','GiB','TiB'], i=0;
    while (Math.abs(value)>=1024 && i<4) {value/=1024;i++;}
    return sign+value.toFixed(i?1:0)+' '+units[i]+(unit==='rate'?'/s':'');
}
function captureBaseline(frame, options) {
    options=options||{};
    return {at:frame.monotonic,wallTime:frame.wallTime,metrics:metricSpecs.map(function(m) {
        var quality=providerState(frame,m.provider,options.now), value=measured(valueAt(frame,m.path));
        return {id:m.id,label:m.label,unit:m.unit,value:usable(quality)?value:null,quality:quality,sampledAt:((frame.capabilities||{})[m.provider]||{}).sampledAt};
    })};
}
function compare(baseline, frame, options) {
    if (!baseline) return [];
    var current=captureBaseline(frame,options);
    return current.metrics.map(function(m) {
        var b=rows(baseline.metrics).filter(function(b){return b.id===m.id;})[0]||{}, delta=finite(m.value)&&finite(b.value)?m.value-b.value:null;
        return {id:m.id,label:m.label,before:format(b.value,m.unit),current:format(m.value,m.unit),delta:delta,change:format(delta,m.unit,true),
            quality:!usable(m.quality)?m.quality:!usable(b.quality)?'baseline '+(b.quality||'unavailable'):m.quality==='partial'||b.quality==='partial'?'partial':'available'};
    });
}
function report(frame, session, pins, baseline, options) {
    options=options||{};
    var findings=assess(frame,options), out=['Tactical Display / operator report',options.frozen?'FROZEN observation':'LIVE observation',
        finite(frame.wallTime)?new Date(frame.wallTime*1000).toISOString():'Observation time unavailable',options.privacy?'Identities redacted':'Local observations',
        '', 'Attention / heuristic triage'];
    if (!findings.length) out.push('No attention thresholds crossed in available observations. This is not a health guarantee.');
    findings.forEach(function(r){out.push(r.severity.toUpperCase()+': '+r.title+' — '+r.evidence, 'Inspect: '+r.next, 'Source: '+r.source);});
    out.push('', 'Baseline comparison'+(baseline && finite(baseline.at)?' / '+Math.max(0,frame.monotonic-baseline.at).toFixed(0)+'s old':''));
    if (!baseline) out.push('No baseline captured.');
    compare(baseline,frame,options).forEach(function(r){out.push(r.label+': '+r.before+' → '+r.current+' ('+r.change+'; '+r.quality+')');});
    out.push('', 'Pinned entities');
    pinRows(pins,frame,options.privacy,options.now).forEach(function(r){out.push(r.name+' / '+r.kind+' / '+r.status+' / '+r.metrics);});
    out.push('', 'Recent activity / observed lifecycle events');
    activity(session,{privacy:options.privacy}).slice(0,20).forEach(function(r){out.push(r.age+' / '+r.kind+' / '+r.name);});
    return out.join('\n');
}
if (typeof module!=='undefined') module.exports={providerState:providerState,assess:assess,freshSession:freshSession,ingest:ingest,freezeSession:freezeSession,activity:activity,togglePin:togglePin,pinRows:pinRows,captureBaseline:captureBaseline,compare:compare,report:report,format:format,displayName:displayName};
