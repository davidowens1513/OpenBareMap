#!/usr/bin/env python3
"""Stage or publish the Everest and Annapurna trekking maps."""
import argparse
from pathlib import Path
import re

from openbaremap import ROOT
from regions import NEPAL_REGIONS
from stage_mountain_editions import REPO_LINK, card, publish, stage

ARCHIVE = 'appsbyonzy-nepal-trekking.zip'
OPTION = '  <option value="nepal">Nepal</option>\n'


def render_homepage(website, entries, _downloads, count):
    page = website.read_text().replace(OPTION, '')
    page = re.sub(r'<!-- Nepal -->.*?<!-- End Nepal -->\n', '', page, flags=re.S)
    option_marker = '  <option value="patagonia">'
    section_marker = '<!-- Patagonia -->'
    if page.count(option_marker) != 1 or page.count(section_marker) != 1:
        raise ValueError('The homepage must contain the existing Patagonia map group')
    page = page.replace(option_marker, OPTION + option_marker, 1)
    cards = ''.join(card(region, entries[region]) for region in NEPAL_REGIONS)
    section = ('<!-- Nepal -->\n<div id="nepal" style="margin-top:2rem"><h3>Nepal</h3>\n'
               '<p>Two Himalayan trekking maps with 20-metre contours, hillshade and mapped glaciers.</p>\n'
               f'{REPO_LINK}\n<div class="map-regions">{cards}</div></div>\n<!-- End Nepal -->\n')
    page = page.replace(section_marker, section + section_marker, 1)
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
    output = ROOT / 'work/nepal-publication'
    if args.publish_assets:
        manifests = {f'../{region}-release/preview/manifest.json': f'{region}-manifest.json'
                     for region in NEPAL_REGIONS}
        publish(output, args.website, regions=NEPAL_REGIONS, render_homepage=render_homepage,
                preview_manifests=manifests)
    else:
        output.mkdir(parents=True, exist_ok=True)
        stage(output, args.website, regions=NEPAL_REGIONS, render=render_homepage,
              archive=ARCHIVE, version_garmin=True)


if __name__ == '__main__':
    main()
