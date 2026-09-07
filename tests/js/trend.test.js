'use strict';
const test=require('node:test'), assert=require('node:assert/strict');
const T=require('../../visual/TrendModel.js');
test('time windows use observation timestamps and keep coordinates finite and bounded',()=>{
    const samples=Array.from({length:80},(_,i)=>({at:100+i,cpuPercent:i}));
    for(const seconds of [15,30,60]) {
        const plot=T.build(samples,'subsystem:cpu',{seconds,width:400,height:100});
        assert.equal(plot.end,179); assert.equal(plot.start,179-seconds);
        assert.ok(plot.samples.every(s=>s.at>=plot.start)); assert.equal(plot.ceiling,100);
        for(const trace of plot.traces)for(const path of trace.paths)for(const p of path)assert.ok(Number.isFinite(p.x)&&p.x>=0&&p.x<=400&&p.y>=0&&p.y<=100);
    }
});
test('missing counters and acquisition gaps break paths rather than joining unknown periods',()=>{
    const samples=[{at:1,readBps:4,writeBps:2},{at:2,readBps:null,writeBps:3},{at:3,readBps:8,writeBps:4},{at:20,readBps:5,writeBps:2}];
    const plot=T.build(samples,'subsystem:storage',{seconds:30,interval:1});
    assert.deepEqual(plot.traces[0].paths.map(p=>p.length),[1,1,1]);
    assert.deepEqual(plot.traces[1].paths.map(p=>p.length),[3,1]);
    assert.equal(T.inspect(plot,10),null);
    assert.equal(T.inspect(plot,2).values[0].value,null);
});
test('paired traces share a scale and have independent text and stroke identities',()=>{
    const plot=T.build([{at:1,netRxBps:4096,netTxBps:1024}],'subsystem:network',{});
    assert.equal(plot.traces[0].name,'Receive'); assert.equal(plot.traces[1].name,'Transmit');
    assert.equal(plot.traces[0].dashed,false); assert.equal(plot.traces[1].dashed,true);
    assert.ok(plot.ceiling>=4096); assert.equal(plot.unit,'rate');
});
test('cursor snaps to measured samples with bounded keyboard navigation',()=>{
    const plot=T.build([{at:1,cpuPercent:10},{at:2,cpuPercent:20},{at:3,cpuPercent:30}],'subsystem:cpu',{});
    assert.equal(T.inspect(plot,2.2).at,2); assert.equal(T.step(plot,null,-1),3);
    assert.equal(T.step(plot,2,-1),1); assert.equal(T.step(plot,3,1),3);
    assert.equal(T.step(plot,1,-1),1); assert.equal(T.step(T.build([],'subsystem:cpu',{}),null,1),null);
});
test('statistics include only finite observed values and report missing current sample',()=>{
    const plot=T.build([{at:1,cpuPercent:10},{at:2,cpuPercent:30},{at:3,cpuPercent:null}],'subsystem:cpu',{});
    const stats=plot.traces[0].stats;
    assert.equal(stats.min,10); assert.equal(stats.max,30); assert.equal(stats.mean,20); assert.equal(stats.current,null);
    const empty=T.build([{at:1,cpuPercent:NaN},{at:2,cpuPercent:Infinity}],'subsystem:cpu',{});
    assert.equal(empty.traces[0].stats.min,null); assert.deepEqual(empty.traces[0].paths,[]);
});
test('pressure lens selects correct some/full metrics without system CPU full',()=>{
    for(const [key,fields] of [['cpu',['cpuSomePercent']],['memory',['memorySomePercent','memoryFullPercent']],['storage',['ioSomePercent','ioFullPercent']]]) {
        const p=T.build([{at:1,cpuSomePercent:4,memorySomePercent:8,memoryFullPercent:2,ioSomePercent:6,ioFullPercent:1}],`subsystem:${key}`,{metric:'pressure'});
        assert.deepEqual(p.traces.map(t=>t.key),fields); assert.equal(p.unit,'percent');
    }
});
test('malformed/out-of-order/duplicate input is bounded, deterministic and immutable',()=>{
    const samples=[{at:3,cpuPercent:3},{at:1,cpuPercent:1},{at:3,cpuPercent:4},{at:2,cpuPercent:-1},null,{at:Infinity}];
    const before=JSON.stringify(samples),p=T.build(samples,'subsystem:cpu',{width:0,height:-5,seconds:999});
    assert.equal(JSON.stringify(samples),before); assert.deepEqual(p.samples.map(s=>s.at),[1,2,3]);
    assert.equal(p.traces[0].stats.current,4); assert.equal(p.seconds,60);
    assert.ok(T.build(Array.from({length:2000},(_,i)=>({at:i,cpuPercent:1})),'subsystem:cpu',{}).samples.length<=120);
});
