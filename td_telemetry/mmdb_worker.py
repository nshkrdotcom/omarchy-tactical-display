#!/usr/bin/env python3
"""One isolated offline-MMDB lookup; parent owns timeout and process-group cleanup."""
from __future__ import annotations
import ipaddress
import json
import os
import sys


def main() -> int:
    if len(sys.argv) != 3:
        return 64
    path = os.path.expanduser(sys.argv[1])
    address = str(ipaddress.ip_address(sys.argv[2]))
    try:
        import maxminddb
        database = maxminddb.open_database(path)
        try:
            value = database.get(address) or {}
        finally:
            database.close()
        result = {
            'ok': True,
            'address': address,
            'offline': {
                'asn': value.get('autonomous_system_number'),
                'organization': str(value.get('autonomous_system_organization', ''))[:512],
                'country': str((value.get('country') or {}).get('iso_code', ''))[:64],
            },
        }
    except (ImportError, OSError, ValueError, TypeError, AttributeError) as error:
        result = {'ok': False, 'address': address, 'error': str(error)[:180]}
    print(json.dumps(result, separators=(',', ':')))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
