#!/usr/bin/env python3
"""Verify source/release trust invariants without modifying the workstation."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
LICENSE_TAIL = "## License\n\nTactical Display is open-source software licensed under the [MIT License](LICENSE)."


def git(*args: str) -> str:
    return subprocess.run(['git', '-C', str(ROOT), *args], check=True, capture_output=True, text=True, timeout=5).stdout.strip()


def source_checks() -> list[str]:
    errors: list[str] = []
    required = ['README.md', 'LICENSE', 'manifest.json', 'Overlay.qml', 'BarWidget.qml',
                'docs/SECURITY-PRIVACY.md', 'docs/TESTING.md']
    for relative in required:
        if not (ROOT / relative).is_file():
            errors.append('missing ' + relative)
    readme = (ROOT / 'README.md').read_text() if (ROOT / 'README.md').is_file() else ''
    if not readme.endswith(LICENSE_TAIL):
        errors.append('README license section changed')
    for path in ROOT.rglob('*'):
        if '.git' in path.parts:
            continue
        if path.is_symlink():
            errors.append('repository symlink: ' + str(path.relative_to(ROOT)))
    try:
        manifest = json.loads((ROOT / 'manifest.json').read_text())
        if manifest.get('id') != 'nshkr.tactical-display' or manifest.get('version') != '1.0.0':
            errors.append('manifest id/version mismatch')
    except (OSError, ValueError):
        errors.append('manifest is unreadable/invalid')
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-only', action='store_true', help='check repository/source invariants without requiring a release tag')
    parser.add_argument('--expect-tag', default='', help='require HEAD to equal this exact Git tag and a clean tracked/untracked tree')
    args = parser.parse_args()
    errors = source_checks()
    report: dict[str, object] = {'status': 'PASS', 'sourceChecks': 'PASS', 'errors': errors}
    if args.expect_tag:
        try:
            head = git('rev-parse', 'HEAD')
            tagged = git('rev-list', '-n', '1', args.expect_tag)
            dirty = bool(git('status', '--porcelain'))
            report.update(head=head, expectedTag=args.expect_tag, tagCommit=tagged, clean=not dirty)
            if head != tagged:
                errors.append(f'HEAD does not equal tag {args.expect_tag}')
            if dirty:
                errors.append('release worktree/index contains changes or untracked files')
        except (OSError, subprocess.SubprocessError) as error:
            errors.append('Git release verification failed: ' + str(error))
    elif not args.source_only:
        errors.append('use --source-only for development or --expect-tag TAG for a release')
    if errors:
        report['status'] = 'FAIL'
        report['sourceChecks'] = 'FAIL'
    print(json.dumps(report, separators=(',', ':')))
    return 0 if not errors else 1


if __name__ == '__main__':
    raise SystemExit(main())
