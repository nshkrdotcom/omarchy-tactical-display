"""One opt-in resolver call, isolated so libc/NSS stalls are killable."""
import ipaddress
import json
import socket
import sys

if __name__ == '__main__':
    address = str(ipaddress.ip_address(sys.argv[1]))
    try:
        print(json.dumps({'address': address, 'name': socket.gethostbyaddr(address)[0]}))
    except (OSError, ValueError):
        print(json.dumps({'address': address, 'name': None}))
