'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const S=require('../../model/Settings.js'),N=require('../../model/Navigation.js'),M=require('../../model/InstrumentModel.js'),L=require('../../visual/Layout.js'),P=require('../../visual/Palette.js'),I=require('../../model/Inspection.js'),Protocol=require('../../model/Protocol.js'),Fixtures=require('../../fixtures/scenarios.js');
const frame=Fixtures.frame();
function view(id,state={},f=frame,settings={}){return M.build(f,Object.assign(N.fresh(id),state),Object.assign({},S.defaults,settings));}
const metrics=t=>Array.from(t).reduce((n,c)=>n+(c.codePointAt(0)>0x2e80?16.8:8.4),0);
test('configuration migrates, validates and preserves unknown inline host fields',()=>{
 assert.equal(S.normalize({tdRefreshProfile:'bogus',tdPrivacy:'yes'}).values.refreshProfile,'balanced');
 assert.equal(S.normalize({tdVersion:50}).readOnly,true);
 const config={bar:{layout:{left:[{id:'nshkr.tactical-display',futureField:'keep',tdPrivacy:true}],center:[],right:[]}},plugins:[]};
 const e=S.entryFromShell(config,'nshkr.tactical-display'),merged=S.mergedEntry(e,S.normalize(e).values);
 assert.equal(merged.futureField,'keep');assert.equal(merged.tdPrivacy,true);assert.equal(config.bar.layout.left[0].tdPrivacy,true);
});
test('malformed, oversized, and command-like payloads cannot become executable input',()=>{
 for(const p of ['[]','false','{bad','x'.repeat(32769)])assert.ok(S.payload(p).errors.length);
 let a=S.payload(JSON.stringify({instrument:'storage',mode:'hold',monitor:'DP-1; rm -rf /',execute:'anything',focus:{processKey:'process:22:100',command:'rm'},privacy:true}));
 assert.equal(a.instrument,'storage');assert.equal(a.mode,'hold');assert.equal(a.execute,undefined);assert.equal(a.focus.command,undefined);assert.equal(a.privacy,true);
});
test('first traversal and reverse traversal are correct with no selection',()=>{
 const nodes=view('processes').results;
 assert.equal(N.traverse(N.fresh('processes'),nodes,1).selectedKey,nodes[0].key);
 assert.equal(N.traverse(N.fresh('processes'),nodes,-1).selectedKey,nodes.at(-1).key);
});
test('selection does not reorder keyboard traversal on every sample',()=>{
 let s=N.fresh('connection'),v=view('connection',s),order=v.results.map(n=>n.key),seen=[];
 for(let i=0;i<order.length;i++){s=N.traverse(s,v.results,1);seen.push(s.selectedKey);v=view('connection',s);assert.deepEqual(v.results.map(n=>n.key),order);}
 assert.deepEqual(seen,order);
});
test('focus/back and cross-instrument intent use instance IDs, not PID-only lookup',()=>{
 const process=frame.processes[4],node=view('processes',{query:String(process.pid)}).allNodes.find(n=>n.key===process.key);
 let s=N.focus(N.fresh('processes'),node);s=N.switchTo(s,'connection');
 let v=view('connection',s),resolved=N.resolveContext(s,v.allNodes);assert.equal(resolved.selectedKey,process.key);
 assert.equal(N.back(resolved).state.instrument,'processes');
 const absent=N.resolveContext(N.switchTo(N.select(N.fresh('processes'),node),'audio'),[]);assert.ok(absent.notice.includes('not present'));
});
test('history and teardown state are bounded',()=>{
 let s=N.fresh('connection');for(let i=0;i<200;i++)s=N.switchTo(s,i%2?'connection':'processes');assert.equal(s.history.length,24);
 assert.equal(N.reset(s).selectedKey,'');assert.equal(N.reset(s).history.length,0);
});
test('connection filters compose protocol, direction, lifecycle and settings',()=>{
 const v=view('connection',{filters:{protocol:'tcp',direction:'inbound',state:'live'}},{...frame},{listeners:false,loopback:false});
 assert.ok(v.edges.length);for(const e of v.edges){assert.equal(e.raw.proto,'tcp');assert.equal(e.raw.kind,'inbound');assert.equal(e.closed,false);}
 assert.equal(v.allNodes.some(n=>n.kind==='listener'),false);
});
test('expanded connection groups expose individual process-instance relationships',()=>{
 const key=frame.groups[0].key,v=view('connection',{expanded:[key]});assert.ok(v.allNodes.some(n=>n.kind==='process'&&n.raw.groupKey===key));
 assert.ok(v.edges.some(e=>e.kind==='relationship'&&e.raw.groupKey===key&&e.raw.processKey.startsWith('process:')));
});
test('fuzzy search handles Unicode, multiple terms and exact PIDs',()=>{
 assert.equal(M.match('Long process cafe PID 1024','prcs 1024'),true);assert.equal(M.match('Firefox 203.0.113.50','fire 203.0'),true);assert.equal(M.match('cafe 104','999'),false);
 const f=Fixtures.frame();f.groups[0].name='\u65e5\u672c\u8a9e \u00e9 <b>not markup</b>';const v=view('processes',{query:'\u65e5\u672c'},f);assert.equal(v.results[0].name,f.groups[0].name);
});
test('privacy covers labels, subtitles, detail fields, socket children and copied text',()=>{
 for(const id of M.catalog.map(c=>c.id)){
  const v=view(id,{},frame,{privacy:true});
  for(const n of v.allNodes){if(n.kind!=='subsystem'){assert.match(n.name,/^[A-Z]+-[A-F0-9]{8}$/);assert.ok(!n.subtitle.includes('/home/'));}}
  const n=v.allNodes.find(n=>n.kind!=='subsystem');if(n){const copy=I.clipboard(n,n.raw,true,frame);assert.ok(!copy.includes('/usr/bin/'));assert.ok(!copy.includes('198.51.'));assert.ok(!copy.includes('process:1000:'));}
 }
 const sockets=I.socketRows(frame.network.links[0].sockets,true);assert.ok(sockets.every(s=>!s.title.includes('192.0.2.')&&!s.details.includes('PID 1000')));
});
test('privacy aliases remain searchable',()=>{const n=view('connection',{},frame,{privacy:true}).allNodes[0];assert.ok(view('connection',{query:n.name},frame,{privacy:true}).results.some(r=>r.key===n.key));});
test('network and storage never invent missing per-flow or per-mount rates',()=>{
 const v=view('connection'),e=v.edges.find(e=>e.kind==='relationship'),r=I.fields({key:e.key,kind:'relationship'},e.raw,false,frame);
 assert.ok(r.find(r=>r.label==='TCP acknowledged goodput').value.includes('Unavailable'));
 const mount=frame.storage.mounts[0];assert.ok(I.fields({key:mount.key,kind:'mount'},mount,false,frame).find(r=>r.label==='Per-mount throughput').value.includes('Not measured'));
});
test('audio routing uses real normalized links and muted lens survives search',()=>{
 const v=view('audio');assert.equal(v.edges.filter(e=>e.kind==='audio-link').length,4);assert.ok(v.allNodes.some(n=>n.kind==='source'));assert.ok(v.allNodes.some(n=>n.raw.default));
 const muted=view('audio',{query:'Music',filters:{lens:'muted'}});assert.equal(muted.visibleNodes.some(n=>n.name==='Music player'),false);
});
test('optional hardware is absent rather than represented by fake zeros',()=>{
 const f=Fixtures.frame('quiet'),v=view('machine',{},f);assert.equal(v.allNodes.filter(n=>n.kind==='subsystem').length,4);assert.equal(v.allNodes.some(n=>n.key==='subsystem:gpu'),false);
 assert.equal(M.bytes(null,true),'\u2014');assert.equal(M.percent(null),'\u2014');
});
test('detail relationship selection survives snapshot replacement',()=>{
 const e=view('connection').edges.find(e=>e.kind==='relationship');const v=view('connection',{selectedKey:e.key});assert.equal(v.selection.key,e.key);assert.ok(v.edges.find(x=>x.key===e.key).selected);assert.ok(I.related(v,v.selection).length>=2);
});
test('schema boundary accepts complete fixture and rejects malformed framing',()=>{
 assert.equal(Protocol.validateSnapshot(frame),'');for(const f of [null,{},[],{...frame,schemaVersion:2},{...frame,processes:null},{...frame,events:new Array(3000)}])assert.ok(Protocol.validateSnapshot(f));
});
for(const mode of M.catalog.map(c=>c.id))for(const density of ['quiet','normal','dense']){
 test(`${mode}/${density}: finite bounded geometry, collision-free labels, no clipped primary labels`,()=>{
  const f=Fixtures.frame(density),v=view(mode,{},f);
  for(const [width,height,font] of [[860,480,14],[1450,710,14],[2460,1190,18],[3300,1540,20]]){
   const layout=L.layout(v,width,height,{fontSize:font,smallSize:font-2,labels:'balanced'}, {},t=>metrics(t)*font/14);
   assert.ok(layout.nodes.length<=160);assert.ok(layout.edges.length<=240);assert.ok(layout.labels.length<=54);
   for(const l of layout.labels){assert.ok(l.x>=0&&l.y>=0&&l.x+l.w<=width&&l.y+l.h<=height,JSON.stringify(l));assert.ok(l.h>=font+10);}
   for(let i=0;i<layout.labels.length;i++)for(let j=i+1;j<layout.labels.length;j++)assert.ok(!L.intersects(layout.labels[i],layout.labels[j],0),`${mode}: overlapping labels`);
   for(const n of layout.nodes)assert.ok(Number.isFinite(n.x)&&Number.isFinite(n.y)&&n.x>=0&&n.y>=0&&n.x<=width&&n.y<=height);
  }
 });
 test(`${mode}/${density}: stable deterministic placement and selected label reservation`,()=>{
  const v=view(mode,{},Fixtures.frame(density)),a=L.layout(v,1450,710,{}, {},metrics),b=L.layout(v,1450,710,{},a.positions,metrics);
  assert.deepEqual(a.positions,b.positions);
  if(v.visibleNodes.length){const key=v.visibleNodes.at(-1).key,focused=view(mode,{selectedKey:key,focusKey:key},Fixtures.frame(density)),c=L.layout(focused,1100,580,{focusKey:key},{},metrics);assert.ok(c.nodes.some(n=>n.key===key));assert.ok(c.labels.some(l=>l.key===key),`${mode}: selected label missing`);}
 });
}
test('contrast normalization handles dark, light, invisible accent and saturated themes',()=>{
 for(const [bg,fg,ac] of [['#090d12','#e7edef','#060606'],['#f6f7f9','#ffffff','#ffff00'],['#07111c','#0b141a','#093149'],['#c50066','#820044','#ff00cc']]){
  const p=P.derive(bg,fg,ac,'#ff0033');
  for(const k of ['foreground','subdued','accent','warning','critical','newly','inbound','outbound','read','write'])assert.ok(P.contrast(P.rgb(p[k]),P.rgb(p.background))>=4.49,`${k}: ${p[k]} / ${p.background}`);
 }
});
test('dense raw input still has bounded render complexity',()=>{
 const large=Fixtures.frame('stress'),start=performance.now(),v=view('connection',{},large),layout=L.layout(v,1920,900,{}, {},metrics);
 assert.ok(v.allNodes.length>1000);assert.ok(layout.nodes.length<=160);assert.ok(layout.edges.length<=240);assert.ok(layout.omittedNodes>1000);assert.ok(performance.now()-start<750);
});
test('normal process trees expose ancestry without forcing a first click',()=>{
 const v=view('processes',{},Fixtures.frame('normal'));
 assert.ok(v.visibleNodes.some(n=>n.kind==='process'));
 assert.ok(v.edges.some(e=>e.kind==='parent'));
});
test('pending demand-scoped instance layer keeps aggregate connection visible',()=>{
 const f=Fixtures.frame('normal'),group=f.network.processes[0];
 f.network.instances=[];f.network.instanceLinks=[];f.network.instanceGroups=[];
 const s=N.toggleGroup(N.fresh('connection'),group.key,false),v=M.build(f,s,S.defaults);
 assert.ok(v.visibleNodes.some(n=>n.key===group.key&&n.kind==='application'));
 assert.ok(v.edges.some(e=>e.kind==='relationship'&&e.sourceKey===group.key));
});
test('connection app focus retains aggregation; expansion is explicit',()=>{
 const f=Fixtures.frame('dense'),s=N.focus(N.fresh('connection'),view('connection',{},f).allNodes.find(n=>n.kind==='application'));
 const v=M.build(f,s,S.defaults);
 assert.equal(s.expanded.length,0);
 assert.ok(v.visibleNodes.filter(n=>n.related&&n.kind==='application').length===1);
 assert.ok(v.edges.filter(e=>e.related).length<30);
});
test('nested malformed metrics and duplicate IDs are rejected before rendering',()=>{
 const f=Fixtures.frame('normal');f.processes[0].cpuPercent='NaN';assert.ok(Protocol.validateSnapshot(f));
 const g=Fixtures.frame('normal');g.processes.push(g.processes[0]);assert.ok(Protocol.validateSnapshot(g));
 const h=Fixtures.frame('normal');h.hardware.thermals[0].temperatureC=Infinity;assert.ok(Protocol.validateSnapshot(h));
 assert.ok(Protocol.validateDetail({type:'detail',key:'x',ended:false,data:{sockets:'not an array'},monotonic:1}));
});
test('actual production helper frame is accepted by frontend schema',()=>{
 const cp=require('node:child_process'),path=require('node:path');
 const raw=cp.execFileSync('python3',[path.join(__dirname,'../../scripts/telemetry.py'),'--once','--instrument','all','--socket-source','proc'],{timeout:8000,maxBuffer:4194304,env:{...process.env,PYTHONDONTWRITEBYTECODE:'1'}});
 assert.equal(Protocol.validateSnapshot(JSON.parse(raw)), '');
});
test('relationship context preserves process instance and application separately',()=>{
 const c=N.contextFor({kind:'relationship',key:'r',raw:{processKey:'process:42:900',groupKey:'application:test',remoteKey:'remote:x'}});
 assert.equal(c.processKey,'process:42:900');assert.equal(c.groupKey,'application:test');
});
test('fixture socket ownership is conserved when groups expand',()=>{
 const f=Fixtures.frame('dense');
 assert.equal(f.network.links.reduce((n,l)=>n+l.socketCount,0),f.network.instanceLinks.reduce((n,l)=>n+l.socketCount,0));
});
test('audio sink focus traces the actual upstream apps, not just one mixer hop',()=>{
 const f=Fixtures.frame('normal'),v=view('audio',{selectedKey:'audio-node:3',focusKey:'audio-node:3'},f);
 assert.ok(v.allNodes.find(n=>n.key==='audio-node:0').related);
 assert.ok(v.allNodes.find(n=>n.key==='audio-node:1').related);
 assert.equal(v.allNodes.find(n=>n.key==='audio-node:5').related,false);
});
test('machine contributor subtitles follow the selected resource metric',()=>{
 const f=Fixtures.frame('normal'),v=view('machine',{selectedKey:'subsystem:memory',focusKey:'subsystem:memory'},f);
 assert.ok(v.allNodes.filter(n=>n.kind==='application'&&n.related).every(n=>n.subtitle.includes('MiB')));
});
test('published configuration schema covers exactly the runtime setting keys',()=>{
 const schema=require('../../config/settings.schema.json');
 assert.deepEqual(Object.keys(schema.properties).filter(k=>k!=='id').sort(),Object.values(S.keys).sort());
 for(const [key,field] of Object.entries(S.keys))assert.deepEqual(schema.properties[field].default,S.defaults[key]);
});

test('fresh unattributed inbound relationship survives expansion and dense layout',()=>{
 const f=Fixtures.frame('dense'),groupKey='application:ssh-unattributed',processKey='process:None:unverified',remoteKey='remote:ssh-client';
 f.network.links.forEach(l=>{l.event='steady';l.newCount=0;});
 f.network.instanceLinks.forEach(l=>{l.event='steady';l.newCount=0;});
 f.network.remotes.forEach(r=>{r.event='steady';});
 f.network.processes.push({key:groupKey,name:'Unattributed',pids:[],processKeys:[processKey],socketCount:1,remoteKeys:[remoteKey],listenerPorts:[22],active:true,event:'steady'});
 f.network.instances.push({key:processKey,name:'Unattributed',pid:null,pids:[],processKeys:[processKey],groupKey:groupKey,socketCount:1,remoteKeys:[remoteKey],active:true,event:'steady'});
 f.network.remotes.push({key:remoteKey,name:'192.168.122.1',address:'192.168.122.1',family:4,scope:'remote',processKeys:[groupKey],socketCount:1,ports:[22],active:true,event:'steady'});
 const aggregate={key:'relationship:ssh',sourceKey:groupKey,targetKey:remoteKey,processKey:groupKey,remoteKey:remoteKey,proto:'tcp',kind:'inbound',direction:'in',servicePort:22,serviceName:'ssh',states:['ESTABLISHED'],socketCount:1,totalSocketCount:1,newCount:1,closedCount:0,active:true,closed:false,event:'opened',eventAgeMs:100,queueBytes:0,processKeys:[processKey]};
 f.network.links.push(aggregate);
 f.network.instanceLinks.push(Object.assign({},aggregate,{key:'relationship:ssh:instance',sourceKey:processKey,processKey:processKey,groupKey:groupKey,processKeys:[processKey]}));
 const v=view('connection',{expanded:[groupKey]},f),proc=v.allNodes.find(n=>n.key===processKey),remote=v.allNodes.find(n=>n.key===remoteKey);
 assert.ok(proc);assert.ok(remote);assert.equal(proc.event,'opened');assert.equal(remote.event,'opened');
 assert.ok(v.edges.some(e=>e.raw.servicePort===22&&e.raw.kind==='inbound'));
 const scene=L.layout(v,720,420,{labels:'balanced'}, {},metrics);
 assert.ok(scene.nodes.some(n=>n.key===processKey),'fresh unattributed process endpoint was density-suppressed');
 assert.ok(scene.nodes.some(n=>n.key===remoteKey),'fresh SSH remote endpoint was density-suppressed');
 assert.ok(scene.edges.some(e=>e.raw.servicePort===22),'fresh SSH relationship was not drawable');
});