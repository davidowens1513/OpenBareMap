#!/usr/bin/env python3
"""Derive every Norway DEM cell once from one aligned, checksum-locked mosaic."""
import gzip
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from openbaremap import ROOT, digest, write

REGIONS = ('norway-south', 'norway-central', 'norway-north')

def main():
    output = ROOT / 'data/regions/norway/shared-terrain-v1'
    output.mkdir(parents=True, exist_ok=True)
    if (output / 'complete.json').exists():
        complete = json.loads((output / 'complete.json').read_text())
        if digest(output / 'sources.lock.json') != complete['sourceSHA256']:
            raise ValueError('Installed shared mosaic record changed')
        for region in REGIONS:
            for name in ('terrain-sources.lock.json', 'garmin/dem-padding.lock.json'):
                record = json.loads((ROOT / 'regions' / region / name).read_text())
                if record.get('sharedNorwayTerrain', {}).get('sha256') != complete['sourceSHA256']:
                    raise ValueError('Shared terrain lock not installed: ' + region + '/' + name)
                for item in record['assets'] + record['sourceAssets']:
                    if digest(ROOT / item['path']) != item['sha256']:
                        raise ValueError('Installed terrain input changed: ' + item['path'])
        print('Verified existing complete shared Norway terrain', flush=True)
        return
    locks = {}
    sources = {}
    cells = {}
    for region in REGIONS:
        for name in ('terrain-sources.lock.json', 'garmin/dem-padding.lock.json'):
            path = ROOT / 'regions' / region / name
            record = json.loads(path.read_text())
            if record.get('sharedNorwayTerrain'):
                raise ValueError('Shared terrain already installed; use its existing locks')
            locks[path] = record
            for item in record['sourceAssets']:
                if digest(ROOT / item['path']) != item['sha256']:
                    raise ValueError('Changed source: ' + item['path'])
                if not item['path'].endswith('.tif'):
                    continue
                key = Path(item['path']).name
                if key in sources and sources[key]['sha256'] != item['sha256']:
                    raise ValueError('Neighbouring editions have different source COGs: ' + key)
                sources.setdefault(key, item)
            for item in record['assets']:
                key = Path(item['path']).name
                if key not in cells or 'Bilinear' in item['operation']:
                    cells[key] = item
    toolchain = json.loads((ROOT / 'topography-toolchain.lock.json').read_text())
    tools = {name: toolchain[name]['path'] for name in ('gdalbuildvrt', 'gdalwarp', 'gdal_translate')}
    for name, path in tools.items():
        if digest(path) != toolchain[name]['sha256']:
            raise ValueError('DEM tool changed: ' + name)
    source_record = {
        'format': 'openbaremap-shared-norway-terrain-v1',
        'sources': [sources[k] for k in sorted(sources)],
        'resolutionDegrees': 1 / 3600,
        'alignment': 'One common EPSG:4326 VRT, fixed 1/3600 degree pixels, target-aligned grid',
        'verticalDatum': 'EGM2008 orthometric metres',
        'toolchain': {name: toolchain[name] for name in tools},
        'builderSHA256': digest(Path(__file__)),
    }
    source_lock = output / 'sources.lock.json'
    if source_lock.exists() and json.loads(source_lock.read_text()) != source_record:
        raise ValueError('Shared mosaic inputs changed')
    write(source_lock, source_record)
    source_sha = digest(source_lock)
    env = os.environ.copy()
    env['PROJ_DATA'] = str(Path(toolchain['proj_database']['path']).parent)
    vrt = output / 'source.vrt'
    if not vrt.exists():
        subprocess.run([tools['gdalbuildvrt'], '-resolution', 'user', '-tr', str(1/3600),
                        str(1/3600), '-tap', str(vrt),
                        *[str(ROOT / item['path']) for item in source_record['sources']]],
                       env=env, check=True, stdout=subprocess.DEVNULL)
    derived = {}
    for number, (name, old) in enumerate(sorted(cells.items()), 1):
        target = output / name
        checkpoint = output / (name + '.json')
        if checkpoint.exists():
            item = json.loads(checkpoint.read_text())
            if item['sharedSourceSHA256'] != source_sha or digest(target) != item['sha256']:
                raise ValueError('Changed shared DEM checkpoint: ' + name)
            derived[name] = item
            continue
        match = re.fullmatch(r'N(\d+)([EW])(\d+)\.hgt\.gz', name)
        if not match:
            raise ValueError('Unexpected Norway DEM name: ' + name)
        lat = int(match[1]); lon = int(match[3]) * (-1 if match[2] == 'W' else 1)
        commands = []
        with tempfile.TemporaryDirectory(prefix='OpenBareMap-Norway-DEM-') as temporary:
            temp = Path(temporary); raw = temp / name.removesuffix('.gz')
            if old['operation'].startswith('Zero ocean cell:'):
                if digest(ROOT / old['path']) != old['sha256']:
                    raise ValueError('Changed verified ocean cell: ' + name)
                shutil.copyfile(ROOT / old['path'], target)
            else:
                tif = temp / 'cell.tif'; half = 1 / 7200
                commands = [
                    [tools['gdalwarp'], '-q', '-of', 'GTiff', '-ot', 'Int16',
                     '-t_srs', 'EPSG:4326', '-te', *map(str, [lon-half, lat-half, lon+1+half, lat+1+half]),
                     '-ts', '3601', '3601', '-r', 'bilinear', '-dstnodata', '0', str(vrt), str(tif)],
                    [tools['gdal_translate'], '-q', '-of', 'SRTMHGT', '-a_nodata', '-32768', str(tif), str(raw)],
                ]
                for command in commands:
                    subprocess.run(command, env=env, check=True)
                with raw.open('rb') as src, target.open('wb') as stream, gzip.GzipFile(filename='', mode='wb', fileobj=stream, mtime=0) as dst:
                    shutil.copyfileobj(src, dst)
            if len(gzip.decompress(target.read_bytes())) != 3601 * 3601 * 2:
                raise ValueError('Invalid shared HGT: ' + name)
        item = {**old, 'path': str(target.relative_to(ROOT)), 'bytes': target.stat().st_size,
                'sha256': digest(target), 'sharedSourceSHA256': source_sha, 'commands': commands}
        write(checkpoint, item); derived[name] = item
        print(f'{number}/{len(cells)} shared Norway cell verified: {name}', flush=True)
    # Install locks only after the entire shared dataset is complete.
    backup = ROOT / 'work/norway-terrain-before-alignment'
    for path, old in locks.items():
        saved = backup / path.relative_to(ROOT)
        if not saved.exists():
            saved.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(path, saved)
        record = {**old, 'assets': [derived[Path(item['path']).name] for item in old['assets']],
                  'sharedNorwayTerrain': {'path': str(source_lock.relative_to(ROOT)), 'sha256': source_sha},
                  'sourceAssets': [*old['sourceAssets'], {'path': str(source_lock.relative_to(ROOT)),
                                  'sha256': source_sha, 'bytes': source_lock.stat().st_size}],
                  'commands': [], 'resampling': source_record['alignment']}
        write(path, record)
    write(output / 'complete.json', {'cells': len(derived), 'sourceSHA256': source_sha,
                                    'status': 'Shared cells installed identically in all Norway source locks'})
    print('All Norway shared terrain locks installed', flush=True)

if __name__ == '__main__':
    main()
