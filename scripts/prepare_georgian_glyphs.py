#!/usr/bin/env python3
"""Pin the Open Sans Georgian glyph ranges used by the Upper Svaneti edition."""

import json

from fetch_region import download
from openbaremap import ROOT, write


SOURCES = {
    'Open Sans Regular': ('Noto Sans Regular', 'aeb80cf9bd04db8b8efbdf9a106053503ccfb8817c6a4813f1e2a9a9854eae6d'),
    'Open Sans Semibold': ('Noto Sans Regular', 'aeb80cf9bd04db8b8efbdf9a106053503ccfb8817c6a4813f1e2a9a9854eae6d'),
    'Open Sans Bold': ('Noto Sans Bold', '23a87dfef6047d32102973aaf736fa4203eb66cbc3c4f46871a80d410efe2ef3'),
}
LICENSE_URL = 'https://raw.githubusercontent.com/google/fonts/main/ofl/notosansgeorgian/OFL.txt'
LICENSE_SHA256 = '8c02263c5d73d40544f9ed91e30c4e947407057a3cc430d7b786189aeceff6df'


def main():
    lock_path = ROOT / 'viewer-assets.lock.json'
    lock = json.loads(lock_path.read_text())
    pinned = []
    for stack, (source_stack, expected) in SOURCES.items():
        quoted = source_stack.replace(' ', '%20')
        url = f'https://demotiles.maplibre.org/font/{quoted}/4096-4351.pbf'
        target = ROOT / 'viewer' / 'fonts' / stack / '4096-4351.pbf'
        item = download(url, target)
        if item['sha256'] != expected:
            raise ValueError(f'Georgian glyph source changed: {stack}')
        pinned.append({'path': str(target.relative_to(ROOT)), 'sha256': expected,
                       'origin': url + f' ({source_stack} Georgian fallback; SIL Open Font License)'})
    license_target = ROOT / 'viewer' / 'fonts' / 'LICENSE-OFL-NOTO.txt'
    license_item = download(LICENSE_URL, license_target)
    if license_item['sha256'] != LICENSE_SHA256:
        raise ValueError('Noto Sans Georgian licence changed')
    pinned.append({'path': str(license_target.relative_to(ROOT)), 'sha256': LICENSE_SHA256,
                   'origin': LICENSE_URL})
    paths = {item['path'] for item in pinned}
    lock['assets'] = [item for item in lock['assets'] if item['path'] not in paths] + pinned
    write(lock_path, lock)
    print('Pinned Noto Sans Georgian fallback glyph ranges and licence.')


if __name__ == '__main__':
    main()
