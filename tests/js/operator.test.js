'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const O = require('../../model/Operator.js');
const F = require('../../fixtures/scenarios.js');

function frame(at = 1000) {
    const f = F.frame();
    f.monotonic = at;
    f.sequence = at;
    Object.values(f.capabilities).forEach(c => { c.sampledAt = at; });
    f.system.pressure = {cpu:{some:{avg10:0}}, memory:{some:{avg10:0}, full:{avg10:0}}, io:{some:{avg10:0}, full:{avg10:0}}};
    return f;
}
function event(f, kind = 'opened', key = f.processes[0].key, domain = 'process') {
    return {key:`event:${key}:${kind}:${f.monotonic}`, entityKey:key, domain, kind, at:f.monotonic, expiresAt:f.monotonic+4};
}
test('briefing differentiates actual stalls from utilization and ignores system CPU full', () => {
    const f = frame(); f.system.cpuPercent = 100; f.system.pressure.cpu.full = {avg10:99};
    assert.equal(O.assess(f).some(r => r.id.startsWith('psi:')), false);
    f.system.pressure.cpu.some.avg10 = 21;
    const r = O.assess(f).find(r => r.id === 'psi:cpu');
    assert.equal(r.severity, 'high'); assert.match(r.evidence, /21.0%.*10/);
    assert.equal(r.entityKey, 'subsystem:cpu'); assert.match(r.next, /contributor/i);
});
test('full memory stalls outrank some stalls and identify simultaneous waiting', () => {
    const f = frame(); f.system.pressure.memory = {some:{avg10:25}, full:{avg10:11}};
    const rows = O.assess(f).filter(r => r.id === 'psi:memory');
    assert.equal(rows.length, 1); assert.match(rows[0].evidence, /all non-idle/i);
    assert.match(rows[0].evidence, /11.0%/);
});
test('unavailable, stale and inactive measurements cannot claim current pressure', () => {
    for (const status of ['unavailable','inactive']) {
        const f = frame(); f.system.pressure.cpu.some.avg10 = 99; f.capabilities.machine.status = status;
        assert.equal(O.assess(f).some(r => r.id === 'psi:cpu'), false);
    }
    const f = frame(); f.system.pressure.cpu.some.avg10 = 99;
    assert.equal(O.assess(f, {now:1020}).some(r => r.id === 'psi:cpu'), false);
    assert.ok(O.assess(f, {now:1020}).some(r => r.id === 'provider:machine' && /stale/i.test(r.evidence)));
    assert.equal(O.providerState(f, 'machine', 1001), 'available');
    assert.equal(O.providerState(f, 'absent'), 'unavailable');
});
test('low available RAM and capacity use denominators and valid timestamped evidence', () => {
    const f = frame(); f.system.memory = {totalBytes:1000, availableBytes:30, usedBytes:970};
    f.storage.mounts = [{key:'mount:one',path:'/private/work',capacity:{totalBytes:1000,availableBytes:20,sampledAt:999}}];
    let rows = O.assess(f); assert.equal(rows.find(r => r.id === 'memory:headroom').severity, 'high');
    assert.equal(rows.find(r => r.id === 'capacity:mount:one').severity, 'high');
    assert.ok(!JSON.stringify(O.assess(f,{privacy:true})).includes('/private/work'));
    f.storage.mounts[0].capacity.sampledAt = 900;
    assert.equal(O.assess(f).some(r => r.id.startsWith('capacity:')), false);
    f.system.memory.totalBytes = 0;
    assert.equal(O.assess(f).some(r => r.id === 'memory:headroom'), false);
});
test('partial provider evidence is qualified and findings stay bounded and deterministically ranked', () => {
    const f = frame(); f.capabilities.machine.status = 'partial'; f.system.pressure.io.some.avg10 = 7;
    const row = O.assess(f).find(r => r.id === 'psi:io'); assert.match(row.evidence, /partial/i);
    f.storage.mounts = Array.from({length:500},(_,i)=>({key:`mount:${i}`,path:`/m/${i}`,capacity:{totalBytes:100,availableBytes:1,sampledAt:1000}}));
    f.capabilities.storage.status = 'partial';
    assert.match(O.assess(f).find(r => r.id.startsWith('capacity:')).evidence, /partial/i);
    assert.ok(O.assess(f).length <= 24); assert.deepEqual(O.assess(f), O.assess(f));
});
test('missing and invalid scalar values are absent evidence, not healthy zeros', () => {
    for (const value of [null,undefined,NaN,Infinity,-1,'50']) {
        const f = frame(); f.system.pressure.cpu.some.avg10 = value; f.system.memory.availableBytes = value;
        assert.equal(O.assess(f).some(r => r.id === 'psi:cpu' || r.id === 'memory:headroom'), false);
    }
    assert.deepEqual(O.assess({}), []);
});
test('session ingests only backend events, deduplicates repeats and retains beyond visual TTL', () => {
    const f = frame(); f.events = [event(f)];
    const s = O.ingest(O.freshSession(), f);
    assert.equal(s.events.length, 1); assert.equal(O.ingest(s, f).events.length, 1);
    const later = frame(1010); later.processes = []; later.events = [];
    const next = O.ingest(s, later); assert.equal(next.events.length, 1);
    assert.equal(next.events.some(e => e.kind === 'closed'), false);
    assert.equal(s.at, 1000); // immutable snapshot remains usable by freeze
});
test('event history expires, sorts, caps and resets when the helper sequence restarts', () => {
    const f = frame(); f.events = Array.from({length:300},(_,i)=>({...event(f),key:`event:${i}`,at:999+i/1000}));
    const s = O.ingest(O.freshSession(), f); assert.equal(s.events.length, 120);
    assert.ok(s.events[0].at >= s.events[119].at);
    assert.equal(O.ingest(s,frame(1400)).events.length, 0);
    const restart = frame(1010); restart.sequence = 1;
    assert.equal(O.ingest(s,restart).events.length, 0);
});
test('activity filters combine instrument and lifecycle with privacy on retained names', () => {
    const f = frame(); f.processes[0].name = 'secret-app'; f.events = [event(f), event(f,'changed','subsystem:cpu','pressure')];
    const s = O.ingest(O.freshSession(),f);
    assert.equal(O.activity(s,{instrument:'machine',kind:'changed'}).length,1);
    assert.equal(O.activity(s,{instrument:'processes',kind:'changed'}).length,0);
    assert.match(O.activity(s).find(e=>e.domain==='process').name,/secret-app/);
    assert.ok(!JSON.stringify(O.activity(s,{privacy:true})).includes('secret-app'));
});
test('pins are capped, lightweight, immutable and remain distinct across PID reuse', () => {
    let pins=[];
    for(let i=0;i<10;i++) pins=O.togglePin(pins,{key:`process:42:${i}`,name:`app-${i}`,kind:'process',raw:{pid:42,sockets:Array(1000).fill('secret')}},'processes');
    assert.equal(pins.length,8); assert.equal(pins[0].key,'process:42:0'); assert.equal(pins[0].raw,undefined);
    const before=JSON.stringify(pins), removed=O.togglePin(pins,pins[0],'processes');
    assert.equal(removed.length,7); assert.equal(JSON.stringify(pins),before);
    const f=frame(); f.processes=[];
    assert.equal(O.pinRows(pins,f,true)[0].status,'not observed');
    assert.ok(!JSON.stringify(O.pinRows(pins,f,true)).includes('app-0'));
});
test('baseline keeps scalars only, compares correct units and rejects stale observations', () => {
    const f=frame(); f.system.cpuPercent=20;
    const b=O.captureBaseline(f);
    assert.equal(b.processes,undefined); assert.ok(JSON.stringify(b).length<6000);
    const next=frame(1002); next.system.cpuPercent=35;
    const delta=O.compare(b,next).find(r=>r.id==='cpu');
    assert.equal(delta.delta,15); assert.match(delta.change,/\+15.0 pp/);
    assert.equal(O.compare(b,next,{now:1050}).find(r=>r.id==='cpu').delta,null);
    next.system.cpuPercent=null;
    assert.equal(O.compare(b,next).find(r=>r.id==='cpu').delta,null);
});
test('operator report is an explicit privacy-safe projection, includes frozen provenance', () => {
    const f=frame(); f.processes[0].name='classified-program'; f.events=[event(f)];
    const s=O.ingest(O.freshSession(),f);
    const pins=O.togglePin([],{key:f.processes[0].key,name:'classified-program',kind:'process'},'processes');
    const report=O.report(f,s,pins,O.captureBaseline(f),{privacy:true,frozen:true});
    assert.match(report,/FROZEN/); assert.match(report,/redacted/i); assert.match(report,/Baseline/);
    assert.ok(!report.includes('classified-program')); assert.ok(!report.includes(f.processes[0].key));
    assert.ok(!report.includes('/usr/bin/'));
});
test('late freeze acknowledgement retains earlier activity but excludes future observations', () => {
    const first=frame(950); first.events=[event(first)];
    let s=O.ingest(O.freshSession(),first);
    const frozen=frame(1000); frozen.events=[event(frozen)]; s=O.ingest(s,frozen);
    const later=frame(1001); later.events=[event(later)]; s=O.ingest(s,later);
    const held=O.freezeSession(s,frozen);
    assert.equal(held.events.length,2); assert.equal(held.at,1000);
    assert.ok(held.events.every(e=>e.at<=1000)); assert.equal(s.events.length,3);
});
test('optional absent hardware is a coverage fact, not an attention item', () => {
    const f=frame(); f.capabilities.gpu.status='unavailable'; f.capabilities.thermal.status='unavailable';
    assert.equal(O.assess(f).some(r=>r.id==='provider:gpu'||r.id==='provider:thermal'),false);
    f.capabilities.gpu.status='partial'; assert.ok(O.assess(f).some(r=>r.id==='provider:gpu'));
});
test('session bounds survive high-churn duplicate frames and reject malformed events', () => {
    const f=frame(); f.events=Array.from({length:2048},(_,i)=>({...event(f),key:`event:${i}`,at:999+i/4096}));
    let s=O.ingest(O.freshSession(),f);
    for(let i=0;i<10;i++)s=O.ingest(s,f);
    assert.equal(s.events.length,120); assert.equal(new Set(s.events.map(e=>e.key)).size,120); assert.ok(s.seen.length<=2048);
    const bad=frame(1001); bad.events=[null,{key:'bad',domain:'constructor',entityKey:'bad',at:1001,kind:'opened'}, {...event(bad),at:1100}];
    assert.equal(O.ingest(s,bad).events.length,120);
    assert.equal(O.ingest(s,bad).events.some(e=>e.key==='bad'),false);
});
test('retained privacy aliases agree with the visualization and stay usable in search', () => {
    const M=require('../../model/InstrumentModel.js');
    for(const kind of ['application','process','remote','mount','device','stream','sink','source','audio-node','audio-link','listener','relationship']) {
        assert.equal(O.displayName({key:'key:private',kind,name:'secret'},true),M.alias(kind,'key:private'));
    }
});
test('pins retain exact group scope for demand-collected process instances', () => {
    const f=frame(), raw=f.processes[0];
    const pins=O.togglePin([],{key:raw.key,name:raw.name,kind:'process',raw},'connection');
    assert.equal(pins[0].groupKey,raw.groupKey);
    assert.equal(O.pinRows(pins,f,false)[0].groupKey,raw.groupKey);
});
test('pin summaries report current measured scalars and qualify stale or absent observations', () => {
    const f=frame(), p=f.processes[0];
    p.cpuPercent=37; p.rssBytes=1048576;
    const pins=O.togglePin([],{key:p.key,name:p.name,kind:'process',raw:p},'processes');
    let row=O.pinRows(pins,f,true)[0];
    assert.match(row.metrics,/37.0%/); assert.match(row.metrics,/1.0 MiB/);
    f.processes[0].cpuPercent=42;
    assert.match(O.pinRows(pins,f,true)[0].metrics,/42.0%/);
    f.capabilities.processes.status='stale';
    row=O.pinRows(pins,f,true)[0]; assert.equal(row.status,'stale'); assert.equal(row.metrics,'Metrics unavailable');
    f.processes=[]; f.network.instances=[]; f.storage.contributors=[];
    assert.equal(O.pinRows(pins,f,true)[0].status,'not observed');
});
test('provider-declared stale observations keep their actual quality classification', () => {
    const f=frame(); f.capabilities.audio.status='stale';
    assert.equal(O.providerState(f,'audio'),'stale');
    assert.match(O.assess(f).find(r=>r.id==='provider:audio').evidence,/stale/);
});
