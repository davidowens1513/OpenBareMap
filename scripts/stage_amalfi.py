#!/usr/bin/env python3
"""Stage the Sorrento, Amalfi and Bay of Naples release."""
import argparse
from pathlib import Path
import re

from openbaremap import ROOT
from stage_mountain_editions import card, publish, stage


REGION = 'amalfi-bay-of-naples'
OUTPUT = ROOT / 'work/amalfi-bay-of-naples-publication'


def render_homepage(website, entries, _downloads, count):
    page = website.read_text()
    page = re.sub(r'<article id="map-amalfi-bay-of-naples">.*?</article>', '', page, flags=re.S)
    section = re.search(r'<!-- Italy -->.*?<!-- End Italy -->', page, flags=re.S)
    if section is None or 'id="map-cinque-terre"' not in section[0]:
        raise ValueError('The website must contain the existing Italy group with Cinque Terre')
    position = page.rindex('</div></div>', section.start(), section.end())
    page = page[:position] + card(REGION, entries[REGION]) + page[position:]
    for phrase in ('OpenBareMap editions from within the app', 'offline hiking maps with'):
        page, changes = re.subn(rf'\b\d+ (?={phrase})', f'{count} ', page)
        if changes != 1:
            raise ValueError(f'Expected one homepage edition count before {phrase!r}')
    return page


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--website', required=True, type=Path)
    parser.add_argument('--publish-assets', action='store_true')
    args = parser.parse_args()
    if args.publish_assets:
        publish(OUTPUT, args.website, regions=(REGION,), render_homepage=render_homepage,
                preview_manifests={f'../{REGION}-release/preview/manifest.json': f'{REGION}-manifest.json'})
    else:
        OUTPUT.mkdir(parents=True, exist_ok=True)
        stage(OUTPUT, args.website, regions=(REGION,), render=render_homepage,
              archive='appsbyonzy-amalfi.zip', version_garmin=True)


if __name__ == '__main__':
    main()
