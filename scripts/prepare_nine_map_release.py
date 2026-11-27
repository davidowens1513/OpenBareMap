#!/usr/bin/env python3
"""Prepare the nine regional profiles for the November 2026 release."""

import json

from openbaremap import ROOT, write
from prepare_eight_map_release import prepare


REGIONS = {
    'north-cascades': {
        'label': 'North Cascades', 'bundle': 'North-Cascades', 'family': 4899, 'zone': 10,
        'bounds': [-121.55, 48.25, -120.75, 48.75], 'date': '2026-11-20',
        'sources': ['washington'], 'base': 'https://download.geofabrik.de/north-america/us/',
        'overrides': {'washington': 'https://download.geofabrik.de/north-america/us/washington/'},
        'cache': 'us-national-parks', 'language': 'en', 'ice': True,
        'required_ice': ['glacier'],
        'coverage': 'North Cascades National Park around Cascade Pass and Sahale Arm, including Marblemount, the Cascade River Road and principal trailhead approaches.',
        'destinations': {
            'marblemount': ('Marblemount', -121.244, 48.527),
            'cascade-river-road': ('Cascade River Road', -121.097, 48.493),
            'cascade-pass-trailhead': ('Cascade Pass Trailhead', -121.075, 48.475),
            'cascade-pass': ('Cascade Pass', -121.060, 48.468),
            'sahale-arm': ('Sahale Arm', -121.050, 48.482),
            'sahale-glacier': ('Sahale Glacier', -121.039, 48.491),
        },
        'inspection': ['Cascade Pass'],
        'ice_note': 'Mapped glaciers and permanent snowfields: OpenStreetMap contributors; corroborated against North Cascades National Park glacier and trail information.',
    },
    'white-mountains': {
        'label': 'White Mountains', 'bundle': 'White-Mountains', 'family': 4900, 'zone': 19,
        'bounds': [-71.95, 43.85, -71.05, 44.45], 'date': '2026-11-26',
        'sources': ['new-hampshire'], 'base': 'https://download.geofabrik.de/north-america/us/new-hampshire/',
        'language': 'en',
        'coverage': 'The White Mountains, including the Presidential Range, Franconia Ridge, Appalachian Mountain Club huts and the connecting trail and road approaches.',
        'destinations': {
            'lincoln': ('Lincoln', -71.671, 44.045), 'franconia-notch': ('Franconia Notch', -71.682, 44.171),
            'lafayette': ('Mount Lafayette', -71.644, 44.160), 'crawford-notch': ('Crawford Notch', -71.414, 44.219),
            'mount-washington': ('Mount Washington', -71.304, 44.271),
            'pinkham-notch': ('Pinkham Notch', -71.253, 44.257), 'gorham': ('Gorham', -71.185, 44.388),
        },
        'inspection': ['Mount Washington', 'Lincoln'],
    },
    'san-juan-mountains': {
        'label': 'San Juan Mountains', 'bundle': 'San-Juan-Mountains', 'family': 4901, 'zone': 13,
        'bounds': [-108.15, 37.65, -107.35, 38.15], 'date': '2026-11-20',
        'sources': ['colorado'], 'base': 'https://download.geofabrik.de/north-america/us/',
        'overrides': {'colorado': 'https://download.geofabrik.de/north-america/us/colorado/'},
        'cache': 'us-national-parks', 'language': 'en', 'ice': True,
        'coverage': 'The San Juan Mountains around Silverton and Ouray, including Ice Lakes Basin, Telluride and the principal walking and road approaches.',
        'destinations': {
            'silverton': ('Silverton', -107.665, 37.812), 'ouray': ('Ouray', -107.672, 38.023),
            'ice-lakes-trailhead': ('Ice Lakes Trailhead', -107.774, 37.807),
            'ice-lakes-basin': ('Ice Lakes Basin', -107.770, 37.816),
            'telluride': ('Telluride', -107.812, 37.937), 'red-mountain-pass': ('Red Mountain Pass', -107.711, 37.898),
        },
        'inspection': ['Silverton', 'Ouray'],
    },
    'aoraki-mount-cook-westland': {
        'label': 'Aoraki / Mount Cook & Westland', 'bundle': 'Aoraki-Mount-Cook-Westland',
        'family': 4902, 'zone': 59, 'bounds': [169.75, -43.80, 170.45, -43.20], 'date': '2026-11-19',
        'sources': ['new-zealand'], 'base': 'https://download.geofabrik.de/australia-oceania/new-zealand/',
        'cache': 'fiordland', 'language': 'en', 'ice': True, 'required_ice': ['glacier'],
        'coverage': 'A cross-divide Southern Alps edition covering Aoraki / Mount Cook and Westland Tai Poutini, including Hooker Valley, Mueller Hut, Tasman Glacier, Fox Glacier and Franz Josef Glacier approaches.',
        'destinations': {
            'aoraki-village': ('Aoraki / Mount Cook Village', 170.097, -43.735),
            'hooker-valley': ('Hooker Valley', 170.091, -43.705), 'mueller-hut': ('Mueller Hut', 170.064, -43.721),
            'tasman-glacier': ('Tasman Glacier', 170.177, -43.610), 'fox-glacier': ('Fox Glacier', 170.017, -43.465),
            'franz-josef': ('Franz Josef / Waiau', 170.181, -43.387),
        },
        'inspection': ['Aoraki / Mount Cook', 'Franz Josef'],
        'ice_note': 'Mapped glaciers and permanent snowfields: OpenStreetMap contributors; corroborated against New Zealand Department of Conservation park and track information.',
    },
    'upper-svaneti': {
        'label': 'Upper Svaneti', 'bundle': 'Upper-Svaneti', 'family': 4903, 'zone': 38,
        'bounds': [42.20, 42.65, 43.35, 43.25], 'date': '2026-11-26',
        'sources': ['georgia'], 'base': 'https://download.geofabrik.de/europe/georgia/',
        'copernicus_padding_fallback': 'mapzen',
        'language': 'ka',
        'glyphs': 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzაბგდევზთიკლმნოპჟრსტუფქღყშჩცძწჭხჯჰ',
        'ice': True, 'required_ice': ['glacier'],
        'coverage': 'Upper Svaneti from Mestia to Ushguli, including the villages, connecting trails, Chalaadi and Shkhara glacier valleys and principal road approaches.',
        'destinations': {
            'mestia': ('Mestia', 42.727, 43.045), 'chalaadi-glacier': ('Chalaadi Glacier', 42.690, 43.117),
            'zhabeshi': ('Zhabeshi', 42.853, 43.039), 'adishi': ('Adishi', 42.990, 42.998),
            'ipralı': ('Iprali', 43.063, 42.938), 'ushguli': ('Ushguli', 43.017, 42.916),
            'shkhara-glacier': ('Shkhara Glacier', 43.106, 42.974),
        },
        'inspection': ['Mestia', 'Ushguli'],
        'ice_note': 'Mapped glaciers and permanent snowfields: OpenStreetMap contributors; named valleys corroborated against Georgia Travel hiking information.',
    },
    'jordan-trail-dana-petra-wadi-rum': {
        'label': 'Jordan Trail – Dana, Petra & Wadi Rum', 'bundle': 'Jordan-Trail-Dana-Petra-Wadi-Rum',
        'family': 4904, 'zone': 36, 'bounds': [35.10, 29.40, 35.85, 30.85], 'date': '2026-11-26',
        'sources': ['jordan'], 'base': 'https://download.geofabrik.de/asia/jordan/', 'language': 'en',
        'coverage': 'The Jordan Trail from Dana through Petra to Wadi Rum, including the complete official sections, stage settlements and walking and vehicle approaches.',
        'destinations': {
            'dana': ('Dana', 35.611, 30.675), 'feynan': ('Feynan Ecolodge', 35.50923, 30.63956),
            'little-petra': ('Little Petra', 35.450, 30.375), 'petra': ('Petra / Wadi Musa', 35.478, 30.322),
            'al-humeima': ('Al-Humeima', 35.344, 29.955), 'wadi-rum': ('Wadi Rum Village', 35.420, 29.576),
        },
        'inspection': ['Dana', 'Wadi Musa'],
    },
    'cordillera-blanca': {
        'label': 'Cordillera Blanca', 'bundle': 'Cordillera-Blanca', 'family': 4905, 'zone': 18,
        # Include the complete INAIGEM Cordillera Blanca glacier inventory extent
        # (-77.8641..-77.1674, -10.0137..-8.3936) as well as the western approaches.
        'bounds': [-77.95, -10.10, -77.05, -8.30], 'date': '2026-11-19',
        'sources': ['peru'], 'base': 'https://download.geofabrik.de/south-america/peru/',
        'cache': 'cusco-inca-trail', 'language': 'es',
        'glyphs': 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzÁÉÍÑÓÚÜáéíñóúü',
        'ice': True, 'required_ice': ['glacier'],
        'coverage': 'Huaraz and the Cordillera Blanca, including Huascarán National Park approaches, the Santa Cruz–Huaripampa trek and principal trailheads and road access.',
        'destinations': {
            'huaraz': ('Huaraz', -77.528, -9.530), 'yungay': ('Yungay', -77.744, -9.141),
            'cashapampa': ('Cashapampa', -77.721, -8.954), 'punta-union': ('Punta Unión', -77.577, -8.993),
            'vaqueria': ('Vaquería', -77.489, -9.008), 'llanganuco': ('Llanganuco', -77.650, -9.050),
            'huascaran': ('Huascarán', -77.605, -9.121),
        },
        'inspection': ['Huaraz', 'Yungay'],
        'ice_note': 'Glacier outlines: INAIGEM Inventario Nacional de Glaciares 2026; permanent snowfields, where mapped: OpenStreetMap contributors. Rock glaciers and temporary snow are excluded.',
    },
    'cordillera-huayhuash': {
        'label': 'Cordillera Huayhuash', 'bundle': 'Cordillera-Huayhuash', 'family': 4906, 'zone': 18,
        'bounds': [-77.35, -10.75, -76.55, -9.80], 'date': '2026-11-19',
        'sources': ['peru'], 'base': 'https://download.geofabrik.de/south-america/peru/',
        'cache': 'cusco-inca-trail', 'language': 'es',
        'glyphs': 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzÁÉÍÑÓÚÜáéíñóúü',
        'ice': True, 'required_ice': ['glacier'],
        'coverage': 'The complete Cordillera Huayhuash trekking circuit, including main passes, camps, trailheads and road approaches from Chiquián and Cajatambo.',
        'destinations': {
            'chiquian': ('Chiquián', -77.155, -10.151), 'llamac': ('Llamac', -76.989, -10.138),
            'cuartelhuain': ('Cuartelhuain', -76.883, -10.084), 'carhuacocha': ('Carhuacocha', -76.913, -10.267),
            'huayhuash': ('Huayhuash', -76.917, -10.400), 'viconga': ('Viconga', -76.905, -10.458),
            'cajatambo': ('Cajatambo', -76.994, -10.474),
        },
        'inspection': ['Chiquián'],
        'ice_note': 'Glacier outlines: INAIGEM Inventario Nacional de Glaciares 2026; permanent snowfields, where mapped: OpenStreetMap contributors. Rock glaciers and temporary snow are excluded.',
    },
    'cerro-castillo': {
        'label': 'Cerro Castillo', 'bundle': 'Cerro-Castillo', 'family': 4907, 'zone': 19,
        'bounds': [-72.55, -46.45, -71.65, -45.55], 'date': '2026-11-22',
        'sources': ['chile'], 'base': 'https://download.geofabrik.de/south-america/',
        'overrides': {'chile': 'https://download.geofabrik.de/south-america/chile/'},
        'cache': 'patagonia', 'language': 'es',
        'glyphs': 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzÁÉÍÑÓÚÜáéíñóúü',
        'ice': True, 'required_ice': ['glacier'],
        'coverage': 'Cerro Castillo National Park in Aysén, including the Las Horquetas traverse, Laguna Castillo, Estero Parada, Villa Cerro Castillo and Carretera Austral approaches.',
        'destinations': {
            'villa-cerro-castillo': ('Villa Cerro Castillo', -72.070, -46.119),
            'las-horquetas': ('Las Horquetas', -72.187, -45.907), 'laguna-castillo': ('Laguna Castillo', -72.168, -46.080),
            'cerro-castillo': ('Cerro Castillo', -72.194, -46.064), 'estero-parada': ('Estero Parada', -72.236, -46.118),
            'laguna-chiguay': ('Laguna Chiguay', -72.067, -45.962),
        },
        'inspection': ['Villa Cerro Castillo'],
        'ice_note': 'Glacier outlines: Chile Dirección General de Aguas, Inventario Público de Glaciares 2022 v2; permanent snowfields, where mapped: OpenStreetMap contributors. Rock glaciers and temporary snow are excluded.',
    },
}


def validate(slug, edition):
    west, south, east, north = edition['bounds']
    outside = [key for key, (_, lon, lat) in edition['destinations'].items()
               if not west <= lon <= east or not south <= lat <= north]
    if outside:
        raise ValueError(f'{slug} anchors outside proposed footprint: {outside}')


def add_route_settings(slug):
    path = ROOT / 'regions' / slug / 'region.json'
    edition = json.loads(path.read_text())
    edition.update({
        'routeCorridor': True,
        'routeBufferMetres': 12000,
        'routeContinuityMaxMetres': 100,
        'coverageBoundary': True,
        'coverageBoundaryLabel': '12 km Jordan Trail walking and access corridor',
        'boundaryAttribution': 'Route alignment © OpenStreetMap contributors, ODbL; official section names and endpoints checked against the Jordan Trail Association.',
        'routeOverlayId': 'jordan-trail-route',
        'optionalBasemapLayers': ['water_name', 'cycling_route', 'ferry', 'island_name'],
    })
    write(path, edition)


if __name__ == '__main__':
    families = [edition['family'] for edition in REGIONS.values()]
    if len(families) != len(set(families)):
        raise ValueError('Duplicate Garmin family ID in nine-map release')
    for slug, config in REGIONS.items():
        validate(slug, config)
        prepare(slug, config)
    add_route_settings('jordan-trail-dana-petra-wadi-rum')
