#!/usr/bin/env python3
"""Stage the complete US National Parks release and verify published map assets."""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from http.client import HTTPException
from html import escape
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.parse import quote
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from zipfile import ZIP_DEFLATED, ZipFile

from shapely.geometry import mapping, shape

from build_app_distribution import archive_tree, build_one
from openbaremap import ROOT, digest, write
from regions import US_PARK_REGIONS, profile
from verify_app_distribution import read_hash

VERSION = '2.0.0'
PUBLIC = 'https://downloads.appsbyonzy.dev/'
PREFIX = f'OpenBareMap/us-national-parks/{VERSION}/'
PREVIEW = PREFIX + 'preview'
REMOTE = 'r2:baregps-production-assets/'
PLATFORMS = {'ios': 'iOS', 'android': 'Android', 'garmin': 'Garmin'}
APP_CATALOGUE = 'OpenBareMap/app-bundles-v1/catalog.json'
WORLDWIDE_CATALOGUE = 'OpenBareMap/worldwide-catalog-v1.json'
CATALOGUE_CACHE_POLICY = 'no-cache, max-age=0, must-revalidate'


def run(*command):
    subprocess.run(list(map(str, command)), cwd=ROOT, check=True)


def checked(path, sha):
    if digest(path) != sha:
        raise ValueError(f'Checksum changed: {path}')
    return path


def preview_url(region):
    return f'{PUBLIC}{PREVIEW}/{region}/index.html'


def add_to_archive(directory, source, archive_name=None):
    target = directory / (archive_name or source.name)
    if target.exists():
        checked(target, digest(source))
    else:
        os.link(source, target)


def download_row(label, url, guide=None):
    instructions = f' <span aria-hidden="true">|</span> <a href="{escape(guide, quote=True)}">Instructions</a>' if guide else ''
    return (f'<div class="download-row"><span class="download-kind">{label}</span>'
            f' <div class="download-line"><span aria-hidden="true">|</span> '
            f'<a href="{escape(url, quote=True)}">Download</a>{instructions}</div></div>')


def stage_homepage(website, regions, collections, count):
    start = '<!-- US National Parks -->'
    end = '<!-- End US National Parks -->'
    page = re.sub(r'\n?' + re.escape(start) + r'.*?' + re.escape(end) + r'\n?', '', website.read_text(), flags=re.S)
    section = page.index('id="openbaremap"')
    position = page.index('</section>', section)
    position = page.rindex('</div></div></div>', section, position) + len('</div>')
    collection_links = ''.join(
        download_row(f'{label} ({collections[platform]["bytes"] / 1e6:,.0f} MB)',
                     PUBLIC + collections[platform]['key'])
        for platform, label in PLATFORMS.items()
    )
    cards = []
    for region in US_PARK_REGIONS:
        entries = regions[region]
        p = profile(region)
        links = ''.join(
            download_row(PLATFORMS[platform], entries[platform]['url'], entries[platform]['instructionsURL'])
            for platform in PLATFORMS
        )
        cards.append(
            f'<article><h3>{escape(p["label"])}</h3><p>{escape(p["coverage"])}</p>'
            f'<div class="region-actions"><div class="preview-action"><a href="{preview_url(region)}">'
            f'Preview <span aria-hidden="true">↗</span></a></div>{links}</div></article>'
        )
    block = (
        f'\n{start}\n<div id="us-national-parks" style="margin-top:2rem"><h3>US National Parks</h3>'
        f'<div class="map-regions">{"".join(cards)}</div>'
        '<div class="collection-downloads us-national-parks-collection"><h4>US National Parks collection</h4>'
        '<p>Nine maps covering ten parks, with Yellowstone and Grand Teton in one map.</p>'
        f'<p class="tool-subtitle">Version {VERSION} · collection</p>'
        f'<strong>Download all nine US national park maps</strong>{collection_links}</div></div>\n{end}\n'
    )
    page = page[:position] + block + page[position:]
    return re.sub(r'Currently there are \d+ maps available', f'Currently there are {count} maps available', page, count=1)


def stage_website_archive(website, homepage, archive):
    pending = archive.with_suffix('.zip.part')
    with ZipFile(pending, 'w', compression=ZIP_DEFLATED) as zipped:
        for path in sorted(website.parent.rglob('*')):
            if not path.is_file() or path.name == '.DS_Store':
                continue
            if path.stat().st_size < 250 and path.read_bytes().startswith(b'version https://git-lfs.github.com/spec/'):
                raise ValueError(f'Unresolved website LFS pointer: {path}')
            zipped.write(homepage if path == website else path, path.relative_to(website.parent))
    with ZipFile(pending) as zipped:
        if zipped.testzip() or zipped.read('index.html') != homepage.read_bytes():
            raise ValueError('The staged production website archive differs from its source')
    pending.replace(archive)


def stage(output, website, worldwide):
    previews = output / 'preview'
    kits = output / 'kits'
    base_catalog = json.loads((ROOT / 'distribution/app-bundles-v1/catalog.json').read_text())
    old_worldwide = json.loads(worldwide.read_text())
    for region in US_PARK_REGIONS:
        p = profile(region)
        release = ROOT / 'releases' / region / p['mapVersion']
        validation = json.loads((release / 'validation.json').read_text())
        if validation['region'] != region or not validation['irelandPreserved']:
            raise ValueError(f'Missing completed map validation for {region}')
    pending_kits = [region for region in US_PARK_REGIONS if not (kits / region / 'manifest.json').is_file()]
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda region: build_one(region, kits), pending_kits))
    if not (previews / 'manifest.json').is_file():
        cached = ROOT / 'work/alps-web-2.0.0'
        extra = ['--cached-preview', cached] if (cached / 'manifest.json').is_file() else []
        run(sys.executable, 'scripts/build_web_previews.py', '--output', previews, '--origin',
            PUBLIC + PREVIEW, '--regions', *US_PARK_REGIONS, *extra)
    preview_manifest = json.loads((previews / 'manifest.json').read_text())
    if preview_manifest['dataOrigin'] != PUBLIC + PREVIEW or set(preview_manifest['regions']) != set(US_PARK_REGIONS):
        raise ValueError('Preview collection differs from the release')
    for region, datasets in preview_manifest['regions'].items():
        for name, record in datasets.items():
            checked(previews / 'data' / region / f'{name}.pmtiles', record['sha256'])

    uploads = {}
    def asset(path, key):
        uploads[key] = {'key': key, 'path': str(path.relative_to(ROOT)),
                        'bytes': path.stat().st_size, 'sha256': digest(path)}
        return uploads[key]

    for path in previews.rglob('*'):
        if path.is_file():
            asset(path, PREVIEW + '/' + path.relative_to(previews).as_posix())
    entries = {}
    world_entries = {record['id']: record for record in old_worldwide['regions']}
    archive_inputs = output / 'archive-inputs'
    for platform in PLATFORMS:
        (archive_inputs / platform).mkdir(parents=True, exist_ok=True)

    for region in US_PARK_REGIONS:
        p = profile(region)
        inputs = json.loads((kits / region / 'manifest.json').read_text())
        release = ROOT / 'releases' / region / VERSION
        local_garmin = ROOT / 'regions' / region / 'garmin'
        for platform in ('ios', 'android'):
            entry = inputs[platform]
            source = checked(ROOT / entry['localPath'], entry['sha256'])
            release_dir = release / 'app-bundles-v1' / platform
            release_dir.mkdir(parents=True, exist_ok=True)
            add_to_archive(release_dir, source)
            entry['localPath'] = str((release_dir / source.name).relative_to(ROOT))
            asset(ROOT / entry['localPath'], entry['r2Key'])
            guide = checked(source.parent / 'instructions.txt', entry['instructionsSHA256'])
            asset(guide, entry['instructionsURL'].removeprefix(PUBLIC))
            asset(source.parent / 'SHA256SUMS.txt', entry['r2Key'].rsplit('/', 1)[0] + '/SHA256SUMS.txt')
            manifest = release_dir / 'manifest.json'
            write(manifest, entry)
            asset(manifest, entry['r2Key'].rsplit('/', 1)[0] + '/manifest.json')
            add_to_archive(archive_inputs / platform, source)

        report = json.loads((local_garmin / 'build-report.json').read_text())['output']
        image = checked(ROOT / report['path'], report['sha256'])
        guide_key = f'Garmin/{region}-instructions.txt'
        image_asset = asset(image, 'Garmin/' + image.name)
        guide = asset(local_garmin / 'dist/INSTALL.txt', guide_key)
        for filename in ('ATTRIBUTION.txt', 'boundary-source.json', 'terrain-attribution.md', 'terrain-data-sources.md'):
            asset(local_garmin / 'dist' / filename, f'Garmin/{region}/{filename}')
        add_to_archive(archive_inputs / 'garmin', image)
        add_to_archive(archive_inputs / 'garmin', ROOT / guide['path'], region + '-instructions.txt')

        garmin = {'region': region, 'url': PUBLIC + image_asset['key'], 'downloadURL': PUBLIC + image_asset['key'],
                  'instructionsURL': PUBLIC + guide_key, 'instructionsSHA256': guide['sha256'],
                  'bytes': image_asset['bytes'], 'imageSHA256': image_asset['sha256'],
                  'garminPackageRevision': p['garminPackageRevision']}
        garmin_manifest = output / 'garmin-manifests' / region / 'manifest.json'
        garmin_manifest.parent.mkdir(parents=True, exist_ok=True)
        write(garmin_manifest, garmin)
        asset(garmin_manifest, f'Garmin/{region}/manifest.json')
        entries[region] = {**inputs, 'garmin': garmin}
        base_catalog['regions'][region] = inputs
        base_catalog['mapVersions'][region] = VERSION

        footprint = shape(json.loads((ROOT / 'regions' / region / 'coverage.geojson').read_text())['features'][0]['geometry'])
        geometry = mapping(footprint)
        polygons = geometry['coordinates'] if geometry['type'] == 'MultiPolygon' else [geometry['coordinates']]
        phone = inputs['ios']
        world_entries[region] = {'id': region, 'title': 'US National Parks · ' + p['label'], 'version': VERSION,
                                 'url': phone['url'], 'sha256': phone['sha256'], 'bytes': phone['bytes'],
                                 'bounds': p['bounds'], 'coveragePolygons': polygons}

    collections = {}
    for platform, label in PLATFORMS.items():
        zipped = output / f'OpenBareMap-US-National-Parks-{label}.zip'
        temporary = zipped.with_suffix('.zip.part')
        archive_tree(archive_inputs / platform, temporary)
        temporary.replace(zipped)
        collections[platform] = asset(zipped, PREFIX + zipped.name)

    prepared = {'regions': entries, 'downloads': collections, 'assets': list(uploads.values())}
    write(output / 'app-bundles-catalog.json', base_catalog)
    preview_catalog = json.loads((ROOT / 'config/preview-regions.json').read_text())
    preview_entries = {record['id']: record for record in preview_catalog}
    preview_entries.update({region: {'id': region, 'label': profile(region)['label'], 'url': preview_url(region)}
                            for region in US_PARK_REGIONS})
    write(output / 'preview-regions.json', list(preview_entries.values()))
    worldwide_catalog = {**old_worldwide, 'regions': list(world_entries.values())}
    path = output / 'worldwide-catalog-v1.json'
    path.write_text(json.dumps(worldwide_catalog, separators=(',', ':'), ensure_ascii=False) + '\n')
    if path.stat().st_size > 5_000_000:
        raise ValueError('The Worldwide app catalogue exceeds its 5 MB limit')
    homepage = output / 'index.html'
    homepage.write_text(stage_homepage(website, entries, collections, len(base_catalog['regions'])))
    stage_website_archive(website, homepage, output / 'appsbyonzy-us-national-parks.zip')
    write(output / 'release-plan.json', prepared)
    print(f'Prepared nine maps and all-platform downloads under {output.relative_to(ROOT)}.', flush=True)


def transfer_asset(item, verified):
    key = item['key']
    path = checked(ROOT / item['path'], item['sha256'])
    catalogue = key in (APP_CATALOGUE, WORLDWIDE_CATALOGUE)
    if not catalogue and verified.get(key, {}).get('sha256') == item['sha256']:
        return key, verified[key]
    print(f'Publishing {key}', flush=True)
    options = ['--checksum']
    if catalogue:
        options = ['--ignore-times', '--metadata', '--metadata-set', 'content-type=application/json',
                   '--metadata-set', 'cache-control=' + CATALOGUE_CACHE_POLICY, '--s3-no-system-metadata=false']
    run('rclone', 'copyto', path, REMOTE + key, *options, '--s3-no-check-bucket')
    public_url = PUBLIC + quote(key) + ('?sha256=' + item['sha256'] if catalogue else '')
    size, sha, _ = read_hash(public_url)
    if (size, sha) != (item['bytes'], item['sha256']):
        raise ValueError(f'Public readback differs: {key}')
    return key, {'bytes': size, 'sha256': sha, 'verifiedUTC': datetime.now(timezone.utc).isoformat()}


def record_receipt(verified, receipts, key, receipt):
    verified[key] = receipt
    temporary = receipts.with_suffix('.json.part')
    write(temporary, verified)
    temporary.replace(receipts)



def upload_release_assets(output, upload_workers=4):
    plan = json.loads((output / 'release-plan.json').read_text())
    receipts = output / 'public-verification.json'
    verified = json.loads(receipts.read_text()) if receipts.exists() else {}
    verified_assets = sum(verified.get(item['key'], {}).get('sha256') == item['sha256'] for item in plan['assets'])
    print(f'Starting publication with {verified_assets}/{len(plan["assets"])} assets already verified.', flush=True)
    with ThreadPoolExecutor(max_workers=upload_workers) as pool:
        failures = []
        transfers = {pool.submit(transfer_asset, item, verified): item['key'] for item in plan['assets']}
        for pending in as_completed(transfers):
            try:
                result = pending.result()
            except (OSError, ValueError, HTTPException, subprocess.CalledProcessError) as error:
                print(f'Publication failed for {transfers[pending]}: {error}', file=sys.stderr, flush=True)
                failures.append(error)
            else:
                record_receipt(verified, receipts, *result)
        if failures:
            raise RuntimeError(f'{len(failures)} map assets failed publication or readback') from failures[0]

    return plan, verified


def publish(output, website, *, regions=US_PARK_REGIONS, render_homepage=stage_homepage, preview_manifests=None,
            upload_workers=4):
    if preview_manifests is None:
        preview_manifests = {'preview/manifest.json': 'us-national-parks-manifest.json'}
    plan, verified = upload_release_assets(output, upload_workers)
    receipts = output / 'public-verification.json'
    preview_tiles = [item for item in plan['assets'] if item['key'].endswith('.pmtiles')]
    print(f'Checking byte-range responses for {len(preview_tiles)} preview archives.', flush=True)

    def verify_range(item):
        key = item['key']
        request = Request(PUBLIC + quote(key), headers={'Range': 'bytes=0-126', 'User-Agent': 'Mozilla/5.0'})
        try:
            with urlopen(request, timeout=30) as response:
                expected_range = f'bytes 0-126/{item["bytes"]}'
                header = response.read(127)
                if (response.status != 206 or response.headers.get('Content-Range') != expected_range
                        or len(header) != 127 or not header.startswith(b'PMTiles\x03')):
                    raise ValueError(f'Public preview does not serve valid PMTiles byte ranges: {key}')
        except HTTPError as error:
            raise RuntimeError(f'Cloudflare returned HTTP {error.code} for the preview byte-range check: {key}') from error

    with ThreadPoolExecutor(max_workers=min(6, upload_workers)) as pool:
        list(pool.map(verify_range, preview_tiles))

    for filename, key in [('app-bundles-catalog.json', APP_CATALOGUE),
                          ('worldwide-catalog-v1.json', WORLDWIDE_CATALOGUE)]:
        path = output / filename
        staged = json.loads(path.read_text())
        request = Request(PUBLIC + key, headers={'Cache-Control': 'no-cache', 'User-Agent': 'Mozilla/5.0'})
        with urlopen(request, timeout=30) as response:
            live = json.load(response)
        if isinstance(staged['regions'], list):
            entries = {entry['id']: entry for entry in live['regions']}
            entries.update({entry['id']: entry for entry in staged['regions'] if entry['id'] in regions})
            live['regions'] = list(entries.values())
        else:
            live['regions'].update({region: staged['regions'][region] for region in regions})
            live['mapVersions'].update({region: staged['mapVersions'][region] for region in regions})
        if isinstance(live['regions'], list):
            data = json.dumps(live, separators=(',', ':'), ensure_ascii=False) + '\n'
            if len(data.encode()) > 5_000_000:
                raise ValueError('The merged Worldwide app catalogue exceeds its 5 MB limit')
            path.write_text(data)
        else:
            write(path, live)
        record_receipt(verified, receipts, *transfer_asset({'key': key, 'path': str(path.relative_to(ROOT)),
                                                          'bytes': path.stat().st_size, 'sha256': digest(path)}, verified))

    shutil.copyfile(output / 'app-bundles-catalog.json', ROOT / 'distribution/app-bundles-v1/catalog.json')
    for manifest, filename in preview_manifests.items():
        shutil.copyfile(output / manifest, ROOT / 'web-preview' / filename)
    inventory_path = ROOT / 'distribution/r2-assets.json'
    inventory = json.loads(inventory_path.read_text())
    delivery = {item['path']: item for item in inventory['assets']}
    for item in plan['assets']:
        if item['key'].endswith(('.zip', '.img')):
            delivery[item['path']] = {'path': item['path'], 'bytes': item['bytes'], 'sha256': item['sha256'],
                                      'url': PUBLIC + item['key']}
    inventory['assets'] = sorted(delivery.values(), key=lambda item: item['path'])
    write(inventory_path, inventory)

    for region in regions:
        target = ROOT / 'distribution/app-bundles-v1/garmin' / region / 'manifest.json'
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(output / 'garmin-manifests' / region / 'manifest.json', target)

    shutil.copyfile(output / 'preview-regions.json', ROOT / 'config/preview-regions.json')
    # Refresh existing preview menus after all new destinations are reachable.
    navigation = output / ('navigation-' + datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S'))
    run(sys.executable, 'scripts/publish_preview_ui.py', '--output', navigation)
    website.write_text(render_homepage(website, plan['regions'], plan['downloads'], len(live['regions'])))
    stage_website_archive(website, website, output / plan.get('websiteArchive', 'appsbyonzy-us-national-parks.zip'))
    print('Public downloads and preview ranges verified. The website checkout is ready for deployment.', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'work/us-national-parks-release')
    parser.add_argument('--website', type=Path, default=ROOT / 'work/AppsByOnzy-Website/site/index.html')
    parser.add_argument('--worldwide', type=Path,
                        default=ROOT.parent / 'BareGPS-Worldwide/Distribution/worldwide-catalog-v1.json')
    parser.add_argument('--publish-assets', action='store_true', help='Upload completed maps, verify readbacks and update the online catalogues')
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT):
        parser.error('--output must be under OpenBareMap')
    if args.publish_assets:
        publish(output, args.website)
    else:
        output.mkdir(parents=True, exist_ok=True)
        stage(output, args.website, args.worldwide)


if __name__ == '__main__':
    main()
