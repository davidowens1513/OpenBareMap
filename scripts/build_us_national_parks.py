#!/usr/bin/env python3
"""Prepare official US park coverage and build the nine OpenBareMap editions."""

import argparse
from datetime import date
import json
import math
import subprocess
import sys
from urllib.parse import urlencode

from pyproj import Transformer
from shapely import make_valid
from shapely.geometry import LineString, Point, box, mapping, shape
from shapely.ops import nearest_points, transform, unary_union

from fetch_region import download
from openbaremap import ROOT, digest, write
from regions import US_PARK_REGIONS, profile

BOUNDARY_SERVICE = (
    'https://services1.arcgis.com/fBc8EJBxQRMcHlei/arcgis/rest/services/'
    'NPS_Land_Resources_Division_Boundary_and_Tract_Data_Service/FeatureServer/2'
)
GEOFABRIK_US = 'https://download.geofabrik.de/north-america/us/'
BOUNDARY_ATTRIBUTION = 'U.S. National Park Service, Land Resources Division'
BOUNDARY_SHA256 = '2b8108bca8b219c25f2d7faa5f1e7e1d33df29b8faef218167f8ae2281a2177e'


def park_features(raw, codes):
    data = json.loads(raw.read_text())
    if data.get('exceededTransferLimit') or data.get('type') != 'FeatureCollection':
        raise ValueError(f'Incomplete NPS boundary response for {", ".join(codes)}')
    parks = {}
    for feature in data['features']:
        code = feature['properties']['UNIT_CODE']
        if code in codes and feature['geometry']:
            parks.setdefault(code, []).append(make_valid(shape(feature['geometry'])))
    if set(parks) != set(codes):
        raise ValueError(f'Missing NPS boundaries for {sorted(set(codes) - parks.keys())}')
    return {code: unary_union(parks[code]) for code in codes}


def prepare(region, spec, identity, source_date, raw, source):
    directory = ROOT / 'regions' / region
    directory.mkdir(parents=True, exist_ok=True)
    profile_path = directory / 'region.json'
    if profile_path.exists():
        existing = profile(region)
        if existing['sourceDate'] != source_date:
            raise ValueError(f'{region} is already pinned to {existing["sourceDate"]}')
        record = json.loads((directory / 'boundary-source.json').read_text())
        if record['source'] != source:
            raise ValueError(f'{region} boundary source changed')
        for filename, sha in record['outputs'].items():
            if digest(directory / filename) != sha:
                raise ValueError(f'{region} boundary file changed: {filename}')
        return

    codes = spec['parks'] + spec.get('connectorParks', [])
    parks = park_features(raw, codes)
    epsg = 32600 + spec['zone']
    project = Transformer.from_crs(4326, epsg, always_xy=True).transform
    unproject = Transformer.from_crs(epsg, 4326, always_xy=True).transform
    official = unary_union(list(parks.values()))
    park_m = transform(project, official)
    included = [park_m.buffer(spec['bufferKm'] * 1000)]
    anchors = spec['destinations']

    for approach in spec.get('approaches', []):
        checkpoints = [Point(project(*((anchors[point] if isinstance(point, str) else point)[:2]))) for point in approach]
        park_end = nearest_points(checkpoints[-1], park_m)[1]
        included.append(LineString([*checkpoints, park_end]).buffer(5000))
    coverage = transform(unproject, unary_union(included).simplify(15, preserve_topology=True))
    if spec.get('limitContextAtParkNorth'):
        coverage = coverage.intersection(box(-180, -85, 180, official.bounds[3] + 0.001))
    coverage = unary_union([coverage, official])
    if coverage.geom_type not in ('Polygon', 'MultiPolygon') or not coverage.is_valid:
        raise ValueError(f'{region} produced invalid coverage')
    for name, xy in anchors.items():
        if not coverage.covers(Point(*xy[:2])):
            raise ValueError(f'{region} coverage excludes {name}')

    names = {item['properties']['UNIT_CODE']: item['properties']['UNIT_NAME']
             for item in json.loads(raw.read_text())['features']}
    features = [
        {'type': 'Feature', 'properties': {'name': names[code], 'unitCode': code},
         'geometry': mapping(parks[code])}
        for code in spec['parks']
    ]

    def feature_collection(geometry, name):
        return {'type': 'FeatureCollection', 'features': [
            {'type': 'Feature', 'properties': {'name': name}, 'geometry': mapping(geometry)}
        ]}

    files = {
        'park-boundary.geojson': {'type': 'FeatureCollection', 'features': features},
        'coverage.geojson': feature_collection(coverage, 'OpenBareMap coverage limit'),
        'coverage-mask.geojson': feature_collection(box(-180, -85, 180, 85).difference(coverage), 'Outside map coverage'),
    }
    for filename, content in files.items():
        write(directory / filename, content)
    write(directory / 'boundary-source.json', {
        'source': source,
        'parkUnitCodes': spec['parks'],
        'approachUnitCodes': spec.get('connectorParks', []),
        'attribution': BOUNDARY_ATTRIBUTION,
        'bufferMetres': spec['bufferKm'] * 1000,
        'bufferCRS': f'EPSG:{epsg}',
        'areaKm2': round(transform(project, coverage).area / 1e6, 2),
        'outputs': {filename: digest(directory / filename) for filename in files},
    })

    bounds = list(coverage.bounds)
    west, south, east, north = bounds
    terrain = [math.floor(west), math.floor(south), math.ceil(east), math.ceil(north)]
    w, s, e, n = transform(project, coverage).bounds
    grid = [math.floor(w / 10000) * 10000, math.ceil(e / 10000) * 10000,
            math.floor(s / 10000) * 10000, math.ceil(n / 10000) * 10000]
    centre = coverage.representative_point()
    title = '-'.join(part.title() for part in region.removeprefix('us-').split('-'))
    terrain_notice = profile('alps-west')['terrainNotice'].removeprefix('Alps - West ')
    labels = {key: key.replace('-', ' ').title() for key in anchors}
    validation_anchors = {name: value[:2] for name, value in anchors.items()}
    overview_anchors = spec.get('overviewLandAnchorOverrides', {})
    write(profile_path, {
        'id': region, 'label': spec['label'], 'name': 'OpenBareMap ' + spec['label'],
        'mapVersion': '2.0.0', 'minzoom': 4, 'maxzoom': 14, 'townlands': False,
        'contourIntervalMetres': 20, 'minorWaterwayMinzoom': 10, 'coverage': spec['coverage'],
        'bounds': bounds, 'terrainBounds': terrain,
        'coastContextBounds': [terrain[0]-1, terrain[1]-1, terrain[2]+1, terrain[3]+1],
        **({'repairClippedCoastline': True} if spec.get('repairClippedCoastline') else {}),
        'garminContextBounds': bounds, 'garminUseSourceOutline': True,
        'projectedCRS': f'EPSG:{epsg}', 'gridCRS': f'EPSG:{epsg}', 'gridName': f'WGS 84 / UTM {spec["zone"]}N',
        'gridSource': 'utm-grid', 'gridExtent': grid,
        'sourceDate': source_date, 'sourceSlugs': spec['states'], 'sourceBaseURL': GEOFABRIK_US,
        'sourceBaseOverrides': {state: GEOFABRIK_US + state + '/' for state in spec['states']},
        'sourceCacheRegion': 'us-national-parks', 'nativeLanguage': 'en',
        'clipSource': True, 'clipBasemap': True, 'ignoreSourceHeaderBounds': True,
        'coverageBoundary': True, 'boundaryAttribution': BOUNDARY_ATTRIBUTION,
        'coverageBoundaryLabel': 'Map coverage limit',
        'requireBogFeatures': False, 'inspectionNames': spec['inspectionNames'],
        'optionalBasemapLayers': ['station', 'railway', 'ferry', 'cycling_route', 'island_name', 'boundary', 'hiking_route'],
        'garminFamilyId': identity['familyId'], 'garminTileStartId': identity['tileStartId'],
        'garminFilename': f'OpenBareMap-US-{title}.img', 'garminPackageRevision': '2.0.1-trail-detail-r1',
        'styleRevision': f'2.0.0-{region}-r1',
        'terrainProvider': 'copernicus-glo30', 'terrainCacheRegion': 'us-national-parks',
        'terrainAttribution': profile('alps-west')['terrainAttribution'],
        'terrainNotice': terrain_notice[0].upper() + terrain_notice[1:],
        'labelGlyphs': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
        'destinations': {'island': [centre.x, centre.y, 9], **anchors},
        'destinationLabels': {'island': spec['label'], **labels},
        'validationAnchors': validation_anchors,
        **({'overviewLandAnchors': {**validation_anchors, **overview_anchors}} if overview_anchors else {}),
    })
    print(f'{spec["label"]} park boundaries and source configuration verified.', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-date', required=True, type=date.fromisoformat,
                        help='Date of the immutable Geofabrik state extracts, YYYY-MM-DD')
    parser.add_argument('--regions', nargs='+', choices=US_PARK_REGIONS, default=US_PARK_REGIONS)
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    specs = json.loads((ROOT / 'config/us-national-parks.json').read_text())
    identities = json.loads((ROOT / 'garmin/map-identities.json').read_text())
    parks = dict.fromkeys(code for spec in specs.values() for code in spec['parks'] + spec.get('connectorParks', []))
    url = BOUNDARY_SERVICE + '/query?' + urlencode({
        'where': 'UNIT_CODE IN (' + ','.join(f"'{code}'" for code in parks) + ')',
        'outFields': 'UNIT_CODE,UNIT_NAME',
        'outSR': 4326,
        'geometryPrecision': 6,
        'maxAllowableOffset': '0.00005',
        'f': 'geojson',
    })
    raw = ROOT / 'regions/us-national-parks/nps-boundaries.geojson'
    if digest(raw) != BOUNDARY_SHA256:
        raise ValueError('The pinned National Park Service boundaries changed')
    source = download(url, raw)
    for region in dict.fromkeys(args.regions):
        prepare(region, specs[region], identities[region], args.source_date.isoformat(), raw, source)
    if args.prepare_only:
        return
    for region in dict.fromkeys(args.regions):
        subprocess.run([sys.executable, 'scripts/run_full_region.py', '--region', region], cwd=ROOT, check=True)


if __name__ == '__main__':
    main()
