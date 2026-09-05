// Shared Canvas2D drawing implementation, also used by the SVG verification adapter.
// No random positions, timers, telemetry parsing, packet particles or fabricated motion.
function alpha(hex,amount){
    hex=String(hex).replace('#','');if(hex.length!==6)return 'rgba(128,128,128,'+amount+')';
    return 'rgba('+parseInt(hex.slice(0,2),16)+','+parseInt(hex.slice(2,4),16)+','+parseInt(hex.slice(4,6),16)+','+amount+')';
}
function line(ctx,points,color,width,closed){
    if(!points.length)return;ctx.beginPath();ctx.moveTo(points[0][0],points[0][1]);
    for(var i=1;i<points.length;i++)ctx.lineTo(points[i][0],points[i][1]);
    if(closed)ctx.closePath();ctx.strokeStyle=color;ctx.lineWidth=width||1;ctx.stroke();
}
function poly(ctx,points,fill,stroke,width){ctx.beginPath();ctx.moveTo(points[0][0],points[0][1]);for(var i=1;i<points.length;i++)ctx.lineTo(points[i][0],points[i][1]);ctx.closePath();if(fill){ctx.fillStyle=fill;ctx.fill();}if(stroke){ctx.strokeStyle=stroke;ctx.lineWidth=width||1;ctx.stroke();}}
function ellipse(ctx,x,y,rx,ry,color,width,fill){
    var k=0.5522847498;ctx.beginPath();ctx.moveTo(x+rx,y);
    ctx.bezierCurveTo(x+rx,y+k*ry,x+k*rx,y+ry,x,y+ry);
    ctx.bezierCurveTo(x-k*rx,y+ry,x-rx,y+k*ry,x-rx,y);
    ctx.bezierCurveTo(x-rx,y-k*ry,x-k*rx,y-ry,x,y-ry);
    ctx.bezierCurveTo(x+k*rx,y-ry,x+rx,y-k*ry,x+rx,y);
    if(fill){ctx.fillStyle=fill;ctx.fill();}if(color){ctx.strokeStyle=color;ctx.lineWidth=width||1;ctx.stroke();}
}
function label(ctx,text,x,y,p,size,align,opacity){ctx.fillStyle=p.subdued;ctx.font=Math.max(12,size||12)+'px '+(p.fontFamily||'monospace');ctx.textAlign=align||'left';ctx.fillText(text,x,y);}
function plane(ctx,x,y,w,h,p,opacity){
    poly(ctx,[[x-w/2,y],[x,y-h/2],[x+w/2,y],[x,y+h/2]],alpha(p.accent,0.025*opacity),alpha(p.accent,0.26*opacity),1);
    poly(ctx,[[x-w/2,y],[x,y+h/2],[x+w/2,y],[x+w/2,y+8],[x,y+h/2+8],[x-w/2,y+8]],alpha(p.foreground,0.025*opacity),null);
    line(ctx,[[x-w/2,y+8],[x,y+h/2+8],[x+w/2,y+8]],alpha(p.accent,0.15*opacity));
}
function world(ctx,layout,p){
    var w=layout.width,h=layout.height,mode=layout.instrument;
    if(mode==='connection') {
        var cx=w*0.5,cy=h*0.66;
        ellipse(ctx,cx,cy+14,w*0.365,h*0.17,alpha(p.accent,0.075),1,alpha(p.background,0.22));
        ellipse(ctx,cx,cy,w*0.365,h*0.17,alpha(p.accent,0.36),1,alpha(p.accent,0.025));
        ellipse(ctx,cx,cy,w*0.285,h*0.125,alpha(p.accent,0.10),1);
        ellipse(ctx,cx,cy,w*0.13,h*0.057,alpha(p.accent,0.24),1,alpha(p.background,0.15));
        line(ctx,[[cx-w*0.365,cy],[cx+w*0.365,cy]],alpha(p.accent,0.055));
        line(ctx,[[cx,cy-h*0.17],[cx,cy+h*0.17]],alpha(p.accent,0.055));
        ctx.beginPath();ctx.moveTo(w*0.04,h*0.36);ctx.bezierCurveTo(w*0.22,h*0.04,w*0.78,h*0.04,w*0.96,h*0.36);ctx.strokeStyle=alpha(p.foreground,0.11);ctx.lineWidth=1;ctx.stroke();
        label(ctx,'REMOTE SYSTEMS',w*0.5,23,p,12,'center',0.72);
        label(ctx,'LOCAL APPLICATION PLANE',w*0.5,h*0.94,p,12,'center',0.65);
        label(ctx,'THIS MACHINE',cx,cy+4,p,11,'center',0.64);
        label(ctx,'LOOPBACK INSIDE',cx,cy+21,p,10,'center',0.45);
        label(ctx,'Listeners anchor to the boundary',w*0.06,h*0.97,p,11,'left',0.55);
    } else if(mode==='processes') {
        label(ctx,'APPLICATION ISLANDS / OBSERVED ANCESTRY',w*0.5,23,p,12,'center',0.72);
        var groups=layout.nodes.filter(function(n){return n.kind==='application';});
        groups.forEach(function(g){ellipse(ctx,g.x,g.y+8,clampSize(w*0.065,46,92),clampSize(h*0.048,18,34),alpha(p.accent,0.10*g.opacity),1,alpha(p.accent,0.018*g.opacity));});
        label(ctx,'Expand an island to trace individual processes',w*0.06,h*0.97,p,11,'left',0.55);
    } else if(mode==='machine') {
        label(ctx,'RESOURCE CUTAWAY / MEASURED CONTRIBUTORS',w*0.5,23,p,12,'center',0.72);
        layout.nodes.filter(function(n){return n.kind==='subsystem';}).forEach(function(n){plane(ctx,n.x,n.y+16,Math.min(w*0.25,270),Math.min(h*0.15,100),p,n.opacity);});
        label(ctx,'Accounting relationships, not a simulated hardware bus',w*0.06,h*0.97,p,11,'left',0.55);
    } else if(mode==='storage') {
        var levels=[['PROCESS I/O',0.17],['MOUNTED FILESYSTEMS',0.44],['LOGICAL / PARTITION LAYER',0.66],['BLOCK DEVICES',0.84]];
        levels.forEach(function(z){var y=h*z[1];poly(ctx,[[w*0.03,y+10],[w*0.13,y-26],[w*0.97,y-26],[w*0.87,y+10]],alpha(p.accent,0.018),alpha(p.accent,0.10));label(ctx,z[0],w*0.035,y-34,p,11,'left',0.70);});
        label(ctx,'Up-notch = measured reads; down-notch = writes. Dashed links = open descriptors, NOT byte flow',w*0.06,h*0.97,p,11,'left',0.62);
    } else {
        var cols=[['PLAYBACK / CAPTURE',0.15],['ROUTING',0.44],['SINKS / SOURCES',0.72],['DEVICES',0.90]];
        cols.forEach(function(c){var x=w*c[1];line(ctx,[[x,42],[x,h*0.92]],alpha(p.accent,0.10));label(ctx,c[0],x,23,p,11,'center',0.70);});
        label(ctx,'Arrowheads follow actual PipeWire links; gain is not a level meter',w*0.06,h*0.97,p,11,'left',0.60);
    }
}
function clampSize(v,a,b){return Math.max(a,Math.min(b,v));}
function curve(e,mode){
    var a=e.source,b=e.target,dx=b.x-a.x,dy=b.y-a.y;
    if(mode==='connection'&&e.kind==='relationship'){
        var lift=Math.min(110,Math.abs(dx)*0.17+Math.abs(dy)*0.12);
        return [[a.x,a.y],[a.x+dx*0.12,a.y+dy*0.30-lift],[b.x-dx*0.12,b.y-dy*0.25-lift],[b.x,b.y]];
    }
    if(mode==='audio')return [[a.x,a.y],[a.x+dx*0.48,a.y],[b.x-dx*0.48,b.y],[b.x,b.y]];
    return [[a.x,a.y],[a.x+dx*0.12,a.y+dy*0.48],[b.x-dx*0.12,b.y-dy*0.48],[b.x,b.y]];
}
function bezier(c,t){var s=1-t;return [s*s*s*c[0][0]+3*s*s*t*c[1][0]+3*s*t*t*c[2][0]+t*t*t*c[3][0],s*s*s*c[0][1]+3*s*s*t*c[1][1]+3*s*t*t*c[2][1]+t*t*t*c[3][1]];}
function edgeColor(e,p){return e.kind==='open-fd'?p.subdued:e.direction==='in'?p.inbound:e.event==='opened'?p.newly:e.event==='changed'?p.warning:e.closed?p.subdued:p.accent;}
function drawEdge(ctx,e,mode,p){
    var c=curve(e,mode),selected=e.selected||e.source.selected||e.target.selected||e.source.focused||e.target.focused;
    var opacity=selected?0.95:e.closed?0.23:e.related?0.46:0.045;
    var color=edgeColor(e,p),width=selected?2.25:Math.min(3.2,0.65+Math.log(1+e.weight)*0.45);
    var dashed=e.closed||e.kind==='open-fd'||e.muted||e.kind==='audio-link'&&e.state!=='active';
    if(dashed){
        var points=[];for(var i=0;i<=32;i++){var point=bezier(c,i/32);if(i%4<2)points.push(point);else if(points.length){line(ctx,points,alpha(color,opacity),width);points=[];}}
        if(points.length)line(ctx,points,alpha(color,opacity),width);
    }else{
        ctx.beginPath();ctx.moveTo(c[0][0],c[0][1]);ctx.bezierCurveTo(c[1][0],c[1][1],c[2][0],c[2][1],c[3][0],c[3][1]);ctx.strokeStyle=alpha(color,opacity);ctx.lineWidth=width;ctx.stroke();
    }
    if(['membership','listener','device-link','open-fd'].indexOf(e.kind)<0 && !e.closed){
        var t=e.direction==='in'?0.18:0.82,a=bezier(c,t),b=bezier(c,t+(e.direction==='in'?-0.02:0.02)),ang=Math.atan2(b[1]-a[1],b[0]-a[0]),r=selected?6:4;
        poly(ctx,[[a[0]+Math.cos(ang)*r,a[1]+Math.sin(ang)*r],[a[0]+Math.cos(ang+2.5)*r,a[1]+Math.sin(ang+2.5)*r],[a[0]+Math.cos(ang-2.5)*r,a[1]+Math.sin(ang-2.5)*r]],alpha(color,Math.min(1,opacity+0.15)),null);
    }
}
function drawNode(ctx,n,p){
    var x=n.x,y=n.y,r=n.radius,highlight=n.selected||n.focused,color=n.closed?p.subdued:n.event==='opened'?p.newly:n.event==='changed'?p.warning:highlight?p.foreground:p.accent;
    ctx.globalAlpha=n.opacity;
    if(highlight){ellipse(ctx,x,y+5,r+13,r*0.65+6,alpha(p.accent,0.45),1,alpha(p.accent,0.06));}
    var fill=alpha(p.background,0.96),stroke=color;
    if(n.kind==='remote')poly(ctx,[[x,y-r],[x+r,y],[x,y+r],[x-r,y]],fill,stroke,highlight?2:1.4);
    else if(n.kind==='mount')poly(ctx,[[x-r,y-r*0.6],[x+r+3,y-r*0.6],[x+r,y+r*0.6],[x-r-3,y+r*0.6]],fill,stroke,1.4);
    else if(n.kind==='device'||n.kind==='audio-device'){
        poly(ctx,[[x-r,y-3],[x,y-r],[x+r,y-3],[x,y+3]],fill,stroke,1.4);
        line(ctx,[[x-r,y+2],[x,y+8],[x+r,y+2]],stroke,1.4);
    }else if(n.kind==='listener'){
        line(ctx,[[x-r,y-r],[x-r,y+r],[x+r,y+r],[x+r,y-r]],stroke,1.8);
        line(ctx,[[x-3,y-r-3],[x-3,y],[x+3,y],[x+3,y-r-3]],stroke,1);
    }else if(n.kind==='stream')poly(ctx,[[x-r,y-r],[x+r,y],[x-r,y+r]],fill,stroke,1.4);
    else if(n.kind==='sink'||n.kind==='source'||n.kind==='audio-node'){
        ellipse(ctx,x,y,r,r,stroke,1.4,fill);
        if(n.raw.default)ellipse(ctx,x,y,r+4,r+4,stroke,1);
        if(n.raw.mute)line(ctx,[[x-r-2,y+r+2],[x+r+2,y-r-2]],p.critical,2);
    }else if(n.kind==='subsystem'){
        // A cutaway component with data-dependent pressure tick, not a circular gauge.
        poly(ctx,[[x-r,y-7],[x,y-17],[x+r,y-7],[x+r,y+8],[x,y+18],[x-r,y+8]],fill,stroke,highlight?2:1.2);
        line(ctx,[[x-r,y-7],[x,y+3],[x+r,y-7]],alpha(color,0.6),1);
        line(ctx,[[x,y+3],[x,y+18]],alpha(color,0.6),1);
        if(typeof n.pressure==='number' && n.pressure>5)poly(ctx,[[x+r+6,y-10],[x+r+10,y-3],[x+r+2,y-3]],p.warning,null);
    }else{
        poly(ctx,[[x-r,y-r],[x+r,y-r],[x+r,y+r],[x-r,y+r]],fill,stroke,highlight?2:1.4);
        if(n.kind==='application')line(ctx,[[x-r+3,y+r+4],[x+r+4,y+r+4],[x+r+4,y-r+3]],alpha(color,0.65),1);
    }
    if(n.event==='changed')line(ctx,[[x-r-4,y-r-4],[x-r-4,y-r+3],[x-r+3,y-r+3]],p.warning,2);
    if(n.raw && (n.zone==='io-process'||n.kind==='device')){
        // Static up/down notches indicate actually observed read/write activity.
        if(typeof n.raw.readBps==='number' && n.raw.readBps>0)poly(ctx,[[x-r-10,y-6],[x-r-14,y+1],[x-r-6,y+1]],p.read,null);
        if(typeof n.raw.writeBps==='number' && n.raw.writeBps>0)poly(ctx,[[x+r+10,y+6],[x+r+14,y-1],[x+r+6,y-1]],p.write,null);
    }
    if(n.closed){line(ctx,[[x-r,y-r],[x+r,y+r]],p.subdued,1);}
    ctx.globalAlpha=1;
}
function draw(ctx,layout,p){
    ctx.clearRect(0,0,layout.width,layout.height);ctx.lineCap='round';ctx.lineJoin='round';
    world(ctx,layout,p);
    layout.edges.slice().sort(function(a,b){return (a.related?1:0)-(b.related?1:0);}).forEach(function(e){drawEdge(ctx,e,layout.instrument,p);});
    layout.nodes.slice().sort(function(a,b){return a.y-b.y;}).forEach(function(n){drawNode(ctx,n,p);});
    layout.labels.forEach(function(l){
        var x=l.x+l.w/2,y=l.y+l.h/2,dx=x-l.nodeX,dy=y-l.nodeY;
        if(Math.sqrt(dx*dx+dy*dy)>l.w*0.7+20)line(ctx,[[l.nodeX,l.nodeY],[x,y]],alpha(p.accent,l.selected?0.5:0.18),1);
    });
}
if(typeof module!=='undefined') module.exports={draw:draw,world:world,drawNode:drawNode,curve:curve,bezier:bezier,alpha:alpha};
