#!/usr/bin/env python3
"""Publish the versioned glacier updates and refresh the production website."""

import argparse
from html import escape, unescape
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from build_app_distribution import archive_tree
from build_distribution_instructions import garmin_instructions
from openbaremap import ROOT, digest, write
from regions import US_PARK_REGIONS, profile, region_path
from stage_mountain_editions import preview_prefix, preview_url, stage
from stage_us_national_parks import PLATFORMS, PUBLIC, add_to_archive, checked, publish, upload_release_assets
from upgrade_permanent_ice import REGIONS, VERSION, WAVES, WORK

PUBLISH = WORK / 'publication'
ARCHIVE = 'appsbyonzy-permanent-ice-updates.zip'
WEBSITE = ROOT / 'work/AppsByOnzy-Website/site/index.html'


def record_previous_links(output):
    previous = output / 'previous-links.json'
    if previous.exists():
        return
    app = json.loads((ROOT / 'distribution/app-bundles-v1/catalog.json').read_text())['regions']
    previews = {record['id']: record['url'] for record in json.loads((ROOT / 'config/preview-regions.json').read_text())}
    links = {}
    for region in REGIONS:
        previous_garmin = WORK / 'previous' / region / 'garmin/build-report.json'
        if not previous_garmin.is_file() and profile(region)['mapVersion'] != VERSION:
            previous_garmin = region_path(region, 'garmin/build-report.json')
        old_image = Path(json.loads(previous_garmin.read_text())['output']['path']).name
        links[region] = {'preview': previews[region], 'ios': app[region]['ios'], 'android': app[region]['android'],
                         'garmin': {'url': PUBLIC + 'Garmin/' + old_image,
                                    'instructionsURL': PUBLIC + 'Garmin/' + region + '-instructions.txt'}}
    write(previous, links)


def render_homepage(website, entries, collections, count):
    links = json.loads((PUBLISH / 'previous-links.json').read_text())
    page = website.read_text()
    intro = 'land-cover detail and named summits.'
    ice = ' Selected mountain editions also show mapped glaciers and permanent snowfields.'
    if intro + ice not in page and page.count(intro) == 1:
        page = page.replace(intro, intro + ice, 1)
    for region, entry in entries.items():
        old = links[region]
        substitutions = [(old['preview'], preview_url(region), False)]
        for platform in PLATFORMS:
            substitutions.extend((old[platform][key], entry[platform][key], platform == 'garmin' and key == 'url')
                                 for key in ('url', 'instructionsURL'))
        for before, after, optional_query in substitutions:
            pattern = 'href="' + re.escape(escape(before, quote=True)) + (r'(?:\?[^"]*)?' if optional_query else '') + '"'
            page, changed = re.subn(pattern, lambda _: 'href="' + escape(after, quote=True) + '"', page)
            if not changed and ('href="' + escape(after, quote=True) + '"') not in page:
                raise ValueError(f'Missing {region} link on website: {before}')
    for platform, label in PLATFORMS.items():
        item = collections[platform]
        old = re.escape(PUBLIC + 'OpenBareMap/us-national-parks/2.0.0/OpenBareMap-US-National-Parks-' + label + '.zip')
        new = re.escape(PUBLIC + item['key'])
        page, changed = re.subn(r'href="(?:' + old + '|' + new + ')">' + label + r' \([^<]*\)</a>',
                                lambda _: f'href="{PUBLIC + item["key"]}">{label} ({item["bytes"] / 1e6:,.0f} MB)</a>', page)
        if changed != 1:
            raise ValueError('Missing individual US collection download: ' + platform)
    page, changed = re.subn(r'Currently there are \d+ maps available', f'Currently there are {count} maps available', page, count=1)
    if changed != 1:
        raise ValueError('Missing count on the homepage')
    return page


def collections_for(entries, asset):
    app = json.loads((ROOT / 'distribution/app-bundles-v1/catalog.json').read_text())['regions']
    for platform in PLATFORMS:
        directory = PUBLISH / 'collection-inputs' / platform
        directory.mkdir(parents=True, exist_ok=True)
        for region in US_PARK_REGIONS:
            if platform != 'garmin':
                item = (entries[region] if region in entries else app[region])[platform]
                add_to_archive(directory, checked(ROOT / item['localPath'], item['sha256']))
                continue
            manifest = PUBLISH / 'garmin-manifests' / region / 'manifest.json' if region in entries else (
                ROOT / 'distribution/app-bundles-v1/garmin' / region / 'manifest.json')
            item = json.loads(manifest.read_text())
            name = Path(urlsplit(item['url']).path).name
            source = ROOT / 'regions' / region / 'garmin/dist' / name
            guide = ROOT / 'regions' / region / 'garmin/dist/INSTALL.txt'
            add_to_archive(directory, checked(source, item['imageSHA256']))
            add_to_archive(directory, checked(guide, item['instructionsSHA256']), region + '-instructions.txt')
    packages = {}
    for platform, label in PLATFORMS.items():
        output = PUBLISH / f'OpenBareMap-US-National-Parks-{label}.zip'
        if not output.exists():
            temporary = output.with_suffix('.part')
            archive_tree(PUBLISH / 'collection-inputs' / platform, temporary)
            temporary.replace(output)
        packages[platform] = asset(output, f'OpenBareMap/us-national-parks/{VERSION}/{output.name}')
    return packages


def change_worldwide_titles():
    """Keep the existing Worldwide display labels, including the US group prefix."""
    previous = json.loads((ROOT / 'work/canadian-rockies-publication/worldwide-catalog-v1.json').read_text())
    metadata = {entry['id']: entry for entry in previous['regions']}
    path = PUBLISH / 'worldwide-catalog-v1.json'
    updated = json.loads(path.read_text())
    for entry in updated['regions']:
        old = metadata[entry['id']]
        for field in ('title', 'bounds', 'coveragePolygons'):
            entry[field] = old[field]
    write(path, updated)


def record_release():
    plan = json.loads((PUBLISH / 'release-plan.json').read_text())
    receipts = json.loads((PUBLISH / 'public-verification.json').read_text())
    if any(receipts.get(item['key'], {}).get('sha256') != item['sha256'] for item in plan['assets']):
        raise ValueError('Release verification is incomplete')
    previous = json.loads((PUBLISH / 'previous-links.json').read_text())
    readme = ROOT / 'README.md'
    markdown = readme.read_text()
    for region, entry in plan['regions'].items():
        for platform in PLATFORMS:
            for field in ('url', 'instructionsURL'):
                before = re.escape(previous[region][platform][field])
                query = r'(?:\?[^)]+)?' if platform == 'garmin' and field == 'url' else ''
                markdown = re.sub(before + query + r'(?=\))', lambda _: entry[platform][field], markdown)
    readme.write_text(markdown)
    write(ROOT / 'web-preview/verification/permanent-ice-publication.json',
          {'mapVersion': VERSION, 'regionIds': list(plan['regions']), 'verifiedPublicAssets': len(plan['assets']),
           'previewArchivesWithVerifiedByteRanges': sum(item['key'].endswith('.pmtiles') for item in plan['assets']),
           'publicAssetsAndCatalogues': receipts})


def upload_us_collections():
    output = PUBLISH / 'us-collections'
    output.mkdir(exist_ok=True)
    entries = {}
    for number in (1, 2):
        wave = PUBLISH / f'wave-{number}'
        plan = json.loads((wave / 'release-plan.json').read_text())
        entries.update(plan['regions'])
        for region in plan['regions']:
            source = wave / 'garmin-manifests' / region / 'manifest.json'
            target = PUBLISH / 'garmin-manifests' / region / 'manifest.json'
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
    assets = []

    def asset(path, key):
        item = {'key': key, 'path': str(path.relative_to(ROOT)), 'bytes': path.stat().st_size, 'sha256': digest(path)}
        assets.append(item)
        return item

    collections_for(entries, asset)
    write(output / 'release-plan.json', {'assets': assets})
    upload_release_assets(output, upload_workers=3)


def upload_editions(output, editions):
    output.mkdir(exist_ok=True)
    for region in editions:
        region_path(region, 'garmin/dist/INSTALL.txt').write_text(
            garmin_instructions(region, profile(region)['garminFilename']))
    stage(output, WEBSITE, regions=editions, render=None,
          products_for=lambda region: WORK / region, version_garmin=True)
    receipts = output / 'public-verification.json'
    verified = json.loads(receipts.read_text()) if receipts.exists() else {}
    for region in editions:
        early = PUBLISH / f'region-{region}/public-verification.json'
        if early.exists() and early != receipts:
            verified.update(json.loads(early.read_text()))
    write(receipts, verified)
    upload_release_assets(output, upload_workers=8)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--publish-assets', action='store_true')
    action.add_argument('--upload-wave', type=int, choices=range(1, len(WAVES) + 1))
    action.add_argument('--upload-region', choices=REGIONS)
    action.add_argument('--upload-us-collections', action='store_true')
    args = parser.parse_args()
    PUBLISH.mkdir(parents=True, exist_ok=True)
    if args.upload_wave:
        upload_editions(PUBLISH / f'wave-{args.upload_wave}', WAVES[args.upload_wave - 1])
    elif args.upload_region:
        upload_editions(PUBLISH / f'region-{args.upload_region}', (args.upload_region,))
    elif args.upload_us_collections:
        upload_us_collections()
    elif args.publish_assets:
        receipts = PUBLISH / 'public-verification.json'
        verified = json.loads(receipts.read_text()) if receipts.exists() else {}
        for path in [*PUBLISH.glob('wave-*/public-verification.json'),
                     PUBLISH / 'us-collections/public-verification.json']:
            if not path.exists():
                continue
            verified.update(json.loads(path.read_text()))
        write(receipts, verified)
        manifests = {f'../{region}/preview/manifest.json': f'{region}-permanent-ice-manifest.json' for region in REGIONS}
        publish(PUBLISH, WEBSITE, regions=REGIONS, render_homepage=render_homepage,
                preview_manifests=manifests, upload_workers=10)
        record_release()
    else:
        record_previous_links(PUBLISH)
        stage(PUBLISH, WEBSITE, regions=REGIONS, render=render_homepage, archive=ARCHIVE,
              products_for=lambda region: WORK / region, version_garmin=True, collections_for=collections_for)
        change_worldwide_titles()


if __name__ == '__main__':
    main()
