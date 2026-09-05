import json
from pathlib import Path
import socket
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import telemetry  # noqa: E402


class TelemetryParsingTests(unittest.TestCase):
    def test_ipv4_procfs_endianness(self):
        self.assertEqual(telemetry.parse_ipv4("0100007F"), "127.0.0.1")

    def test_ipv6_procfs_endianness(self):
        self.assertEqual(telemetry.parse_ipv6("00000000000000000000000001000000"), "::1")

    def test_parse_tcp_row(self):
        line = "  0: 0100007F:1F90 00000000:0000 0A 00000000:00000000 00:00000000 00000000  1000        0 424242 1 0000000000000000 100 0 0 10 0"
        row = telemetry.parse_proc_net_line(line, "tcp", socket.AF_INET)
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row["localAddress"], "127.0.0.1")
        self.assertEqual(row["localPort"], 8080)
        self.assertEqual(row["state"], "LISTEN")
        self.assertEqual(row["inode"], "424242")

    def test_classification(self):
        base = {
            "proto": "tcp",
            "localPort": 443,
            "remoteAddress": "203.0.113.5",
            "remotePort": 55555,
            "state": "ESTABLISHED",
        }
        self.assertEqual(telemetry.classify_socket(base, {("tcp", 443)}), "inbound")
        outbound = dict(base, localPort=52000)
        self.assertEqual(telemetry.classify_socket(outbound, {("tcp", 443)}), "outbound")
        loopback = dict(base, localPort=52000, remoteAddress="127.0.0.1")
        self.assertEqual(telemetry.classify_socket(loopback, set()), "loopback")


class LiveTelemetryTests(unittest.TestCase):
    def test_live_engine_frame_has_valid_ranges(self):
        engine = telemetry.TelemetryEngine()
        frame = engine.sample()
        self.assertEqual(frame["version"], 3)
        self.assertIn("system", frame)
        self.assertIn("processes", frame)
        self.assertIn("network", frame)
        self.assertIsNone(frame["system"]["netRxBps"])
        self.assertIsNone(frame["system"]["netTxBps"])
        self.assertGreaterEqual(frame["system"]["uptimeSeconds"], 0)
        self.assertIsInstance(frame["processes"], list)
        self.assertIn("summary", frame["network"])
        self.assertIn("links", frame["network"])
        json.dumps(frame)

    def test_cli_once_emits_json(self):
        completed = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "telemetry.py"), "--once", "--interval", "0.25"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        frame = json.loads(completed.stdout.strip())
        self.assertEqual(frame["version"], 3)
        self.assertIn("netRxBps", frame["system"])
        self.assertIsInstance(frame["processes"], list)


if __name__ == "__main__":
    unittest.main()
