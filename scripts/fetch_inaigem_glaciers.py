#!/usr/bin/env python3
"""Fetch and pin the official INAIGEM 2026 glacier outlines for Peru editions."""

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import urllib.parse
import urllib.request

from openbaremap import ROOT, digest, write
from regions import profile, region_path

sys.path.insert(0, str(ROOT / 'work/python'))

SERVICE = ('https://services6.arcgis.com/c9GFTG11debu0wsH/arcgis/rest/services/'
           'BD_Inventario_Glaciares_2026/FeatureServer/0')
SERVICE_ITEM = '1f263580b58c401bbe5dce56fb9b34e0'
REPORT = ('https://sinia.minam.gob.pe/sites/default/files/archivos/public/docs/'
          'Inventario%20Nacional%20de%20Glaciares%202023.pdf')
EDITIONS = {
    'cordillera-blanca': 'Blanca',
    'cordillera-huayhuash': 'Huayhuash',
}


def request_json(url, parameters=None):
    if parameters:
        url += '?' + urllib.parse.urlencode(parameters)
    request = urllib.request.Request(
        url, headers={'User-Agent': 'OpenBareMap/2.0 (+https://openbaremap.org)'})
    with urllib.request.urlopen(request, timeout=180) as response:
        result = json.load(response)
    if 'error' in result:
        raise RuntimeError(result['error'])
    return result


def write_collection(path, features):
    with path.open('w') as stream:
        stream.write('{"type":"FeatureCollection","features":[\n')
        for index, feature in enumerate(features):
            if index:
                stream.write(',\n')
            stream.write(json.dumps(feature, ensure_ascii=False, separators=(',', ':')))
        stream.write('\n]}\n')


def build(region):
    from shapely.geometry import mapping, shape
    from shapely.ops import unary_union

    cordillera = EDITIONS[region]
    query = f"cordillera='{cordillera}' AND tipo_glac IN ('Cubierto','Descubierto')"
    source = request_json(SERVICE + '/query', {
        'f': 'geojson',
        'where': query,
        'outFields': ('FID,id,cod_glac,nomb_glac,tipo_glac,unidad_gla,cordillera,'
                      'area_m2,area_km2,imagen'),
        'outSR': 4326,
        'returnGeometry': 'true',
        'resultRecordCount': 2000,
    })
    if source.get('exceededTransferLimit'):
        raise ValueError('INAIGEM query exceeded its transfer limit')
    raw = source['features']
    groups = defaultdict(list)
    metadata = {}
    source_types = defaultdict(set)
    source_units = defaultdict(set)
    imagery = set()
    area = defaultdict(float)
    for feature in raw:
        properties = feature['properties']
        code = str(properties['cod_glac']).strip()
        if not code:
            raise ValueError('Official glacier feature has no cod_glac')
        geometry = shape(feature['geometry'])
        if geometry.is_empty:
            raise ValueError('Official glacier feature has empty geometry: ' + code)
        if not geometry.is_valid:
            geometry = geometry.buffer(0)
        groups[code].append(geometry)
        metadata.setdefault(code, properties)
        source_types[code].add(properties['tipo_glac'])
        source_units[code].add(properties['unidad_gla'])
        if properties.get('imagen'):
            imagery.add(properties['imagen'])
        area[code] += float(properties.get('area_km2') or 0)
    delivered = []
    for code in sorted(groups):
        geometry = unary_union(groups[code])
        if geometry.is_empty or not geometry.is_valid:
            raise ValueError('Could not dissolve official glacier geometry: ' + code)
        name = str(metadata[code].get('nomb_glac') or '').strip()
        properties = {
            'class': 'glacier',
            'source': 'INAIGEM Inventario Nacional de Glaciares 2026',
            'source_id': code,
            'glacier_type': ','.join(sorted(source_types[code])),
            'glacier_unit': ','.join(sorted(source_units[code])),
            'source_area_km2': round(area[code], 8),
        }
        if name:
            properties.update(name=name, name_es=name)
        delivered.append({'type': 'Feature', 'geometry': mapping(geometry),
                          'properties': properties})
    # Huayhuash also has seven separately identified rock glaciers in the
    # service. They are periglacial debris forms, not glacier/snow symbols.
    expected = {'cordillera-blanca': 495, 'cordillera-huayhuash': 83}[region]
    if len(delivered) != expected:
        raise ValueError(f'Expected {expected} official glacier identifiers, got {len(delivered)}')
    directory = ROOT / 'data/regions' / region
    directory.mkdir(parents=True, exist_ok=True)
    output = directory / 'inaigem-glaciers-2026.geojson'
    if output.exists():
        raise FileExistsError(output)
    write_collection(output, delivered)
    layer = request_json(SERVICE, {'f': 'json'})
    item = request_json('https://www.arcgis.com/sharing/rest/content/items/' + SERVICE_ITEM,
                        {'f': 'json'})
    record = {
        'dataset': 'INAIGEM Inventario Nacional de Glaciares 2026',
        'producer': ('Instituto Nacional de Investigación en Glaciares y Ecosistemas de '
                     'Montaña (INAIGEM), Peru'),
        'serviceItemId': SERVICE_ITEM,
        'serviceURL': SERVICE,
        'query': query,
        'cordillera': cordillera,
        'path': str(output.relative_to(ROOT)),
        'sha256': digest(output),
        'bytes': output.stat().st_size,
        'accessedUTC': datetime.now(timezone.utc).isoformat(),
        'serviceCreatedEpochMs': item['created'],
        'serviceModifiedEpochMs': item['modified'],
        'serviceCapabilities': layer['capabilities'],
        'sourceImagery': sorted(imagery),
        'sourceFeatureCount': len(raw),
        'officialGlacierIdentifierCount': len(groups),
        'deliveredDissolvedFeatureCount': len(delivered),
        'sourceAreaKm2': round(sum(area.values()), 8),
        'classes': ['glacier'],
        'excluded': ['tipo_glac=Rocoso (rock glaciers)', 'temporary or seasonal snow'],
        'attribution': 'Glacier outlines: INAIGEM, Inventario Nacional de Glaciares 2026.',
        'useTerms': ('INAIGEM makes the cartographic inventory available for public use and '
                     'requires users to reference INAIGEM; the ArcGIS item has no separate '
                     'licenseInfo field.'),
        'methodReference': REPORT,
        'methodNote': ('The preceding INGLOG II report documents the public shapefile, '
                       '1:25,000 interpretation scale, and INAIGEM attribution requirement.'),
    }
    lock_path = region_path(region, 'sources.lock.json')
    lock = json.loads(lock_path.read_text())
    lock['permanentIce'] = record
    write(lock_path, lock)
    print(json.dumps(record, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--region', choices=EDITIONS, required=True)
    arguments = parser.parse_args()
    if profile(arguments.region).get('permanentIceSourceNote', '').find('INAIGEM') < 0:
        parser.error('Region profile does not select INAIGEM permanent ice')
    build(arguments.region)
