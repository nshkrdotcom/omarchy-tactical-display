from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import telemetry  # noqa: E402


def contact(**overrides):
    base = {
        "key": "socket-a",
        "proto": "tcp",
        "family": 4,
        "state": "ESTABLISHED",
        "kind": "outbound",
        "local": "10.0.0.2:51000",
        "remote": "203.0.113.20:443",
        "localAddress": "10.0.0.2",
        "localPort": 51000,
        "remoteAddress": "203.0.113.20",
        "remotePort": 443,
        "pid": 4242,
        "process": "browser",
        "command": "browser --profile default",
        "executable": "browser",
        "queueBytes": 0,
        "activity": 0,
        "ageMs": 250,
        "closed": False,
        "closedAgeMs": 0,
    }
    base.update(overrides)
    return base


class NetworkModelTests(unittest.TestCase):
    def test_groups_sockets_into_process_to_remote_relationship(self):
        contacts = [
            contact(key="a", localPort=51000),
            contact(key="b", localPort=51001),
        ]
        model = telemetry.build_network_model(contacts)

        self.assertEqual(model["summary"]["processes"], 1)
        self.assertEqual(model["summary"]["remoteSystems"], 1)
        self.assertEqual(model["summary"]["connections"], 2)
        self.assertEqual(len(model["processes"]), 1)
        self.assertEqual(len(model["remotes"]), 1)
        self.assertEqual(len(model["links"]), 1)
        self.assertEqual(model["links"][0]["socketCount"], 2)
        self.assertEqual(model["links"][0]["direction"], "out")
        self.assertEqual(model["links"][0]["servicePort"], 443)
        self.assertEqual(model["links"][0]["newCount"], 2)
        self.assertEqual(model["summary"]["newConnections"], 2)
        self.assertEqual(model["processes"][0]["command"], "browser --profile default")

    def test_inbound_relationship_uses_local_service_port(self):
        inbound = contact(
            key="in",
            kind="inbound",
            localPort=8080,
            remotePort=55001,
            remoteAddress="198.51.100.9",
            remote="198.51.100.9:55001",
            process="server",
        )
        model = telemetry.build_network_model([inbound])
        link = model["links"][0]
        self.assertEqual(link["direction"], "in")
        self.assertEqual(link["servicePort"], 8080)
        self.assertEqual(model["summary"]["inbound"], 1)

    def test_listener_is_machine_aperture_not_remote_system(self):
        listener = contact(
            key="listen",
            state="LISTEN",
            kind="listen",
            localAddress="0.0.0.0",
            localPort=3000,
            remoteAddress="0.0.0.0",
            remotePort=0,
            remote="*",
            process="dev-server",
        )
        model = telemetry.build_network_model([listener])
        self.assertEqual(model["summary"]["listeners"], 1)
        self.assertEqual(model["summary"]["connections"], 0)
        self.assertEqual(len(model["listeners"]), 1)
        self.assertEqual(len(model["remotes"]), 0)
        self.assertEqual(len(model["links"]), 0)

    def test_loopback_stays_inside_local_scope(self):
        loop = contact(
            key="loop",
            kind="loopback",
            localAddress="127.0.0.1",
            localPort=51001,
            remoteAddress="127.0.0.1",
            remotePort=4000,
            remote="127.0.0.1:4000",
        )
        model = telemetry.build_network_model([loop])
        self.assertEqual(model["remotes"][0]["scope"], "loopback")
        self.assertEqual(model["links"][0]["direction"], "local")
        self.assertEqual(model["summary"]["remoteSystems"], 0)
        self.assertEqual(model["summary"]["loopback"], 1)

    def test_closed_relationship_is_retained_but_not_counted_active(self):
        closed = contact(key="closed", closed=True, closedAgeMs=500, state="CLOSED")
        model = telemetry.build_network_model([closed])
        self.assertEqual(model["summary"]["connections"], 0)
        self.assertEqual(model["summary"]["recentClosed"], 1)
        self.assertFalse(model["links"][0]["active"])
        self.assertEqual(model["links"][0]["closedAgeMs"], 500)


if __name__ == "__main__":
    unittest.main()
