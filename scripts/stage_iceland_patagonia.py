#!/usr/bin/env python3
"""Stage validated Iceland and Patagonia editions for publication."""
import argparse
from pathlib import Path
import re

from openbaremap import ROOT
from regions import ICELAND_PATAGONIA_REGIONS
from stage_mountain_editions import REPO_LINK, card, publish, stage

ARCHIVE = 'appsbyonzy-iceland-patagonia.zip'
GROUPS = (
    ('iceland', 'Iceland', ICELAND_PATAGONIA_REGIONS[:1], 'eastern-europe'),
    ('patagonia', 'Patagonia', ICELAND_PATAGONIA_REGIONS[1:], 'us-national-parks'),
)


def render_homepage(website, entries, _downloads, count):
    page = website.read_text()
    for group, label, regions, following_group in GROUPS:
        option = f'  <option value="{group}">{label}</option>\n'
        page = page.replace(option, '')
        page = re.sub(f'<!-- {label} -->.*?<!-- End {label} -->\n', '', page, flags=re.S)
        option_marker = f'  <option value="{following_group}">'
        section_marker = f'<div id="{following_group}"'
        # Keep the existing section comment immediately before its section.
        comment = '<!-- Eastern Europe -->' if following_group == 'eastern-europe' else '<!-- US National Parks -->'
        if comment in page:
            section_marker = comment
        if page.count(option_marker) != 1 or page.count(section_marker) != 1:
            raise ValueError(f'Missing or duplicate homepage marker for {following_group}')
        page = page.replace(option_marker, option + option_marker, 1)
        cards = ''.join(card(region, entries[region]) for region in regions)
        section = (f'<!-- {label} -->\n<div id="{group}" style="margin-top:2rem">'
                   f'<h3>{label}</h3>\n'
                   '<p>The map key distinguishes glaciers from mapped permanent snowfields.</p>\n'
                   f'{REPO_LINK}\n<div class="map-regions">{cards}</div></div>\n<!-- End {label} -->\n')
        page = page.replace(section_marker, section + section_marker, 1)
    for phrase in ('OpenBareMap editions from within the app', 'offline hiking maps with'):
        page, changes = re.subn(rf'\b\d+ (?={phrase})', f'{count} ', page)
        if changes != 1:
            raise ValueError(f'Expected one homepage edition count before {phrase!r}')
    return page


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publish-assets', action='store_true')
    parser.add_argument('--website', type=Path, default=ROOT / 'work/AppsByOnzy-Website/site/index.html')
    args = parser.parse_args()
    output = ROOT / 'work/iceland-patagonia-publication'
    website = args.website.resolve()
    if args.publish_assets:
        manifests = {
            f'../{region}-release/preview/manifest.json': f'{region}-manifest.json'
            for region in ICELAND_PATAGONIA_REGIONS
        }
        publish(output, website, regions=ICELAND_PATAGONIA_REGIONS,
                render_homepage=render_homepage, preview_manifests=manifests)
    else:
        output.mkdir(parents=True, exist_ok=True)
        stage(output, website, regions=ICELAND_PATAGONIA_REGIONS,
              render=render_homepage, archive=ARCHIVE, version_garmin=True)


if __name__ == '__main__':
    main()
