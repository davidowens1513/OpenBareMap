#!/usr/bin/env python3
"""Stage or publish the Cusco, Kilimanjaro and Fiordland editions."""

import argparse
import json
from pathlib import Path
import re

from openbaremap import ROOT
from regions import WORLDWIDE_TREKKING_REGIONS
from stage_mountain_editions import REPO_LINK, card, publish, stage

OUTPUT = ROOT / 'work/worldwide-trekking-publication'
ARCHIVE = 'appsbyonzy-worldwide-trekking.zip'
GROUPS = (
    ('peru', 'Peru', 'cusco-inca-trail'),
    ('tanzania', 'Tanzania', 'kilimanjaro'),
    ('new-zealand', 'New Zealand', 'fiordland'),
)


def render_homepage(website, entries, _downloads, count):
    page = website.read_text()
    options, sections = [], []
    for group, label, region in GROUPS:
        option = f'  <option value="{group}">{label}</option>\n'
        page = page.replace(option, '')
        page = re.sub(rf'<!-- {label} -->.*?<!-- End {label} -->\n', '', page, flags=re.S)
        options.append(option)
        sections.append(
            f'<!-- {label} -->\n<div id="{group}" style="margin-top:2rem">'
            f'<h3>{label}</h3>\n{REPO_LINK}\n<div class="map-regions">'
            f'{card(region, entries[region])}</div></div>\n<!-- End {label} -->\n'
        )

    option_marker = '  <option value="us-national-parks">'
    section_marker = '<!-- US National Parks -->'
    if page.count(option_marker) != 1 or page.count(section_marker) != 1:
        raise ValueError('Expected one US National Parks option and section')
    page = page.replace(option_marker, ''.join(options) + option_marker, 1)
    page = page.replace(section_marker, ''.join(sections) + section_marker, 1)
    for phrase in ('OpenBareMap editions from within the app', 'offline hiking maps with'):
        page, changes = re.subn(rf'\b\d+ (?={phrase})', f'{count} ', page)
        if changes != 1:
            raise ValueError(f'Expected one homepage edition count before {phrase!r}')
    return page


def merge_worldwide_catalogue(staged, baseline):
    catalogue = json.loads(baseline.read_text())
    entries = {entry['id']: entry for entry in catalogue['regions']}
    incoming = json.loads(staged.read_text())['regions']
    if {entry['id'] for entry in incoming} != set(WORLDWIDE_TREKKING_REGIONS):
        raise ValueError('The staged Worldwide catalogue must contain the three trekking editions')
    entries.update((entry['id'], entry) for entry in incoming)
    catalogue['regions'] = list(entries.values())
    data = json.dumps(catalogue, separators=(',', ':'), ensure_ascii=False) + '\n'
    if len(data.encode()) > 5_000_000:
        raise ValueError('The staged Worldwide catalogue exceeds the app’s 5 MB limit')
    staged.write_text(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--website', type=Path, required=True)
    parser.add_argument('--worldwide-baseline', type=Path)
    parser.add_argument('--publish-assets', action='store_true')
    args = parser.parse_args()
    regions = WORLDWIDE_TREKKING_REGIONS
    if args.publish_assets:
        manifests = {
            f'../{region}-release/preview/manifest.json': f'{region}-manifest.json'
            for region in regions
        }
        publish(OUTPUT, args.website, regions=regions, render_homepage=render_homepage,
                preview_manifests=manifests)
    else:
        OUTPUT.mkdir(parents=True, exist_ok=True)
        stage(OUTPUT, args.website, regions=regions, render=render_homepage,
              archive=ARCHIVE, version_garmin=True)
        if args.worldwide_baseline:
            merge_worldwide_catalogue(OUTPUT / 'worldwide-catalog-v1.json', args.worldwide_baseline)


if __name__ == '__main__':
    main()
