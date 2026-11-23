#!/usr/bin/env python3
"""Stage or publish the two Iberian Camino editions and the Azores."""
import argparse
from pathlib import Path
import re

from openbaremap import ROOT
from stage_mountain_editions import card, publish, stage
from stage_worldwide_trekking import merge_worldwide_catalogue

GROUPS = (
    ('portugal', 'camino-portugues'),
    ('france-spain', 'camino-del-norte'),
    ('atlantic-islands', 'azores'),
)
EDITIONS = tuple(region for _, region in GROUPS)
OUTPUT = ROOT / 'work/camino-azores-publication'
ARCHIVE = 'appsbyonzy-camino-azores.zip'


def render_homepage(website, entries, _downloads, count):
    page = website.read_text()
    for group, region in GROUPS:
        page = re.sub(rf'<article id="map-{region}">.*?</article>', '', page, flags=re.S)
        marker = f'<div id="{group}"'
        if page.count(marker) != 1:
            raise ValueError(f'Expected one website group for {group}')
        start = page.index(marker)
        grid_start = page.index('<div class="map-regions">', start)
        grid_end = page.index('</article></div>', grid_start) + len('</article>')
        page = page[:grid_end] + card(region, entries[region]) + page[grid_end:]
    for phrase in ('OpenBareMap editions from within the app', 'offline hiking maps with'):
        page, matches = re.subn(rf'\b\d+ (?={phrase})', f'{count} ', page)
        if matches != 1:
            raise ValueError(f'Expected one edition count before {phrase!r}')
    return page


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--website', type=Path, required=True)
    parser.add_argument('--worldwide-baseline', type=Path)
    parser.add_argument('--publish-assets', action='store_true')
    args = parser.parse_args()
    if args.publish_assets:
        manifests = {f'../{region}-release/preview/manifest.json': f'{region}-manifest.json' for region in EDITIONS}
        publish(OUTPUT, args.website, regions=EDITIONS, render_homepage=render_homepage, preview_manifests=manifests)
    else:
        OUTPUT.mkdir(parents=True, exist_ok=True)
        stage(OUTPUT, args.website, regions=EDITIONS, render=render_homepage, archive=ARCHIVE, version_garmin=True)
        if args.worldwide_baseline:
            merge_worldwide_catalogue(OUTPUT/'worldwide-catalog-v1.json', args.worldwide_baseline, regions=EDITIONS)


if __name__ == '__main__':
    main()
