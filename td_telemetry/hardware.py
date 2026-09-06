"""Optional, conservative hardware providers; all metrics may legitimately be absent."""
from __future__ import annotations
import csv
import io
from pathlib import Path
import shutil
import time
from .common import Capability, clean, number, optional_text, run_command, stable_id


class HardwareProvider:
    def __init__(self) -> None:
        self.last_at = -100.0
        self.rows = {'gpus': [], 'thermals': [], 'fans': []}
        self.capabilities = {}

    def sample(self, now: float) -> dict:
        if now - self.last_at < 5:
            return self.rows
        self.last_at = now
        started = time.monotonic()
        self.rows = {'gpus': [], 'thermals': [], 'fans': []}
        gc = Capability('gpu', 'DRM sysfs or nvidia-smi CSV', status='unavailable', level='optional', sampledAt=now, intervalSeconds=5,
                        reason='No supported unprivileged GPU counters exposed.', complete=False)
        tc = Capability('thermal', 'hwmon sysfs', status='unavailable', level='optional', sampledAt=now, intervalSeconds=5,
                        reason='No readable hwmon thermal sensors.', complete=False)
        for path in sorted(Path('/sys/class/drm').glob('card[0-9]*/device'))[:16]:
            util = number(optional_text(path / 'gpu_busy_percent', limit=128))
            used = number(optional_text(path / 'mem_info_vram_used', limit=128))
            total = number(optional_text(path / 'mem_info_vram_total', limit=128))
            if util is not None or used is not None:
                self.rows['gpus'].append({'key': stable_id('gpu', str(path.resolve())), 'name': path.parent.name,
                                         'utilizationPercent': util, 'memoryUsedBytes': used, 'memoryTotalBytes': total,
                                         'temperatureC': None, 'source': 'DRM sysfs counters'})
        # Vendor tooling is a fallback only; avoid process/power overhead when DRM sysfs already satisfies GPU observation.
        if not self.rows['gpus'] and shutil.which('nvidia-smi'):
            try:
                raw = run_command(['nvidia-smi', '--query-gpu=uuid,name,utilization.gpu,memory.used,memory.total,temperature.gpu', '--format=csv,noheader,nounits'], timeout=0.8, max_bytes=65536).decode(errors='replace')
                for row in csv.reader(io.StringIO(raw)):
                    if len(row) != 6:
                        continue
                    used, total = number(row[3]), number(row[4])
                    self.rows['gpus'].append({'key': stable_id('gpu', row[0].strip()), 'name': clean(row[1].strip()),
                                             'utilizationPercent': number(row[2]), 'memoryUsedBytes': used * 1048576 if used is not None else None,
                                             'memoryTotalBytes': total * 1048576 if total is not None else None,
                                             'temperatureC': number(row[5]), 'source': 'nvidia-smi; 5s conservative polling'})
            except (OSError, ValueError, RuntimeError, TimeoutError) as error:
                gc.reason = clean(error, 200)
        for hwmon in sorted(Path('/sys/class/hwmon').glob('hwmon*'))[:32]:
            name = optional_text(hwmon / 'name', limit=128) or hwmon.name
            for sensor in list(hwmon.glob('temp*_input'))[:32]:
                val = number(optional_text(sensor, limit=128))
                if val is None or not -100000 <= val <= 250000:
                    continue
                label = optional_text(sensor.with_name(sensor.name.replace('_input', '_label')), limit=128) or sensor.stem
                critical = number(optional_text(sensor.with_name(sensor.name.replace('_input', '_crit')), limit=128))
                self.rows['thermals'].append({'key': stable_id('thermal', str(sensor.resolve())), 'name': clean(name + ' / ' + label),
                                              'temperatureC': val / 1000, 'criticalC': critical / 1000 if critical is not None else None, 'source': 'hwmon millidegrees C'})
            for sensor in list(hwmon.glob('fan*_input'))[:16]:
                rpm = number(optional_text(sensor, limit=128))
                if rpm is not None:
                    self.rows['fans'].append({'key': stable_id('fan', str(sensor.resolve())), 'name': clean(name + ' / ' + sensor.stem), 'rpm': rpm, 'source': 'hwmon RPM'})
        if self.rows['gpus']:
            gc.status, gc.complete, gc.reason = 'available', True, ''
        if self.rows['thermals'] or self.rows['fans']:
            tc.status, tc.complete, tc.reason = 'available', True, ''
        gc.durationMs = tc.durationMs = round((time.monotonic() - started) * 1000, 3)
        self.capabilities = {'gpu': gc.json(), 'thermal': tc.json()}
        return self.rows