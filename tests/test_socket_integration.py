import os
from pathlib import Path
import socket
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import telemetry  # noqa: E402


class RealProcfsSocketIntegrationTests(unittest.TestCase):
    def test_tcp_listener_connection_and_close_are_seen_via_procfs(self):
        sampler = telemetry.SocketSampler()
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        accepted = None
        try:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(("127.0.0.1", 0))
            port = server.getsockname()[1]
            server.listen(1)

            client.connect(("127.0.0.1", port))
            accepted, _ = server.accept()

            contacts = sampler.sample(time.monotonic())
            matching = [c for c in contacts if c.get("localPort") == port]
            self.assertTrue(matching, f"no procfs contact found for live TCP port {port}")

            listeners = [c for c in matching if c.get("state") == "LISTEN"]
            self.assertTrue(listeners, f"no LISTEN contact found for live TCP port {port}: {matching!r}")
            self.assertEqual(listeners[0].get("kind"), "listen")
            self.assertEqual(listeners[0].get("pid"), os.getpid())
            self.assertNotEqual(listeners[0].get("process"), "unknown")
            self.assertTrue(listeners[0].get("command"), "argv0/executable identity missing")
            self.assertNotIn("test_socket_integration.py", listeners[0].get("command", ""), "full process arguments leaked into telemetry")

            loopback = [c for c in matching if c.get("kind") == "loopback" and c.get("state") == "ESTABLISHED"]
            self.assertTrue(loopback, f"no established loopback contact found: {matching!r}")

            listener_key = listeners[0]["key"]
        finally:
            if accepted is not None:
                accepted.close()
            client.close()
            server.close()

        # LISTEN disappears immediately from procfs. The sampler should retain
        # it briefly as a fading CLOSED ghost so Radar does not pop contacts.
        after = sampler.sample(time.monotonic())
        ghost = next((c for c in after if c.get("key") == listener_key), None)
        self.assertIsNotNone(ghost, "closed listener was not retained as a ghost")
        self.assertTrue(ghost.get("closed"))
        self.assertEqual(ghost.get("state"), "CLOSED")


if __name__ == "__main__":
    unittest.main()
