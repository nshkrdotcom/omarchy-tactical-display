"""Production aggregate history exposes stall semantics without identity retention."""
from unittest import TestCase
from unittest.mock import patch
from td_telemetry.engine import TelemetryEngine


class PressureTrendTests(TestCase):
    def test_history_contains_measured_some_full_pressure_and_preserves_missing(self):
        engine = TelemetryEngine(instrument='machine')
        pressure = {'cpu': {'some': {'avg10': 7}, 'full': {'avg10': 90}},
                    'memory': {'some': {'avg10': 2}, 'full': {'avg10': 1}},
                    'io': None}
        try:
            with patch.object(engine.machine_provider, 'sample', return_value={'pressure': pressure}):
                frame = engine.sample()
            row = frame['trend'][-1]
            self.assertEqual(row['cpuSomePercent'], 7)
            self.assertEqual(row['memorySomePercent'], 2)
            self.assertEqual(row['memoryFullPercent'], 1)
            self.assertIsNone(row['ioSomePercent'])
            self.assertIsNone(row['ioFullPercent'])
            self.assertNotIn('cpuFullPercent', row)
        finally:
            engine.close()
