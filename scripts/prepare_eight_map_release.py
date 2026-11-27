#!/usr/bin/env python3
"""Prepare the eight regional profiles for the November 2026 release."""

from math import ceil, floor

from pyproj import Transformer

from openbaremap import ROOT, write
from regions import profile


REGIONS = {
    'gran-sasso': {
        'label': 'Gran Sasso', 'bundle': 'Gran-Sasso', 'family': 4891, 'zone': 33,
        'bounds': [13.25, 42.25, 13.95, 42.75], 'date': '2026-11-26',
        'sources': ['sud'], 'base': 'https://download.geofabrik.de/europe/italy/',
        'overrides': {'sud': 'https://download.geofabrik.de/europe/italy/sud/'},
        'language': 'it', 'glyphs': 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzÀÈÉÌÒÙàèéìòù',
        'coverage': 'Gran Sasso e Monti della Laga, including Campo Imperatore, Corno Grande, Prati di Tivo, Assergi, L’Aquila and the principal mountain approaches.',
        'destinations': {
            'laquila': ('L’Aquila', 13.3995, 42.3498), 'asserigi': ('Assergi', 13.5147, 42.4236),
            'campo-imperatore': ('Campo Imperatore', 13.5582, 42.4427),
            'corno-grande': ('Corno Grande', 13.5656, 42.4697),
            'prati-di-tivo': ('Prati di Tivo', 13.5741, 42.4992),
            'pietracamela': ('Pietracamela', 13.5550, 42.5230),
        },
        'inspection': ["L'Aquila"],
        'ice': True, 'required_ice': ['glacier'],
        'ice_note': 'Glacier and permanent snowfield outlines are from OpenStreetMap.',
    },
    'northern-drakensberg': {
        'label': 'Northern Drakensberg', 'bundle': 'Northern-Drakensberg', 'family': 4892, 'zone': 35,
        'bounds': [28.65, -29.40, 29.75, -28.50], 'date': '2026-11-26',
        'sources': ['south-africa', 'lesotho'], 'base': 'https://download.geofabrik.de/africa/',
        'overrides': {'south-africa': 'https://download.geofabrik.de/africa/south-africa/',
                      'lesotho': 'https://download.geofabrik.de/africa/lesotho/'},
        'cache': 'south-africa', 'language': 'en',
        'coverage': 'The Northern Drakensberg escarpment from Royal Natal and the Amphitheatre to Cathedral Peak, Giant’s Castle and the adjoining Lesotho highlands.',
        'destinations': {
            'royal-natal': ('Royal Natal', 28.943, -28.690), 'amphitheatre': ('Amphitheatre', 28.890, -28.761),
            'tugela-falls': ('Tugela Falls', 28.893, -28.752), 'sentinel': ('Sentinel', 28.880, -28.743),
            'cathedral-peak': ('Cathedral Peak', 29.063, -28.951), 'giants-castle': ('Giant’s Castle', 29.346, -29.346),
            'monks-cowl': ('Monk’s Cowl', 29.124, -29.048),
        },
        'inspection': ['Cathedral Peak'],
    },
    'cape-peninsula': {
        'label': 'Cape Peninsula', 'bundle': 'Cape-Peninsula', 'family': 4893, 'zone': 34,
        'bounds': [18.25, -34.38, 18.58, -33.82], 'date': '2026-11-26',
        'sources': ['south-africa'], 'base': 'https://download.geofabrik.de/africa/south-africa/',
        'cache': 'south-africa', 'language': 'en',
        'coverage': 'Cape Town and the Cape Peninsula, including Table Mountain, Lion’s Head, Silvermine, Chapman’s Peak, Cape Point and the False Bay coast.',
        'destinations': {
            'cape-town': ('Cape Town', 18.4241, -33.9249), 'table-mountain': ('Table Mountain', 18.4098, -33.9628),
            'lions-head': ('Lion’s Head', 18.389, -33.935), 'constantia-nek': ('Constantia Nek', 18.406, -34.011),
            'silvermine': ('Silvermine', 18.424, -34.087), 'chapmans-peak': ('Chapman’s Peak', 18.360, -34.087),
            'simons-town': ('Simon’s Town', 18.433, -34.193), 'cape-point': ('Cape Point', 18.497, -34.357),
        },
        'inspection': ['Cape Town', 'Hout Bay'],
    },
    'mount-rainier': {
        'label': 'Mount Rainier', 'bundle': 'Mount-Rainier', 'family': 4894, 'zone': 10,
        'bounds': [-122.05, 46.65, -121.45, 47.05], 'date': '2026-11-20',
        'sources': ['washington'], 'base': 'https://download.geofabrik.de/north-america/us/',
        'overrides': {'washington': 'https://download.geofabrik.de/north-america/us/washington/'},
        'cache': 'us-national-parks', 'terrain_cache': 'us-national-parks', 'language': 'en', 'ice': True,
        'coverage': 'Mount Rainier National Park and its approaches, including Paradise, Sunrise, Longmire, Carbon River, Mowich Lake and the Wonderland Trail.',
        'destinations': {
            'mount-rainier': ('Mount Rainier', -121.7603, 46.8523), 'paradise': ('Paradise', -121.735, 46.786),
            'sunrise': ('Sunrise', -121.642, 46.914), 'longmire': ('Longmire', -121.812, 46.750),
            'mowich-lake': ('Mowich Lake', -121.861, 46.933), 'carbon-river': ('Carbon River', -121.897, 46.993),
            'white-river': ('White River', -121.534, 46.902),
        },
        'inspection': ['Mount Rainier', 'Longmire'],
    },
    'vancouver-island-west-coast-trail': {
        'label': 'Vancouver Island West Coast Trail', 'bundle': 'Vancouver-Island-West-Coast-Trail',
        'family': 4895, 'zone': 10, 'bounds': [-125.35, 48.42, -124.20, 49.02], 'date': '2026-11-20',
        'sources': ['british-columbia'], 'base': 'https://download.geofabrik.de/north-america/canada/',
        'overrides': {'british-columbia': 'https://download.geofabrik.de/north-america/canada/british-columbia/'},
        'cache': 'canadian-rockies', 'terrain_cache': 'canadian-rockies', 'language': 'en',
        'coverage': 'Vancouver Island’s West Coast Trail between Pachena Bay and Port Renfrew, including Bamfield, Nitinat Narrows, Carmanah, Walbran and the Juan de Fuca coast.',
        'destinations': {
            'bamfield': ('Bamfield', -125.137, 48.835), 'pachena-bay': ('Pachena Bay', -125.108, 48.825),
            'nitinat-narrows': ('Nitinat Narrows', -124.787, 48.663), 'carmanah': ('Carmanah', -124.704, 48.612),
            'walbran': ('Walbran Creek', -124.668, 48.584), 'gordon-river': ('Gordon River', -124.414, 48.508),
            'port-renfrew': ('Port Renfrew', -124.421, 48.555),
        },
        'inspection': ['Bamfield', 'Port Renfrew'],
        'overview_land': {'walbran': [-124.668, 48.584]},
    },
    'garibaldi-whistler': {
        'label': 'Garibaldi & Whistler', 'bundle': 'Garibaldi-Whistler', 'family': 4896, 'zone': 10,
        'bounds': [-123.30, 49.65, -122.65, 50.25], 'date': '2026-11-20',
        'sources': ['british-columbia'], 'base': 'https://download.geofabrik.de/north-america/canada/',
        'overrides': {'british-columbia': 'https://download.geofabrik.de/north-america/canada/british-columbia/'},
        'cache': 'canadian-rockies', 'terrain_cache': 'canadian-rockies', 'language': 'en', 'ice': True,
        'coverage': 'Garibaldi Provincial Park and Whistler, including the Sea to Sky corridor, Garibaldi Lake, Black Tusk, Elfin Lakes, Wedgemount Lake and the Fitzsimmons Range.',
        'destinations': {
            'whistler': ('Whistler', -122.957, 50.116), 'garibaldi-lake': ('Garibaldi Lake', -123.031, 49.934),
            'black-tusk': ('Black Tusk', -123.042, 49.968), 'panorama-ridge': ('Panorama Ridge', -123.027, 49.955),
            'elfin-lakes': ('Elfin Lakes', -122.988, 49.761), 'wedgemount-lake': ('Wedgemount Lake', -122.806, 50.171),
            'squamish': ('Squamish', -123.156, 49.701),
        },
        'inspection': ['Whistler'],
    },
    'cotopaxi-quilotoa': {
        'label': 'Cotopaxi & Quilotoa', 'bundle': 'Cotopaxi-Quilotoa', 'family': 4897, 'zone': 17,
        'bounds': [-79.15, -1.10, -78.25, -0.45], 'date': '2026-11-26',
        'sources': ['ecuador'], 'base': 'https://download.geofabrik.de/south-america/ecuador/',
        'language': 'es', 'glyphs': 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzÁÉÍÑÓÚÜáéíñóúü', 'ice': True,
        'coverage': 'Cotopaxi National Park and the Quilotoa Loop, including Latacunga, the Cotopaxi refuges, Laguna Limpiopungo, Quilotoa, Chugchilán and Isinliví.',
        'destinations': {
            'latacunga': ('Latacunga', -78.617, -0.935), 'cotopaxi': ('Cotopaxi', -78.437, -0.680),
            'jose-rivas-refuge': ('José Rivas Refuge', -78.438, -0.658), 'limpiopungo': ('Laguna Limpiopungo', -78.473, -0.626),
            'quilotoa': ('Quilotoa', -78.899, -0.866), 'chugchilan': ('Chugchilán', -78.922, -0.756),
            'isinlivi': ('Isinliví', -78.870, -0.662),
        },
        'inspection': ['Latacunga', 'Cotopaxi'],
    },
    'aconcagua': {
        'label': 'Aconcagua', 'bundle': 'Aconcagua', 'family': 4898, 'zone': 19,
        'bounds': [-70.35, -33.25, -69.25, -32.45], 'date': '2026-11-22',
        'sources': ['argentina', 'chile'], 'base': 'https://download.geofabrik.de/south-america/',
        'overrides': {'argentina': 'https://download.geofabrik.de/south-america/argentina/',
                      'chile': 'https://download.geofabrik.de/south-america/chile/'},
        'cache': 'patagonia', 'terrain_cache': 'patagonia', 'language': 'es',
        'glyphs': 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzÁÉÍÑÓÚÜáéíñóúü', 'ice': True,
        'coverage': 'Aconcagua Provincial Park and the high Andes approaches from Argentina and Chile, including Horcones, Confluencia, Plaza de Mulas, Puente del Inca and Los Penitentes.',
        'destinations': {
            'aconcagua': ('Aconcagua', -70.0109, -32.6532), 'horcones': ('Horcones', -69.942, -32.825),
            'confluencia': ('Confluencia', -69.970, -32.760), 'plaza-de-mulas': ('Plaza de Mulas', -70.059, -32.646),
            'puente-del-inca': ('Puente del Inca', -69.912, -32.825), 'los-penitentes': ('Los Penitentes', -69.852, -32.838),
            'uspallata': ('Uspallata', -69.348, -32.593),
        },
        'inspection': ['Aconcagua', 'Puente del Inca'],
    },
}


def prepare(region, edition):
    template = profile('cusco-inca-trail')
    west, south, east, north = edition['bounds']
    southern = south < 0
    epsg = 32700 + edition['zone'] if southern else 32600 + edition['zone']
    projected_crs = f'EPSG:{epsg}'
    project = Transformer.from_crs(4326, projected_crs, always_xy=True)
    points = [project.transform(lon, lat) for lon in (west, east) for lat in (south, north)]
    eastings, northings = zip(*points)
    grid_extent = [floor(min(eastings) / 10000) * 10000, ceil(max(eastings) / 10000) * 10000,
                   floor(min(northings) / 10000) * 10000, ceil(max(northings) / 10000) * 10000]
    terrain_bounds = [floor(west), floor(south), ceil(east), ceil(north)]
    stops = edition['destinations']
    label = edition['label']
    centre = [(west + east) / 2, (south + north) / 2, 9]
    overrides = edition.get('overrides', {})
    output = {
        **template,
        'id': region,
        'name': f'OpenBareMap {label}',
        'label': label,
        'mapVersion': '2.0.0',
        'coverage': edition['coverage'],
        'bounds': edition['bounds'],
        'terrainBounds': terrain_bounds,
        'coastContextBounds': [terrain_bounds[0] - 1, terrain_bounds[1] - 1,
                               terrain_bounds[2] + 1, terrain_bounds[3] + 1],
        'projectedCRS': projected_crs,
        'gridCRS': projected_crs,
        'gridName': f'WGS 84 / UTM zone {edition["zone"]}{"S" if southern else "N"}',
        'gridExtent': grid_extent,
        'sourceDate': edition['date'],
        'sourceSlugs': edition['sources'],
        'sourceBaseURL': edition['base'],
        'nativeLanguage': edition['language'],
        'labelGlyphs': edition.get('glyphs', 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'),
        'garminContextBounds': edition['bounds'],
        'garminFamilyId': edition['family'],
        'garminTileStartId': edition['family'] * 10000 + 1,
        'garminFilename': f'OpenBareMap-{edition["bundle"]}.img',
        'garminPackageRevision': '2.0.0-r1',
        'garminVersionedDelivery': True,
        'styleRevision': f'2.0.0-{region}-r1',
        'inspectionNames': edition['inspection'],
        'terrainNotice': template['terrainNotice'].replace('Cusco & the Inca Trail', label),
        'destinations': {'island': centre, **{key: [lon, lat, 13] for key, (_, lon, lat) in stops.items()}},
        'destinationLabels': {'island': label, **{key: name for key, (name, _, _) in stops.items()}},
        'validationAnchors': {key: [lon, lat] for key, (_, lon, lat) in stops.items()},
        'appBundleName': edition['bundle'],
        'permanentIce': edition.get('ice', False),
    }
    if required_ice := edition.get('required_ice'):
        output['requiredPermanentIce'] = required_ice
    else:
        output.pop('requiredPermanentIce', None)
    if ice_note := edition.get('ice_note'):
        output['permanentIceSourceNote'] = ice_note
    else:
        output.pop('permanentIceSourceNote', None)
    if overview_land := edition.get('overview_land'):
        output['overviewLandAnchors'] = overview_land
    else:
        output.pop('overviewLandAnchors', None)
    if overrides:
        output['sourceBaseOverrides'] = overrides
    else:
        output.pop('sourceBaseOverrides', None)
    if cache := edition.get('cache'):
        output['sourceCacheRegion'] = cache
    else:
        output.pop('sourceCacheRegion', None)
    if terrain_cache := edition.get('terrain_cache'):
        output['terrainCacheRegion'] = terrain_cache
    else:
        output.pop('terrainCacheRegion', None)
    if len(edition['sources']) > 1:
        output['sourceOutputStem'] = region
    else:
        output.pop('sourceOutputStem', None)
    directory = ROOT / 'regions' / region
    directory.mkdir(parents=True, exist_ok=True)
    write(directory / 'region.json', output)


if __name__ == '__main__':
    for slug, config in REGIONS.items():
        prepare(slug, config)
