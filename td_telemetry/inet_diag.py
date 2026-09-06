"""Unprivileged Linux SOCK_DIAG TCP dump. /proc is the production fallback.

Layouts are Linux uapi/linux/{inet_diag,tcp}.h. Only length-checked attributes
are consumed. TCP goodput is acknowledged/received bytes, not wire bandwidth.
"""
from __future__ import annotations
import socket
import struct
import time
from .procfs import TCP_STATES


def parse_message(data: bytes) -> dict | None:
    if len(data) < 72:
        raise ValueError('short inet_diag_msg')
    family, state = data[0], data[1]
    if family not in (socket.AF_INET, socket.AF_INET6):
        return None
    sport, dport = struct.unpack_from('!HH', data, 4)
    width = 4 if family == socket.AF_INET else 16
    local = socket.inet_ntop(family, data[8:8 + width])
    remote = socket.inet_ntop(family, data[24:24 + width])
    cookie_a, cookie_b = struct.unpack_from('=II', data, 44)
    _, rqueue, wqueue, uid, inode = struct.unpack_from('=IIIII', data, 52)
    listener = state == 10
    row = {'proto': 'tcp', 'family': 4 if family == socket.AF_INET else 6,
           'localAddress': local, 'remoteAddress': remote, 'localPort': sport, 'remotePort': dport,
           'state': TCP_STATES.get(f'{state:02X}', f'STATE_{state}'), 'uid': uid, 'inode': str(inode),
           'cookie': f'{cookie_a:08x}{cookie_b:08x}', 'source': 'inet_diag',
           'rxQueueBytes': None if listener else rqueue, 'txQueueBytes': None if listener else wqueue,
           'queueBytes': None if listener else rqueue + wqueue,
           'listenBacklogCurrent': rqueue if listener else None, 'listenBacklogLimit': wqueue if listener else None,
           'rttMs': None, 'bytesAcked': None, 'bytesReceived': None}
    pos = 72
    while pos + 4 <= len(data):
        length, kind = struct.unpack_from('=HH', data, pos)
        if length < 4 or pos + length > len(data):
            raise ValueError('invalid inet_diag attribute')
        attr = data[pos + 4:pos + length]
        if kind & 0x3fff == 2:
            if len(attr) >= 72 and not listener:
                row['rttMs'] = struct.unpack_from('=I', attr, 68)[0] / 1000
            if len(attr) >= 136 and not listener:
                row['bytesAcked'], row['bytesReceived'] = struct.unpack_from('=QQ', attr, 120)
        pos += (length + 3) & ~3
    return row


def dump_tcp(family: int, limit: int = 20000, deadline: float = 0.2) -> list[dict]:
    rows = []
    seq = int(time.monotonic_ns() & 0x7fffffff)
    # all states except TIME_WAIT and CLOSE; request INET_DIAG_INFO.
    states = 0xfff & ~(1 << 6) & ~(1 << 7)
    req = struct.pack('=BBBBI', family, socket.IPPROTO_TCP, 2, 0, states) + bytes(40) + b'\xff' * 8
    header = struct.pack('=IHHII', 16 + len(req), 20, 0x301, seq, 0)
    end = time.monotonic() + deadline
    with socket.socket(socket.AF_NETLINK, socket.SOCK_RAW, 4) as sock:
        sock.settimeout(deadline)
        sock.bind((0, 0))
        sock.sendto(header + req, (0, 0))
        while True:
            remaining = end - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('inet_diag deadline exceeded')
            sock.settimeout(remaining)
            data, _, flags, sender = sock.recvmsg(262144)
            if flags & socket.MSG_TRUNC:
                raise ValueError('inet_diag datagram truncated')
            if sender[0] != 0:
                continue
            offset = 0
            while offset + 16 <= len(data):
                length, typ, msgflags, rseq, _ = struct.unpack_from('=IHHII', data, offset)
                if length < 16 or offset + length > len(data):
                    raise ValueError('malformed netlink frame')
                payload = data[offset + 16:offset + length]
                offset += (length + 3) & ~3
                if rseq != seq:
                    continue
                if msgflags & 0x10:
                    raise RuntimeError('inet_diag dump interrupted; retry via procfs')
                if typ == 3:
                    if len(payload) >= 4 and struct.unpack_from('=i', payload)[0] < 0:
                        raise OSError('inet_diag dump failed')
                    return rows
                if typ == 2:
                    code = struct.unpack_from('=i', payload)[0] if len(payload) >= 4 else -1
                    if code:
                        raise OSError(-code, 'inet_diag kernel error')
                    continue
                if typ != 20:
                    continue
                row = parse_message(payload)
                if row:
                    rows.append(row)
                if len(rows) >= limit:
                    return rows