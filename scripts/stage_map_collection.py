#!/usr/bin/env python3
"""Stage and validate collection releases for the standalone OpenBareMap website."""

import argparse
from collections import Counter
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET

from shapely.geometry import shape

from detailed_coverage_maps import SPECS, coverage_svg
from openbaremap import ROOT
from package_preview_ui import grouped_options
from regions import profile
from stage_mountain_editions import PUBLIC, download_row, publish, stage, stage_website_archive
from stage_worldwide_trekking import merge_worldwide_catalogue


SITE_URL = 'https://openbaremap.com'
SITE_ROOTS = ('openbaremap', 'site')
APP_COUNT_PATTERNS = (
    r'\b\d+(?= OpenBareMap editions from within the app)',
    r'\b\d+(?= offline hiking maps with)',
)


def preview_url(region):
    return f'{PUBLIC}OpenBareMap/{region}/{profile(region)["mapVersion"]}/preview/{region}/index.html'


def ice_note(region):
    if not profile(region).get('permanentIce'):
        return ''
    return '<p>Glaciers are shown in blue. The map key includes a separate symbol for permanent snowfields.</p>'


def card(region, entries, countries):
    metadata = profile(region)
    links = ''.join(
        download_row(label, entries[platform]['url'], entries[platform]['instructionsURL'])
        for platform, label in (('ios', 'iOS'), ('android', 'Android'), ('garmin', 'Garmin'))
    )
    return (
        f'<article id="map-{region}"><h3>{escape(metadata["label"])} · {escape(countries[region])}</h3>'
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


def render_homepage(website, entries, countries, groups, count):
    page = website.read_text()
    for region in entries:
        page = re.sub(rf'<article id="map-{re.escape(region)}">.*?</article>', '', page, flags=re.S)
    for group, (_label, regions) in groups.items():
        start = page.index(f'<div id="{group}"')
        group_end = matching_div_close(page, start)
        grid_start = page.find('<div class="map-regions">', start, group_end)
        if grid_start == -1:
            raise ValueError(f'Missing map card grid: {group}')
        grid_end = matching_div_close(page, grid_start)
        cards = ''.join(card(region, entries[region], countries) for region in regions)
        page = page[:grid_end] + cards + page[grid_end:]
    return update_counts(page, count, r'(?<=Explore )\d+(?= maps with)')


def update_counts(page, count, *patterns):
    for pattern in patterns:
        page, changes = re.subn(pattern, str(count), page)
        if changes != 1:
            raise ValueError(f'Expected one edition count matching {pattern}')
    return page


def footprint_svg(region):
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


def area_page(region, entries, countries, attribution):
    metadata = profile(region)
    label = escape(metadata['label'])
    country = escape(countries[region])
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
  <link rel="canonical" href="{SITE_URL}/maps/{region}/">
  <link rel="stylesheet" href="../area.css">
  <title>{label} Offline Hiking Map for Garmin &amp; BareGPS | OpenBareMap</title>
</head>
<body>
  <header><div class="wrap topbar"><a class="brand" href="/"><img src="/assets/openbaremap.png" width="34" height="34" alt=""><span class="brand-label"><span>Apps by Onzy<span aria-hidden="true"> ↗</span></span> <span>- OpenBareMap</span></span></a><nav aria-label="Main navigation"><a href="/maps/">All maps</a> <a href="/install/">Installation help</a></nav></div></header>
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
        <figure class="map-frame"><a href="{preview}" aria-label="Open the interactive {label} map" class="coverage-preview-link"><img src="coverage.svg" width="840" height="498" alt="Published OpenBareMap coverage for {label} · {country}"><span class="preview-prompt">Open full map preview</span></a><figcaption>Published mobile map footprint · {escape(attribution)}</figcaption></figure>
        <p class="extra">{coverage}</p>{ice_note(region)}
      </section>
    </div>
    <section class="section" id="download" aria-labelledby="download-title">
      <h2 id="download-title">Get the offline map</h2>
      <div class="platforms">
        <article class="card"><h3>Garmin</h3><p><a href="{escape(garmin['url'], quote=True)}">Download Garmin map</a> · {format_megabytes(garmin['bytes'])} (.img)</p><ol><li>Check that your Garmin accepts custom <code>.img</code> maps.</li><li>Copy the downloaded file to the Garmin map folder specified for your device.</li><li>Safely disconnect the device, then enable the region in its map settings.</li></ol><p><a href="{escape(garmin['instructionsURL'], quote=True)}">Full Garmin installation instructions</a> · <a href="/install/#garmin">Garmin setup guide</a></p></article>
        <article class="card"><h3>BareGPS Worldwide for iPhone</h3><ol><li>Open <strong>Settings</strong> in BareGPS Worldwide.</li><li>Open <strong>OpenBareMap Downloads</strong> and select <strong>{label}</strong> · {format_megabytes(ios['bytes'])}.</li><li>Download the region in the app over Wi-Fi.</li></ol><p><a href="https://appsbyonzy.dev/#baregps-ios">Find BareGPS Worldwide</a> · <a href="/install/#iphone">iPhone setup guide</a></p></article>
      </div>
      <details class="card developers"><summary>iOS and Android bundles for app developers</summary><ul><li><a href="{escape(ios['url'], quote=True)}">Download iOS bundle</a> · {format_megabytes(ios['bytes'])} · <a href="{escape(ios['instructionsURL'], quote=True)}">iOS bundle instructions</a></li><li><a href="{escape(android['url'], quote=True)}">Download Android bundle</a> · {format_megabytes(android['bytes'])} · <a href="{escape(android['instructionsURL'], quote=True)}">Android bundle instructions</a></li></ul></details>
    </section>
  </main>
  <footer><div class="wrap"><a href="https://github.com/davidowens1513/OpenBareMap">OpenBareMap project and source</a><a href="https://www.openstreetmap.org/copyright">OpenStreetMap data and licence</a></div></footer>
</body>
</html>
'''


def update_directory(path, countries, groups):
    page = path.read_text()
    for group, (label, regions) in groups.items():
        for region in regions:
            page = re.sub(rf'\s*<li><a href="{re.escape(region)}/">.*?</a></li>', '', page)
        pattern = re.compile(rf'(<section class="card"><h2>{re.escape(escape(label))}</h2><ul>)(.*?)(\s*</ul></section>)', re.S)
        match = pattern.search(page)
        if not match:
            raise ValueError(f'Missing map directory group: {group}')
        links = ''.join(
            f'\n          <li><a href="{region}/">{escape(profile(region)["label"])} · {escape(countries[region])}</a></li>'
            for region in regions
        )
        page = page[:match.start()] + match.group(1) + match.group(2) + links + match.group(3) + page[match.end():]
    path.write_text(page)


def source_note(region):
    lock = ROOT / 'regions' / region / 'sources.lock.json'
    record = json.loads(lock.read_text()) if lock.exists() else {}
    notes = ['© OpenStreetMap contributors']
    ice = record.get('permanentIce')
    if ice and ice.get('attribution'):
        notes.append(ice['attribution'])
    boundary = ROOT / 'regions' / region / 'boundary-source.json'
    if boundary.exists():
        for source in json.loads(boundary.read_text()).get('sources', []):
            if source.get('attribution'):
                notes.append(source['attribution'])
    return ' · '.join(notes)


def update_sitemap(path, regions):
    tree = ET.parse(path)
    root = tree.getroot()
    namespace = root.tag.removesuffix('urlset')
    existing = {item.findtext(namespace + 'loc') for item in root}
    for region in regions:
        url = f'{SITE_URL}/maps/{region}/'
        if url not in existing:
            ET.SubElement(ET.SubElement(root, namespace + 'url'), namespace + 'loc').text = url
    if namespace:
        ET.register_namespace('', namespace[1:-1])
    ET.indent(tree, space='  ')
    tree.write(path, encoding='utf-8', xml_declaration=True)


class PageLinks(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.links = []
        self.feed(path.read_text())

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ('a', 'link', 'img', 'script'):
            self.links.append(attrs)


def require_ids(label, actual, expected):
    counts = Counter(actual)
    missing = sorted(expected - counts.keys())
    extra = sorted(counts.keys() - expected)
    duplicates = sorted(region for region, count in counts.items() if count > 1)
    if missing or extra or duplicates:
        raise ValueError(f'{label} differs: missing={missing}, extra={extra}, duplicates={duplicates}')


def validate_release(output, website):
    app = json.loads((output / 'app-bundles-catalog.json').read_text())['regions']
    worldwide_path = output / 'worldwide-catalog-v1.json'
    worldwide = json.loads(worldwide_path.read_text())
    previews = json.loads((output / 'preview-regions.json').read_text())
    plan = json.loads((output / 'release-plan.json').read_text())
    staged = plan['regions']
    expected = set(app)
    if not expected or not staged.keys() <= expected:
        raise ValueError('The app-bundle catalogue omits planned map editions')
    if worldwide_path.stat().st_size > 5_000_000:
        raise ValueError('Worldwide catalogue exceeds 5 MB')
    if worldwide.get('schemaVersion') != 1 or len(expected) > 256:
        raise ValueError('Worldwide catalogue requires schema version 1 and at most 256 editions')
    require_ids('Worldwide catalogue', (entry['id'] for entry in worldwide['regions']), expected)
    require_ids('Preview selector', (entry['id'] for entry in previews), expected)
    grouped_options(previews, None)
    site = website / 'openbaremap'
    directory = site / 'maps'
    homepage_links = PageLinks(site / 'index.html').links
    require_ids('Map cards', (link['href'].removeprefix('/maps/').rstrip('/') for link in homepage_links
                             if 'map-area-link' in link.get('class', '').split()), expected)
    directory_links = PageLinks(directory / 'index.html').links
    require_ids('Map directory', (link['href'].rstrip('/') for link in directory_links
                                 if re.fullmatch(r'[a-z0-9-]+/', link.get('href', ''))), expected)
    require_ids('Area pages', (p.parent.name for p in directory.glob('*/index.html')), expected)
    sitemap = [item.text for item in ET.parse(site / 'sitemap.xml').findall('.//{*}loc')]
    require_ids('OpenBareMap sitemap', sitemap, {
        f'{SITE_URL}/', f'{SITE_URL}/maps/', f'{SITE_URL}/install/',
        *(f'{SITE_URL}/maps/{region}/' for region in expected),
    })
    old_sitemap = ET.parse(website / 'site/sitemap.xml')
    if any(urlsplit(item.text).path.startswith('/maps') for item in old_sitemap.findall('.//{*}loc')):
        raise ValueError('Map entries still appear in the Apps by Onzy sitemap')
    preview_urls = {entry['id']: entry['url'] for entry in previews}
    asset_urls = {PUBLIC + asset['key'] for asset in plan['assets']}
    for page in [*site.rglob('*.html'), website / 'site/index.html']:
        root = site if page.is_relative_to(site) else website / 'site'
        for link in PageLinks(page).links:
            value = link.get('href') or link.get('src')
            if not value:
                continue
            url = urlsplit(value)
            if url.scheme or url.netloc or not url.path:
                continue
            target = root / url.path.lstrip('/') if url.path.startswith('/') else page.parent / url.path
            if target.is_dir():
                target /= 'index.html'
            if not target.is_file():
                raise ValueError(f'{page.relative_to(website)}: missing local link {value}')
    for region in sorted(expected):
        path = directory / region
        links = PageLinks(path / 'index.html').links
        canonical = [link['href'] for link in links if link.get('rel') == 'canonical']
        if canonical != [f'{SITE_URL}/maps/{region}/']:
            raise ValueError(f'{region}: wrong canonical URL')
        if not (path / 'coverage.svg').is_file():
            raise ValueError(f'{region}: coverage.svg is missing')
        if region not in staged:
            continue
        hrefs = {link.get('href') for link in links}
        required = {preview_urls[region]}
        for platform in ('ios', 'android', 'garmin'):
            required.update(staged[region][platform][field] for field in ('url', 'instructionsURL'))
        if not required <= asset_urls:
            raise ValueError(f'{region}: release plan omits download or preview assets')
        if not required <= hrefs:
            raise ValueError(f'{region}: area page omits release download or preview links')
    return len(expected)


def stage_websites(output, website, entries, countries, groups, count):
    with TemporaryDirectory(prefix='website-', dir=output) as directory:
        prepared = Path(directory)
        # Use tracked files so Finder duplicates and unrelated local files cannot enter either ZIP.
        tracked = subprocess.check_output(['git', '-C', str(website), 'ls-files', '-z', '--', *SITE_ROOTS])
        for name in tracked.split(b'\0'):
            if name:
                relative = Path(name.decode())
                source = website / relative
                target = prepared / relative
                if source.is_symlink() or not source.is_file():
                    raise ValueError(f'Missing or unsupported website source: {source}')
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)

        standalone = prepared / 'openbaremap'
        homepage = standalone / 'index.html'
        apps = prepared / 'site/index.html'
        homepage.write_text(render_homepage(homepage, entries, countries, groups, count))
        apps.write_text(update_counts(apps.read_text(), count, *APP_COUNT_PATTERNS))
        maps = standalone / 'maps'
        changed = [homepage, apps, maps / 'index.html', standalone / 'sitemap.xml']
        for region, downloads in entries.items():
            destination = maps / region
            destination.mkdir(parents=True, exist_ok=True)
            page = destination / 'index.html'
            page.write_text(area_page(region, downloads, countries, source_note(region)))
            coverage = destination / 'coverage.svg'
            if not coverage.exists():
                render_coverage = coverage_svg if region in SPECS else footprint_svg
                coverage.write_text(render_coverage(region))
            changed += [page, coverage]
        update_directory(maps / 'index.html', countries, groups)
        update_sitemap(standalone / 'sitemap.xml', entries)
        validate_release(output, prepared)
        archives = [('openbaremap', 'openbaremap-pages.zip'), ('site', 'appsbyonzy-pages.zip')]
        for root, name in archives:
            index = prepared / root / 'index.html'
            stage_website_archive(index, index, prepared / name)
        for _, name in archives:
            (prepared / name).replace(output / name)
        for path in changed:
            target = website / path.relative_to(prepared)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)


def collection_cli(description, output, regions, countries, groups):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('--website-repo', type=Path, required=True,
                        help='AppsByOnzy-Website checkout containing openbaremap/ and site/')
    parser.add_argument('--worldwide', type=Path, required=True)
    parser.add_argument('--publish-assets', action='store_true')
    args = parser.parse_args()
    website = args.website_repo.resolve()
    if not args.worldwide.is_file():
        parser.error('--worldwide must be the existing BareGPS Worldwide distribution catalogue')
    if not all((website / root / 'index.html').is_file() for root in SITE_ROOTS):
        parser.error('--website-repo must contain openbaremap/index.html and site/index.html')

    def prepare(plan, count):
        stage_websites(output, website, plan['regions'], countries, groups, count)

    if args.publish_assets:
        manifests = {f'../{region}-release/preview/manifest.json': f'{region}-manifest.json'
                     for region in regions}
        publish(output, None, regions=regions, render_homepage=None, prepare_release=prepare,
                preview_manifests=manifests, upload_workers=6)
    else:
        output.mkdir(parents=True, exist_ok=True)
        stage(output, None, regions=regions, render=None, version_garmin=True)
        merge_worldwide_catalogue(output / 'worldwide-catalog-v1.json', args.worldwide, regions=regions)
        plan = json.loads((output / 'release-plan.json').read_text())
        count = len(json.loads((output / 'app-bundles-catalog.json').read_text())['regions'])
        prepare(plan, count)
    shutil.copyfile(output / 'worldwide-catalog-v1.json', args.worldwide)
    print(f'Verified Pages archives: {output / "openbaremap-pages.zip"} and {output / "appsbyonzy-pages.zip"}')
