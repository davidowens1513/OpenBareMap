#!/usr/bin/env python3
"""Create a versioned permanent-ice update using an accepted regional release."""

import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys

from build_cartography_2 import rebuild
from build_region import record_output
from build_region_garmin import compress
from build_region_geometry import landcover
from openbaremap import ROOT, digest, write
from regions import profile, region_path, region_style

VERSION = '2.0.1'
REVISION = VERSION + '-glacier-r1'
LAYER = 'permanent_ice'
PYRENEES_SOURCE_NOTE = ('Glacier outlines are from OpenStreetMap. The 2025 Aneto survey mapped a smaller active glacier.')
WORK = ROOT / 'work/glacier-updates'
WAVES = (
    ('us-glacier', 'us-olympic'),
    ('us-yosemite', 'us-yellowstone-grand-teton', 'us-rocky-mountain'),
    ('alps-west', 'alps-central', 'alps-tyrol-bavaria', 'alps-east', 'dolomites'),
    ('norway-south', 'norway-central', 'norway-north'),
    ('pyrenees',),
)
REGIONS = tuple(region for wave in WAVES for region in wave)


def run(*args, env=None):
    print('Running:', *args, flush=True)
    subprocess.run([sys.executable, *map(str, args)], cwd=ROOT, env=env, check=True)


def extract(region):
    from shapely.geometry import shape
    from shapely.ops import unary_union
    from shapely.prepared import prep

    output = WORK / 'geometry' / region
    output.mkdir(parents=True, exist_ok=True)
    checkpoint = output / 'ice.json'
    if checkpoint.exists():
        return
    settings = profile(region)
    locked = json.loads(region_path(region, 'sources.lock.json').read_text())['osm']
    source = ROOT / locked['path']
    if digest(source) != locked['sha256']:
        raise ValueError('OSM source differs from the accepted release')
    footprint = None
    if settings.get('coverageBoundary'):
        coverage = json.loads(region_path(region, 'coverage.geojson').read_text())
        footprint = prep(unary_union([shape(feature['geometry']) for feature in coverage['features']]))
    pending = output / 'ice.geojson.part'
    counts = landcover(source, pending, settings['bounds'], permanent_ice=True, ice_footprint=footprint, ice_only=True)
    result = output / 'ice.geojson'
    pending.replace(result)
    write(checkpoint, {'region': region, 'sourceSHA256': locked['sha256'],
                       'geometrySHA256': digest(result), 'permanentIce': counts['permanentIce']})


def add_ice_layer(ice, bounds, original, target, directory):
    config = {'layers': {LAYER: {'minzoom': 4, 'maxzoom': 14, 'source': str(ice),
                                  'source_columns': ['class', 'name', 'name_en'],
                                  'simplify_below': 14, 'simplify_level': 0.000008, 'simplify_ratio': 2}},
              'settings': {'minzoom': 4, 'maxzoom': 14, 'basezoom': 14, 'bounding_box': bounds,
                           'include_ids': False, 'compress': 'gzip', 'name': 'OpenBareMap permanent ice',
                           'description': 'Mapped glacier and permanent snowfield polygons', 'version': VERSION}}
    config_file = directory / 'tilemaker.json'
    write(config_file, config)
    process = directory / 'process.lua'
    process.write_text('node_keys={}\nway_keys={}\nfunction node_function() end\nfunction way_function() end\n')
    tiles = directory / 'ice.mbtiles'
    if not tiles.exists():
        tool = shutil.which('tilemaker')
        if digest(tool) != json.loads((ROOT / 'toolchain.lock.json').read_text())['tilemaker']['sha256']:
            raise ValueError('Tilemaker changed')
        with (directory / 'tilemaker.log').open('w') as log:
            subprocess.run([tool, '--output', str(tiles), '--config', str(config_file),
                            '--process', str(process), '--threads', '1'], stdout=log, stderr=subprocess.STDOUT, check=True)
    report = rebuild(original, target, tiles, LAYER)
    if report['replacement_feature_instances'] == 0:
        raise ValueError('No ice polygons survived tiling')
    with closing(sqlite3.connect(tiles)) as source, closing(sqlite3.connect(target)) as output:
        added = json.loads(source.execute("SELECT value FROM metadata WHERE name='json'").fetchone()[0])
        schema = json.loads(output.execute("SELECT value FROM metadata WHERE name='json'").fetchone()[0])
        if any(layer['id'] == LAYER for layer in schema['vector_layers']):
            raise ValueError('Original basemap already advertises a permanent ice overlay')
        schema['vector_layers'].extend(added['vector_layers'])
        output.execute("UPDATE metadata SET value=? WHERE name='json'", (json.dumps(schema),))
        output.execute("UPDATE metadata SET value=? WHERE name='version'", (VERSION,))
        output.commit()
    return report['unchanged_other_layers_sha256']


def preserve_inputs(region, prior, geometry):
    garmin = region_path(region, 'garmin')
    garmin.mkdir(exist_ok=True)
    for name in ('style', 'coverage.poly', 'dem-padding.lock.json', 'coastal-context', 'inputs', 'device-installations.json'):
        old, new = prior / name, garmin / name
        if not old.exists() or new.exists():
            continue
        if old.is_dir():
            shutil.copytree(old, new, copy_function=shutil.copy2 if name == 'style' else os.link)
        else:
            shutil.copy2(old, new)
    lock = garmin / 'inputs.lock.json'
    if not lock.exists():
        inputs = json.loads((prior / lock.name).read_text())
        for item in inputs['inputs']:
            if digest(ROOT / item['path']) != item['sha256']:
                raise ValueError('Prior Garmin input differs from locked build')
        inputs['inputs'].append(compress(geometry / 'ice.geojson', garmin / 'inputs/permanent-ice.geojson.gz'))
        write(lock, inputs)
    dist = garmin / 'dist'
    dist.mkdir(exist_ok=True)
    for old_image in (prior / 'dist').glob('*.img'):
        target = dist / old_image.name
        if not target.exists():
            os.link(old_image, target)


def prepare(region):
    edition = region_path(region, '')
    pending = WORK / 'geometry' / region
    backup = WORK / 'previous' / region
    backup.mkdir(parents=True, exist_ok=True)
    release = ROOT / 'releases' / region / VERSION
    report_path = release / 'permanent-ice-update.json'
    if report_path.is_file():
        return
    profile_path = edition / 'region.json'
    active_path = edition / 'active-map.json'
    for source in (profile_path, active_path, edition / 'style.json'):
        saved = backup / source.name
        if not saved.exists():
            shutil.copy2(source, saved)
    old = json.loads((backup / 'active-map.json').read_text())
    settings = json.loads((backup / 'region.json').read_text())
    if old['mapVersion'] != '2.0.0' or settings['mapVersion'] != old['mapVersion']:
        raise ValueError('Expected the accepted 2.0.0 inputs')
    locked = json.loads((edition / 'sources.lock.json').read_text())['osm']
    extract(region)
    ice = json.loads((pending / 'ice.json').read_text())
    if ice['sourceSHA256'] != locked['sha256'] or not ice['permanentIce']['glacier']:
        raise ValueError('Expected glacier geometry from the accepted source')
    if digest(pending / 'ice.geojson') != ice['geometrySHA256']:
        raise ValueError('Ice geometry differs from its extraction checkpoint')
    for dataset in old['datasets'].values():
        if digest(ROOT / dataset['path']) != dataset['sha256']:
            raise ValueError('A selected input differs from its accepted checksum')
    maps = release / 'maps'
    maps.mkdir(parents=True, exist_ok=True)
    target = maps / 'basemap.mbtiles'
    dataset_record = pending / 'basemap-record.json'
    if not dataset_record.exists():
        new = pending / 'basemap-building.mbtiles'
        old_base = ROOT / old['datasets']['basemap']['path']
        checksum = add_ice_layer(pending / 'ice.geojson', settings['bounds'], old_base, new, pending)
        new.replace(target)
        write(dataset_record, {'basemap': record_output(target), 'unchangedBaseLayersSHA256': checksum})
    record = json.loads(dataset_record.read_text())
    if digest(target) != record['basemap']['sha256']:
        raise ValueError('New basemap does not match its checkpoint')
    geometry = release / 'build-records' / (region + '-geometry')
    geometry.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(pending / 'ice.geojson', geometry / 'ice.geojson')
    write(geometry / 'geometry-report.json', {'region': region, 'osm': locked, 'outputs': {'ice.geojson': ice['geometrySHA256']},
                                              'counts': {'permanentIce': ice['permanentIce']}, 'permanentIce': ice['permanentIce']})
    for name in ('garmin', 'legend', 'ios', 'android', 'exports'):
        original, prior = edition / name, backup / name
        if original.exists() and not prior.exists():
            original.rename(prior)
    preserve_inputs(region, backup / 'garmin', geometry)
    old_name = Path(json.loads((backup / 'garmin/build-report.json').read_text())['output']['path']).stem
    settings.update(mapVersion=VERSION, permanentIce=True, permanentIceLayer=LAYER, styleRevision=REVISION,
                    garminPackageRevision=REVISION, garminFilename=old_name + '-Glaciers.img')
    if region == 'pyrenees':
        settings['permanentIceSourceNote'] = PYRENEES_SOURCE_NOTE
    write(profile_path, settings)
    selected = dict(old, mapVersion=VERSION, storageRevision=REVISION, styleRevision=REVISION,
                    datasets=dict(old['datasets'], basemap=record['basemap']))
    write(active_path, selected)
    write(edition / 'style.json', region_style(region))
    write(report_path, {'previousMapVersion': old['mapVersion'], 'mapVersion': VERSION,
                        'preservedTerrain': {name: old['datasets'][name] for name in ('topography', 'hillshade', 'grid')},
                        'preservedBasemapLayersSHA256': record['unchangedBaseLayersSHA256'], 'iceExtraction': ice})


def build(region):
    prepare(region)
    edition = region_path(region, '')
    release = ROOT / 'releases' / region / VERSION
    if not (edition / 'legend/legend-manifest.json').exists():
        run('scripts/build_app_legend.py', '--region', region)
    for platform, script in [('ios', 'ios/build_bundle.py'), ('android', 'android/build_package.py')]:
        destination = edition / platform
        if not (destination / 'validation.json').exists():
            run(script, '--region', region, '--output', destination)
    if not (edition / 'garmin/build-report.json').exists():
        env = dict(os.environ, OPENBAREMAP_BUILD_ROOT=str(WORK / 'native'))
        run('scripts/build_region_garmin.py', '--region', region, '--geometry',
            release / 'build-records' / (region + '-geometry'), env=env)
    if not (release / 'validation.json').exists():
        run('scripts/validate_region.py', '--region', region)
    products = WORK / region
    if not (products / 'kits' / region / 'manifest.json').exists():
        run('scripts/build_app_distribution.py', '--regions', region, '--output', products / 'kits',
            '--catalog', products / 'catalog.json')
    if not (products / 'preview/manifest.json').exists():
        origin = f'https://downloads.appsbyonzy.dev/OpenBareMap/{region}/{VERSION}/preview'
        run('scripts/build_web_previews.py', '--regions', region, '--output', products / 'preview', '--origin', origin,
            '--cached-preview', 'work/canadian-rockies-banff-release/preview')
    print(region, 'versioned glacier release ready for staging', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--extract-only', action='store_true')
    parser.add_argument('regions', nargs='+', choices=REGIONS)
    arguments = parser.parse_args()
    for region in arguments.regions:
        (extract if arguments.extract_only else build)(region)
