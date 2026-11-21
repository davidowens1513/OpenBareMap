#!/usr/bin/env python3
"""Stage and publish the Picos de Europa and High Tatras editions."""

import argparse
from html import escape
import json
from pathlib import Path
import re

from shapely.geometry import mapping, shape

from openbaremap import ROOT, digest, write
from regions import profile
from stage_us_national_parks import (
    PLATFORMS, PUBLIC, add_to_archive, checked, download_row, publish, stage_website_archive,
)

REGIONS = ('picos-de-europa', 'high-tatras')
ARCHIVE = 'appsbyonzy-picos-de-europa-and-high-tatras.zip'
REPO_LINK = ('<div class="region-actions map-group-repo"><a class="map-github" '
             'href="https://github.com/davidowens1513/OpenBareMap">OpenBareMap on GitHub '
             '<span aria-hidden="true">↗</span></a></div>')


def preview_prefix(region):
    return f'OpenBareMap/{region}/{profile(region)["mapVersion"]}/preview'


def preview_url(region):
    return f'{PUBLIC}{preview_prefix(region)}/{region}/index.html'


def render_homepage(website, entries, _downloads, count):
    def card(region):
        p = profile(region)
        rows = ''.join(download_row(label, entries[region][platform]['url'],
                                    entries[region][platform]['instructionsURL'])
                       for platform, label in PLATFORMS.items())
        return (f'<article id="map-{region}"><h3>{escape(p["label"])}</h3><p>{escape(p["coverage"])}</p>'
                f'<div class="region-actions"><div class="preview-action"><a href="{preview_url(region)}">'
                f'Preview <span aria-hidden="true">↗</span></a></div>{rows}</div></article>')

    page = website.read_text()
    page = re.sub(r'<article id="map-picos-de-europa">.*?</article>', '', page, flags=re.S)
    page = re.sub(r'<!-- Eastern Europe -->.*?<!-- End Eastern Europe -->\n', '', page, flags=re.S)
    page = page.replace('  <option value="eastern-europe">Eastern Europe</option>\n', '')
    option = '  <option value="norway">Norway</option>'
    if page.count(option) != 1:
        raise ValueError('Expected one Norway option in the map-group picker')
    page = page.replace(option, option + '\n  <option value="eastern-europe">Eastern Europe</option>')
    start = page.index('<div id="france-spain"')
    end = page.index('<div id="alps"', start)
    grid_end = page.rindex('</div></div>', start, end)
    page = page[:grid_end] + card('picos-de-europa') + page[grid_end:]
    position = page.index('<div id="mediterranean-islands"')
    eastern = ('<!-- Eastern Europe -->\n<div id="eastern-europe" style="margin-top:2rem">'
               '<h3>Eastern Europe</h3>\n' + REPO_LINK + '\n<div class="map-regions">'
               + card('high-tatras') + '</div></div>\n<!-- End Eastern Europe -->\n')
    page = page[:position] + eastern + page[position:]
    page, changes = re.subn(r'Currently there are \d+ maps available', f'Currently there are {count} maps available', page, count=1)
    if changes != 1:
        raise ValueError('Missing OpenBareMap map count')
    return page


def stage(output, website, *, regions=REGIONS, render=render_homepage, archive=ARCHIVE):
    entries, assets, worldwide = {}, {}, []
    app_catalog = json.loads((ROOT / 'distribution/app-bundles-v1/catalog.json').read_text())
    previews = json.loads((ROOT / 'config/preview-regions.json').read_text())
    preview_entries = {record['id']: record for record in previews}

    def asset(path, key):
        assets[key] = {'key': key, 'path': str(path.relative_to(ROOT)),
                       'bytes': path.stat().st_size, 'sha256': digest(path)}
        return assets[key]

    for region in regions:
        p = profile(region)
        release = ROOT / 'releases' / region / p['mapVersion']
        garmin = ROOT / 'regions' / region / 'garmin'
        products = ROOT / 'work' / (region + '-release')
        validation = json.loads((release / 'validation.json').read_text())
        if validation['region'] != region or not validation['irelandPreserved']:
            raise ValueError(f'Missing completed validation for {region}')
        preview = products / 'preview'
        manifest = json.loads((preview / 'manifest.json').read_text())
        if manifest['dataOrigin'] != PUBLIC + preview_prefix(region) or set(manifest['regions']) != {region}:
            raise ValueError(f'Preview configuration differs for {region}')
        for dataset, record in manifest['regions'][region].items():
            checked(preview / 'data' / region / f'{dataset}.pmtiles', record['sha256'])
        for path in sorted(preview.rglob('*')):
            if path.is_file():
                asset(path, preview_prefix(region) + '/' + path.relative_to(preview).as_posix())
        preview_entries[region] = {'id': region, 'label': p['label'], 'url': preview_url(region)}

        mobile = json.loads((products / 'kits' / region / 'manifest.json').read_text())
        for platform, entry in mobile.items():
            source = checked(ROOT / entry['localPath'], entry['sha256'])
            release_dir = release / 'app-bundles-v1' / platform
            release_dir.mkdir(parents=True, exist_ok=True)
            add_to_archive(release_dir, source)
            path = release_dir / source.name
            entry['localPath'] = str(path.relative_to(ROOT))
            asset(path, entry['r2Key'])
            guide = checked(source.parent / 'instructions.txt', entry['instructionsSHA256'])
            key = entry['r2Key'].rsplit('/', 1)[0]
            asset(guide, entry['instructionsURL'].removeprefix(PUBLIC))
            asset(source.parent / 'SHA256SUMS.txt', key + '/SHA256SUMS.txt')
            manifest_path = release_dir / 'manifest.json'
            write(manifest_path, entry)
            asset(manifest_path, key + '/manifest.json')
        app_catalog['regions'][region] = mobile
        app_catalog['mapVersions'][region] = p['mapVersion']

        report = json.loads((garmin / 'build-report.json').read_text())['output']
        image = checked(ROOT / report['path'], report['sha256'])
        image_key = 'Garmin/' + image.name
        guide_key = f'Garmin/{region}-instructions.txt'
        image_asset = asset(image, image_key)
        guide = asset(garmin / 'dist/INSTALL.txt', guide_key)
        for name in ('ATTRIBUTION.txt', 'terrain-attribution.md', 'terrain-data-sources.md', 'boundary-source.json'):
            if name == 'boundary-source.json' and not p.get('coverageBoundary'):
                continue
            asset(garmin / 'dist' / name, f'Garmin/{region}/{name}')
        native = {'region': region, 'url': PUBLIC + image_key, 'downloadURL': PUBLIC + image_key,
                  'instructionsURL': PUBLIC + guide_key, 'instructionsSHA256': guide['sha256'],
                  'bytes': image_asset['bytes'], 'imageSHA256': image_asset['sha256'],
                  'garminPackageRevision': p['garminPackageRevision']}
        manifest_path = output / 'garmin-manifests' / region / 'manifest.json'
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        write(manifest_path, native)
        asset(manifest_path, f'Garmin/{region}/manifest.json')
        entries[region] = {**mobile, 'garmin': native}

        footprint = json.loads((garmin / 'render-coverage.geojson').read_text())['features'][0]['geometry']
        polygon = mapping(shape(footprint))
        polygons = polygon['coordinates'] if polygon['type'] == 'MultiPolygon' else [polygon['coordinates']]
        phone = mobile['ios']
        worldwide.append({'id': region, 'title': p['label'], 'version': p['mapVersion'],
                          'bounds': p['bounds'], 'coveragePolygons': polygons,
                          **{name: phone[name] for name in ('url', 'sha256', 'bytes')}})

    write(output / 'app-bundles-catalog.json', app_catalog)
    write(output / 'worldwide-catalog-v1.json', {'regions': worldwide})
    write(output / 'preview-regions.json', list(preview_entries.values()))
    write(output / 'release-plan.json', {'regions': entries, 'downloads': {}, 'assets': list(assets.values()),
                                        'websiteArchive': archive})
    homepage = output / 'index.html'
    homepage.write_text(render(website, entries, {}, len(app_catalog['regions'])))
    stage_website_archive(website, homepage, output / archive)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publish-assets', action='store_true')
    args = parser.parse_args()
    output = ROOT / 'work/picos-tatras-publication'
    website = ROOT / 'work/AppsByOnzy-Website/site/index.html'
    if args.publish_assets:
        manifests = {f'../{region}-release/preview/manifest.json': f'{region}-manifest.json' for region in REGIONS}
        publish(output, website, regions=REGIONS, render_homepage=render_homepage, preview_manifests=manifests)
    else:
        output.mkdir(parents=True, exist_ok=True)
        stage(output, website)


if __name__ == '__main__':
    main()
