#!/usr/bin/env python3
"""Stage or publish the eight-map November 2026 OpenBareMap release."""

import argparse
from html import escape
import json
from pathlib import Path
import re
import shutil

from shapely.geometry import shape

from openbaremap import ROOT
from regions import EIGHT_MAP_RELEASE_REGIONS, profile
from stage_mountain_editions import PUBLIC, REPO_LINK, download_row, publish, stage, stage_website_archive
from stage_worldwide_trekking import merge_worldwide_catalogue


OUTPUT = ROOT / 'work/eight-map-publication'
ARCHIVE = 'appsbyonzy-eight-map-release.zip'
COUNTRIES = {
    'gran-sasso': 'Italy',
    'northern-drakensberg': 'South Africa & Lesotho',
    'cape-peninsula': 'South Africa',
    'mount-rainier': 'USA',
    'vancouver-island-west-coast-trail': 'Canada',
    'garibaldi-whistler': 'Canada',
    'cotopaxi-quilotoa': 'Ecuador',
    'aconcagua': 'Argentina & Chile',
}
GROUPS = {
    'western-europe': ('Western Europe', ('gran-sasso',)),
    'africa': ('Africa', ('northern-drakensberg', 'cape-peninsula')),
    'north-america': ('North America', (
        'mount-rainier', 'vancouver-island-west-coast-trail', 'garibaldi-whistler',
    )),
    'south-america': ('South America', ('cotopaxi-quilotoa', 'aconcagua')),
}


def preview_url(region):
    return f'{PUBLIC}OpenBareMap/{region}/{profile(region)["mapVersion"]}/preview/{region}/index.html'


def ice_note(region):
    if not profile(region).get('permanentIce'):
        return ''
    return '<p>Glaciers are shown in blue. The map key includes a separate symbol for permanent snowfields.</p>'


def card(region, entries):
    metadata = profile(region)
    links = ''.join(
        download_row(label, entries[platform]['url'], entries[platform]['instructionsURL'])
        for platform, label in (('ios', 'iOS'), ('android', 'Android'), ('garmin', 'Garmin'))
    )
    return (
        f'<article id="map-{region}"><h3>{escape(metadata["label"])} · {escape(COUNTRIES[region])}</h3>'
        f'<p>{escape(metadata["coverage"])}</p>{ice_note(region)}'
        f'<p class="tool-subtitle">Version {metadata["mapVersion"]} · mobile build r3 / '
        f'Garmin build {metadata["garminPackageRevision"]}</p>'
        f'<div class="region-actions"><div class="preview-action"><a href="{preview_url(region)}">'
        f'Preview <span aria-hidden="true">↗</span></a> <span aria-hidden="true">|</span> '
        f'<a class="map-area-link" href="/maps/{region}/">{escape(metadata["label"])} map details</a>'
        f'</div>{links}</div></article>'
    )


def matching_div_close(page, opening):
    depth = 0
    for match in re.finditer(r'</?div\b[^>]*>', page[opening:], flags=re.I):
        if match.group().startswith('</'):
            depth -= 1
            if depth == 0:
                return opening + match.start()
        else:
            depth += 1
    raise ValueError('Unclosed map region grid')


def render_homepage(website, entries, _downloads, count):
    page = website.read_text()
    for region in EIGHT_MAP_RELEASE_REGIONS:
        page = re.sub(rf'<article id="map-{re.escape(region)}">.*?</article>', '', page, flags=re.S)
    for group, (_label, regions) in GROUPS.items():
        start = page.index(f'<div id="{group}"')
        grid_start = page.index('<div class="map-regions">', start)
        grid_end = matching_div_close(page, grid_start)
        cards = ''.join(card(region, entries[region]) for region in regions)
        page = page[:grid_end] + cards + page[grid_end:]
    for phrase in ('OpenBareMap editions from within the app', 'offline hiking maps with'):
        page, changes = re.subn(rf'\b\d+ (?={phrase})', f'{count} ', page)
        if changes != 1:
            raise ValueError(f'Expected one edition count before {phrase!r}')
    return page


def coverage_svg(region):
    geometry = shape(json.loads((ROOT / 'regions' / region / 'garmin/render-coverage.geojson').read_text())['features'][0]['geometry'])
    minimum_x, minimum_y, maximum_x, maximum_y = geometry.bounds
    width = max(maximum_x - minimum_x, 0.01)
    height = max(maximum_y - minimum_y, 0.01)
    scale = min(740 / width, 370 / height)
    offset_x = (840 - width * scale) / 2
    offset_y = (450 - height * scale) / 2

    def point(coordinate):
        x = offset_x + (coordinate[0] - minimum_x) * scale
        y = offset_y + (maximum_y - coordinate[1]) * scale
        return f'{x:.1f},{y:.1f}'

    def ring_path(ring):
        coordinates = list(ring.coords)
        return 'M' + ' L'.join(point(coordinate) for coordinate in coordinates) + 'Z'

    polygons = geometry.geoms if geometry.geom_type == 'MultiPolygon' else (geometry,)
    paths = []
    for polygon in polygons:
        paths.append(ring_path(polygon.exterior))
        paths.extend(ring_path(ring) for ring in polygon.interiors)
    label = escape(profile(region)['label'])
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 840 498" role="img">
<title>{label} map coverage</title>
<rect width="840" height="450" fill="#e7f0f2"/>
<path d="{' '.join(paths)}" fill="#55a265" fill-opacity=".42" stroke="#146b35" stroke-width="4" stroke-linejoin="round" fill-rule="evenodd"/>
<g fill="#1c3026" font-family="Arial,sans-serif" font-size="23" font-weight="700" text-anchor="middle">
<rect x="784" y="13" width="43" height="62" rx="9" fill="#fffefa" fill-opacity=".88"/>
<text x="805.5" y="39">N</text><path d="M805.5 46l-8 18 8-5 8 5z"/>
</g>
<g font-family="Arial,sans-serif" font-size="26" fill="#1c3026">
<rect y="450" width="840" height="48" fill="#fafbf7"/><path d="M0 450H840" stroke="#c8d5c6"/>
<rect x="20" y="464" width="25" height="20" rx="3" fill="#8bc693" stroke="#146b35" stroke-width="2.5"/>
<text x="57" y="483">Published map coverage</text>
</g></svg>\n'''


def format_megabytes(value):
    return f'{value / 1_000_000:,.0f} MB'


def area_page(region, entries):
    metadata = profile(region)
    label = escape(metadata['label'])
    country = escape(COUNTRIES[region])
    coverage = escape(metadata['coverage'])
    preview = preview_url(region)
    garmin = entries['garmin']
    ios = entries['ios']
    android = entries['android']
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Free offline OpenBareMap for {label}. {coverage}">
  <meta name="theme-color" content="#146b35">
  <link rel="canonical" href="https://appsbyonzy.dev/maps/{region}/">
  <link rel="stylesheet" href="../area.css">
  <title>{label} Offline Hiking Map for Garmin &amp; BareGPS | OpenBareMap</title>
</head>
<body>
  <header><div class="wrap topbar"><a class="brand" href="/"><img src="../../assets/app-icons/ireland-ios.png" width="34" height="34" alt="">Apps by Onzy</a><nav aria-label="Catalogue"><a href="/maps/">All OpenBareMap areas</a></nav></div></header>
  <main class="wrap">
    <div class="hero">
      <section aria-labelledby="page-title">
        <p class="eyebrow">OpenBareMap · {country}</p>
        <h1 id="page-title">{label} offline hiking map</h1>
        <p class="lede">Free offline topographic mapping for compatible Garmin devices and BareGPS Worldwide.</p>
        <p class="version">Version {metadata['mapVersion']} · mobile build r3 / Garmin build {metadata['garminPackageRevision']}</p>
        <div class="hero-actions"><a class="button" href="#download">Get the offline map</a><a href="{preview}">Open interactive map</a></div>
      </section>
      <section class="hero-coverage" aria-labelledby="coverage-title">
        <h2 id="coverage-title">Map coverage and detail</h2>
        <figure class="map-frame"><a href="{preview}" aria-label="Open the interactive {label} map" class="coverage-preview-link"><img src="coverage.svg" width="840" height="498" alt="Published OpenBareMap coverage for {label} · {country}"><span class="preview-prompt">Click or tap the map to open the full interactive preview</span></a><figcaption>Published mobile map footprint · © OpenStreetMap contributors</figcaption></figure>
        <p class="extra">{coverage}</p>{ice_note(region)}
      </section>
    </div>
    <section class="section" id="download" aria-labelledby="download-title">
      <h2 id="download-title">Get the offline map</h2>
      <div class="platforms">
        <article class="card"><h3>Garmin</h3><p><a href="{escape(garmin['url'], quote=True)}">Download Garmin map</a> · {format_megabytes(garmin['bytes'])} (.img)</p><ol><li>Check that your Garmin accepts custom <code>.img</code> maps.</li><li>Copy the downloaded file to the Garmin map folder specified for your device.</li><li>Safely disconnect the device, then enable the region in its map settings.</li></ol><p><a href="{escape(garmin['instructionsURL'], quote=True)}">Full Garmin installation instructions</a></p></article>
        <article class="card"><h3>BareGPS Worldwide for iPhone</h3><ol><li>Open <strong>Settings</strong> in BareGPS Worldwide.</li><li>Open <strong>OpenBareMap Downloads</strong> and select <strong>{label}</strong> · {format_megabytes(ios['bytes'])}.</li><li>Download the region in the app over Wi-Fi.</li></ol><p><a href="/#baregps-ios">Find BareGPS Worldwide</a></p></article>
      </div>
      <details class="card developers"><summary>iOS and Android bundles for app developers</summary><ul><li><a href="{escape(ios['url'], quote=True)}">Download iOS bundle</a> · {format_megabytes(ios['bytes'])} · <a href="{escape(ios['instructionsURL'], quote=True)}">iOS bundle instructions</a></li><li><a href="{escape(android['url'], quote=True)}">Download Android bundle</a> · {format_megabytes(android['bytes'])} · <a href="{escape(android['instructionsURL'], quote=True)}">Android bundle instructions</a></li></ul></details>
    </section>
  </main>
  <footer><div class="wrap"><a href="https://github.com/davidowens1513/OpenBareMap">OpenBareMap project and source</a><a href="https://www.openstreetmap.org/copyright">OpenStreetMap data and licence</a></div></footer>
</body>
</html>
'''


def update_directory(path):
    page = path.read_text()
    for group, (label, regions) in GROUPS.items():
        for region in regions:
            page = re.sub(rf'\s*<li><a href="{re.escape(region)}/">.*?</a></li>', '', page)
        pattern = re.compile(rf'(<section class="card"><h2>{re.escape(label)}</h2><ul>)(.*?)(\s*</ul></section>)', re.S)
        match = pattern.search(page)
        if not match:
            raise ValueError(f'Missing map directory group: {group}')
        links = ''.join(
            f'\n          <li><a href="{region}/">{escape(profile(region)["label"])} · {escape(COUNTRIES[region])}</a></li>'
            for region in regions
        )
        page = page[:match.start()] + match.group(1) + match.group(2) + links + match.group(3) + page[match.end():]
    path.write_text(page)


def update_sitemap(path):
    page = path.read_text()
    for region in EIGHT_MAP_RELEASE_REGIONS:
        line = f'  <url><loc>https://appsbyonzy.dev/maps/{region}/</loc></url>'
        page = page.replace(line + '\n', '')
        page = page.replace('</urlset>', line + '\n</urlset>')
    path.write_text(page)


def update_website(website, entries, homepage=None):
    site = website.parent
    if homepage:
        shutil.copyfile(homepage, website)
    for region in EIGHT_MAP_RELEASE_REGIONS:
        directory = site / 'maps' / region
        directory.mkdir(parents=True, exist_ok=True)
        (directory / 'index.html').write_text(area_page(region, entries[region]))
        (directory / 'coverage.svg').write_text(coverage_svg(region))
    update_directory(site / 'maps/index.html')
    update_sitemap(site / 'sitemap.xml')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--website', type=Path, required=True)
    parser.add_argument('--worldwide', type=Path, required=True)
    parser.add_argument('--publish-assets', action='store_true')
    args = parser.parse_args()
    manifests = {
        f'../{region}-release/preview/manifest.json': f'{region}-manifest.json'
        for region in EIGHT_MAP_RELEASE_REGIONS
    }
    if args.publish_assets:
        publish(OUTPUT, args.website, regions=EIGHT_MAP_RELEASE_REGIONS,
                render_homepage=render_homepage, preview_manifests=manifests, upload_workers=6)
        plan = json.loads((OUTPUT / 'release-plan.json').read_text())
        update_website(args.website, plan['regions'])
        shutil.copyfile(OUTPUT / 'worldwide-catalog-v1.json', args.worldwide)
    else:
        OUTPUT.mkdir(parents=True, exist_ok=True)
        stage(OUTPUT, args.website, regions=EIGHT_MAP_RELEASE_REGIONS, render=render_homepage,
              archive=ARCHIVE, version_garmin=True)
        merge_worldwide_catalogue(OUTPUT / 'worldwide-catalog-v1.json', args.worldwide,
                                  regions=EIGHT_MAP_RELEASE_REGIONS)
        plan = json.loads((OUTPUT / 'release-plan.json').read_text())
        update_website(args.website, plan['regions'], OUTPUT / 'index.html')
    stage_website_archive(args.website, args.website, OUTPUT / ARCHIVE)
    print('Eight-map release staged with catalogues, area pages and website archive.', flush=True)


if __name__ == '__main__':
    main()
