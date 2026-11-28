#!/usr/bin/env python3
"""Check local and, optionally, public links for the nine-map release."""

import argparse
from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from openbaremap import ROOT
from regions import NINE_MAP_RELEASE_REGIONS
from stage_map_collection import validate_release


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.targets = []

    def handle_starttag(self, _tag, attrs):
        values = dict(attrs)
        self.targets.extend(values[name] for name in ('href', 'src') if values.get(name))


def local_target(base, value, site=None):
    value = value.split('#', 1)[0].split('?', 1)[0]
    if not value or value.startswith(('http://', 'https://', 'mailto:', 'data:', 'javascript:')):
        return None
    if value.startswith('/'):
        return site / value.removeprefix('/') if site else None
    return base / value


def check_readme(path):
    missing = []
    text = path.read_text()
    targets = re.findall(r'!?(?:\[[^]]*\])\(([^)]+)\)', text)
    parser = Links()
    parser.feed(text)
    targets.extend(parser.targets)
    for value in targets:
        target = local_target(path.parent, value)
        if target is not None and not target.exists():
            missing.append(f'{path.relative_to(ROOT)} -> {value}')
    return missing


def public_urls():
    text = (ROOT / 'README.md').read_text()
    urls = set(re.findall(r'https://downloads\.appsbyonzy\.dev/[^)" ]+', text))
    return sorted(url for url in urls if any('/' + region + '/' in url for region in NINE_MAP_RELEASE_REGIONS))


def check_public(urls):
    failures = []
    for index, url in enumerate(urls, 1):
        request = Request(url, headers={'Range': 'bytes=0-0', 'User-Agent': 'OpenBareMap-release-check'})
        try:
            with urlopen(request, timeout=30) as response:
                if response.status not in (200, 206):
                    failures.append(f'{response.status} {url}')
        except HTTPError as error:
            failures.append(f'{error.code} {url}')
        print(f'Public link {index}/{len(urls)} checked', flush=True)
    return failures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--website-repo', type=Path, required=True)
    parser.add_argument('--publication', type=Path, default=ROOT / 'work/nine-map-publication')
    parser.add_argument('--public', action='store_true')
    args = parser.parse_args()
    missing = check_readme(ROOT / 'README.md') + check_readme(ROOT / 'distribution/README.md')
    count = validate_release(args.publication, args.website_repo.resolve())
    if args.public:
        missing.extend(check_public(public_urls()))
    if missing:
        raise SystemExit('Link check failed:\n' + '\n'.join(missing))
    public = len(public_urls()) if args.public else 0
    print(f'Link check passed: two READMEs, both website roots, {count}-entry catalogues'
          f'{f", and {public} new public URLs" if args.public else ""}.')


if __name__ == '__main__':
    main()
