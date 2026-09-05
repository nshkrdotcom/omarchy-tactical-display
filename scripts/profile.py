#!/usr/bin/env python3
"""Measure real backend samples, without saving endpoint/process identity data."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import platform
import resource
import statistics
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from td_telemetry.engine import TelemetryEngine, INSTRUMENTS


def percentile(values: list[float], p: float) -> float:
    return sorted(values)[min(len(values)-1, int((len(values)-1)*p))]


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--instrument',choices=(*INSTRUMENTS,'all'),default='all')
    p.add_argument('--samples',type=int,default=40)
    p.add_argument('--interval',type=float,default=0.75)
    p.add_argument('--output',type=Path)
    a=p.parse_args()
    if not 2<=a.samples<=100000 or not .25<=a.interval<=10:p.error('samples 2..100000; interval 0.25..10 seconds')
    e=TelemetryEngine(a.instrument,interval=a.interval)
    durations=[];sizes=[];rss=[];current_rss=[];counts=[];caps={};start=time.monotonic();cpu=time.process_time()
    try:
        for i in range(a.samples):
            sample_start=time.monotonic();f=e.sample()
            durations.append(float(f['sampleDurationMs']));sizes.append(len(json.dumps(f,separators=(',',':')).encode()))
            rss.append(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
            current_rss.append(int(Path('/proc/self/statm').read_text().split()[1])*os.sysconf('SC_PAGE_SIZE')//1024)
            counts.append({'processes':len(f['processes']),'relationships':len(f['network']['links']),'audioNodes':len(f['audio']['nodes']),'mounts':len(f['storage']['mounts'])})
            caps={k:{'status':v['status'],'source':v['source']} for k,v in f['capabilities'].items()}
            if i+1<a.samples:time.sleep(max(0,a.interval-(time.monotonic()-sample_start)))
        elapsed=time.monotonic()-start
        report={'status':'PASS','scope':'Real Linux backend only; not shell/Qt/GPU-frame performance','platform':platform.platform(),
                'python':platform.python_version(),'cpuCount':os.cpu_count(),'instrument':a.instrument,'samples':a.samples,'intervalSeconds':a.interval,
                'elapsedSeconds':round(elapsed,3),'samplerCpuPercentOneCore':round((time.process_time()-cpu)/elapsed*100,3),
                'sampleMs':{'p50':round(statistics.median(durations),3),'p95':round(percentile(durations,.95),3),'max':round(max(durations),3)},
                'maxFrameBytes':max(sizes),'residentKiB':{'first':current_rss[0],'last':current_rss[-1],'max':max(current_rss)},
                'rssHighWaterKiB':{'first':rss[0],'last':rss[-1],'max':max(rss)},'firstCounts':counts[0],'lastCounts':counts[-1],'capabilities':caps}
    finally:e.close()
    raw=json.dumps(report,indent=2)+'\n'
    if a.output:
        a.output.parent.mkdir(parents=True,exist_ok=True)
        with os.fdopen(os.open(a.output,os.O_WRONLY|os.O_CREAT|os.O_TRUNC|os.O_NOFOLLOW,0o600),'w') as out:out.write(raw)
    print(raw,end='');return 0

if __name__=='__main__':raise SystemExit(main())
