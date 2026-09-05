"""Isolated statvfs worker. Parent imposes an absolute deadline/output budget."""
import json
import os
import sys


def main() -> None:
    paths = json.loads(sys.stdin.buffer.read(65537))
    if not isinstance(paths, list) or len(paths) > 64:
        raise ValueError('invalid path batch')
    for path in paths:
        if not isinstance(path, str) or not path.startswith('/') or len(path) > 4096:
            continue
        try:
            s = os.statvfs(path)
            row = {'path': path, 'totalBytes': s.f_blocks * s.f_frsize, 'availableBytes': s.f_bavail * s.f_frsize,
                   'usedBytes': (s.f_blocks - s.f_bfree) * s.f_frsize}
            print(json.dumps(row), flush=True)
        except OSError:
            continue


if __name__ == '__main__':
    main()
