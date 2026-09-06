"""Socket parsing retained from the supplied baseline, with bounded readers."""
from __future__ import annotations
import ipaddress
from pathlib import Path
import socket
import sys
import time
from typing import Any
from .common import read_text

TCP_STATES = {'01': 'ESTABLISHED', '02': 'SYN_SENT', '03': 'SYN_RECV',
              '04': 'FIN_WAIT1', '05': 'FIN_WAIT2', '06': 'TIME_WAIT',
              '07': 'CLOSE', '08': 'CLOSE_WAIT', '09': 'LAST_ACK',
              '0A': 'LISTEN', '0B': 'CLOSING', '0C': 'NEW_SYN_RECV'}
VISIBLE_TCP_STATES = set(TCP_STATES.values()) - {'TIME_WAIT', 'CLOSE'}


def parse_ipv4(hex_address: str) -> str:
    raw = bytes.fromhex(hex_address)
    return socket.inet_ntop(socket.AF_INET, raw[::-1] if sys.byteorder == 'little' else raw)


def parse_ipv6(hex_address: str) -> str:
    raw = bytes.fromhex(hex_address)
    if sys.byteorder == 'little':
        raw = b''.join(raw[i:i + 4][::-1] for i in range(0, 16, 4))
    return socket.inet_ntop(socket.AF_INET6, raw)


def parse_endpoint(token: str, family: int) -> tuple[str, int]:
    address, port = token.split(':', 1)
    return (parse_ipv4(address) if family == socket.AF_INET else parse_ipv6(address), int(port, 16))


def is_unspecified(address: str, port: int = 0) -> bool:
    try:
        return port == 0 and ipaddress.ip_address(address).is_unspecified
    except ValueError:
        return False


def is_loopback(address: str) -> bool:
    try:
        ip = ipaddress.ip_address(address)
        return ip.is_loopback or bool(getattr(ip, 'ipv4_mapped', None) and ip.ipv4_mapped.is_loopback)
    except ValueError:
        return False


def display_endpoint(address: str, port: int) -> str:
    return f'[{address}]:{port}' if ':' in address else f'{address}:{port}'


def parse_proc_net_line(line: str, proto: str, family: int) -> dict[str, Any] | None:
    fields = line.split()
    if len(fields) < 10 or fields[0] == 'sl':
        return None
    try:
        la, lp = parse_endpoint(fields[1], family)
        ra, rp = parse_endpoint(fields[2], family)
        tx, rx = (int(n, 16) for n in fields[4].split(':', 1))
        state = TCP_STATES.get(fields[3], fields[3]) if proto == 'tcp' else ('BOUND' if is_unspecified(ra, rp) else 'CONNECTED')
        return {'proto': proto, 'family': 4 if family == socket.AF_INET else 6,
                'localAddress': la, 'localPort': lp, 'remoteAddress': ra, 'remotePort': rp,
                'state': state, 'queueBytes': tx + rx, 'txQueueBytes': tx, 'rxQueueBytes': rx,
                'uid': int(fields[7]), 'inode': fields[9], 'source': 'procfs',
                'rttMs': None, 'bytesAcked': None, 'bytesReceived': None, 'cookie': None}
    except (ValueError, IndexError, OSError):
        return None


def read_socket_table(path: str | Path, proto: str, family: int, limit: int = 20000,
                      deadline: float | None = None) -> list[dict[str, Any]]:
    rows = []
    with open(path, encoding='ascii', errors='replace') as f:
        next(f, '')
        for index, line in enumerate(f):
            if len(rows) >= limit or (deadline is not None and index % 32 == 0 and time.monotonic() >= deadline):
                break
            item = parse_proc_net_line(line[:4096], proto, family)
            if item is not None and (proto != 'tcp' or item['state'] in VISIBLE_TCP_STATES):
                rows.append(item)
    return rows


def classify_socket(row: dict[str, Any], listeners: set[tuple[str, int]]) -> str:
    # Compatibility entry point for baseline tests. Production additionally
    # checks addresses, families and owners (network.classify_with_evidence).
    if row['state'] in {'LISTEN', 'BOUND'} or is_unspecified(row['remoteAddress'], row['remotePort']):
        return 'listen'
    if is_loopback(row['remoteAddress']):
        return 'loopback'
    return 'inbound' if (row['proto'], row['localPort']) in listeners else 'outbound'