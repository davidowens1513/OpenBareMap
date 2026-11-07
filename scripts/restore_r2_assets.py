#!/usr/bin/env python3
"""Restore explicitly selected published assets from R2, verifying bytes and SHA-256."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def verify(path, asset):
    if path.stat().st_size != asset['bytes']:
        raise ValueError('Size mismatch: ' + asset['path'])
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if digest != asset['sha256']:
        raise ValueError('Checksum mismatch: ' + asset['path'])


def restore(asset):
    destination = ROOT / asset['path']
    if destination.exists():
        verify(destination, asset)
        print('Already verified:', asset['path'])
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, suffix='.restoring', delete=False) as out:
            temporary = Path(out.name)
            with urllib.request.urlopen(asset['url'], timeout=120) as source:
                total = 0
                while chunk := source.read(1024 * 1024):
                    total += len(chunk)
                    if total > asset['bytes']:
                        raise ValueError('Download exceeds expected size: ' + asset['path'])
                    out.write(chunk)
        verify(temporary, asset)
        # Avoid replacing a file created by another process while downloading.
        os.link(temporary, destination)
        print('Restored:', asset['path'])
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--list', action='store_true', help='List assets without downloading')
    parser.add_argument('--all', action='store_true', help='Restore all assets (approximately 7.49 GB)')
    parser.add_argument('--path', action='append', default=[], help='Restore a listed repository path; repeatable')
    args = parser.parse_args()
    assets = json.loads((ROOT / 'distribution/r2-assets.json').read_text())['assets']
    if args.list:
        for asset in assets:
            print(f"{asset['bytes'] / 1e9:.3f} GB  {asset['path']}")
        return
    known = {asset['path'] for asset in assets}
    if set(args.path) - known:
        parser.error('Unknown asset path')
    if not args.all and not args.path:
        parser.error('Choose --list, --path PATH, or --all')
    for asset in assets:
        if args.all or asset['path'] in args.path:
            restore(asset)


if __name__ == '__main__':
    main()
