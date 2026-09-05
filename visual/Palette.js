// WCAG relative luminance normalization. Never trust arbitrary theme accents.
function rgb(c) {
    if(Array.isArray(c) && c.length===3)return c.map(function(x){return Math.max(0,Math.min(1,Number(x)||0));});
    if(typeof c === 'object' && c !== null && c.r !== undefined) return [c.r,c.g,c.b];
    var s=String(c||'').replace('#','');
    if(s.length===8) s=s.slice(2);
    if(s.length===3) s=s.replace(/./g,function(x){return x+x;});
    if(!/^[0-9a-f]{6}$/i.test(s)) return [0.04,0.05,0.07];
    return [parseInt(s.slice(0,2),16)/255,parseInt(s.slice(2,4),16)/255,parseInt(s.slice(4,6),16)/255];
}
function hex(v) {return '#'+v.map(function(x){return ('0'+Math.round(Math.max(0,Math.min(1,x))*255).toString(16)).slice(-2);}).join('');}
function lum(v) {var a=rgb(v).map(function(x){return x<=0.04045?x/12.92:Math.pow((x+0.055)/1.055,2.4);});return a[0]*0.2126+a[1]*0.7152+a[2]*0.0722;}
function contrast(a,b) {var x=lum(a),y=lum(b);return (Math.max(x,y)+0.05)/(Math.min(x,y)+0.05);}
function mix(a,b,t) {a=rgb(a);b=rgb(b);return hex([a[0]*(1-t)+b[0]*t,a[1]*(1-t)+b[1]*t,a[2]*(1-t)+b[2]*t]);}
function normalize(color,bg,target) {
    color=hex(rgb(color));bg=hex(rgb(bg));
    if(contrast(color,bg)>=target) return color;
    var end=contrast('#ffffff',bg)>contrast('#000000',bg)?'#ffffff':'#000000';
    for(var i=1;i<=40;i++){var test=mix(color,end,i/40);if(contrast(test,bg)>=target)return test;}
    return end;
}
function derive(bg,fg,accent,urgent) {
    bg=hex(rgb(bg));var text=normalize(fg,bg,7), focus=normalize(accent,bg,4.5);
    return {background:bg,foreground:text,accent:focus,subdued:normalize(mix(text,bg,0.44),bg,4.5),
        line:normalize(mix(text,bg,0.6),bg,3),warning:normalize('#daaa58',bg,4.5),
        critical:normalize(urgent||'#db6172',bg,4.5),newly:normalize(mix(focus,'#56ba9a',0.55),bg,4.5),
        inbound:normalize(mix(focus,'#bc94d6',0.5),bg,4.5),outbound:focus,read:focus,
        write:normalize('#cc955b',bg,4.5),plane:mix(bg,focus,0.055),panel:bg,light:lum(bg)>0.5};
}
if(typeof module!=='undefined') module.exports={rgb:rgb,hex:hex,lum:lum,contrast:contrast,mix:mix,normalize:normalize,derive:derive};
