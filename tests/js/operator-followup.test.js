'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const O=require('../../model/Operator.js'),M=require('../../model/InstrumentModel.js'),F=require('../../fixtures/scenarios.js');
function frame() {
    const f=F.frame(); f.monotonic=1000; f.sequence=1;
    Object.values(f.capabilities).forEach(c=>{c.sampledAt=1000;});
    return f;
}
test('actual PipeWire media classes preserve field aliases in pins and retained events',()=>{
    for(const [mediaClass,kind] of [['Audio/Sink','sink'],['Audio/Source','source'],['Stream/Output/Audio','stream'],['Audio/Duplex','audio-node']]) {
        const f=frame(),key='audio:node:private';
        f.audio.nodes=[{key,kind:'node',mediaClass,name:'Sensitive device',mute:false}];
        f.events=[{key:'event:audio',entityKey:key,domain:'audio-node',kind:'changed',at:1000}];
        const pins=O.togglePin([],{key,kind,name:'Sensitive device'},'audio');
        assert.equal(O.pinRows(pins,f,true)[0].name,M.alias(kind,key));
        const s=O.ingest(O.freshSession(),f);
        assert.equal(O.activity(s,{privacy:true})[0].name,M.alias(kind,key));
    }
});
test('a fresh storage provider does not make expired mount capacity current',()=>{
    const f=frame(),key='mount:private';
    f.storage.mounts=[{key,path:'/private',capacity:{availableBytes:4096,totalBytes:8192,sampledAt:900}}];
    const pins=O.togglePin([],{key,kind:'mount',name:'/private'},'storage');
    assert.doesNotMatch(O.pinRows(pins,f,false)[0].metrics,/4.0 KiB available/);
    assert.match(O.pinRows(pins,f,false)[0].metrics,/capacity.*stale/i);
    f.storage.mounts[0].capacity.sampledAt=999;
    assert.match(O.pinRows(pins,f,false)[0].metrics,/4.0 KiB available/);
    assert.match(O.pinRows(pins,f,false,1040)[0].metrics,/unavailable/i);
});
test('lifecycle-only activity combines opened and closed without discarding retained changes',()=>{
    const f=frame();
    f.events=['opened','changed','closed'].map((kind,i)=>({key:'event:'+i,entityKey:f.processes[0].key,domain:'process',kind,at:998+i}));
    const s=O.ingest(O.freshSession(),f),before=JSON.stringify(s);
    assert.deepEqual(O.activity(s,{kind:'lifecycle'}).map(r=>r.kind),['closed','opened']);
    assert.equal(O.activity(s,{kind:'all'}).length,3);
    assert.equal(JSON.stringify(s),before);
});
test('change explanations retain only known field names and never identity-bearing values',()=>{
    const f=frame();
    f.events=[{key:'event:changed',entityKey:f.processes[0].key,domain:'process',kind:'changed',at:1000,
        changedFields:['state','socketCount','parentKey','/private/secret','constructor','state'],before:{name:'secret'}}];
    const s=O.ingest(O.freshSession(),f);
    const row=O.activity(s,{privacy:true})[0];
    assert.match(row.detail,/State changed/); assert.match(row.detail,/Socket count changed/); assert.match(row.detail,/Parent changed/);
    assert.doesNotMatch(JSON.stringify(s),/private\/secret|constructor|"before"/);
    assert.match(O.report(f,s,[],null,{privacy:true}),/Socket count changed/);
});
