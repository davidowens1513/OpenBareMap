#!/usr/bin/env python3
"""Prepare and pin Chile DGA official glacier coverage for Cerro Castillo."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess

from openbaremap import ROOT, digest, write
from regions import profile, region_path

ARCHIVE = ROOT / 'data/sources/chile/Inventario-Publico-de-Glaciares-2022-v2.zip'
ARCHIVE_SHA256 = 'a67b8dcdb2133ef435450d41c3a9565d56dcdbe180aa0e10fb52148f6cde8151'
DOWNLOAD = ('https://dga.mop.gob.cl/uploads/sites/13/2024/07/'
            'Inventario-Publico-de-Glaciares-2022-v2.zip')
PUBLICATION = 'https://dga.mop.gob.cl/inventario-publico-de-glaciares-actualizacion-2022/'
SHAPEFILE = ('/vsizip/' + str(ARCHIVE) +
             '/Inventario Publico de Glaciares 2022 v2/IPG_2022_v2/IPG_2022_v2.shp')


def build(region):
    if region != 'cerro-castillo':
        raise ValueError('Chile official-glacier preparation is scoped to Cerro Castillo')
    if digest(ARCHIVE) != ARCHIVE_SHA256:
        raise ValueError('Chile DGA glacier inventory archive changed')
    edition = profile(region)
    toolchain = json.loads((ROOT / 'topography-toolchain.lock.json').read_text())
    ogr = Path(toolchain['ogr2ogr']['path'])
    if digest(ogr) != toolchain['ogr2ogr']['sha256']:
        raise ValueError('Locked ogr2ogr changed')
    directory = ROOT / 'data/regions' / region
    directory.mkdir(parents=True, exist_ok=True)
    raw = directory / 'dga-glaciers-2022-v2.raw.geojson'
    output = directory / 'dga-glaciers-2022-v2.geojson'
    if output.exists():
        raise FileExistsError(output)
    env = os.environ.copy()
    env['PROJ_DATA'] = str(Path(toolchain['proj_database']['path']).parent)
    subprocess.run([
        str(ogr), '-f', 'GeoJSON', str(raw), SHAPEFILE,
        '-t_srs', 'EPSG:4326', '-spat', *map(str, edition['bounds']),
        '-where', "CLASIFICA <> 'GLACIAR ROCOSO'",
        '-select', ('COD_GLA,NOM_GLA,NOMBRE,CLASIFICA,AREA_KM2,CUBIERTO,'
                    'FUEN_FECHA,INVE_FECHA'),
        '-lco', 'RFC7946=YES', '-lco', 'COORDINATE_PRECISION=7',
    ], env=env, check=True)
    source = json.loads(raw.read_text())
    features = []
    classifications = {}
    dates = set()
    identifiers = set()
    area = 0.0
    for feature in source['features']:
        original = feature['properties']
        identifier = str(original['COD_GLA']).strip()
        if not identifier or identifier in identifiers:
            raise ValueError('Missing or duplicate DGA glacier identifier: ' + identifier)
        identifiers.add(identifier)
        classification = str(original['CLASIFICA']).strip()
        classifications[classification] = classifications.get(classification, 0) + 1
        if classification == 'GLACIAR ROCOSO':
            raise ValueError('Rock glacier entered delivered ice geometry')
        if original.get('FUEN_FECHA'):
            dates.add(original['FUEN_FECHA'])
        area += float(original.get('AREA_KM2') or 0)
        name = str(original.get('NOMBRE') or original.get('NOM_GLA') or '').strip()
        properties = {
            'class': 'glacier',
            'source': 'Chile DGA Inventario Público de Glaciares 2022 v2',
            'source_id': identifier,
            'glacier_type': classification,
        }
        if name:
            properties.update(name=name, name_es=name)
        features.append({'type': 'Feature', 'geometry': feature['geometry'],
                         'properties': properties})
    if len(features) != 503 or round(area, 8) != 98.48910007:
        raise ValueError(f'Unexpected Cerro Castillo official inventory result: {len(features)}, {area}')
    write(output, {'type': 'FeatureCollection', 'features': features})
    raw.unlink()
    record = {
        'dataset': 'Inventario Público de Glaciares 2022 v2',
        'producer': 'Dirección General de Aguas (DGA), Ministerio de Obras Públicas, Chile',
        'publicationURL': PUBLICATION,
        'downloadURL': DOWNLOAD,
        'archive': {
            'path': str(ARCHIVE.relative_to(ROOT)),
            'sha256': ARCHIVE_SHA256,
            'bytes': ARCHIVE.stat().st_size,
        },
        'sourceLayer': 'IPG_2022_v2',
        'sourceDBFLastUpdate': '2024-11-22',
        'sourceImageDateRange': [min(dates), max(dates)],
        'queryBounds': edition['bounds'],
        'query': "spatial intersection; CLASIFICA <> 'GLACIAR ROCOSO'",
        'path': str(output.relative_to(ROOT)),
        'sha256': digest(output),
        'bytes': output.stat().st_size,
        'accessedUTC': datetime.now(timezone.utc).isoformat(),
        'sourceFeatureCount': len(features),
        'officialGlacierIdentifierCount': len(identifiers),
        'deliveredFeatureCount': len(features),
        'sourceAreaKm2': round(area, 8),
        'sourceClassCounts': classifications,
        'classes': ['glacier'],
        'excluded': ['CLASIFICA=GLACIAR ROCOSO', 'temporary or seasonal snow'],
        'attribution': ('Glacier outlines: Dirección General de Aguas, '
                        'Inventario Público de Glaciares 2022 v2.'),
        'publicAccessBasis': ('Official public vector inventory published by DGA; Chilean '
                              'regulation identifies it as the official glacier register and '
                              'provides public access to its information.'),
    }
    lock_path = region_path(region, 'sources.lock.json')
    lock = json.loads(lock_path.read_text())
    lock['permanentIce'] = record
    write(lock_path, lock)
    print(json.dumps(record, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--region', choices=['cerro-castillo'], required=True)
    args = parser.parse_args()
    build(args.region)
