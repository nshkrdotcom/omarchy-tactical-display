function controls(instrument,state,settings) {
    var f=state.filters||{};
    if(instrument==='connection')return [
        {key:'direction',label:'Origin: '+(f.direction||'any'),values:['any','outbound','inbound','loopback'],hint:'V / Origin is inferred from visible listeners'},
        {key:'protocol',label:'Protocol: '+(f.protocol||'any'),values:['any','tcp','udp'],hint:'N / TCP and UDP'},
        {key:'state',label:'State: '+(f.state||'any'),values:['any','live','closed','listeners'],hint:'B / Live, recent close, or listeners'}];
    if(instrument==='processes')return [{key:'emphasis',label:'Emphasis: '+(f.emphasis||'cpu'),values:['cpu','memory','threads','network','io'],hint:'E / Rank processes by resource usage'}];
    if(instrument==='storage')return [{key:'lens',label:'Lens: '+(f.lens||'all'),values:['all','reads','writes','mounts','devices'],hint:'V / Filter by observed I/O or topology layer'}];
    if(instrument==='audio')return [{key:'lens',label:'Lens: '+(f.lens||'all'),values:['all','playback','capture','muted','devices'],hint:'V / Audio graph lens'}];
    return [];
}
function settingsRows(){return [
    {key:'defaultInstrument',label:'First-run instrument',choices:['connection','processes','machine','storage','audio'],hint:'Later opens remember the last instrument.'},
    {key:'animation',label:'Motion',choices:['reduced','normal','vivid'],hint:'Transition and update animation speed.'},
    {key:'refreshProfile',label:'Refresh',choices:['efficient','balanced','responsive'],hint:'Target cadence: 1.5 / 0.75 / 0.35 s. Audio: 2 s. Hardware: 5 s.'},
    {key:'labels',label:'Label density',choices:['minimal','balanced','dense'],hint:'Changes the label budget, not readable text size.'},
    {key:'naming',label:'Endpoint names',choices:['raw','local','dns'],hint:'DNS is explicit opt-in: system-resolver PTR lookups may leave the machine. Privacy mode suppresses them.'},
    {key:'loopback',label:'Show loopback',choices:[true,false],hint:'Local-to-local communication remains inside the machine plane.'},
    {key:'listeners',label:'Show listeners',choices:[true,false],hint:'Includes UDP bindings, separately labeled; these are not remote connections.'},
    {key:'privacy',label:'Screen-share privacy',choices:[true,false],hint:'Masks process names, network endpoints, and desktop background for screen sharing.'},
    {key:'barMode',label:'Bar display',choices:['icon','label'],hint:'Vertical bars always use compact TD text.'},
    {key:'audioActions',label:'Enable audio actions',choices:[false,true],hint:'Opt-in mute/default changes, with confirmation and one-step undo. Observe-only remains the default.'}
];}
if(typeof module!=='undefined')module.exports={controls:controls,settingsRows:settingsRows};
