// Strict host boundary. Test fixtures pass the same validation as real snapshots.
function isObject(o){return o!==null&&typeof o==='object'&&!Array.isArray(o);}
function finite(n){return typeof n==='number'&&isFinite(n);}
var textFields=['key','name','displayName','groupKey','groupName','parentKey','processKey','remoteKey','deviceKey','sourceKey','targetKey','executable','cgroup','state','event','proto','kind','local','remote','address','serviceName','nameSource','groupProvenance','mediaClass','serial','path','fsType','majorMinor','errorKind','reason','suggestion','status','level','provider','sampleFormat'];
var numberFields=['pid','ppid','uid','objectId','startTicks','threads','socketCount','newCount','closedCount','port','servicePort','family','mountId','inFlight','sampleRate','volume','ageMs','monotonic','wallTime','intervalSeconds','eventAgeMs','sampledAt','firstSeenMonotonic'];
var listFields=['pids','processKeys','remoteKeys','states','ports','listenerPorts','slaves','children'];
function treeError(root){
    var work=[{value:root,depth:0}],budget=350000;
    while(work.length){
        var task=work.pop(),v=task.value;
        if(--budget<0||task.depth>14)return 'Object depth/work limit exceeded';
        if(v===null||typeof v==='boolean')continue;
        if(typeof v==='string'){if(v.length>8192)return 'String limit exceeded';continue;}
        if(typeof v==='number'){if(!isFinite(v))return 'Non-finite numeric observation';continue;}
        if(Array.isArray(v)){if(v.length>48000)return 'Collection limit exceeded';for(var i=0;i<v.length;i++)work.push({value:v[i],depth:task.depth+1,metadata:task.metadata});continue;}
        if(!isObject(v))return 'Invalid JSON value';
        var keys=Object.keys(v);if(keys.length>512)return 'Object property limit exceeded';
        for(var k=0;k<keys.length;k++){
            var name=keys[k],child=v[name];
            if(name==='__proto__'||name==='constructor'||name==='prototype')return 'Unsafe object property';
            if(child!==null&&child!==undefined&&!task.metadata){
                if(textFields.indexOf(name)>=0&&typeof child!=='string')return 'Expected text: '+name;
                if((numberFields.indexOf(name)>=0||/(?:Bytes|Bps|Percent|Ticks|Ms)$/.test(name))&&!finite(child))return 'Expected finite measurement: '+name;
                if(listFields.indexOf(name)>=0&&!Array.isArray(child))return 'Expected array: '+name;
                if(['closed','default','mute','sharedOwnership','complete','ioAvailable','nameTrusted','frozen'].indexOf(name)>=0&&typeof child!=='boolean')return 'Expected boolean: '+name;
            }
            work.push({value:child,depth:task.depth+1,metadata:task.metadata||name==="provenance"});
        }
    }
    return '';
}
function validRows(rows,limit){
    if(!Array.isArray(rows)||rows.length>limit)return false;
    var keys=Object.create(null);
    for(var i=0;i<rows.length;i++){
        var r=rows[i];if(!isObject(r)||typeof r.key!=='string'||!r.key||r.key.length>512||keys[r.key])return false;
        keys[r.key]=true;
    }
    return true;
}
function validateSnapshot(frame) {
    if(!isObject(frame)||frame.schemaVersion!==3||frame.type!=='snapshot')return 'Unsupported snapshot schema';
    if(!finite(frame.monotonic)||!finite(frame.wallTime))return 'Invalid timestamps';
    if(!isObject(frame.capabilities)||!isObject(frame.system)||!validRows(frame.processes,24000)||!validRows(frame.groups,24000))return 'Malformed process/resource collections';
    var sections={network:['processes','remotes','links','listeners'],storage:['devices','mounts','links','contributors'],audio:['nodes','devices','links'],hardware:['gpus','thermals','fans']};
    var error='';
    Object.keys(sections).forEach(function(s){if(!isObject(frame[s])){error='Missing '+s;return;}sections[s].forEach(function(k){if(!validRows(frame[s][k],48000))error='Malformed '+s+'.'+k;});});
    if(error)return error;
    if(frame.network.instances!==undefined&&!validRows(frame.network.instances,24000)||frame.network.instanceLinks!==undefined&&!validRows(frame.network.instanceLinks,48000))return 'Malformed instance layer';
    var providers=Object.keys(frame.capabilities);
    if(providers.length>32||providers.some(function(k){var c=frame.capabilities[k];return !isObject(c)||typeof c.status!=='string'||typeof c.source!=='string';}))return 'Malformed capability map';
    if(!Array.isArray(frame.events)||frame.events.length>2048||!Array.isArray(frame.trend)||frame.trend.length>120)return 'Unbounded temporal state';
    return treeError(frame);
}
function validateDetail(frame){
    if(!isObject(frame)||frame.type!=='detail'||typeof frame.key!=='string'||frame.key.length>512||typeof frame.ended!=='boolean')return 'Invalid inspection response';
    if(!frame.ended&&(!isObject(frame.data)||!finite(frame.monotonic)||!Array.isArray(frame.data.sockets)||frame.data.sockets.length>64))return 'Invalid inspection data';
    return treeError(frame);
}
if(typeof module!=='undefined')module.exports={validateSnapshot:validateSnapshot,validateDetail:validateDetail};
