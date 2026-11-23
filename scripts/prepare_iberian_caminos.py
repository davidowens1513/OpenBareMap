#!/usr/bin/env python3
"""Prepare the Portuguese and Northern Way overlays and their 10 km footprints."""
import json
from math import ceil, floor
from urllib.parse import urlencode

from pyproj import Geod, Transformer
from shapely import Point, box, transform, union_all
from shapely.geometry import LineString, mapping, shape
from shapely.ops import substring

from fetch_region import download
from openbaremap import ROOT, digest, write

OPEN_PILGRIMAGES = 'https://cdn.jsdelivr.net/gh/walktalkmeditate/open-pilgrimages@v1.13.0/routes/'
IGN_COAST = 'https://nco.ign.es/server/rest/services/nco/CaminoSantiago/MapServer/1/query?' + urlencode({
    'where': "sde.datos_nco.CST.id_camino='ES18a'", 'outFields': 'sde.datos_nco.CST.id_etapa,sde.datos_nco.CST.nombre,sde.datos_nco.CST.longitud',
    'outSR': 4326, 'returnZ': 'false', 'returnM': 'false', 'f': 'geojson',
})
OSM_CREDIT = 'OpenStreetMap contributors, ODbL, via Open Pilgrimages 1.13.0'
IGN_CREDIT = 'Rutas de Caminos de Santiago, FEAACS / IGN, CC BY 4.0'
FRENCH_CREDIT = 'OpenBareMap Camino Francés, FEAACS / IGN (CC BY 4.0) and OpenStreetMap (ODbL)'
GEOD = Geod(ellps='WGS84')
EDITION_STOPS = {
    'camino-portugues': {
        'porto': ('Porto', (-8.611, 41.142)),
        'viana-do-castelo': ('Viana do Castelo', (-8.832, 41.693)),
        'caminha': ('Caminha', (-8.837, 41.877)),
        'ponte-de-lima': ('Ponte de Lima', (-8.583, 41.768)),
        'tui': ('Tui', (-8.645, 42.046)),
        'a-guarda': ('A Guarda', (-8.874, 41.902)),
        'vigo': ('Vigo', (-8.723, 42.237)),
        'redondela': ('Redondela', (-8.609, 42.282)),
        'pontevedra': ('Pontevedra', (-8.645, 42.432)),
        'padron': ('Padrón', (-8.66, 42.739)),
        'santiago': ('Santiago de Compostela', (-8.5445, 42.8809)),
    },
    'camino-del-norte': {
        'irun': ('Irún', (-1.789, 43.339)),
        'san-sebastian': ('San Sebastián', (-1.984, 43.321)),
        'bilbao': ('Bilbao', (-2.923, 43.257)),
        'santander': ('Santander', (-3.807, 43.461)),
        'llanes': ('Llanes', (-4.754, 43.420)),
        'gijon': ('Gijón', (-5.662, 43.542)),
        'aviles': ('Avilés', (-5.922, 43.556)),
        'ribadeo': ('Ribadeo', (-7.042, 43.536)),
        'villalba': ('Vilalba', (-7.681, 43.299)),
        'arzua': ('Arzúa', (-8.1605, 42.9273)),
        'santiago': ('Santiago de Compostela', (-8.5445, 42.8809)),
    },
}


def without_retraces(geometry):
    points = []
    positions = {}
    for point in shape(geometry).coords:
        point = tuple(point[:2])
        if point in positions:
            keep = positions[point] + 1
            for prior in points[keep:]:
                del positions[prior]
            del points[keep:]
        else:
            positions[point] = len(points)
            points.append(point)
    return LineString(points)


def source(directory, filename, url, credit):
    path = directory / filename
    item = download(url, path)
    return json.loads(path.read_text())['features'], {**item, 'attribution': credit}


def join(lines, maximum_gap):
    points = list(lines[0].coords)
    for line in lines[1:]:
        if Point(points[-1]).distance(Point(line.coords[0])) > maximum_gap:
            raise ValueError(f'Unexpected route gap near {points[-1]}')
        points.extend(line.coords)
    return LineString(points)


def tails_at_junction(upstream, downstream, maximum_gap):
    endpoint = Point(upstream.coords[-1])
    junction = downstream.project(endpoint)
    if downstream.interpolate(junction).distance(endpoint) > maximum_gap:
        raise ValueError('The source alignments no longer meet')
    return substring(downstream, junction, downstream.length)


def feature(name, geometry):
    return {'type': 'Feature', 'properties': {'name': name}, 'geometry': mapping(geometry)}


def save_collection(path, features):
    write(path, {'type': 'FeatureCollection', 'features': features})


def prepare(region):
    source_root = ROOT / 'data/regions' / region
    out = ROOT / 'regions' / region
    out.mkdir(parents=True, exist_ok=True)
    is_portuguese = region == 'camino-portugues'
    crs = 'EPSG:25829' if is_portuguese else 'EPSG:25830'
    forward = Transformer.from_crs(4326, crs, always_xy=True).transform
    reverse = Transformer.from_crs(crs, 4326, always_xy=True).transform

    def project(geom):
        return transform(geom, forward, interleaved=False)

    def unproject(geom):
        return transform(geom, reverse, interleaved=False)

    upstream = 'camino-portugues' if is_portuguese else 'camino-norte'
    features, upstream_record = source(source_root, 'route.geojson', OPEN_PILGRIMAGES+upstream+'/route.geojson', OSM_CREDIT)
    records = [upstream_record]
    main = project(without_retraces(features[0]['geometry']))
    if is_portuguese:
        coastal, record = source(source_root, 'coastal-portugal.geojson',
                                 OPEN_PILGRIMAGES+upstream+'/variants/coastal/route.geojson', OSM_CREDIT)
        records.append(record)
        official, record = source(source_root, 'coastal-spain.geojson', IGN_COAST, IGN_CREDIT)
        records.append(record)
        stages = {f['properties']['sde.datos_nco.CST.id_etapa']: project(without_retraces(f['geometry'])) for f in official}
        first, second, third = (stages[k] for k in ('01a', '02a', '03a'))
        # IGN stage 02 continues past the Castrelos junction where stage 03 starts.
        castrelos = Point(third.coords[0])
        if second.distance(castrelos) > 20:
            raise ValueError('The coastal stages no longer meet in Castrelos')
        spanish = join([first, substring(second, 0, second.project(castrelos)), third,
                        tails_at_junction(third, main, 70)], 70)
        portuguese = project(without_retraces(coastal[0]['geometry']))
        if not 500 <= Point(portuguese.coords[-1]).distance(Point(spanish.coords[0])) <= 3000:
            raise ValueError('Unexpected distance across the Minho at Caminha')
        # The river crossing is a break in the walking overlay. Both banks
        # and the crossing sit within the continuous 10 km coverage.
        routes = [('Camino Portugués Central', main), ('Coastal Way – Portugal', portuguese),
                  ('Coastal Way – Galicia to Santiago', spanish)]
        changes = 'Exact retraces removed. The Spanish coastal stages are joined at Castrelos and the Central Way near Redondela. The Minho crossing at Caminha separates the walking lines.'
        credit = OSM_CREDIT + ' · ' + IGN_CREDIT
    else:
        french = ROOT / 'regions/camino-frances/camino-route.geojson'
        provenance = json.loads(french.with_name('boundary-source.json').read_text())
        if digest(french) != provenance['routeSHA256']:
            raise ValueError('The accepted Camino Francés alignment has changed')
        records.append({'path': str(french.relative_to(ROOT)), 'sha256': digest(french), 'attribution': FRENCH_CREDIT})
        final = project(shape(json.loads(french.read_text())['features'][0]['geometry']))
        main = join([main, tails_at_junction(main, final, 70)], 70)
        routes = [('Camino del Norte', main)]
        changes = 'Exact retraces removed. The Camino Francés alignment from Arzúa supplies the shared final approach to Santiago.'
        credit = OSM_CREDIT + ' · ' + FRENCH_CREDIT

    lengths = {name: GEOD.geometry_length(unproject(line))/1000 for name, line in routes}
    if is_portuguese:
        if not all(low <= length <= high for length, (low, high) in zip(lengths.values(), [(210, 270), (95, 135), (145, 195)])):
            raise ValueError(f'Unexpected Portuguese alignment lengths: {lengths}')
    elif not 770 <= next(iter(lengths.values())) <= 850:
        raise ValueError(f'Unexpected Northern Way length: {lengths}')

    stops = EDITION_STOPS[region]
    lines = union_all([line for _, line in routes])
    for name, coordinates in stops.values():
        if project(Point(*coordinates)).distance(lines) > 3200:
            raise ValueError(f'The route alignments miss {name}')
    corridor = union_all([line.buffer(10_000, quad_segs=16) for _, line in routes])
    coverage = unproject(corridor)
    overlays = [feature(name, unproject(line.simplify(5))) for name, line in routes]
    if not coverage.is_valid or not all(coverage.covers(shape(item['geometry'])) for item in overlays):
        raise ValueError('The 10 km footprint does not cover the route overlays')
    save_collection(out/'camino-route.geojson', overlays)
    save_collection(out/'coverage.geojson', [feature('10 km route corridor', coverage)])
    save_collection(out/'coverage-mask.geojson', [feature('Outside map coverage', box(-180, -85, 180, 85).difference(coverage))])
    save_collection(out/'park-boundary.geojson', [])
    write(out/'boundary-source.json', {
        'sources': records, 'changes': changes, 'bufferMetres': 10_000, 'bufferCRS': crs,
        'routeLengthKilometres': round(lengths[next(iter(lengths))], 2),
        'alignmentLengthsKilometres': {name: round(km, 2) for name, km in lengths.items()},
        'coverageSquareKilometres': round(corridor.area/1e6, 1),
        'coverageSHA256': digest(out/'coverage.geojson'), 'routeSHA256': digest(out/'camino-route.geojson'),
    })

    west, south, east, north = coverage.bounds
    xmin, ymin, xmax, ymax = corridor.bounds
    terrain = [floor(west), floor(south), ceil(east), ceil(north)]
    p = json.loads((ROOT/'regions/camino-frances/region.json').read_text())
    p.pop('sourceCacheRegion', None)
    label = 'Camino Portugués' if is_portuguese else 'Camino del Norte'
    bundle = 'Camino-Portugues' if is_portuguese else 'Camino-del-Norte'
    endpoints = 'Porto to Santiago de Compostela on both the Central and Coastal routes' if is_portuguese else 'Irún to Santiago de Compostela via the northern coast and Arzúa'
    family = 4883 if is_portuguese else 4884
    p.update(id=region, label=label, name='OpenBareMap '+label, coverage=endpoints+' with 10 km of coverage on either side.',
             appBundleName=bundle, bounds=list(coverage.bounds), terrainBounds=terrain,
             coastContextBounds=[terrain[0]-1, terrain[1]-1, terrain[2]+1, terrain[3]+1],
             garminContextBounds=list(coverage.bounds), projectedCRS=crs, gridCRS=crs,
             gridName='ETRS89 / UTM '+('29N' if is_portuguese else '30N'),
             gridExtent=[floor(xmin/10000)*10000, ceil(xmax/10000)*10000, floor(ymin/10000)*10000, ceil(ymax/10000)*10000],
             sourceSlugs=['spain', 'portugal' if is_portuguese else 'aquitaine'],
             sourceBaseOverrides={'spain':'https://download.geofabrik.de/europe/spain/',
                                  'portugal':'https://download.geofabrik.de/europe/portugal/',
                                  'aquitaine':'https://download.geofabrik.de/europe/france/aquitaine/'},
             nativeLanguage='pt' if is_portuguese else 'es', boundaryAttribution=credit, routeOverlayLabel=label,
             labelGlyphs='ÁÀÂÃÇÈÉÊÍÑÓÔÕÚÜáàâãçèéêíñóôõúü',
             garminFamilyId=family, garminTileStartId=family*10000+1,
             garminFilename=f'OpenBareMap-{bundle}.img', garminVersionedDelivery=True, garminPackageRevision='2.0.0-r1',
             styleRevision=f'2.0.0-{region}-r1',
             terrainNotice=p['terrainNotice'].replace('Camino Francés elevation',label+' elevation'),
             destinations={'island': [*(coverage.representative_point().coords[0]), 8 if is_portuguese else 7],
                           **{key: [*coords, 12] for key, (_, coords) in stops.items()}},
             destinationLabels={'island':label, **{key:name for key, (name, _) in stops.items()}},
             validationAnchors={key:coords for key, (_, coords) in stops.items()},
             inspectionNames=['Porto', 'Tui', 'Santiago de Compostela'] if is_portuguese else ['Bilbao', 'Santander', 'Santiago de Compostela'])
    if not is_portuguese:
        # Keep the town shortcut at the harbour and check the coarse land
        # polygon just inland, where coastline simplification cannot move it.
        p['overviewLandAnchors'] = {**p['validationAnchors'], 'llanes': [-4.758, 43.418]}
    write(out/'region.json', p)
    print(f'{label}: {lengths}. Coverage {corridor.area/1e6:,.0f} km²; terrain bounds {terrain}.')


if __name__ == '__main__':
    for edition in EDITION_STOPS:
        prepare(edition)
