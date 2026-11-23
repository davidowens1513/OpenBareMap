#!/usr/bin/env python3
"""Stage or publish Camino Francés and Cinque Terre & Portofino."""
import argparse
from pathlib import Path
import re

from openbaremap import ROOT
from regions import EUROPEAN_WALKING_REGIONS
from stage_mountain_editions import REPO_LINK, card, publish, stage

ARCHIVE = 'appsbyonzy-european-walks.zip'
OPTION = '  <option value="italy">Italy</option>\n'


def render_homepage(website, entries, _downloads, count):
    page = website.read_text().replace(OPTION, '')
    page = re.sub(r'<article id="map-camino-frances">.*?</article>', '', page, flags=re.S)
    page = re.sub(r'<!-- Italy -->.*?<!-- End Italy -->\n', '', page, flags=re.S)
    option_marker = '  <option value="alps">'
    france_spain = '<div id="france-spain"'
    alpine = '<div id="alps"'
    if any(page.count(marker) != 1 for marker in (option_marker, france_spain, alpine)):
        raise ValueError('The homepage must contain the France & Spain and Alps groups')
    page = page.replace(option_marker, OPTION + option_marker, 1)
    start = page.index(france_spain)
    end = page.index(alpine, start)
    position = page.rindex('</div></div>', start, end)
    page = page[:position] + card('camino-frances', entries['camino-frances']) + page[position:]
    italy = ('<!-- Italy -->\n<div id="italy" style="margin-top:2rem"><h3>Italy</h3>\n'
             f'{REPO_LINK}\n<div class="map-regions">{card("cinque-terre", entries["cinque-terre"])}</div></div>\n'
             '<!-- End Italy -->\n')
    page = page.replace(alpine, italy + alpine, 1)
    for phrase in ('OpenBareMap editions from within the app', 'offline hiking maps with'):
        page, changes = re.subn(rf'\b\d+ (?={phrase})', f'{count} ', page)
        if changes != 1:
            raise ValueError(f'Expected one homepage edition count before {phrase!r}')
    return page


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publish-assets', action='store_true')
    parser.add_argument('--website', type=Path, required=True)
    args = parser.parse_args()
    output = ROOT / 'work/european-walks-publication'
    regions = EUROPEAN_WALKING_REGIONS
    if args.publish_assets:
        manifests = {f'../{region}-release/preview/manifest.json': f'{region}-manifest.json' for region in regions}
        publish(output, args.website, regions=regions, render_homepage=render_homepage, preview_manifests=manifests)
    else:
        output.mkdir(parents=True, exist_ok=True)
        stage(output, args.website, regions=regions, render=render_homepage, archive=ARCHIVE, version_garmin=True)


if __name__ == '__main__':
    main()
