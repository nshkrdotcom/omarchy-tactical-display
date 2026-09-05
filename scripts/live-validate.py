#!/usr/bin/env python3
"""Opt-in real Quattro lifecycle and soak runner; never substitutes a fake host."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
PLUGIN='nshkr.tactical-display'
MODES=('connection','processes','machine','storage','audio')


def command(*argv: str, timeout: float=8) -> str:
    p=subprocess.run(argv,capture_output=True,text=True,timeout=timeout,check=True)
    result=p.stdout.strip()
    if result.lower() in ('false','unknown','error'):raise RuntimeError('Native shell rejected '+argv[2])
    return result


def diagnostic() -> dict:
    raw=command('omarchy-shell','shell','call',PLUGIN,'diagnostics','{}')
    value=json.loads(raw)
    if isinstance(value,str):value=json.loads(value)
    if not isinstance(value,dict):raise ValueError('Native diagnostics did not return an object')
    return value


def wait_ready(mode: str, timeout: float=10) -> dict:
    until=time.monotonic()+timeout;last='not loaded'
    while time.monotonic()<until:
        try:
            d=diagnostic()
            if d.get('opened') and d.get('fresh') and d.get('helperPid',0)>0 and d.get('instrument')==mode:return d
            last=str({k:d.get(k) for k in ('opened','fresh','ready','status','instrument')})
        except (ValueError,RuntimeError,subprocess.SubprocessError) as exc:last=str(exc)
        time.sleep(.15)
    raise RuntimeError('Native overlay did not become ready: '+last)


def proc_stat(pid: int) -> dict | None:
    try:
        raw=Path(f'/proc/{pid}/stat').read_text();v=raw[raw.rfind(')')+2:].split()
        return {'pid':pid,'ppid':int(v[1]),'startTicks':int(v[19]),'cpuTicks':int(v[11])+int(v[12]),'rssBytes':int(v[21])*os.sysconf('SC_PAGE_SIZE')}
    except (OSError,ValueError,IndexError):return None


def matching_helpers() -> list[int]:
    found=[];expected=os.fsencode(str(ROOT/'scripts/telemetry.py'))
    for p in Path('/proc').iterdir():
        if p.name.isdecimal():
            try:
                if p.stat().st_uid==os.getuid() and expected in (p/'cmdline').read_bytes().split(b'\0'):found.append(int(p.name))
            except OSError:pass
    return found


def hide_and_reap(pid: int) -> None:
    previous=proc_stat(pid)
    command('omarchy-shell','shell','hide',PLUGIN)
    until=time.monotonic()+5
    while time.monotonic()<until:
        current=proc_stat(pid)
        if current is None or previous and current['startTicks']!=previous['startTicks']:return
        time.sleep(.1)
    raise RuntimeError('Telemetry helper survived shell hide')


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',action='store_true',help='explicit permission to summon/hide this overlay repeatedly')
    p.add_argument('--cycles',type=int,default=50)
    p.add_argument('--soak-seconds',type=int,default=1800)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if not a.run:p.error('--run is required; this tool takes and releases overlay keyboard focus')
    if not 1<=a.cycles<=1000 or not 0<=a.soak_seconds<=86400:p.error('cycles 1..1000; soak-seconds 0..86400')
    if a.output.resolve().is_relative_to(ROOT):p.error('keep evidence OUTSIDE the watched plugin directory')
    missing=[x for x in ('omarchy','omarchy-shell','hyprctl') if not shutil.which(x)]
    if missing or not os.environ.get('WAYLAND_DISPLAY'):
        print(json.dumps({'status':'NOT RUN','reason':'Real Wayland/Omarchy environment required','missing':missing}));return 77
    report={'status':'RUNNING','startedUtc':datetime.now(timezone.utc).isoformat(),'cycles':[], 'soak':[],
            'manualGates':{'keyboardHold':'NOT RUN','barClickOrientation':'NOT RUN','monitorHotplug':'NOT RUN','visualMatrix':'NOT RUN','frameHitches':'NOT RUN','hotReload':'NOT RUN','shellRestart':'NOT RUN'}}
    try:
        report['manifestValidation']=command('omarchy','plugin','validate',str(ROOT))
        report['hyprlandVersion']=command('hyprctl','version')
        omarchy=os.environ.get('OMARCHY_PATH')
        if omarchy:
            report['omarchyCommit']=command('git','-C',omarchy,'rev-parse','HEAD')
            report['omarchyVersion']=command('git','-C',omarchy,'describe','--tags','--always')
        # Close an existing session only after --run was explicitly requested.
        command('omarchy-shell','shell','hide',PLUGIN)
        for i in range(a.cycles):
            mode=MODES[i%len(MODES)];start=time.monotonic()
            command('omarchy-shell','shell','summon',PLUGIN,json.dumps({'instrument':mode}))
            d=wait_ready(mode);ready_ms=round((time.monotonic()-start)*1000,2);helpers=matching_helpers()
            if len(helpers)!=1 or helpers[0]!=d['helperPid']:raise RuntimeError('Expected one shared helper, observed '+str(helpers))
            helper=proc_stat(d['helperPid']);parent=proc_stat(helper['ppid']) if helper else None
            hide_and_reap(d['helperPid'])
            report['cycles'].append({'cycle':i+1,'instrument':mode,'readyMs':ready_ms,
                                    'diagnostic':d,'helper':helper,'shellAtOpen':parent,'shellAfterHide':proc_stat(parent['pid']) if parent else None,'status':'PASS'})
        if a.soak_seconds:
            start=time.monotonic();mode='connection';command('omarchy-shell','shell','summon',PLUGIN,json.dumps({'instrument':mode}));wait_ready(mode)
            last_switch=start;last_seq=None;last_pid=None
            while time.monotonic()-start<a.soak_seconds:
                if time.monotonic()-last_switch>=60:
                    mode=MODES[(MODES.index(mode)+1)%len(MODES)]
                    command('omarchy-shell','shell','summon',PLUGIN,json.dumps({'instrument':mode}));wait_ready(mode);last_switch=time.monotonic()
                d=diagnostic()
                if not d.get('fresh'):raise RuntimeError('Stale telemetry during native soak')
                if len(matching_helpers())!=1:raise RuntimeError('Helper duplication during native soak')
                if d['helperPid']==last_pid and d['sequence']==last_seq:raise RuntimeError('Telemetry sequence stopped advancing')
                last_seq,last_pid=d['sequence'],d['helperPid'];helper=proc_stat(last_pid)
                report['soak'].append({'seconds':round(time.monotonic()-start,2),'diagnostic':d,'helper':helper,'shell':proc_stat(helper['ppid']) if helper else None})
                time.sleep(3)
            hide_and_reap(last_pid)
        report['status']='PASS';report['soakStatus']='PASS' if a.soak_seconds>=1800 else 'PARTIAL' if a.soak_seconds else 'NOT RUN';report['scope']='Native IPC/helper lifecycle only; manual gates remain NOT RUN'
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError,KeyboardInterrupt) as exc:
        report['status']='FAIL';report['error']=str(exc)
    finally:
        try:command('omarchy-shell','shell','hide',PLUGIN)
        except (OSError,RuntimeError,subprocess.SubprocessError):pass
        a.output.parent.mkdir(parents=True,exist_ok=True)
        fd=os.open(a.output,os.O_WRONLY|os.O_CREAT|os.O_TRUNC|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'w') as out:json.dump(report,out,indent=2)
    print(json.dumps({'status':report['status'],'completedCycles':len(report['cycles']),'soakSamples':len(report['soak']),'evidence':str(a.output),'manualGates':report['manualGates']}))
    return 0 if report['status']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
