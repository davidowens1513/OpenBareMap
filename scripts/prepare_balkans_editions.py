#!/usr/bin/env python3
"""Prepare profiles for the five Balkans walking editions."""
from math import ceil, floor

from pyproj import Transformer

from openbaremap import ROOT, write
from regions import profile

EDITIONS = {
    'peaks-of-the-balkans': {
        'label': 'Peaks of the Balkans', 'bundle': 'Peaks-of-the-Balkans', 'family': 4886,
        'sources': ['albania', 'montenegro', 'kosovo'], 'zone': 34, 'language': 'sq',
        'bounds': [19.52, 42.25, 20.39, 42.81],
        'coverage': 'The Peaks of the Balkans circuit through Albania, Montenegro and Kosovo, including Theth, Valbona, Plav, the Rugova valley and Pejë.',
        'destinations': {
            'theth': ('Theth', 19.769, 42.395), 'valbona': ('Valbona', 19.889, 42.452),
            'cerem': ('Çerem', 19.985, 42.489), 'doberdol': ('Dobërdol', 20.060, 42.549),
            'plav': ('Plav', 19.945, 42.596), 'gusinje': ('Gusinje', 19.833, 42.562),
            'peje': ('Pejë', 20.289, 42.659), 'reka-e-allages': ('Reka e Allagës', 20.178, 42.695),
        },
        'inspection': ['Theth', 'Plav'],
    },
    'durmitor': {
        'label': 'Durmitor', 'bundle': 'Durmitor', 'family': 4887,
        'sources': ['montenegro'], 'zone': 34, 'language': 'sr',
        'bounds': [18.87, 43.0, 19.36, 43.29],
        'coverage': 'Durmitor National Park and approaches, including Žabljak, Black Lake, Bobotov Kuk, the Sedlo trailhead and the Tara Canyon bridge.',
        'destinations': {
            'zabljak': ('Žabljak', 19.121, 43.155), 'black-lake': ('Black Lake', 19.088, 43.144),
            'bobotov-kuk': ('Bobotov Kuk', 19.034, 43.127), 'sedlo': ('Sedlo trailhead', 19.054, 43.100),
            'tara-bridge': ('Tara Canyon bridge', 19.294, 43.150),
        },
        'inspection': ['Bobotov Kuk'],
    },
    'zagori-vikos-gorge': {
        'label': 'Zagori & Vikos Gorge', 'bundle': 'Zagori-Vikos-Gorge', 'family': 4888,
        'sources': ['greece'], 'zone': 34, 'language': 'el',
        'bounds': [20.63, 39.75, 21.15, 40.075],
        'coverage': 'Zagori’s villages and stone bridges, Vikos Gorge, the upper Aoos valley, and the Tymfi massif.',
        'destinations': {
            'monodendri': ('Monodendri', 20.747, 39.882), 'papingo': ('Papingo', 20.717, 39.969),
            'vikos': ('Vikos', 20.691, 39.951), 'tymfi': ('Tymfi', 20.827, 39.976),
            'dragon-lake': ('Dragon Lake', 20.785, 39.985), 'kipoi': ('Kipoi', 20.791, 39.863),
            'konitsa': ('Konitsa', 20.7433, 40.0443),
        },
        'inspection': ['Konitsa'],
    },
    'mount-olympus': {
        'label': 'Mount Olympus', 'bundle': 'Mount-Olympus', 'family': 4889,
        'sources': ['greece'], 'zone': 34, 'language': 'el',
        'bounds': [22.22, 39.92, 22.69, 40.20],
        'coverage': 'Mount Olympus and its trailhead approaches, including Litochoro, Enipeas Gorge, Prionia, Mytikas and the Muses Plateau.',
        'destinations': {
            'litochoro': ('Litochoro', 22.503, 40.103), 'prionia': ('Prionia', 22.406, 40.084),
            'mytikas': ('Mytikas', 22.358, 40.086), 'muses-plateau': ('Muses Plateau', 22.370, 40.095),
            'dion': ('Dion', 22.486, 40.172),
        },
        'inspection': ['Litochoro', 'Mytikas'],
    },
    'menalon-trail': {
        'label': 'Menalon Trail', 'bundle': 'Menalon-Trail', 'family': 4890,
        'sources': ['greece'], 'zone': 34, 'language': 'el',
        'bounds': [21.91, 37.47, 22.29, 37.82],
        'coverage': 'The eight stages of the Menalon Trail from Stemnitsa to Lagkadia, with the Lousios Gorge and the surrounding Arcadian village paths.',
        'destinations': {
            'stemnitsa': ('Stemnitsa', 22.0831, 37.5561), 'dimitsana': ('Dimitsana', 22.041, 37.596),
            'elati': ('Elati', 22.1491, 37.6268), 'vytina': ('Vytina', 22.182, 37.669),
            'magouliana': ('Magouliana', 22.1268, 37.6779), 'valtetsiniko': ('Valtetsiniko', 22.0974, 37.7047),
            'lagkadia': ('Lagkadia', 22.0317, 37.6827), 'lousios-gorge': ('Lousios Gorge', 22.065, 37.544),
        },
        'inspection': ['Stemnitsa', 'Dimitsana'],
    },
}

GREEK_GLYPHS = 'ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩΆΈΉΊΌΎΏαβγδεζηθικλμνξοπρσςτυφχψωάέήίόύώϊΐϋΰ'
LATIN_GLYPHS = 'ÇçËëĆćČčĐđŠšŽž'


def prepare(region, edition):
    template = profile('picos-de-europa')
    label, family = edition['label'], edition['family']
    bounds = edition['bounds']
    west, south, east, north = bounds
    terrain = [floor(west), floor(south), ceil(east), ceil(north)]
    zone = edition['zone']
    crs = f'EPSG:{25800+zone}'
    projection = Transformer.from_crs(4326, crs, always_xy=True)
    xmin, ymin, xmax, ymax = projection.transform_bounds(*bounds)
    stops = edition['destinations']
    for key, (_, lon, lat) in stops.items():
        if not west < lon < east or not south < lat < north:
            raise ValueError(f'{region}: {key} is outside the map')
    template.pop('sourceBaseOverrides', None)
    template.update(
        id=region, name='OpenBareMap '+label, label=label, appBundleName=edition['bundle'],
        coverage=edition['coverage'], bounds=bounds, terrainBounds=terrain,
        coastContextBounds=[terrain[0]-1, terrain[1]-1, terrain[2]+1, terrain[3]+1],
        projectedCRS=crs, gridCRS=crs, gridName=f'ETRS89 / UTM {zone}N',
        gridExtent=[floor(xmin/10000)*10000, ceil(xmax/10000)*10000,
                    floor(ymin/10000)*10000, ceil(ymax/10000)*10000],
        sourceDate='2026-11-17' if edition['language']=='el' else '2026-11-22', sourceSlugs=edition['sources'], sourceCacheRegion='balkans',
        sourceBaseURL='https://download.geofabrik.de/europe/',
        sourceBaseOverrides={slug: f'https://download.geofabrik.de/europe/{slug}/' for slug in edition['sources']},
        terrainCacheRegion='balkans', clipTerrainToBounds=True, repairClippedCoastline=True,
        garminContextBounds=bounds, garminFamilyId=family, garminTileStartId=family*10000+1,
        garminFilename=f'OpenBareMap-{edition["bundle"]}.img', garminPackageRevision='2.0.0-r1',
        garminVersionedDelivery=True, styleRevision=f'2.0.0-{region}-r1',
        nativeLanguage=edition['language'], inspectionNames=edition['inspection'],
        labelGlyphs=GREEK_GLYPHS if edition['language']=='el' else LATIN_GLYPHS,
        terrainNotice=template['terrainNotice'].replace('Picos de Europa elevation',label+' elevation'),
        destinations={'island': [(west+east)/2, (south+north)/2, 10 if region=='peaks-of-the-balkans' else 11],
                      **{key:[lon,lat,12] for key,(_,lon,lat) in stops.items()}},
        destinationLabels={'island':label, **{key:name for key,(name,_,_) in stops.items()}},
        validationAnchors={key:[lon,lat] for key,(_,lon,lat) in stops.items()},
        optionalBasemapLayers=['ferry','island_name','cycling_route','railway','station','hiking_route','boundary'],
    )
    directory = ROOT/'regions'/region
    directory.mkdir(parents=True,exist_ok=True)
    write(directory/'region.json',template)


if __name__ == '__main__':
    for slug, config in EDITIONS.items():
        prepare(slug, config)
