#!/usr/bin/env python3
"""Stage or publish the nine-map 27 November 2026 OpenBareMap release."""

import argparse
from html import escape
import json
from pathlib import Path
import shutil

from shapely.geometry import shape

from openbaremap import ROOT
from regions import NINE_MAP_RELEASE_REGIONS, profile
import stage_eight_map_release as base
from stage_mountain_editions import publish, stage, stage_website_archive
from stage_worldwide_trekking import merge_worldwide_catalogue


OUTPUT = ROOT / 'work/nine-map-publication'
ARCHIVE = 'appsbyonzy-nine-map-release.zip'
COUNTRIES = {
    'north-cascades': 'USA',
    'white-mountains': 'USA',
    'san-juan-mountains': 'USA',
    'aoraki-mount-cook-westland': 'New Zealand',
    'upper-svaneti': 'Georgia',
    'jordan-trail-dana-petra-wadi-rum': 'Jordan',
    'cordillera-blanca': 'Peru',
    'cordillera-huayhuash': 'Peru',
    'cerro-castillo': 'Chile',
}
GROUPS = {
    'north-america': ('North America', (
        'north-cascades', 'white-mountains', 'san-juan-mountains',
    )),
    'oceania': ('Oceania', ('aoraki-mount-cook-westland',)),
    'eastern-europe': ('Eastern Europe', ('upper-svaneti',)),
    'asia': ('Asia', ('jordan-trail-dana-petra-wadi-rum',)),
    'south-america': ('South America', (
        'cordillera-blanca', 'cordillera-huayhuash', 'cerro-castillo',
    )),
}


base.EIGHT_MAP_RELEASE_REGIONS = NINE_MAP_RELEASE_REGIONS
base.OUTPUT = OUTPUT
base.ARCHIVE = ARCHIVE
base.COUNTRIES = COUNTRIES
base.GROUPS = GROUPS


def source_note(region):
    lock = ROOT / 'regions' / region / 'sources.lock.json'
    if not lock.exists():
        return ''
    record = json.loads(lock.read_text())
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


def coverage_svg(region):
    document = base.coverage_svg_original(region)
    if region != 'jordan-trail-dana-petra-wadi-rum':
        return document
    coverage = shape(json.loads(
        (ROOT / 'regions' / region / 'garmin/render-coverage.geojson').read_text()
    )['features'][0]['geometry'])
    route_document = json.loads((ROOT / 'regions' / region / 'jordan-trail-route.geojson').read_text())
    routes = [shape(feature['geometry']) for feature in route_document['features']]
    minimum_x, minimum_y, maximum_x, maximum_y = coverage.bounds
    width = max(maximum_x - minimum_x, 0.01)
    height = max(maximum_y - minimum_y, 0.01)
    scale = min(740 / width, 370 / height)
    offset_x = (840 - width * scale) / 2
    offset_y = (450 - height * scale) / 2

    def point(coordinate):
        x = offset_x + (coordinate[0] - minimum_x) * scale
        y = offset_y + (maximum_y - coordinate[1]) * scale
        return f'{x:.1f},{y:.1f}'

    parts = []
    for route in routes:
        lines = route.geoms if route.geom_type == 'MultiLineString' else (route,)
        parts.extend('M' + ' L'.join(point(coordinate) for coordinate in line.coords) for line in lines)
    overlay = (
        f'<path d="{" ".join(parts)}" fill="none" stroke="#7337a8" stroke-width="5" '
        'stroke-linecap="round" stroke-linejoin="round"/>'
    )
    document = document.replace('<g fill="#1c3026"', overlay + '\n<g fill="#1c3026"', 1)
    document = document.replace(
        '<text x="57" y="483">Published map coverage</text>',
        '<text x="57" y="483">Published map coverage</text>'
        '<path d="M335 474H375" stroke="#7337a8" stroke-width="5" stroke-linecap="round"/>'
        '<text x="388" y="483">Jordan Trail</text>',
    )
    return document


base.coverage_svg_original = base.coverage_svg
base.coverage_svg = coverage_svg


def area_page(region, entries):
    page = base.area_page_original(region, entries)
    return page.replace(
        'Published mobile map footprint · © OpenStreetMap contributors',
        'Published mobile map footprint · ' + escape(source_note(region)),
    )


base.area_page_original = base.area_page
base.area_page = area_page


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--website', type=Path, required=True)
    parser.add_argument('--worldwide', type=Path, required=True)
    parser.add_argument('--publish-assets', action='store_true')
    args = parser.parse_args()
    manifests = {
        f'../{region}-release/preview/manifest.json': f'{region}-manifest.json'
        for region in NINE_MAP_RELEASE_REGIONS
    }
    if args.publish_assets:
        publish(OUTPUT, args.website, regions=NINE_MAP_RELEASE_REGIONS,
                render_homepage=base.render_homepage, preview_manifests=manifests,
                upload_workers=6)
        plan = json.loads((OUTPUT / 'release-plan.json').read_text())
        base.update_website(args.website, plan['regions'])
        shutil.copyfile(OUTPUT / 'worldwide-catalog-v1.json', args.worldwide)
    else:
        OUTPUT.mkdir(parents=True, exist_ok=True)
        stage(OUTPUT, args.website, regions=NINE_MAP_RELEASE_REGIONS,
              render=base.render_homepage, archive=ARCHIVE, version_garmin=True)
        merge_worldwide_catalogue(OUTPUT / 'worldwide-catalog-v1.json', args.worldwide,
                                  regions=NINE_MAP_RELEASE_REGIONS)
        plan = json.loads((OUTPUT / 'release-plan.json').read_text())
        base.update_website(args.website, plan['regions'], OUTPUT / 'index.html')
    stage_website_archive(args.website, args.website, OUTPUT / ARCHIVE)
    print('Nine-map release staged with catalogues, area pages and website archive.', flush=True)


if __name__ == '__main__':
    main()
