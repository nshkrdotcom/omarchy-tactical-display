#!/usr/bin/env python3
"""Dependency-free telemetry backend for Omarchy Tactical Display.

Emits one JSON object per line. It reads Linux procfs only. No network requests,
DNS lookups, packet capture, or elevated privileges are used.
"""

from __future__ import annotations

import argparse
import glob
import ipaddress
import json
import math
import os
from pathlib import Path
import socket
import sys
import time
from typing import Any

TCP_STATES = {
    "01": "ESTABLISHED",
    "02": "SYN_SENT",
    "03": "SYN_RECV",
    "04": "FIN_WAIT1",
    "05": "FIN_WAIT2",
    "06": "TIME_WAIT",
    "07": "CLOSE",
    "08": "CLOSE_WAIT",
    "09": "LAST_ACK",
    "0A": "LISTEN",
    "0B": "CLOSING",
    "0C": "NEW_SYN_RECV",
}

VISIBLE_TCP_STATES = {
    "ESTABLISHED",
    "SYN_SENT",
    "SYN_RECV",
    "LISTEN",
    "CLOSE_WAIT",
}

GHOST_TTL_MS = 2600
NEW_TTL_MS = 1800
MAX_CONTACTS = 180


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def read_text(path: str | Path, default: str = "") -> str:
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace").strip()
    except (OSError, ValueError):
        return default


def parse_ipv4(hex_address: str) -> str:
    raw = bytes.fromhex(hex_address)
    return socket.inet_ntop(socket.AF_INET, raw[::-1])


def parse_ipv6(hex_address: str) -> str:
    raw = bytes.fromhex(hex_address)
    # /proc/net/tcp6 stores each 32-bit word in host byte order.
    normalized = b"".join(raw[index : index + 4][::-1] for index in range(0, 16, 4))
    return socket.inet_ntop(socket.AF_INET6, normalized)


def parse_endpoint(token: str, family: int) -> tuple[str, int]:
    address_hex, port_hex = token.split(":", 1)
    address = parse_ipv4(address_hex) if family == socket.AF_INET else parse_ipv6(address_hex)
    return address, int(port_hex, 16)


def is_unspecified(address: str, port: int) -> bool:
    if port != 0:
        return False
    try:
        return ipaddress.ip_address(address).is_unspecified
    except ValueError:
        return False


def is_loopback(address: str) -> bool:
    try:
        return ipaddress.ip_address(address).is_loopback
    except ValueError:
        return False


def display_endpoint(address: str, port: int) -> str:
    if ":" in address:
        return f"[{address}]:{port}"
    return f"{address}:{port}"


def parse_proc_net_line(line: str, proto: str, family: int) -> dict[str, Any] | None:
    fields = line.split()
    if len(fields) < 10 or fields[0] == "sl":
        return None

    try:
        local_address, local_port = parse_endpoint(fields[1], family)
        remote_address, remote_port = parse_endpoint(fields[2], family)
        state_code = fields[3]
        tx_hex, rx_hex = fields[4].split(":", 1)
        tx_queue = int(tx_hex, 16)
        rx_queue = int(rx_hex, 16)
        uid = int(fields[7])
        inode = fields[9]
    except (ValueError, IndexError, OSError):
        return None

    state = TCP_STATES.get(state_code, state_code) if proto == "tcp" else ("BOUND" if is_unspecified(remote_address, remote_port) else "CONNECTED")

    return {
        "proto": proto,
        "family": 4 if family == socket.AF_INET else 6,
        "localAddress": local_address,
        "localPort": local_port,
        "remoteAddress": remote_address,
        "remotePort": remote_port,
        "state": state,
        "queueBytes": tx_queue + rx_queue,
        "uid": uid,
        "inode": inode,
    }


def read_socket_table(path: str, proto: str, family: int) -> list[dict[str, Any]]:
    try:
        lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []

    rows: list[dict[str, Any]] = []
    for line in lines[1:]:
        parsed = parse_proc_net_line(line, proto, family)
        if parsed is not None:
            rows.append(parsed)
    return rows


def process_map_for_inodes(inodes: set[str]) -> dict[str, dict[str, Any]]:
    if not inodes:
        return {}

    result: dict[str, dict[str, Any]] = {}
    current_uid = os.getuid()

    for proc_path in glob.glob("/proc/[0-9]*"):
        if len(result) >= len(inodes):
            break
        try:
            if os.stat(proc_path).st_uid != current_uid:
                continue
        except OSError:
            continue

        pid_text = proc_path.rsplit("/", 1)[-1]
        comm = read_text(f"{proc_path}/comm", "")
        raw_cmdline = read_text(f"{proc_path}/cmdline", "")
        argv0 = raw_cmdline.split("\x00", 1)[0].strip() if raw_cmdline else ""
        try:
            executable = os.path.basename(os.readlink(f"{proc_path}/exe"))
        except OSError:
            executable = ""
        fd_dir = f"{proc_path}/fd"
        try:
            fd_names = os.listdir(fd_dir)
        except OSError:
            continue

        for fd_name in fd_names:
            try:
                target = os.readlink(f"{fd_dir}/{fd_name}")
            except OSError:
                continue
            if not target.startswith("socket:[") or not target.endswith("]"):
                continue
            inode = target[8:-1]
            if inode in inodes and inode not in result:
                result[inode] = {
                    "pid": int(pid_text),
                    "process": comm or executable or "unknown",
                    "command": argv0[:220],
                    "executable": executable,
                }

    return result


def classify_socket(row: dict[str, Any], listeners: set[tuple[str, int]]) -> str:
    remote_address = str(row["remoteAddress"])
    remote_port = int(row["remotePort"])
    local_port = int(row["localPort"])
    proto = str(row["proto"])

    if row["state"] in {"LISTEN", "BOUND"} or is_unspecified(remote_address, remote_port):
        return "listen"
    if is_loopback(remote_address):
        return "loopback"
    if (proto, local_port) in listeners:
        return "inbound"
    return "outbound"


def socket_priority(contact: dict[str, Any]) -> tuple[int, int, int]:
    kind_rank = {"listen": 0, "inbound": 1, "outbound": 2, "loopback": 3}.get(str(contact.get("kind")), 4)
    process_rank = 0 if contact.get("pid") else 1
    state_rank = 0 if contact.get("state") in {"ESTABLISHED", "CONNECTED", "LISTEN", "BOUND"} else 1
    return kind_rank, process_rank, state_rank


def load_raw_sockets() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    rows.extend(read_socket_table("/proc/net/tcp", "tcp", socket.AF_INET))
    rows.extend(read_socket_table("/proc/net/tcp6", "tcp", socket.AF_INET6))
    rows.extend(read_socket_table("/proc/net/udp", "udp", socket.AF_INET))
    rows.extend(read_socket_table("/proc/net/udp6", "udp", socket.AF_INET6))

    filtered: list[dict[str, Any]] = []
    for row in rows:
        if row["proto"] == "tcp" and row["state"] not in VISIBLE_TCP_STATES:
            continue
        filtered.append(row)
    return filtered


class SocketSampler:
    def __init__(self) -> None:
        self.first_seen: dict[str, float] = {}
        self.last_contacts: dict[str, dict[str, Any]] = {}
        self.ghosts: dict[str, tuple[float, dict[str, Any]]] = {}

    @staticmethod
    def stable_key(row: dict[str, Any], process: dict[str, Any] | None) -> str:
        pid = process.get("pid") if process else None
        if row["state"] in {"LISTEN", "BOUND"}:
            identity = f"{row['proto']}|{pid or row['inode']}|{row['localAddress']}|{row['localPort']}|*"
        else:
            identity = (
                f"{row['proto']}|{pid or row['inode']}|{row['localAddress']}|{row['localPort']}|"
                f"{row['remoteAddress']}|{row['remotePort']}"
            )
        return identity

    def sample(self, now: float) -> list[dict[str, Any]]:
        rows = load_raw_sockets()
        inodes = {str(row["inode"]) for row in rows if row.get("inode")}
        process_map = process_map_for_inodes(inodes)
        listeners = {
            (str(row["proto"]), int(row["localPort"]))
            for row in rows
            if row["state"] in {"LISTEN", "BOUND"}
        }

        contacts: dict[str, dict[str, Any]] = {}
        for row in rows:
            process = process_map.get(str(row["inode"]))
            key = self.stable_key(row, process)
            first_seen = self.first_seen.setdefault(key, now)
            queue_bytes = int(row.get("queueBytes") or 0)
            activity = clamp(math.log10(queue_bytes + 1) / 5 if queue_bytes else 0.0, 0.0, 1.0)

            contact = {
                "key": key,
                "proto": row["proto"],
                "family": row["family"],
                "state": row["state"],
                "kind": classify_socket(row, listeners),
                "local": display_endpoint(str(row["localAddress"]), int(row["localPort"])),
                "remote": "*" if is_unspecified(str(row["remoteAddress"]), int(row["remotePort"])) else display_endpoint(str(row["remoteAddress"]), int(row["remotePort"])),
                "localAddress": row["localAddress"],
                "localPort": row["localPort"],
                "remoteAddress": row["remoteAddress"],
                "remotePort": row["remotePort"],
                "pid": process.get("pid") if process else None,
                "process": process.get("process") if process else "unknown",
                "command": process.get("command") if process else "",
                "executable": process.get("executable") if process else "",
                "queueBytes": queue_bytes,
                "activity": round(activity, 4),
                "ageMs": int((now - first_seen) * 1000),
                "closed": False,
                "closedAgeMs": 0,
            }
            contacts[key] = contact
            self.ghosts.pop(key, None)

        # Convert sockets that disappeared since the previous sample into short-lived ghosts.
        for key, previous in self.last_contacts.items():
            if key not in contacts and key not in self.ghosts:
                ghost = dict(previous)
                ghost["closed"] = True
                ghost["closedAgeMs"] = 0
                ghost["state"] = "CLOSED"
                self.ghosts[key] = (now, ghost)

        expired: list[str] = []
        for key, (closed_at, ghost) in self.ghosts.items():
            closed_age_ms = int((now - closed_at) * 1000)
            if closed_age_ms > GHOST_TTL_MS:
                expired.append(key)
                self.first_seen.pop(key, None)
                continue
            ghost_frame = dict(ghost)
            ghost_frame["closedAgeMs"] = closed_age_ms
            contacts[key] = ghost_frame

        for key in expired:
            self.ghosts.pop(key, None)

        active_contacts = {key: value for key, value in contacts.items() if value.get("closed") is not True}
        self.last_contacts = active_contacts

        ordered = sorted(contacts.values(), key=socket_priority)
        if len(ordered) > MAX_CONTACTS:
            ordered = ordered[:MAX_CONTACTS]
        return ordered



def service_name(proto: str, port: int) -> str:
    """Return a local /etc/services-style name without doing any DNS/network I/O."""
    if port <= 0:
        return ""
    try:
        return socket.getservbyport(int(port), "tcp" if proto == "tcp" else "udp")
    except (OSError, OverflowError):
        return ""


def process_key_for_contact(contact: dict[str, Any]) -> str:
    pid = contact.get("pid")
    if pid:
        return f"proc:{int(pid)}"
    kind = str(contact.get("kind") or "unknown")
    return f"proc:unattributed:{kind}"


def _node_lifecycle(items: list[dict[str, Any]]) -> tuple[bool, int, int]:
    active = [item for item in items if item.get("closed") is not True]
    if active:
        newest = min(int(item.get("ageMs") or 0) for item in active)
        return True, newest, 0
    closed_age = min((int(item.get("closedAgeMs") or GHOST_TTL_MS) for item in items), default=GHOST_TTL_MS)
    return False, 0, closed_age


def build_network_model(contacts: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate kernel sockets into a spatial model humans can actually read.

    The primary visual unit is not a socket. It is a relationship:
    local process -> remote system (or the reverse for likely inbound traffic).
    Socket multiplicity and ports/protocols are retained on each relationship.
    """
    process_members: dict[str, list[dict[str, Any]]] = {}
    remote_members: dict[str, list[dict[str, Any]]] = {}
    link_members: dict[str, list[dict[str, Any]]] = {}
    listener_members: dict[str, list[dict[str, Any]]] = {}

    for contact in contacts:
        pkey = process_key_for_contact(contact)
        process_members.setdefault(pkey, []).append(contact)
        kind = str(contact.get("kind") or "outbound")

        if kind == "listen":
            lkey = f"listener:{pkey}:{contact.get('proto')}:{contact.get('localAddress')}:{contact.get('localPort')}"
            listener_members.setdefault(lkey, []).append(contact)
            continue

        address = str(contact.get("remoteAddress") or "")
        if not address:
            continue
        rkey = f"remote:{address}"
        remote_members.setdefault(rkey, []).append(contact)
        proto = str(contact.get("proto") or "tcp")
        service_port = int(contact.get("localPort") or 0) if kind == "inbound" else int(contact.get("remotePort") or 0)
        link_key = f"link:{pkey}:{rkey}:{kind}:{proto}:{service_port}"
        link_members.setdefault(link_key, []).append(contact)

    processes: list[dict[str, Any]] = []
    for key, members in process_members.items():
        active, age_ms, closed_age_ms = _node_lifecycle(members)
        exemplar = next((item for item in members if item.get("pid")), members[0])
        active_members = [item for item in members if item.get("closed") is not True]
        processes.append({
            "key": key,
            "pid": exemplar.get("pid"),
            "name": str(exemplar.get("process") or "unattributed"),
            "command": str(exemplar.get("command") or ""),
            "executable": str(exemplar.get("executable") or ""),
            "socketCount": len(active_members),
            "listenerCount": sum(1 for item in active_members if item.get("kind") == "listen"),
            "outboundCount": sum(1 for item in active_members if item.get("kind") == "outbound"),
            "inboundCount": sum(1 for item in active_members if item.get("kind") == "inbound"),
            "loopbackCount": sum(1 for item in active_members if item.get("kind") == "loopback"),
            "queueBytes": sum(int(item.get("queueBytes") or 0) for item in active_members),
            "newCount": sum(1 for item in active_members if int(item.get("ageMs") if item.get("ageMs") is not None else NEW_TTL_MS + 1) < NEW_TTL_MS),
            "active": active,
            "ageMs": age_ms,
            "closedAgeMs": closed_age_ms,
        })

    remotes: list[dict[str, Any]] = []
    for key, members in remote_members.items():
        active, age_ms, closed_age_ms = _node_lifecycle(members)
        address = str(members[0].get("remoteAddress") or "")
        active_members = [item for item in members if item.get("closed") is not True]
        kinds = sorted({str(item.get("kind") or "outbound") for item in active_members or members})
        ports = sorted({int(item.get("remotePort") or 0) for item in active_members or members if int(item.get("remotePort") or 0) > 0})[:12]
        remotes.append({
            "key": key,
            "address": address,
            "family": int(members[0].get("family") or 4),
            "scope": "loopback" if is_loopback(address) else "external",
            "socketCount": len(active_members),
            "processCount": len({process_key_for_contact(item) for item in active_members}),
            "outboundCount": sum(1 for item in active_members if item.get("kind") == "outbound"),
            "inboundCount": sum(1 for item in active_members if item.get("kind") == "inbound"),
            "loopbackCount": sum(1 for item in active_members if item.get("kind") == "loopback"),
            "kinds": kinds,
            "ports": ports,
            "newCount": sum(1 for item in active_members if int(item.get("ageMs") if item.get("ageMs") is not None else NEW_TTL_MS + 1) < NEW_TTL_MS),
            "active": active,
            "ageMs": age_ms,
            "closedAgeMs": closed_age_ms,
        })

    links: list[dict[str, Any]] = []
    for key, members in link_members.items():
        active_members = [item for item in members if item.get("closed") is not True]
        active, age_ms, closed_age_ms = _node_lifecycle(members)
        exemplar = active_members[0] if active_members else members[0]
        kind = str(exemplar.get("kind") or "outbound")
        proto = str(exemplar.get("proto") or "tcp")
        service_port = int(exemplar.get("localPort") or 0) if kind == "inbound" else int(exemplar.get("remotePort") or 0)
        queue_bytes = sum(int(item.get("queueBytes") or 0) for item in active_members)
        pressure = clamp(math.log10(queue_bytes + 1) / 5 if queue_bytes else 0.0, 0.0, 1.0)
        states = sorted({str(item.get("state") or "UNKNOWN") for item in active_members or members})
        state = "ESTABLISHED" if "ESTABLISHED" in states else ("CONNECTED" if "CONNECTED" in states else states[0])
        links.append({
            "key": key,
            "processKey": process_key_for_contact(exemplar),
            "remoteKey": f"remote:{exemplar.get('remoteAddress')}",
            "process": str(exemplar.get("process") or "unattributed"),
            "pid": exemplar.get("pid"),
            "address": str(exemplar.get("remoteAddress") or ""),
            "kind": kind,
            "direction": "in" if kind == "inbound" else ("local" if kind == "loopback" else "out"),
            "proto": proto,
            "servicePort": service_port,
            "service": service_name(proto, service_port),
            "state": state if active else "CLOSED",
            "states": states,
            "socketCount": len(active_members),
            "closedSocketCount": sum(1 for item in members if item.get("closed") is True),
            "localPorts": sorted({int(item.get("localPort") or 0) for item in active_members or members if int(item.get("localPort") or 0) > 0})[:12],
            "remotePorts": sorted({int(item.get("remotePort") or 0) for item in active_members or members if int(item.get("remotePort") or 0) > 0})[:12],
            "queueBytes": queue_bytes,
            "queuePressure": round(pressure, 4),
            "newCount": sum(1 for item in active_members if int(item.get("ageMs") if item.get("ageMs") is not None else NEW_TTL_MS + 1) < NEW_TTL_MS),
            "active": active,
            "ageMs": age_ms,
            "closedAgeMs": closed_age_ms,
        })

    listeners: list[dict[str, Any]] = []
    for key, members in listener_members.items():
        active_members = [item for item in members if item.get("closed") is not True]
        active, age_ms, closed_age_ms = _node_lifecycle(members)
        exemplar = active_members[0] if active_members else members[0]
        proto = str(exemplar.get("proto") or "tcp")
        port = int(exemplar.get("localPort") or 0)
        listeners.append({
            "key": key,
            "processKey": process_key_for_contact(exemplar),
            "process": str(exemplar.get("process") or "unattributed"),
            "pid": exemplar.get("pid"),
            "address": str(exemplar.get("localAddress") or ""),
            "port": port,
            "proto": proto,
            "service": service_name(proto, port),
            "active": active,
            "ageMs": age_ms,
            "closedAgeMs": closed_age_ms,
        })

    processes.sort(key=lambda item: (-int(bool(item["active"])), -int(item["socketCount"]), str(item["name"]), str(item["key"])))
    remotes.sort(key=lambda item: (-int(bool(item["active"])), -int(item["socketCount"]), str(item["address"])))
    links.sort(key=lambda item: (-int(bool(item["active"])), {"inbound": 0, "outbound": 1, "loopback": 2}.get(str(item["kind"]), 3), -int(item["socketCount"]), str(item["key"])))
    listeners.sort(key=lambda item: (-int(bool(item["active"])), str(item["process"]), int(item["port"])))

    active_contacts = [item for item in contacts if item.get("closed") is not True]
    active_connections = [item for item in active_contacts if item.get("kind") != "listen"]
    return {
        "processes": processes,
        "remotes": remotes,
        "links": links,
        "listeners": listeners,
        "summary": {
            "processes": sum(1 for item in processes if item["active"] and item["socketCount"] > 0),
            "remoteSystems": sum(1 for item in remotes if item["active"] and item["scope"] == "external"),
            "connections": len(active_connections),
            "listeners": sum(1 for item in active_contacts if item.get("kind") == "listen"),
            "outbound": sum(1 for item in active_connections if item.get("kind") == "outbound"),
            "inbound": sum(1 for item in active_connections if item.get("kind") == "inbound"),
            "loopback": sum(1 for item in active_connections if item.get("kind") == "loopback"),
            "newConnections": sum(1 for item in active_connections if int(item.get("ageMs") if item.get("ageMs") is not None else NEW_TTL_MS + 1) < NEW_TTL_MS),
            "recentClosed": sum(1 for item in contacts if item.get("closed") is True),
            "unattributed": sum(1 for item in active_contacts if not item.get("pid")),
        },
    }


def read_network_bytes() -> tuple[int, int]:
    rx_total = 0
    tx_total = 0
    for line in read_text("/proc/net/dev").splitlines()[2:]:
        if ":" not in line:
            continue
        name, values_text = line.split(":", 1)
        if name.strip() == "lo":
            continue
        fields = values_text.split()
        if len(fields) < 16:
            continue
        try:
            rx_total += int(fields[0])
            tx_total += int(fields[8])
        except ValueError:
            continue
    return rx_total, tx_total


def read_uptime() -> float:
    try:
        return float(read_text("/proc/uptime").split()[0])
    except (ValueError, IndexError):
        return 0.0


class NetworkRateSampler:
    def __init__(self) -> None:
        self.prev_rx, self.prev_tx = read_network_bytes()
        self.prev_time = time.monotonic()

    def sample(self, now: float) -> dict[str, Any]:
        rx, tx = read_network_bytes()
        elapsed = max(now - self.prev_time, 0.001)
        rx_bps = max(rx - self.prev_rx, 0) / elapsed
        tx_bps = max(tx - self.prev_tx, 0) / elapsed
        self.prev_rx = rx
        self.prev_tx = tx
        self.prev_time = now
        return {
            "netRxBps": round(rx_bps, 2),
            "netTxBps": round(tx_bps, 2),
            "uptimeSeconds": round(read_uptime(), 1),
        }


class TelemetryEngine:
    def __init__(self) -> None:
        self.system = NetworkRateSampler()
        self.sockets = SocketSampler()

    def sample(self) -> dict[str, Any]:
        now = time.monotonic()
        contacts = self.sockets.sample(now)
        return {
            "version": 2,
            "timestamp": time.time(),
            "system": self.system.sample(now),
            "contacts": contacts,
            "network": build_network_model(contacts),
        }


def emit(sample: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(sample, separators=(",", ":"), ensure_ascii=True) + "\n")
    sys.stdout.flush()


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Tactical Display Linux telemetry emitter")
    parser.add_argument("--interval", type=float, default=0.75, help="sample interval in seconds")
    parser.add_argument("--once", action="store_true", help="emit one frame and exit")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    interval = clamp(float(args.interval), 0.25, 10.0)
    engine = TelemetryEngine()

    if args.once:
        # Let delta-based network metrics obtain a meaningful second point.
        time.sleep(min(interval, 0.3))
        emit(engine.sample())
        return 0

    try:
        while True:
            started = time.monotonic()
            emit(engine.sample())
            spent = time.monotonic() - started
            time.sleep(max(0.01, interval - spent))
    except BrokenPipeError:
        return 0
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
