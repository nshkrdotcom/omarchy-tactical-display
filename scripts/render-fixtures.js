#!/usr/bin/env node
/* Developer-only shared-renderer SVG evidence. NOT a Quickshell/Qt screenshot.
 * No fixture import exists in the production entry points or helper.
 * Usage: node scripts/render-fixtures.js --out /tmp/tactical-previews
 */
'use strict';
const fs=require('node:fs'),path=require('node:path');
const Model=require('../model/InstrumentModel'),Nav=require('../model/Navigation'),Settings=require('../model/Settings');
const Layout=require('../visual/Layout'),Draw=require('../visual/Draw'),Palette=require('../visual/Palette'),Inspection=require('../model/Inspection');
const Fixtures=require('../fixtures/scenarios');
const args=process.argv.slice(2);function argument(k,f){let i=args.indexOf(k);return i>=0?args[i+1]:f;}
const out=argument('--out','/tmp/tactical-previews');fs.mkdirSync(out,{recursive:true});
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&apos;'}[c]));
class SvgCanvas {
 constructor(w,h){this.width=w;this.height=h;this.elements=[];this.globalAlpha=1;this.fillStyle='#fff';this.strokeStyle='#fff';this.lineWidth=1;this.font='14px monospace';this.textAlign='left';this.path='';}
 clearRect(){this.elements=[];}beginPath(){this.path='';}moveTo(x,y){this.path+=`M${x},${y} `;}lineTo(x,y){this.path+=`L${x},${y} `;}bezierCurveTo(...p){this.path+='C'+p.join(',')+' ';}closePath(){this.path+='Z ';}
 fill(){this.elements.push(`<path d="${this.path}" fill="${esc(this.fillStyle)}" opacity="${this.globalAlpha}"/>`);}
 stroke(){this.elements.push(`<path d="${this.path}" fill="none" stroke="${esc(this.strokeStyle)}" stroke-width="${this.lineWidth}" opacity="${this.globalAlpha}" stroke-linecap="round" stroke-linejoin="round"/>`);}
 fillText(t,x,y){this.elements.push(`<text x="${x}" y="${y}" style="font:${esc(this.font)}" text-anchor="${this.textAlign==='center'?'middle':this.textAlign==='right'?'end':'start'}" fill="${esc(this.fillStyle)}" opacity="${this.globalAlpha}">${esc(t)}</text>`);}
}
function text(t,x,y,size,color,extra=''){return `<text x="${x}" y="${y}" font-family="DejaVu Sans Mono,monospace" font-size="${size}" fill="${color}" ${extra}>${esc(t)}</text>`;}
function rect(x,y,w,h,fill,stroke='none'){return `<rect x="${x}" y="${y}" width="${Math.max(0,w)}" height="${Math.max(0,h)}" rx="3" fill="${fill}" stroke="${stroke}"/>`;}
function render(mode,scenario,variant,width=1920,height=1080){
 const frame=Fixtures.frame(scenario),settings={...Settings.defaults,privacy:variant==='privacy',animation:variant==='reduced'?'reduced':'normal'};
 let state=Nav.fresh(mode),view=Model.build(frame,state,settings);
 if(variant==='selected'||variant==='light'||variant==='search'){
  const chosen=view.results.find(n=>mode==='audio'?n.kind==='sink':mode==='connection'||mode==='processes'?n.kind==='application':mode==='machine'?n.kind==='subsystem':n.kind==='device')||view.results[0];
  if(chosen){state=Nav.select(state,chosen);state=Nav.focus(state,chosen);if(variant==='search')state.query=chosen.name.slice(0,4);}
 }
 view=Model.build(frame,state,settings);
 const p=variant==='light'?Palette.derive('#f3f0e7','#202327','#b58236','#c12248'):Palette.derive('#101b24','#e4e9ea','#93c6be','#ee647c');p.fontFamily='DejaVu Sans Mono';
 const margin=width<1100?24:46,header=width<1100?190:220,detail=state.selectedKey?(width<1100?0:350):0;
 const fieldWidth=width-2*margin-detail-(detail?24:0),fieldHeight=height-header-margin-42-(state.selectedKey&&width<1100?200:0);
 const measure=t=>Array.from(String(t)).reduce((n,c)=>n+(/[\u3000-\uffef]/.test(c)?16:9.64),0);
 const scene=Layout.layout(view,fieldWidth,fieldHeight,{labels:settings.labelDensity,fontSize:16,smallSize:13,focusKey:state.focusKey},{},measure);
 const ctx=new SvgCanvas(scene.width,scene.height);Draw.draw(ctx,scene,p);
 let svg=`<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">`;
 svg+=rect(0,0,width,height,p.background)+rect(margin,0,56,3,p.accent);
 svg+=text('TACTICAL DISPLAY  /  LOCAL INSTRUMENTS',margin,margin+10,12,p.subdued);
 svg+=text(view.info.name,margin,margin+47,28,p.foreground)+text(view.info.purpose,margin,margin+73,14,p.subdued);
 svg+=text('TEST FIXTURE / NOT A QUATTRO CAPTURE',width-margin,margin+15,12,p.warning,'text-anchor="end"');
 let railX=margin;
 Model.catalog.forEach((m,i)=>{const t=(i+1)+' '+m.shortName,w=measure(t)+26;svg+=rect(railX,margin+93,w,32,m.id===mode?p.plane:p.background,m.id===mode?p.accent:p.line)+text(t,railX+12,margin+114,12,m.id===mode?p.foreground:p.subdued);railX+=w+6;});
 if(railX+290<width)svg+=text('/ Search   Space Freeze   ? Legend',railX+16,margin+114,12,p.subdued);
 svg+=`<path d="M${margin},${margin+141} H${width-margin}" stroke="${p.line}"/>`;
 svg+=text(view.status.map(s=>s[0]+' '+s[1]).join('   '),margin,margin+164,12,p.foreground);
 svg+=`<g transform="translate(${margin},${header})">`+ctx.elements.join('');
 scene.labels.forEach(l=>{svg+=`<g opacity="${l.opacity}">`+rect(l.x,l.y,l.w,l.h,p.background,l.selected?p.accent:'none')+text(l.text,l.x+7,l.y+19,16,p.foreground);if(l.secondary)svg+=text(l.secondary,l.x+7,l.y+36,13,p.subdued);svg+='</g>';});
 svg+='</g>';
 if(detail&&view.selection){const x=width-margin-detail;svg+=rect(x,header,detail,fieldHeight,p.panel,p.line)+text('INSPECT / '+view.selection.kind.toUpperCase(),x+18,header+28,12,p.accent)+text(Layout.fitText(view.selection.name,detail-36,measure),x+18,header+57,17,p.foreground);
  const rows=Inspection.fields(view.selection,view.selection.raw,settings.privacy,frame);let y=header+94;
  rows.slice(0,8).forEach(r=>{svg+=text(r.label,x+18,y,12,p.subdued)+text(Layout.fitText(r.value,detail-36,measure),x+18,y+22,14,p.foreground);y+=60;});
 }
 if(!view.visibleNodes.length)svg+=text(view.empty||'No observations in this view',width/2,header+fieldHeight*0.42,16,p.subdued,'text-anchor="middle"');
 svg+=text('1-5 Switch  / Search  Tab Select  Enter Focus  F Isolate  Space Freeze  Esc Close  /  Backspace Back',margin,height-27,12,p.subdued);
 svg+=text(`${scene.nodes.length} nodes / ${scene.edges.length} links / ${scene.labels.length} labels / ${scene.omittedNodes} omitted`,width-margin,height-27,12,p.subdued,'text-anchor="end"');
 svg+='</svg>';
 const name=`${mode}-${scenario}-${variant}-${width}x${height}`;fs.writeFileSync(path.join(out,name+'.svg'),svg);
 return {file:name+'.svg',mode,scenario,variant,width,height,nodes:scene.nodes.length,edges:scene.edges.length,labels:scene.labels.length,omittedNodes:scene.omittedNodes,omittedEdges:scene.omittedEdges};
}
const modes=argument('--instrument','all')==='all'?Model.catalog.map(x=>x.id):[argument('--instrument','connection')];
const records=[];
for(const mode of modes){
 for(const [scenario,variant] of [['quiet','normal'],['normal','normal'],['dense','normal'],['dense','selected'],['normal','search'],['normal','light'],['normal','privacy'],['normal','reduced']])records.push(render(mode,scenario,variant));
 records.push(render(mode,'dense','normal',1280,720));
 records.push(render(mode,'normal','selected',2560,1440));
}
fs.writeFileSync(path.join(out,'metrics.json'),JSON.stringify({notice:'TEST FIXTURES: shared JS layout/draw executed; SVG text approximates Qt FontMetrics. These are not Qt/Omarchy screenshots.',records},null,2)+'\n');
console.log(`Wrote ${records.length} shared-renderer SVG previews to ${out}`);
