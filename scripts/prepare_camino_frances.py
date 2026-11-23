#!/usr/bin/env python3
"""Pin the primary French Way alignment and generate its 10 km map corridor."""
import json
import re
from urllib.parse import urlencode

from pyproj import Geod, Transformer
from shapely import transform
from shapely.geometry import LineString, Point, box, mapping

from openbaremap import ROOT, digest, write

SOURCE = ROOT / 'data/regions/camino-frances'
OUTPUT = ROOT / 'regions/camino-frances'
ATTRIBUTION = 'Federación Española de Asociaciones de Amigos del Camino de Santiago (FEAACS), CC BY 4.0 · OpenStreetMap contributors, ODbL'
IGN_URL = 'https://nco.ign.es/server/rest/services/nco/CaminoSantiago/MapServer/1/query?' + urlencode({
    'where': "sde.datos_nco.CST.id_camino='ES01c'",
    'outFields': 'sde.datos_nco.CST.id_etapa,sde.datos_nco.CST.nombre,sde.datos_nco.CST.longitud',
    'outSR': 4326, 'returnZ': 'false', 'returnM': 'false', 'f': 'geojson',
})
OSM_URL = 'https://cdn.jsdelivr.net/gh/walktalkmeditate/open-pilgrimages@v1.13.0/routes/camino-frances/route.geojson'
CRS = 'EPSG:25830'
GEOD = Geod(ellps='WGS84')


def metres(a, b):
    return GEOD.inv(*a, *b)[2]


def coordinates(feature):
    if feature['geometry']['type'] != 'LineString':
        raise ValueError('Expected single-line source stages')
    return [tuple(point[:2]) for point in feature['geometry']['coordinates']]


def feature_collection(name, geometry):
    return {'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'properties': {'name': name},
                                                      'geometry': mapping(geometry)}]}


def main():
    from fetch_region import download

    ign = SOURCE / 'camino-frances-ign.geojson'
    osm = SOURCE / 'camino-frances-route.geojson'
    for path, url in ((ign, IGN_URL), (osm, OSM_URL)):
        if not path.is_file():
            download(url, path)
    official = json.loads(ign.read_text())['features']
    stages = {feature['properties']['sde.datos_nco.CST.id_etapa']: coordinates(feature)
              for feature in official if re.fullmatch(r'\d\da', feature['properties']['sde.datos_nco.CST.id_etapa'])}
    expected = [f'{stage:02d}a' for stage in range(5, 34)]
    if set(stages) != set(expected):
        raise ValueError('The primary IGN stages have changed')

    # The service appends part of a return leg to the final stage. Start at the
    # previous stage's exact endpoint, then follow the line back to the cathedral.
    last = stages['33a']
    join = min(range(len(last)), key=lambda index: metres(last[index], stages['32a'][-1]))
    if metres(last[join], stages['32a'][-1]) > 10 or metres(last[0], (-8.5445, 42.8809)) > 30:
        raise ValueError('The final Camino stage has changed')
    stages['33a'] = last[join::-1]

    # IGN's ES01c begins in Puente la Reina. Use the OSM alignment upstream
    # from that junction, removing exact retraces in the source route.
    initial = coordinates(json.loads(osm.read_text())['features'][0])
    join = min(range(len(initial)), key=lambda index: metres(initial[index], stages['05a'][0]))
    if metres(initial[join], stages['05a'][0]) > 100:
        raise ValueError('The OSM route does not meet the official route at Puente la Reina')
    prefix = []
    index = {}
    for point in initial[:join + 1]:
        if point in index:
            for abandoned in prefix[index[point] + 1:]:
                del index[abandoned]
            del prefix[index[point] + 1:]
        else:
            index[point] = len(prefix)
            prefix.append(point)
    if not 80_000 <= GEOD.geometry_length(LineString(prefix)) <= 105_000:
        raise ValueError('Unexpected Saint-Jean to Puente la Reina distance')
    spine = prefix.copy()
    for stage in expected:
        if metres(spine[-1], stages[stage][0]) > 100:
            raise ValueError(f'Disconnected route before {stage}')
        spine.extend(stages[stage])
    route = LineString(spine)
    length = GEOD.geometry_length(route)
    if not 745_000 <= length <= 810_000:
        raise ValueError('The assembled route length is inconsistent with the French Way')

    project = Transformer.from_crs(4326, CRS, always_xy=True).transform
    unproject = Transformer.from_crs(CRS, 4326, always_xy=True).transform
    projected = transform(route, project, interleaved=False)
    corridor = projected.buffer(10_000, quad_segs=16)
    coverage = transform(corridor, unproject, interleaved=False)
    if not coverage.is_valid or not coverage.covers(route):
        raise ValueError('The corridor does not cover the entire route')
    OUTPUT.mkdir(parents=True, exist_ok=True)
    write(OUTPUT / 'camino-route.geojson', feature_collection('Camino Francés', transform(projected.simplify(5), unproject, interleaved=False)))
    write(OUTPUT / 'coverage.geojson', feature_collection('10 km from the main Camino Francés', coverage))
    write(OUTPUT / 'coverage-mask.geojson', feature_collection('Outside map coverage', box(-180, -85, 180, 85).difference(coverage)))
    write(OUTPUT / 'park-boundary.geojson', {'type': 'FeatureCollection', 'features': []})
    write(OUTPUT / 'boundary-source.json', {
        'sources': [{'url': url, 'sha256': digest(path), 'attribution': attribution} for url, path, attribution in (
            (IGN_URL, ign, 'Rutas de Caminos de Santiago 2020–2026 CC BY 4.0 FEAACS'),
            (OSM_URL, osm, 'OpenStreetMap contributors, ODbL, via Open Pilgrimages 1.13.0'),
        )],
        'changes': 'Main route stages joined and source retraces removed. A projected circular buffer was computed around the resulting route.',
        'bufferMetres': 10_000, 'bufferCRS': CRS, 'routeLengthKilometres': round(length / 1000, 2),
        'coverageSquareKilometres': round(corridor.area / 1e6, 1),
        'coverageSHA256': digest(OUTPUT / 'coverage.geojson'), 'routeSHA256': digest(OUTPUT / 'camino-route.geojson'),
    })

    stops = {
        'saint-jean': ('Saint-Jean-Pied-de-Port', (-1.23723, 43.16234)),
        'roncesvalles': ('Roncesvalles', (-1.3192, 43.0098)),
        'pamplona': ('Pamplona', (-1.6412, 42.8185)),
        'puente-la-reina': ('Puente la Reina', (-1.81797, 42.67148)),
        'logrono': ('Logroño', (-2.4474, 42.4665)),
        'burgos': ('Burgos', (-3.7047, 42.3408)),
        'carrion': ('Carrión de los Condes', (-4.6019, 42.3370)),
        'leon': ('León', (-5.5666, 42.5996)),
        'astorga': ('Astorga', (-6.0548, 42.4576)),
        'ponferrada': ('Ponferrada', (-6.5915, 42.5449)),
        'sarria': ('Sarria', (-7.4166, 42.776)),
        'santiago': ('Santiago de Compostela', (-8.5445, 42.8809)),
    }
    for name, xy in stops.values():
        if transform(Point(*xy), project, interleaved=False).distance(projected) > 2000:
            raise ValueError(f'The assembled route misses {name}')
    west, south, east, north = coverage.bounds
    xmin, ymin, xmax, ymax = corridor.bounds
    profile = json.loads((ROOT / 'regions/picos-de-europa/region.json').read_text())
    center = transform(projected.interpolate(0.5, normalized=True), unproject, interleaved=False).coords[0]
    profile.update(id='camino-frances', name='OpenBareMap Camino Francés', label='Camino Francés',
                   appBundleName='Camino-Frances', coverage='The French Way from Saint-Jean-Pied-de-Port to Santiago de Compostela, in a corridor extending 10 km to either side of the main route.',
                   bounds=[west, south, east, north], terrainBounds=[-9, 42, -1, 44], coastContextBounds=[-10, 41, 0, 45],
                   garminContextBounds=[west, south, east, north], projectedCRS=CRS, gridCRS=CRS,
                   gridName='ETRS89 / UTM 30N', gridExtent=[int(xmin // 10000) * 10000, (int(xmax // 10000) + 1) * 10000,
                                                           int(ymin // 10000) * 10000, (int(ymax // 10000) + 1) * 10000],
                   sourceDate='2026-11-22', sourceSlugs=['spain', 'aquitaine'], sourceBaseURL='https://download.geofabrik.de/europe/',
                   sourceBaseOverrides={'spain': 'https://download.geofabrik.de/europe/spain/',
                                        'aquitaine': 'https://download.geofabrik.de/europe/france/aquitaine/'},
                   sourceCacheRegion='camino-frances', nativeLanguage='es', garminFamilyId=4874, garminTileStartId=48740001,
                   garminFilename='OpenBareMap-Camino-Frances.img', styleRevision='2.0.0-camino-frances-r1',
                   inspectionNames=['Pamplona', 'Burgos', 'Santiago de Compostela'],
                   labelGlyphs='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzÀÁÈÉÍÑÓÚÜàáèéíñóúüç',
                   coverageBoundary=True, routeCorridor=True, coverageBoundaryLabel='10 km map coverage limit',
                   clipTerrainToBounds=True, repairClippedCoastline=True,
                   boundaryAttribution=ATTRIBUTION,
                   destinations={'island': [*center, 7], **{k: [*v, 12] for k, (_, v) in stops.items()}},
                   destinationLabels={'island': 'Camino Francés', **{k: v for k, (v, _) in stops.items()}},
                   validationAnchors={k: v for k, (_, v) in stops.items()},
                   terrainNotice=profile['terrainNotice'].replace('Picos de Europa elevation', 'Camino Francés elevation'))
    write(OUTPUT / 'region.json', profile)
    print(f'Validated {length / 1000:.1f} km of route and {corridor.area / 1e6:,.0f} km² of coverage.')


if __name__ == '__main__':
    main()
