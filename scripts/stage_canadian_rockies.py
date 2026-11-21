#!/usr/bin/env python3
"""Stage separate Canadian Rockies downloads and add their website group."""

import argparse
from html import escape
import json
import re

from openbaremap import ROOT
from regions import CANADIAN_ROCKIES_REGIONS, profile
from stage_mountain_editions import PLATFORMS, REPO_LINK, download_row, preview_url, publish, stage

ARCHIVE = 'appsbyonzy-canadian-rockies.zip'
OPTION = '  <option value="canadian-rockies">Canadian Rockies</option>\n'


def render_homepage(website, entries, _downloads, count):
    cards = []
    for region in CANADIAN_ROCKIES_REGIONS:
        p = profile(region)
        downloads = ''.join(download_row(label, entries[region][platform]['url'],
                                         entries[region][platform]['instructionsURL'])
                            for platform, label in PLATFORMS.items())
        cards.append(f'<article id="map-{region}"><h3>{escape(p["label"])}</h3>'
                     f'<p>{escape(p["coverage"])}</p><div class="region-actions">'
                     f'<div class="preview-action"><a href="{preview_url(region)}">'
                     'Preview <span aria-hidden="true">↗</span></a></div>' + downloads + '</div></article>')
    section = ('<!-- Canadian Rockies -->\n<div id="canadian-rockies" style="margin-top:2rem">'
               '<h3>Canadian Rockies</h3>\n'
               '<p>Glaciers are shown in blue. The map key includes a separate symbol for permanent snowfields.</p>\n'
               + REPO_LINK + '\n<div class="map-regions">'
               + ''.join(cards) + '</div></div>\n<!-- End Canadian Rockies -->\n')
    page = re.sub(r'<!-- Canadian Rockies -->.*?<!-- End Canadian Rockies -->\n', '', website.read_text(), flags=re.S)
    page = page.replace(OPTION, '')
    marker = '  <option value="us-national-parks">US National Parks</option>'
    if page.count(marker) != 1:
        raise ValueError('Expected one US National Parks option in the map-group picker')
    page = page.replace(marker, OPTION + marker)
    start = page.index('<!-- US National Parks -->')
    page = page[:start] + section + page[start:]
    page, changes = re.subn(r'Currently there are \d+ maps available', f'Currently there are {count} maps available', page, count=1)
    if changes != 1:
        raise ValueError('Missing OpenBareMap map count')
    return page


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publish-assets', action='store_true')
    args = parser.parse_args()
    output = ROOT / 'work/canadian-rockies-publication'
    website = ROOT / 'work/AppsByOnzy-Website/site/index.html'
    for region in CANADIAN_ROCKIES_REGIONS:
        report = ROOT / 'build' / (region + '-release') / 'build.json'
        if not report.exists() or not json.loads(report.read_text()).get('geometryReport', {}).get('permanentIce'):
            parser.error(f'{region} must be rebuilt with permanent ice before publication')
    if args.publish_assets:
        manifests = {f'../{region}-release/preview/manifest.json': f'{region}-manifest.json' for region in CANADIAN_ROCKIES_REGIONS}
        publish(output, website, regions=CANADIAN_ROCKIES_REGIONS, render_homepage=render_homepage,
                preview_manifests=manifests)
    else:
        output.mkdir(parents=True, exist_ok=True)
        stage(output, website, regions=CANADIAN_ROCKIES_REGIONS, render=render_homepage, archive=ARCHIVE)


if __name__ == '__main__':
    main()
