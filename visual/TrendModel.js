// Timestamp-based geometry and cursor semantics shared by Qt and regression tests.
function finite(v) { return typeof v==='number' && isFinite(v); }
function value(v) { return finite(v) && v>=0 ? v : null; }
function series(selected, metric) {
    if (metric==='pressure' && ['subsystem:cpu','subsystem:memory','subsystem:storage'].indexOf(selected)>=0) {
        var prefix=selected==='subsystem:cpu'?'cpu':selected==='subsystem:memory'?'memory':'io';
        var pressure=[{key:prefix+'SomePercent',name:'Some stalled',role:'warning'}];
        if (prefix!=='cpu') pressure.push({key:prefix+'FullPercent',name:'All non-idle stalled',role:'critical'});
        return pressure;
    }
    if (selected==='subsystem:memory') return [{key:'memoryUsedBytes',name:'Used memory',role:'accent'}];
    if (selected==='subsystem:storage') return [{key:'readBps',name:'Read',role:'read'},{key:'writeBps',name:'Write',role:'write'}];
    if (selected==='subsystem:network') return [{key:'netRxBps',name:'Receive',role:'inbound'},{key:'netTxBps',name:'Transmit',role:'outbound'}];
    return [{key:'cpuPercent',name:'Host CPU',role:'accent'}];
}
function niceCeiling(v) {
    if (!(v>0)) return 1;
    var magnitude=Math.pow(10,Math.floor(Math.log(v)/Math.LN10)), fraction=v/magnitude;
    return (fraction<=1?1:fraction<=2?2:fraction<=5?5:10)*magnitude;
}
function build(input, selected, options) {
    options=options||{};
    var specs=series(selected,options.metric), seconds=[15,30,60].indexOf(options.seconds)>=0?options.seconds:60;
    var width=Math.max(1,finite(options.width)?options.width:400),height=Math.max(1,finite(options.height)?options.height:100);
    var unique=Object.create(null);
    (Array.isArray(input)?input:[]).slice(-120).forEach(function(s){if(s && finite(s.at)) unique[s.at]=s;});
    var sorted=Object.keys(unique).map(function(k){return unique[k];}).sort(function(a,b){return a.at-b.at;});
    var end=finite(options.end)?options.end:sorted.length?sorted[sorted.length-1].at:0;
    var start=end-seconds, samples=sorted.filter(function(s){return s.at>=start && s.at<=end;});
    var percent=/Percent$/.test(specs[0].key), unit=percent?'percent':/Bps$/.test(specs[0].key)?'rate':'bytes';
    var maximum=0;
    samples.forEach(function(s){specs.forEach(function(t){var v=value(s[t.key]);if(v!==null && (!percent || v<=100)) maximum=Math.max(maximum,v);});});
    var ceiling=specs[0].key==='cpuPercent'?100:percent?Math.min(100,Math.max(5,niceCeiling(maximum))):niceCeiling(maximum);
    var gap=Math.max(3, (value(options.interval)||1)*3);
    var traces=specs.map(function(spec,index) {
        var paths=[],path=[],min=null,max=null,total=0,count=0,previous=null;
        samples.forEach(function(s) {
            var v=value(s[spec.key]);if (percent && v>100) v=null;
            if (v===null || previous!==null && s.at-previous>gap) { if(path.length) paths.push(path);path=[]; }
            if (v!==null) {
                min=min===null?v:Math.min(min,v);max=max===null?v:Math.max(max,v);total+=v;count++;
                path.push({at:s.at,value:v,x:Math.max(0,Math.min(width,(s.at-start)/seconds*width)),y:height-Math.min(ceiling,v)/ceiling*height});
            }
            previous=s.at;
        });
        if(path.length)paths.push(path);
        var current=samples.length?value(samples[samples.length-1][spec.key]):null;
        if(percent && current>100)current=null;
        return {key:spec.key,name:spec.name,role:spec.role,dashed:index>0,paths:paths,stats:{min:min,max:max,mean:count?total/count:null,current:current,count:count}};
    });
    return {samples:samples,start:start,end:end,seconds:seconds,width:width,height:height,ceiling:ceiling,unit:unit,gap:gap,traces:traces};
}
function inspect(plot, at) {
    if (!finite(at) || at<plot.start || at>plot.end || !plot.samples.length) return null;
    var nearest=plot.samples[0];
    plot.samples.forEach(function(s){if(Math.abs(s.at-at)<Math.abs(nearest.at-at))nearest=s;});
    if (Math.abs(nearest.at-at)>plot.gap/2) return null;
    return {at:nearest.at,x:(nearest.at-plot.start)/plot.seconds*plot.width,
        values:plot.traces.map(function(t){var v=value(nearest[t.key]);return {key:t.key,name:t.name,value:plot.unit==='percent' && v>100?null:v};})};
}
function step(plot, at, direction) {
    if(!plot.samples.length)return null;
    if(!finite(at))return plot.samples[plot.samples.length-1].at;
    var index=0;
    for(var i=0;i<plot.samples.length;i++)if(plot.samples[i].at<=at)index=i;
    return plot.samples[Math.max(0,Math.min(plot.samples.length-1,index+(direction<0?-1:1)))].at;
}
if(typeof module!=='undefined')module.exports={build:build,series:series,inspect:inspect,step:step};
