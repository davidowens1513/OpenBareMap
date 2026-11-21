#!/usr/bin/env python3
"""Prepare park-shaped footprints and shared terrain sources for the Canadian Rockies."""

from concurrent.futures import ThreadPoolExecutor
import json
import math
from urllib.parse import urlencode

from pyproj import Transformer
from shapely import make_valid, transform
from shapely.geometry import LineString, Point, box, mapping, shape
from shapely.ops import unary_union

from fetch_copernicus import BASE as COPERNICUS
from fetch_region import download
from openbaremap import ROOT, digest, write
from regions import profile

CANADA = 'https://download.geofabrik.de/north-america/canada/'
CACHE = ROOT / 'data/regions/canadian-rockies'
FEDERAL = ('https://services2.arcgis.com/wCOMu5IS7YdSyPNx/arcgis/rest/services/'
           'vw_Places_Public_lieux_public_APCA/FeatureServer/0/query')
ALBERTA = ('https://geospatial.alberta.ca/titan/rest/services/boundary/'
           'parks_protected_areas_alberta/FeatureServer/0/query')
BC = 'https://openmaps.gov.bc.ca/geo/pub/WHSE_TANTALIS.TA_PARK_ECORES_PA_SVW/ows'
CRS = 'EPSG:32611'
ATTRIBUTION = 'Parks Canada · Government of Alberta · Province of British Columbia'
PARKWAY = [(-116.7479, 51.9760), (-116.787, 52.015), (-117.051, 52.111),
           (-117.123, 52.167), (-117.2217, 52.2212)]


def park_sources():
    federal = {name: name + ' National Park of Canada'
               for name in ('Banff', 'Jasper', 'Yoho', 'Kootenay', 'Waterton Lakes')}
    alberta = {name: name for name in ('Spray Valley', 'Peter Lougheed', 'Elbow-Sheep Wildland',
                                       'Don Getty Wildland', 'Castle', 'Castle Wildland')}
    bc = {name: name.upper() + ' PARK' for name in ('Mount Robson', 'Mount Assiniboine',
                                                   'Hamber', 'Elk Lakes', 'Akamina-Kishinena')}
    parks, records = {}, []
    for source, endpoint, field, names in (
        ('parks-canada', FEDERAL, 'DESC_EN', federal),
        ('alberta-parks', ALBERTA, 'NAME', alberta),
        ('bc-parks', BC, 'PROTECTED_LANDS_NAME', bc),
    ):
        values = ','.join(f"'{value}'" for value in names.values())
        expression = f'{field} IN ({values})'
        if source == 'bc-parks':
            params = {'service': 'WFS', 'version': '2.0.0', 'request': 'GetFeature',
                      'typeNames': 'pub:WHSE_TANTALIS.TA_PARK_ECORES_PA_SVW',
                      'outputFormat': 'application/json', 'srsName': 'EPSG:4326', 'CQL_FILTER': expression}
        else:
            params = {'where': expression, 'outFields': field, 'outSR': 4326, 'f': 'geojson'}
            if source == 'alberta-parks':
                params['where'] += " AND STATUS = 'OC'"
        filename = CACHE / f'{source}-boundaries.geojson'
        records.append(download(endpoint + '?' + urlencode(params), filename))
        data = json.loads(filename.read_text())
        if data.get('type') != 'FeatureCollection' or data.get('exceededTransferLimit'):
            raise ValueError(f'Incomplete boundary response from {source}')
        for name, value in names.items():
            features = [make_valid(shape(f['geometry'])) for f in data['features']
                        if f['geometry'] and f['properties'][field] == value]
            if not features:
                raise ValueError(f'{source} did not return {value}')
            parks[name] = unary_union(features)
    return parks, records


def collection(features):
    return {'type': 'FeatureCollection', 'features': [
        {'type': 'Feature', 'properties': {'name': name}, 'geometry': mapping(geometry)}
        for name, geometry in features
    ]}


def prepare(region, spec, parks, records, identity):
    directory = ROOT / 'regions' / region
    directory.mkdir(parents=True, exist_ok=True)
    project = Transformer.from_crs(4326, CRS, always_xy=True).transform
    unproject = Transformer.from_crs(CRS, 4326, always_xy=True).transform
    shapes = {name: transform(parks[name], project, interleaved=False).simplify(12, preserve_topology=True)
              for name in spec['parks']}
    anchors = spec['anchors']
    parts = [unary_union(list(shapes.values())).buffer(spec['bufferKm'] * 1000)]
    parts += [Point(project(*xy)).buffer(6000) for xy in anchors.values()]
    for approach in spec['approaches']:
        parts.append(LineString([project(*(anchors[point] if isinstance(point, str) else point))
                                 for point in approach]).buffer(6000))
    if spec.get('sharedParkway'):
        parts.append(LineString([project(*point) for point in PARKWAY]).buffer(9500))
    coverage = transform(unary_union(parts).simplify(20, preserve_topology=True), unproject, interleaved=False)
    park_shapes = {name: transform(geometry, unproject, interleaved=False) for name, geometry in shapes.items()}
    if 'southLimit' in spec:
        limit = box(-180, spec['southLimit'], 180, 85)
        coverage = coverage.intersection(limit)
        park_shapes = {name: geometry.intersection(limit) for name, geometry in park_shapes.items()}
    coverage = unary_union([coverage, *park_shapes.values()])
    if coverage.geom_type not in ('Polygon', 'MultiPolygon') or not coverage.is_valid:
        raise ValueError(f'Invalid coverage for {region}')
    if any(not coverage.covers(Point(*xy)) for xy in anchors.values()):
        raise ValueError(f'Missing destination in {region}')
    geometries = {
        'park-boundary.geojson': collection(park_shapes.items()),
        'coverage.geojson': collection([('Map coverage limit', coverage)]),
        'coverage-mask.geojson': collection([('Outside map coverage', box(-180, -85, 180, 85).difference(coverage))]),
    }
    for filename, content in geometries.items():
        write(directory / filename, content)
    projected_coverage = transform(coverage, project, interleaved=False)
    area = round(projected_coverage.area / 1e6, 1)
    write(directory / 'boundary-source.json', {'sources': records, 'attribution': ATTRIBUTION,
          'parks': spec['parks'], 'bufferMetres': spec['bufferKm'] * 1000, 'bufferCRS': CRS, 'areaKm2': area,
          'outputs': {name: digest(directory / name) for name in geometries}})
    w, s, e, n = coverage.bounds
    terrain = [math.floor(w), math.floor(s), math.ceil(e), math.ceil(n)]
    x1, y1, x2, y2 = projected_coverage.bounds
    grid = [math.floor(x1 / 10000) * 10000, math.ceil(x2 / 10000) * 10000,
            math.floor(y1 / 10000) * 10000, math.ceil(y2 / 10000) * 10000]
    template = profile('high-tatras')
    label = spec['label']
    centre = coverage.representative_point()
    locations = {rekey(name): [*xy, 12] for name, xy in anchors.items()}
    write(directory / 'region.json', {
        **template, 'id': region, 'label': label, 'name': f'OpenBareMap {label}', 'coverage': spec['coverage'],
        'bounds': list(coverage.bounds), 'terrainBounds': terrain,
        'coastContextBounds': [terrain[0]-1, terrain[1]-1, terrain[2]+1, terrain[3]+1],
        'projectedCRS': CRS, 'gridCRS': CRS, 'gridName': 'WGS 84 / UTM 11N', 'gridExtent': grid,
        'sourceDate': '2026-11-20', 'sourceSlugs': ['alberta', 'british-columbia'], 'sourceBaseURL': CANADA,
        'sourceBaseOverrides': {slug: CANADA + slug + '/' for slug in ('alberta', 'british-columbia')},
        'sourceCacheRegion': 'canadian-rockies', 'terrainCacheRegion': 'canadian-rockies',
        'nativeLanguage': 'en', 'labelGlyphs': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'clipTerrainToBounds': True,
        'coverageBoundary': True, 'boundaryAttribution': ATTRIBUTION, 'coverageBoundaryLabel': 'Map coverage limit',
        'permanentIce': True,
        'garminFamilyId': identity['familyId'], 'garminTileStartId': identity['tileStartId'],
        'garminContextBounds': list(coverage.bounds), 'garminFilename': f'OpenBareMap-{region.title()}.img',
        'styleRevision': f'2.0.0-{region}-r1', 'inspectionNames': spec['inspectionNames'],
        'terrainNotice': template['terrainNotice'].replace('High Tatras', label),
        'destinations': {'island': [centre.x, centre.y, 8], **locations},
        'destinationLabels': {'island': label, **{rekey(name): name for name in anchors}},
        'validationAnchors': {key: value[:2] for key, value in locations.items()},
    })
    print(f'{label}: {area:,.0f} km²; {len(anchors)} destinations within the footprint', flush=True)
    return coverage, terrain


def rekey(name):
    return name.lower().replace(' ', '-')


def prefetch_terrain(bounds):
    cache = CACHE / 'copernicus'
    index = download(COPERNICUS + 'tileList.txt', cache / 'tileList.txt')
    available = set((ROOT / index['path']).read_text().splitlines())
    cells = {(lat, lon) for w, s, e, n in bounds for lat in range(s - 1, n + 1) for lon in range(w - 1, e + 1)}

    def acquire(cell):
        lat, lon = cell
        stem = f'Copernicus_DSM_COG_10_N{lat:02d}_00_W{abs(lon):03d}_00_DEM'
        if stem not in available and stem + '/' not in available:
            raise ValueError(f'Missing Copernicus source tile: {stem}')
        download(f'{COPERNICUS}{stem}/{stem}.tif', cache / (stem + '.tif'))

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(acquire, sorted(cells)))
    print(f'{len(cells)} shared Copernicus source tiles are ready', flush=True)


def main():
    specs = json.loads((ROOT / 'config/canadian-rockies.json').read_text())
    identities = json.loads((ROOT / 'garmin/map-identities.json').read_text())
    parks, records = park_sources()
    results = [prepare(region, spec, parks, records, identities[region]) for region, spec in specs.items()]
    south, north, foothills = (geometry for geometry, _ in results)
    if not south.intersection(north).covers(LineString(PARKWAY)):
        raise ValueError('Icefields Parkway overlap has a gap')
    if not south.intersection(foothills).covers(Point(-115.3479, 51.0890)):
        raise ValueError('Missing Canmore overlap')
    if foothills.bounds[1] != 49:
        raise ValueError('Southern edition must meet the US border')
    prefetch_terrain([bounds for _, bounds in results])


if __name__ == '__main__':
    main()
