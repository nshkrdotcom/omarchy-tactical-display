#!/usr/bin/env python3
"""Real PipeWire graph test with an opt-in silent, temporary playback stream."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import wave
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from td_telemetry.audio import AudioProvider
from td_telemetry.processes import ProcessProvider


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',action='store_true');a=p.parse_args()
    if not a.run:p.error('--run permits creating a temporary silent playback stream (no mixer changes)')
    if not all(shutil.which(x) for x in ('pw-dump','pw-play')):
        print('NOT RUN: pw-dump/pw-play are required in a real PipeWire session');return 77
    provider=AudioProvider();processes=ProcessProvider()
    first=provider.sample(time.monotonic(),processes.sample(time.monotonic()))
    if provider.capability.status not in ('available','partial'):
        print('NOT RUN: '+provider.capability.reason);return 77
    if not any(n.get('mediaClass')=='Audio/Sink' for n in first['nodes']):
        print('NOT RUN: no playback sink exists');return 77
    with tempfile.TemporaryDirectory(prefix='tactical-audio-') as temp:
        wav=Path(temp)/'silence.wav'
        with wave.open(str(wav),'wb') as out:
            out.setnchannels(2);out.setsampwidth(2);out.setframerate(48000);out.writeframes(b'\0'*(48000*2*2*12))
        child=subprocess.Popen(['pw-play',str(wav)],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        try:
            until=time.monotonic()+9
            while time.monotonic()<until and child.poll() is None:
                f=provider.sample(time.monotonic(),processes.sample(time.monotonic()))
                keys={n['key'] for n in f['nodes'] if n.get('pid')==child.pid}
                routes=[l for l in f['links'] if l.get('sourceKey') in keys]
                if keys and routes:
                    print(json.dumps({'status':'PASS','scope':'Real silent stream discovered with outgoing PipeWire links','nodes':len(keys),'links':len(routes)}));return 0
                time.sleep(.5)
            print('FAIL: controlled stream was not observed with an outgoing route');return 1
        finally:
            if child.poll() is None:child.terminate()
            try:child.wait(timeout=2)
            except subprocess.TimeoutExpired:child.kill();child.wait()
            if child.stderr:child.stderr.close()

if __name__=='__main__':raise SystemExit(main())
