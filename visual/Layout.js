// Deterministic semantic anchors, bounded point collisions and a second-pass label allocator.
// Runs at model/interaction frequency, never in a frame callback.
function hash(s) {var h=2166136261;for(var i=0;i<s.length;i++){h^=s.charCodeAt(i);h=Math.imul(h,16777619);}return h>>>0;}
function clamp(v,a,b){return Math.max(a,Math.min(b,v));}
function intersects(a,b,pad){pad=pad||0;return a.x<b.x+b.w+pad && a.x+a.w+pad>b.x && a.y<b.y+b.h+pad && a.y+a.h+pad>b.y;}
function unit(key,salt){return hash(key+':'+salt)/4294967295;}
function rank(a,b){return (b.selected?1:0)-(a.selected?1:0)||(b.focused?1:0)-(a.focused?1:0)||(b.related?1:0)-(a.related?1:0)||((b.event==='opened')?1:0)-((a.event==='opened')?1:0)||b.priority-a.priority||a.key.localeCompare(b.key);}
function anchor(n,mode,focus) {
    var u=unit(n.key,'x'),v=unit(n.key,'y'),g=unit(n.groupKey||n.key,'group'),angle=(u*2-1)*Math.PI;
    var x=0.5,y=0.5,bounds={x:0.055,y:0.09,w:0.89,h:0.83};
    if(mode==='connection') {
        if(n.zone==='horizon') {x=0.10+0.8*u;y=0.15+0.17*Math.pow((x-0.5)/0.4,2)+0.065*(v-0.5);bounds={x:0.055,y:0.09,w:0.89,h:0.30};}
        else if(n.zone==='near') {x=0.5+0.285*Math.cos(angle);y=0.65+0.125*Math.sin(angle);bounds={x:0.16,y:0.48,w:0.68,h:0.34};}
        else if(n.zone==='local') {x=0.5+0.105*Math.cos(angle);y=0.64+0.047*Math.sin(angle);bounds={x:0.37,y:0.55,w:0.26,h:0.2};}
        else if(n.zone==='boundary') {x=0.5+0.40*Math.cos(angle);y=0.68+0.205*Math.sin(angle);bounds={x:0.055,y:0.46,w:0.89,h:0.47};}
        else {x=0.5;y=0.83;}
        if(focus && n.focused) {x=0.5;y=n.kind==='remote'?0.24:0.65;}
        if(focus && n.related && !n.focused && n.zone==='horizon') {x=0.1+0.8*u;y=0.19+0.14*Math.pow((x-0.5)/0.4,2);}
    } else if(mode==='processes') {
        var islandKey=n.zone==='island'?n.key:n.groupKey||n.key;
        var ix=0.16+0.68*unit(islandKey,'x'),iy=0.16+0.40*unit(islandKey,'y');
        if(n.zone==='island') {x=ix;y=iy;}
        else {x=ix+(u-0.5)*0.20;y=iy+0.10+Math.min(n.topologyDepth,5)*0.055+(v-0.5)*0.018;}
        if(focus && n.focused) {x=0.5;y=0.45;}
        bounds={x:0.055,y:0.10,w:0.89,h:0.80};
    } else if(mode==='machine') {
        var zones={compute:[0.31,0.32],memory:[0.64,0.29],storage:[0.29,0.69],network:[0.65,0.66],gpu:[0.84,0.46],thermal:[0.48,0.86]};
        if(zones[n.zone]){x=zones[n.zone][0];y=zones[n.zone][1];}
        else {
            var z=zones[n.resourceZone]||[0.5,0.5];
            x=z[0]+(u-0.5)*0.25;y=z[1]+(v<0.5?-0.17:0.16)+(v-0.5)*0.06;
        }
    } else if(mode==='storage') {
        var levels={'io-process':0.17,mount:0.44,'logical-device':0.66,device:0.84};
        x=0.09+0.82*u;y=(levels[n.zone]||0.5)+(v-0.5)*0.075;
        bounds={x:0.055,y:(levels[n.zone]||0.5)-0.08,w:0.89,h:0.16};
    } else {
        var columns={'audio-playback':0.13,'audio-capture':0.16,'audio-route':0.44,'audio-endpoint':0.72,'audio-hardware':0.90};
        x=(columns[n.zone]||0.5)+(u-0.5)*0.045;
        y=n.zone==='audio-playback'?0.17+0.38*v:n.zone==='audio-capture'?0.65+0.19*v:0.16+0.66*v;
        bounds={x:x-0.075,y:0.10,w:0.15,h:0.79};
    }
    return {x:x,y:y,bounds:bounds};
}
function fitText(text,width,measure) {
    text=String(text||'');if(measure(text)<=width)return text;
    var lo=0,hi=text.length;
    while(lo<hi){var mid=Math.ceil((lo+hi)/2);if(measure(text.slice(0,mid)+'\u2026')<=width)lo=mid;else hi=mid-1;}
    return text.slice(0,lo)+'\u2026';
}
function layout(view,width,height,options,previous,measure) {
    options=options||{};previous=previous||{};measure=measure||function(t){return t.length*8;};
    var w=Math.max(240,width),h=Math.max(180,height),mode=view.instrument,focus=!!options.focusKey;
    var scale=Math.max(1,(options.fontSize||14)/14);
    var budget=clamp(Math.floor(w*h/(8500*scale*scale)),28,160),labelBudget=clamp(Math.floor(w*h/(scale*scale*(options.labels==='dense'?19000:options.labels==='minimal'?48000:29000))),8,52);
    var candidates=(view.visibleNodes||[]).slice().sort(rank),chosen=candidates.slice(0,budget),nodes=[],positions={},lookup={},occupied=[];
    // Spatial hash makes the bounded collision solver O(N * fixedAttempts), not O(N^2).
    var cells={},cellSize=44;
    function keysFor(box){var keys=[];for(var x=Math.floor(box.x/cellSize);x<=Math.floor((box.x+box.w)/cellSize);x++)for(var y=Math.floor(box.y/cellSize);y<=Math.floor((box.y+box.h)/cellSize);y++)keys.push(x+','+y);return keys;}
    function collides(box){var keys=keysFor(box);for(var i=0;i<keys.length;i++){var rows=cells[keys[i]]||[];for(var j=0;j<rows.length;j++)if(intersects(box,rows[j],2))return true;}return false;}
    function occupy(box){keysFor(box).forEach(function(k){if(!cells[k])cells[k]=[];cells[k].push(box);});occupied.push(box);}
    // Reserve semantic annotation space as well as node/label space.
    if(mode==='connection')occupy({x:w*0.5-72,y:h*0.66-10,w:144,h:42});
    if(mode==='storage') [0.17,0.44,0.66,0.84].forEach(function(level){occupy({x:w*0.035,y:h*level-50,w:Math.min(225,w*0.3),h:22});});
    var hiddenByCollision=0;
    chosen.forEach(function(source){
        var n={};Object.keys(source).forEach(function(k){n[k]=source[k];});
        var base=anchor(n,mode,focus),prior=previous[n.key],same=prior && prior.mode===mode && prior.zone===n.zone && prior.focusKey===(options.focusKey||'');
        var ax=(same?prior.x:base.x)*w,ay=(same?prior.y:base.y)*h;
        var radius=n.kind==='subsystem'?22:n.kind==='application'?10:8;
        var markerSize=n.kind==='subsystem'?52:32;
        var box,px=ax,py=ay,placed=false;
        var b={x:Math.max(24,base.bounds.x*w),y:Math.max(42,base.bounds.y*h),
               maxX:Math.min(w-24,(base.bounds.x+base.bounds.w)*w),maxY:Math.min(h-30,(base.bounds.y+base.bounds.h)*h)};
        for(var i=0;i<48;i++) {
            var ring=Math.ceil(Math.sqrt(i)),theta=i*2.3999632297;
            px=clamp(ax+(i?Math.cos(theta)*ring*10:0),b.x,b.maxX);
            py=clamp(ay+(i?Math.sin(theta)*ring*8:0),b.y,b.maxY);
            box={x:px-markerSize/2,y:py-markerSize/2,w:markerSize,h:markerSize};
            if(!collides(box)){placed=true;break;}
        }
        if(!placed && !n.selected && !n.focused){hiddenByCollision++;return;}
        n.x=px;n.y=py;n.radius=radius;n.selected=!!n.selected;n.focused=!!n.focused;
        n.opacity=n.selected||n.focused?1:n.closed?0.42:!n.related?0.20:!n.match?0.25:1;
        positions[n.key]={mode:mode,zone:n.zone,x:px/w,y:py/h,focusKey:options.focusKey||''};
        lookup[n.key]=n;nodes.push(n);occupy(box);
    });
    var edges=(view.edges||[]).filter(function(e){return lookup[e.sourceKey]&&lookup[e.targetKey];});
    edges.sort(function(a,b){return (b.related?1:0)-(a.related?1:0)||(b.event==='opened'?1:0)-(a.event==='opened'?1:0)||b.weight-a.weight||a.key.localeCompare(b.key);});
    var edgeBudget=mode==='connection'?Math.min(144,Math.max(48,Math.floor(w*h/11000))):200;
    if(view.selection && mode==='connection'){
        var semantic=edges.filter(function(e){return e.related;}),context=edges.filter(function(e){return !e.related;});
        edges=semantic.concat(context.slice(0,24));
    }
    var omittedEdges=Math.max(0,(view.edges||[]).length-Math.min(edgeBudget,edges.length));
    edges=edges.slice(0,edgeBudget).map(function(source){
        var e={};Object.keys(source).forEach(function(k){e[k]=source[k];});e.source=lookup[e.sourceKey];e.target=lookup[e.targetKey];return e;
    });
    // Label placement has its own budget. Text never gets smaller under density.
    var labels=[],labelBoxes=[],maxLabelWidth=Math.min(280,w*0.29),primaryHeight=options.fontSize||14,secondaryHeight=options.smallSize||12;
    nodes.slice().sort(rank).forEach(function(n){
        if(labels.length>=labelBudget && !n.selected && !n.focused)return;
        var text=fitText(n.name,maxLabelWidth-14,measure),secondary=(n.selected||n.focused||nodes.length<32||n.kind==='subsystem'||n.kind==='device')?fitText(n.subtitle,maxLabelWidth-14,measure):'';
        var bw=Math.ceil(Math.max(measure(text),secondary?measure(secondary)*secondaryHeight/primaryHeight:0)+14),bh=secondary?primaryHeight+secondaryHeight+21:primaryHeight+10;
        var r=Math.max(n.radius+10,22);
        var candidates=[{x:n.x+r,y:n.y-bh/2},{x:n.x-bw/2,y:n.y-r-bh},{x:n.x-bw/2,y:n.y+r},{x:n.x-r-bw,y:n.y-bh/2},
                        {x:n.x+r,y:n.y-r-bh},{x:n.x-r-bw,y:n.y+r}];
        var chosen=null;
        for(var i=0;i<candidates.length;i++){
            var c={x:candidates[i].x,y:candidates[i].y,w:bw,h:bh};
            if(c.x<4||c.y<36||c.x+c.w>w-4||c.y+c.h>h-10)continue;
            if(collides(c))continue;
            if(labelBoxes.some(function(b){return intersects(c,b,4);}))continue;
            chosen=c;break;
        }
        if(!chosen && (n.selected||n.focused)){
            // Dedicated screen-space selection label, with an explicit leader line.
            for(var x=8;x+bw<w-8;x+=bw+8){var c={x:x,y:38,w:bw,h:bh};if(!collides(c)&&!labelBoxes.some(function(b){return intersects(c,b,4);})){chosen=c;break;}}
        }
        if(chosen){labels.push({key:n.key,x:chosen.x,y:chosen.y,w:chosen.w,h:chosen.h,text:text,secondary:secondary,
                               fullText:n.name+(n.subtitle?' / '+n.subtitle:''),selected:n.selected||n.focused,opacity:n.opacity,nodeX:n.x,nodeY:n.y});labelBoxes.push(chosen);}
    });
    return {instrument:mode,width:w,height:h,nodes:nodes,edges:edges,labels:labels,positions:positions,
        omittedNodes:Math.max(0,candidates.length-budget)+hiddenByCollision,omittedEdges:omittedEdges,
        labelBudget:labelBudget,nodeBudget:budget,allNodeCount:candidates.length,focusKey:options.focusKey||''};
}
if(typeof module!=='undefined') module.exports={layout:layout,anchor:anchor,intersects:intersects,fitText:fitText,hash:hash};
