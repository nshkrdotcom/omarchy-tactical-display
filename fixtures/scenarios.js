// TEST-ONLY deterministic observations. Never imported by runtime QML or Python.
// Reserved documentation IPs and fictional names: these are NOT live telemetry.
function clone(o){return JSON.parse(JSON.stringify(o));}
function frame(density) {
    density=density||'normal';
    var groups=density==='stress'?350:density==='dense'?18:6;
    var remotes=density==='stress'?1600:density==='dense'?54:12;
    var rowsPerGroup=density==='stress'?14:density==='dense'?8:3;
    var f={schemaVersion:3,type:'snapshot',sequence:4,monotonic:1000,wallTime:1700000000,instrument:'all',intervalSeconds:0.75,
        fixture:true,capabilities:{},processes:[],groups:[],system:{cpuPercent:28,cores:[{key:'cpu0',cpuPercent:48,package:'0',core:'0'},{key:'cpu1',cpuPercent:8,package:'0',core:'1'}],load:[1.2,0.8,0.6],memory:{totalBytes:34359738368,usedBytes:10737418240,availableBytes:23622320128,cacheBytes:6442450944,buffersBytes:10000000,swapUsedBytes:0,swapTotalBytes:4294967296},pressure:{cpu:{some:{avg10:2.1}},memory:{some:{avg10:0}},io:{some:{avg10:6.5}}},netRxBps:491520,netTxBps:81920,uptimeSeconds:25000,interfaces:[{key:'eth0:2',name:'eth0',rxBps:491520,txBps:81920}],networkScope:'sum of non-loopback interface counters'},
        network:{processes:[],instances:[],instanceLinks:[],remotes:[],links:[],listeners:[],summary:{}},storage:{devices:[],mounts:[],links:[],contributors:[],summary:{}},audio:{nodes:[],devices:[],links:[],ports:[],clients:[],defaults:{}},hardware:{gpus:[],thermals:[],fans:[]},events:[],trend:[],limits:{fixture:'Test data only'}};
    ['processes','network','machine','storage','audio','gpu','thermal','enrichment'].forEach(function(p){f.capabilities[p]={provider:p,source:'TEST FIXTURE / '+p,status:'available',level:'fixture',sampledAt:1000,intervalSeconds:0.75,durationMs:3,complete:true,reason:'',suggestion:''};});
    var names=['Firefox','Terminal','Project API','Code editor','Media player','PipeWire'];
    for(var g=0;g<groups;g++){
        var group={key:'application:fixture-'+g,name:names[g%names.length]+(g>=6?' '+g:''),processKeys:[],pids:[],cpuPercent:(g*13+4)%90,rssBytes:(60+g%10*73)*1048576,threads:4+g%12,readBps:g===1?2097152:0,writeBps:g===2?6291456:0,networkSockets:0,executable:'/usr/bin/'+names[g%6].toLowerCase().replace(/ /g,'-'),cgroup:'0::/app.slice/app-fixture-'+g+'.scope',provenance:'fixture cgroup (observed in scenario)',active:true,closed:false,event:g===2?'opened':'steady'};
        for(var p=0;p<rowsPerGroup;p++){
            var pid=1000+g*rowsPerGroup+p,key='process:'+pid+':'+(100+p),parent=p?('process:'+(pid-1)+':'+(100+p-1)):null;
            var row={key:key,pid:pid,ppid:p?pid-1:1,startTicks:100+p,name:group.name+(p?' worker '+p:''),executable:group.executable,cgroup:group.cgroup,state:'S',groupKey:group.key,groupName:group.name,groupProvenance:group.provenance,parentKey:parent,cpuPercent:group.cpuPercent/rowsPerGroup,rssBytes:Math.floor(group.rssBytes/rowsPerGroup),threads:3,readBps:group.readBps/rowsPerGroup,writeBps:group.writeBps/rowsPerGroup,readBytes:8388608,writeBytes:16777216,uid:1000,event:p===2&&g===1?'opened':'steady',closed:false,ageMs:10000,eventAgeMs:200};
            group.pids.push(pid);group.processKeys.push(key);f.processes.push(row);
        }
        f.groups.push(group);
        f.network.processes.push(Object.assign({},group,{socketCount:0,remoteKeys:[],listenerPorts:[],command:group.executable}));
    }
    for(var r=0;r<remotes;r++)f.network.remotes.push({key:'remote:fixture-'+r,name:r<6?['docs.example.test','source.example.test','packages.example.test','media.example.test','api.example.test','shared.example.test'][r]:'2001:db8::'+(r+1).toString(16),address:r<240?'198.51.100.'+(r+1):'2001:db8::'+(r+1).toString(16),family:r<240?4:6,scope:r===remotes-1?'loopback':'remote',nameSource:'fixture local alias',nameTrusted:true,processKeys:[],socketCount:0,ports:[],event:r===1?'opened':'steady',active:true,closed:false,ageMs:8000,eventAgeMs:300});
    f.network.remotes[f.network.remotes.length-1].name='localhost';f.network.remotes[f.network.remotes.length-1].address='127.0.0.1';
    var linksPerGroup=density==='stress'?24:density==='dense'?11:4;
    for(var gi=0;gi<groups;gi++)for(var j=0;j<linksPerGroup;j++){
        var ri=(gi*5+j*3)%remotes,remote=f.network.remotes[ri],owner=f.network.processes[gi],socketCount=2+j%5,closed=gi===1&&j===2;
        var link={key:'relationship:fixture-'+gi+'-'+j,sourceKey:owner.key,targetKey:remote.key,processKey:owner.key,remoteKey:remote.key,groupKey:owner.key,proto:j===3?'udp':'tcp',kind:remote.scope==='loopback'?'loopback':j===1?'inbound':'outbound',direction:j===1?'in':'out',servicePort:j===1?8080:j===3?443:443,states:[closed?'CLOSED':'ESTABLISHED'],socketCount:closed?0:socketCount,totalSocketCount:socketCount,newCount:j===0?1:0,closedCount:closed?socketCount:0,active:!closed,closed:closed,event:closed?'closed':j===0?'opened':'steady',queueBytes:gi===2&&j===0?65536:0,ackedBps:null,receivedBps:null,ageMs:12000,processKeys:owner.processKeys,sharedOwnership:false,provenance:'matching fixture listener; inference, not connect provenance',sockets:[],eventAgeMs:400};
        for(var si=0;si<socketCount;si++)link.sockets.push({key:'socket:fixture-'+gi+'-'+j+'-'+si,proto:link.proto,state:link.states[0],local:'192.0.2.10:'+(40000+si),remote:remote.address+':443',source:'TEST FIXTURE',owners:[{name:owner.name,pid:owner.pids[si%owner.pids.length],processKey:owner.processKeys[si%owner.processKeys.length]}],queueBytes:0,ackedBps:null,receivedBps:null});
        f.network.links.push(link);owner.socketCount+=link.socketCount;if(owner.remoteKeys.indexOf(remote.key)<0)owner.remoteKeys.push(remote.key);
        remote.socketCount+=link.socketCount;if(remote.processKeys.indexOf(owner.key)<0)remote.processKeys.push(owner.key);if(remote.ports.indexOf(link.servicePort)<0)remote.ports.push(link.servicePort);
        f.groups[gi].networkSockets=owner.socketCount;
        owner.processKeys.forEach(function(pk,index){
            var children=link.sockets.filter(function(s){return s.owners.some(function(o){return o.processKey===pk;});});
            if(!children.length)return;
            var il=clone(link);il.key+=':instance-'+index;il.processKey=pk;il.sourceKey=pk;il.sockets=clone(children);il.socketCount=link.closed?0:children.length;il.totalSocketCount=children.length;il.processKeys=[pk];f.network.instanceLinks.push(il);
        });
    }
    f.processes.forEach(function(p){var group=f.network.processes.find(g=>g.key===p.groupKey);f.network.instances.push(Object.assign({},p,{pids:[p.pid],socketCount:f.network.instanceLinks.filter(l=>l.processKey===p.key).reduce((a,l)=>a+l.socketCount,0),remoteKeys:group.remoteKeys,processKeys:[p.key],active:true}));});
    [1,2,3].forEach(function(i){var owner=f.network.processes[i%groups];f.network.listeners.push({key:'listener:fixture-'+i,name:'TCP '+(8080+i),proto:'tcp',port:8080+i,local:'0.0.0.0:'+(8080+i),processKey:owner.key,groupKey:owner.key,processKeys:owner.processKeys,socketCount:1,state:'LISTEN',role:'listener',active:true,event:'steady',socketPreview:[]});owner.listenerPorts.push(8080+i);});
    f.network.summary={connections:f.network.links.reduce((a,l)=>a+l.socketCount,0),processes:groups,remoteSystems:remotes-1,listeners:3,relationships:f.network.links.filter(l=>l.active).length};
    var devices=density==='dense'?10:4,mountNames=['/','/home','/boot','/mnt/archive','/srv/data','/var/lib/containers'];
    for(var d=0;d<devices;d++){
        var partition=d===1,dev={key:'block:259:'+d,majorMinor:'259:'+d,name:d===0?'nvme0n1':d===1?'nvme0n1p2':d===2?'dm-0':'nvme'+d+'n1',partition:partition,parentKey:partition?'block:259:0':null,slaves:d===2?['block:259:1']:[],physical:d===0||d>2,model:'Fixture SSD',readBps:d===0?2097152:0,writeBps:d===0?6291456:0,busyPercent:d===0?34:0,inFlight:d===0?2:0,readAwaitMs:d===0?0.42:null,writeAwaitMs:d===0?1.12:null};f.storage.devices.push(dev);
        var mount={key:'mount:fixture-'+d,mountId:40+d,path:mountNames[d%mountNames.length]+(d>5?'/'+d:''),name:mountNames[d%mountNames.length],fsType:'ext4',source:'/dev/'+dev.name,deviceKey:dev.key,majorMinor:dev.majorMinor,capacity:{totalBytes:1000000000000,availableBytes:540000000000,sampledAt:999},provenance:'/proc/self/mountinfo (fixture)'};mount.name=mount.path;f.storage.mounts.push(mount);f.storage.links.push({key:'mount-device:'+d,sourceKey:mount.key,targetKey:dev.key,kind:'mount-device',provenance:'mountinfo major:minor'});
        if(partition)f.storage.links.push({key:'partition:'+d,sourceKey:dev.key,targetKey:'block:259:0',kind:'partition'});
        if(d===2)f.storage.links.push({key:'slave:'+d,sourceKey:dev.key,targetKey:'block:259:1',kind:'backing-device'});
    }
    f.storage.contributors=f.processes.slice(0,Math.min(12,f.processes.length)).map(clone);
    f.storage.contributors.forEach(function(p,i){f.storage.links.push({key:'fd:'+i,sourceKey:p.key,targetKey:f.storage.mounts[i%devices].key,kind:'open-fd',count:1,provenance:'fdinfo mnt_id; structural, NOT per-mount byte attribution'});});
    f.storage.summary={readBps:2097152,writeBps:6291456,physicalDevices:2,aggregateScope:'whole physical leaf devices only'};
    var audio=[['Music player','Stream/Output/Audio',null,false],['Browser audio','Stream/Output/Audio',null,false],['System routing','Audio/Filter',null,false],['USB speakers','Audio/Sink','audio-device:0',true],['USB microphone','Audio/Source','audio-device:1',true],['Call capture','Stream/Input/Audio',null,false]];
    audio.forEach(function(a,i){f.audio.nodes.push({key:'audio-node:'+i,name:a[0],nodeName:'fixture.node.'+i,mediaClass:a[1],deviceKey:a[2],default:a[3],state:i===1?'idle':'running',mute:i===1,volume:0.75,objectId:40+i,serial:String(100+i),processKey:f.processes[i].key,groupKey:f.processes[i].groupKey,pid:f.processes[i].pid,sampleRate:48000,channels:2,event:i===0?'opened':'steady',eventAgeMs:400});});
    [[0,2],[1,2],[2,3],[4,5]].forEach(function(l,i){for(var channel=0;channel<2;channel++)f.audio.links.push({key:'audio-link:'+i+':'+channel,sourceKey:'audio-node:'+l[0],targetKey:'audio-node:'+l[1],state:i===1?'paused':'active',outputNodeId:40+l[0],inputNodeId:40+l[1]});});
    f.audio.devices=[{key:'audio-device:0',name:'USB DAC',objectId:80,serial:"200"},{key:'audio-device:1',name:'USB microphone',objectId:81,serial:"201"}];
    f.hardware.gpus=[{key:'gpu:fixture',name:'Fixture GPU',utilizationPercent:42,memoryUsedBytes:3221225472,memoryTotalBytes:17179869184,temperatureC:48,source:'TEST FIXTURE / optional hardware'}];
    f.hardware.thermals=[{key:'thermal:fixture',name:'Fixture package sensor',temperatureC:56,source:'TEST FIXTURE / hwmon'}];
    for(var t=0;t<60;t++)f.trend.push({at:941+t,cpuPercent:20+10*Math.sin(t/8),memoryUsedBytes:10737418240,readBps:2097152,writeBps:t>30?6291456:0,netRxBps:491520,netTxBps:81920});
    if(density==='quiet'){
        f.network={processes:[],instances:[],instanceLinks:[],remotes:[],links:[],listeners:[],summary:{connections:0,processes:0,remoteSystems:0,listeners:0,relationships:0}};
        f.audio.nodes=[];f.audio.links=[];f.audio.devices=[];f.groups=[];f.processes=[];f.storage.contributors=[];f.storage.links=f.storage.links.filter(l=>l.kind!=='open-fd');f.system.cpuPercent=0;f.hardware={gpus:[],thermals:[],fans:[]};
    }
    return f;
}
if(typeof module!=='undefined')module.exports={frame:frame};
