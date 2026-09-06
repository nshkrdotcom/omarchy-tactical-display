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
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from td_telemetry.common import proc_child_count
PLUGIN='nshkr.tactical-display'
MODES=('connection','processes','machine','storage','audio')


def command(*argv: str, timeout: float=8) -> str:
    p=subprocess.run(argv,capture_output=True,text=True,timeout=timeout,check=True)
    result=p.stdout.strip()
    if result.lower() in ('false','unknown','error'):raise RuntimeError('Native shell rejected '+argv[2])
    return result


def omarchy_git_metadata(path: str | None) -> dict[str, str]:
    if not path:
        return {}

    metadata = {'omarchyPath': path}
    git = shutil.which('git')
    if not git:
        return metadata

    try:
        probe = subprocess.run(
            (git, '-C', path, 'rev-parse', '--is-inside-work-tree'),
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if probe.returncode != 0 or probe.stdout.strip() != 'true':
            return metadata

        commit = command(git, '-C', path, 'rev-parse', 'HEAD')
        version = command(git, '-C', path, 'describe', '--tags', '--always')
    except (OSError, RuntimeError, subprocess.SubprocessError):
        return metadata

    metadata['omarchyCommit'] = commit
    metadata['omarchyVersion'] = version
    return metadata


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


def wait_soak_diagnostic(mode: str, timeout: float=1.0) -> tuple[dict, int]:
    until=time.monotonic()+timeout
    last='not loaded'
    retries=0
    while time.monotonic()<until:
        try:
            d=diagnostic()
            if d.get('opened') and d.get('fresh') and d.get('helperPid',0)>0 and d.get('instrument')==mode:
                return d,retries
            last=str({k:d.get(k) for k in ('opened','fresh','ready','status','instrument')})
        except (ValueError,RuntimeError,subprocess.SubprocessError) as exc:
            last=str(exc)
        retries+=1
        time.sleep(.05)
    raise RuntimeError('Native diagnostics unavailable during soak after bounded retry: '+last)


def proc_stat(pid: int) -> dict | None:
    try:
        base=Path(f'/proc/{pid}');raw=(base/'stat').read_text();v=raw[raw.rfind(')')+2:].split()
        fd_count=sum(1 for _ in (base/'fd').iterdir())
        child_count=proc_child_count(pid)
        return {'pid':pid,'ppid':int(v[1]),'startTicks':int(v[19]),'cpuTicks':int(v[11])+int(v[12]),
                'rssBytes':int(v[21])*os.sysconf('SC_PAGE_SIZE'),'fdCount':fd_count,'childCount':child_count}
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
    p.add_argument('--max-helper-rss-mib',type=int,default=256)
    p.add_argument('--max-helper-fds',type=int,default=128)
    p.add_argument('--max-helper-children',type=int,default=4)
    p.add_argument('--max-helper-cpu-percent',type=float,default=75.0,help='one-core percent averaged between soak samples')
    p.add_argument('--max-ready-ms',type=float,default=5000.0)
    p.add_argument('--max-sample-ms',type=float,default=1500.0)
    p.add_argument('--max-shell-rss-growth-mib',type=int,default=128)
    p.add_argument('--max-shell-fd-growth',type=int,default=64)
    p.add_argument('--max-shell-child-growth',type=int,default=16)
    a=p.parse_args()
    if not a.run:p.error('--run is required; this tool takes and releases overlay keyboard focus')
    if not 1<=a.cycles<=1000 or not 0<=a.soak_seconds<=86400:p.error('cycles 1..1000; soak-seconds 0..86400')
    if min(a.max_helper_rss_mib,a.max_helper_fds,a.max_helper_children,a.max_helper_cpu_percent,a.max_ready_ms,a.max_sample_ms,a.max_shell_rss_growth_mib,a.max_shell_fd_growth,a.max_shell_child_growth)<=0:p.error('resource budgets must be positive')
    if a.output.resolve().is_relative_to(ROOT):p.error('keep evidence OUTSIDE the watched plugin directory')
    missing=[x for x in ('omarchy','omarchy-shell','hyprctl') if not shutil.which(x)]
    if missing or not os.environ.get('WAYLAND_DISPLAY'):
        print(json.dumps({'status':'NOT RUN','reason':'Real Wayland/Omarchy environment required','missing':missing}));return 77
    report={'status':'RUNNING','startedUtc':datetime.now(timezone.utc).isoformat(),'cycles':[], 'soak':[],
            'manualGates':{'keyboardHold':'NOT RUN','barClickOrientation':'NOT RUN','monitorHotplug':'NOT RUN','visualMatrix':'NOT RUN','frameHitches':'NOT RUN','hotReload':'NOT RUN','shellRestart':'NOT RUN'}}
    try:
        report['manifestValidation']=command('omarchy','plugin','validate',str(ROOT))
        report['hyprlandVersion']=command('hyprctl','version')
        report.update(omarchy_git_metadata(os.environ.get('OMARCHY_PATH')))
        # Close an existing session only after --run was explicitly requested.
        command('omarchy-shell','shell','hide',PLUGIN)
        for i in range(a.cycles):
            mode=MODES[i%len(MODES)];start=time.monotonic()
            command('omarchy-shell','shell','summon',PLUGIN,json.dumps({'instrument':mode}))
            d=wait_ready(mode);ready_ms=round((time.monotonic()-start)*1000,2);helpers=matching_helpers()
            if ready_ms>a.max_ready_ms:raise RuntimeError('Overlay readiness exceeded configured latency budget')
            if isinstance(d.get('sampleDurationMs'),(int,float)) and d['sampleDurationMs']>a.max_sample_ms:raise RuntimeError('Helper sample latency exceeded configured budget')
            if len(helpers)!=1 or helpers[0]!=d['helperPid']:raise RuntimeError('Expected one shared helper, observed '+str(helpers))
            helper=proc_stat(d['helperPid']);parent=proc_stat(helper['ppid']) if helper else None
            if helper and helper['rssBytes']>a.max_helper_rss_mib*1024*1024:raise RuntimeError('Helper RSS exceeded configured budget')
            if helper and helper['fdCount']>a.max_helper_fds:raise RuntimeError('Helper FD count exceeded configured budget')
            if helper and helper['childCount'] is None:raise RuntimeError('Helper child-process metric unavailable on target procfs')
            if helper and helper['childCount']>a.max_helper_children:raise RuntimeError('Helper child count exceeded configured budget')
            hide_and_reap(d['helperPid'])
            report['cycles'].append({'cycle':i+1,'instrument':mode,'readyMs':ready_ms,
                                    'diagnostic':d,'helper':helper,'shellAtOpen':parent,'shellAfterHide':proc_stat(parent['pid']) if parent else None,'status':'PASS'})
        if a.soak_seconds:
            start=time.monotonic();mode='connection';command('omarchy-shell','shell','summon',PLUGIN,json.dumps({'instrument':mode}));wait_ready(mode)
            last_switch=start;last_seq=None;last_pid=None;last_helper=None;last_helper_at=None;hz=os.sysconf('SC_CLK_TCK')
            while time.monotonic()-start<a.soak_seconds:
                if time.monotonic()-last_switch>=60:
                    mode=MODES[(MODES.index(mode)+1)%len(MODES)]
                    command('omarchy-shell','shell','summon',PLUGIN,json.dumps({'instrument':mode}));wait_ready(mode);last_switch=time.monotonic()
                d,retries=wait_soak_diagnostic(mode)
                if not d.get('fresh'):raise RuntimeError('Stale telemetry during native soak')
                if len(matching_helpers())!=1:raise RuntimeError('Helper duplication during native soak')
                if d['helperPid']==last_pid and d['sequence']==last_seq:raise RuntimeError('Telemetry sequence stopped advancing')
                last_seq,last_pid=d['sequence'],d['helperPid'];helper=proc_stat(last_pid);sample_at=time.monotonic();helper_cpu=None
                if helper and last_helper and last_helper_at is not None and helper['pid']==last_helper['pid'] and helper['startTicks']==last_helper['startTicks'] and sample_at>last_helper_at:
                    helper_cpu=max(0.0,(helper['cpuTicks']-last_helper['cpuTicks'])/hz/(sample_at-last_helper_at)*100.0)
                last_helper,last_helper_at=helper,sample_at
                if helper and helper['rssBytes']>a.max_helper_rss_mib*1024*1024:raise RuntimeError('Helper RSS exceeded configured budget during soak')
                if helper and helper['fdCount']>a.max_helper_fds:raise RuntimeError('Helper FD count exceeded configured budget during soak')
                if helper and helper['childCount'] is None:raise RuntimeError('Helper child-process metric unavailable on target procfs during soak')
                if helper and helper['childCount']>a.max_helper_children:raise RuntimeError('Helper child count exceeded configured budget during soak')
                if helper_cpu is not None and helper_cpu>a.max_helper_cpu_percent:raise RuntimeError('Helper CPU exceeded configured one-core budget during soak')
                if isinstance(d.get('sampleDurationMs'),(int,float)) and d['sampleDurationMs']>a.max_sample_ms:raise RuntimeError('Helper sample latency exceeded configured budget during soak')
                report['soak'].append({'seconds':round(time.monotonic()-start,2),'diagnostic':d,'diagnosticRetries':retries,'helper':helper,'helperCpuPercentOneCore':round(helper_cpu,3) if helper_cpu is not None else None,'shell':proc_stat(helper['ppid']) if helper else None})
                time.sleep(3)
            hide_and_reap(last_pid)
        shell_samples=[c.get('shellAfterHide') for c in report['cycles'] if c.get('shellAfterHide')]
        shell_growth_rss=shell_growth_fds=shell_growth_children=0
        if shell_samples:
            first=shell_samples[0];same=[x for x in shell_samples if x['pid']==first['pid'] and x['startTicks']==first['startTicks']]
            if same:
                if any(x['childCount'] is None for x in same):
                    raise RuntimeError('Shell child-process metric unavailable on target procfs')
                shell_growth_rss=max(x['rssBytes'] for x in same)-first['rssBytes']
                shell_growth_fds=max(x['fdCount'] for x in same)-first['fdCount']
                shell_growth_children=max(x['childCount'] for x in same)-first['childCount']
                if shell_growth_rss>a.max_shell_rss_growth_mib*1024*1024:raise RuntimeError('Shell RSS growth exceeded configured lifecycle budget')
                if shell_growth_fds>a.max_shell_fd_growth:raise RuntimeError('Shell FD growth exceeded configured lifecycle budget')
                if shell_growth_children>a.max_shell_child_growth:raise RuntimeError('Shell child-process growth exceeded configured lifecycle budget')
        report['resourceBudget']={'maxHelperRssMiB':a.max_helper_rss_mib,'maxHelperFds':a.max_helper_fds,
                                  'maxHelperChildren':a.max_helper_children,'maxHelperCpuPercentOneCore':a.max_helper_cpu_percent,
                                  'maxReadyMs':a.max_ready_ms,'maxSampleMs':a.max_sample_ms,
                                  'maxShellRssGrowthMiB':a.max_shell_rss_growth_mib,'maxShellFdGrowth':a.max_shell_fd_growth,
                                  'maxShellChildGrowth':a.max_shell_child_growth,
                                  'observedShellRssGrowthBytes':shell_growth_rss,'observedShellFdGrowth':shell_growth_fds,
                                  'observedShellChildGrowth':shell_growth_children}
        report['status']='PASS';report['soakStatus']='PASS' if a.soak_seconds>=1800 else 'PARTIAL' if a.soak_seconds else 'NOT RUN';report['scope']='Native IPC/helper lifecycle plus configured CPU-memory-FD-child/readiness/sample-latency containment; manual interaction/visual gates remain NOT RUN'
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