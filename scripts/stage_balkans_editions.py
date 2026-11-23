#!/usr/bin/env python3
"""Stage and publish the five Balkans walking editions."""
import argparse
from pathlib import Path
import re

from openbaremap import ROOT
from regions import BALKANS_REGIONS
from stage_mountain_editions import REPO_LINK, card, publish, stage
from stage_worldwide_trekking import merge_worldwide_catalogue

OUTPUT = ROOT/'work/balkans-publication'
ARCHIVE = 'appsbyonzy-balkans.zip'
OLD_OPTION = '  <option value="turkiye">Türkiye</option>\n'
NEW_OPTION = '  <option value="balkans-turkiye">Balkans &amp; Türkiye</option>\n'
TURKIYE = re.compile(r'<!-- Türkiye -->.*?<!-- End Türkiye -->\n', re.S)
BALKANS = re.compile(r'<!-- Balkans and Türkiye -->.*?<!-- End Balkans and Türkiye -->\n', re.S)


def render_homepage(website, entries, _downloads, count):
    page = website.read_text()
    if page.count(OLD_OPTION) == 1:
        page = page.replace(OLD_OPTION, NEW_OPTION, 1)
    elif page.count(NEW_OPTION) != 1:
        raise ValueError('Expected a single Türkiye or Balkans & Türkiye option')
    turkey, = TURKIYE.findall(page)
    turkey = turkey.replace('<h3>Türkiye</h3>', '<h4>Türkiye</h4>', 1).replace(REPO_LINK+'\n', '', 1)
    cards = ''.join(card(region, entries[region]) for region in BALKANS_REGIONS)
    section = ('<!-- Balkans and Türkiye -->\n<div id="balkans-turkiye" style="margin-top:2rem">'
               f'<h3>Balkans &amp; Türkiye</h3>\n{REPO_LINK}\n<div class="map-regions">{cards}</div>\n'
               f'{turkey}</div>\n<!-- End Balkans and Türkiye -->\n')
    group = BALKANS if BALKANS.search(page) else TURKIYE
    page, changes = group.subn(lambda _: section, page)
    if changes != 1:
        raise ValueError('Expected a single Balkans & Türkiye section')
    for phrase in ('OpenBareMap editions from within the app', 'offline hiking maps with'):
        page, changes = re.subn(rf'\b\d+ (?={phrase})', f'{count} ', page)
        if changes != 1:
            raise ValueError(f'Expected one edition count before {phrase!r}')
    return page


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--website', type=Path, required=True)
    parser.add_argument('--worldwide-baseline', type=Path)
    parser.add_argument('--publish-assets', action='store_true')
    args = parser.parse_args()
    if args.publish_assets:
        manifests = {f'../{region}-release/preview/manifest.json': f'{region}-manifest.json'
                     for region in BALKANS_REGIONS}
        publish(OUTPUT, args.website, regions=BALKANS_REGIONS,
                render_homepage=render_homepage, preview_manifests=manifests)
    else:
        OUTPUT.mkdir(parents=True, exist_ok=True)
        stage(OUTPUT, args.website, regions=BALKANS_REGIONS, render=render_homepage,
              archive=ARCHIVE, version_garmin=True)
        if args.worldwide_baseline:
            merge_worldwide_catalogue(OUTPUT/'worldwide-catalog-v1.json', args.worldwide_baseline,
                                      regions=BALKANS_REGIONS)


if __name__ == '__main__':
    main()
