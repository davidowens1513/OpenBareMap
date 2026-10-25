#!/usr/bin/env python3
"""Explicit source registration and recorded all-Ireland builds. Python standard library only."""
import argparse
from contextlib import closing
import gzip
import hashlib
import json
import re
import shutil
import sqlite3
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def build_name(value):
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,63}',value):
        raise argparse.ArgumentTypeError('Use a short build name containing lowercase letters, digits, underscores or hyphens')
    return value

def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')

def inspect_tiles(path):
    """Compare logical tile payloads, independent of SQLite layout and gzip timestamps."""
    h = hashlib.sha256()
    count = 0
    empty = 0
    with closing(sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True)) as db:
        result = db.execute('PRAGMA integrity_check').fetchone()[0]
        if result != 'ok':
            raise ValueError('SQLite integrity check failed: ' + result)
        for z, x, y, payload in db.execute('SELECT zoom_level,tile_column,tile_row,tile_data FROM tiles ORDER BY zoom_level,tile_column,tile_row'):
            if not 0 <= z <= 30 or not (0 <= x < 2**z and 0 <= y < 2**z):
                raise ValueError('Invalid tile coordinates')
            if payload[:2] == b'\x1f\x8b':
                payload = gzip.decompress(payload)
            if not payload:
                empty += 1
            h.update(f'{z}/{x}/{y}:{len(payload)}:'.encode())
            h.update(payload)
            count += 1
    if count == 0 or empty == count:
        raise ValueError('No nonempty tiles generated')
    return {'tile_count': count, 'empty_tile_count': empty, 'logical_tiles_sha256': h.hexdigest()}

def register(args):
    path = Path(args.input).resolve()
    if not path.is_file() or not path.name.endswith('.osm.pbf'):
        raise ValueError('Provide an existing .osm.pbf source file')
    lock = ROOT / 'sources.lock.json'
    if lock.exists():
        raise ValueError('A source is already registered; review and rename sources.lock.json before replacing it')
    stored_path = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
    write(lock, {'osm': {'path': stored_path, 'url': args.url, 'snapshot_date': args.date, 'sha256': digest(path), 'bytes': path.stat().st_size}})
    print('Source registered; its exact content will be checked before every build.')

def build(args):
    lock = ROOT / 'sources.lock.json'
    if not lock.exists():
        raise ValueError('Register an OSM source first. See README.md.')
    source = json.loads(lock.read_text())['osm']
    source_path = Path(source['path'])
    if not source_path.is_absolute():
        source_path = ROOT / source_path
    if digest(source_path) != source['sha256']:
        raise ValueError('Source checksum changed; build refused')
    tool = shutil.which('tilemaker')
    if not tool:
        raise ValueError('Tilemaker is not installed')
    version = subprocess.run([tool, '--help'], capture_output=True, text=True, check=True).stdout.splitlines()[0]
    identity = {'version': version, 'sha256': digest(tool)}
    tool_lock = ROOT / 'toolchain.lock.json'
    if not tool_lock.exists():
        if not args.accept_toolchain:
            raise ValueError('First build requires --accept-toolchain to record the installed Tilemaker binary')
        write(tool_lock, {'tilemaker': identity, 'scope': 'local binary identity; container and library pinning pending'})
    if json.loads(tool_lock.read_text())['tilemaker'] != identity:
        raise ValueError('Tilemaker differs from the recorded toolchain')
    destination = ROOT / 'build' / args.name
    destination.mkdir(parents=True, exist_ok=False)
    region = json.loads((ROOT / 'config/region.json').read_text())
    config = json.loads((ROOT / 'config/tilemaker.json').read_text())
    config['settings']['minzoom'] = region['minzoom']
    config['settings']['maxzoom'] = region['maxzoom']
    write(destination / 'tilemaker.json', config)
    shutil.copy2(ROOT / 'config/process.lua', destination / 'process.lua')
    command = [tool, '--input', str(source_path), '--output', str(destination / 'basemap.mbtiles'), '--config', str(destination / 'tilemaker.json'), '--process', str(destination / 'process.lua'), '--threads', '1']
    record = {'status': 'started', 'source': source, 'region': region, 'toolchain': identity, 'command': command, 'config_sha256': digest(destination / 'tilemaker.json'), 'process_sha256': digest(destination / 'process.lua')}
    write(destination / 'build.json', record)
    with (destination / 'build.log').open('w') as log:
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
    record['status'] = 'failed'
    record['exit_code'] = result.returncode
    write(destination / 'build.json', record)
    if result.returncode:
        raise ValueError('Tilemaker failed; inspect ' + str(destination / 'build.log'))
    record['validation'] = inspect_tiles(destination / 'basemap.mbtiles')
    from audit import audit
    write(destination / 'audit.json', audit(destination / 'basemap.mbtiles'))
    record['output_sha256'] = digest(destination / 'basemap.mbtiles')
    record['status'] = 'validated vector build'
    write(destination / 'build.json', record)
    print(json.dumps(record['validation'], indent=2))

def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='action', required=True)
    reg = sub.add_parser('register')
    reg.add_argument('input')
    reg.add_argument('--url', required=True)
    reg.add_argument('--date', required=True, help='Actual source snapshot date, YYYY-MM-DD')
    run = sub.add_parser('build')
    run.add_argument('name',type=build_name)
    run.add_argument('--accept-toolchain', action='store_true')
    compare = sub.add_parser('compare')
    compare.add_argument('first',nargs='?',default='ireland-a',type=build_name)
    compare.add_argument('second',nargs='?',default='ireland-b',type=build_name)
    args = parser.parse_args()
    try:
        if args.action == 'register':
            from datetime import date
            date.fromisoformat(args.date)
            register(args)
        elif args.action == 'build':
            build(args)
        else:
            a = inspect_tiles(ROOT / 'build' / args.first / 'basemap.mbtiles')
            b = inspect_tiles(ROOT / 'build' / args.second / 'basemap.mbtiles')
            if a != b:
                raise ValueError('Tile payloads differ between builds')
            print('PASS: coordinate-sorted, decompressed tile payloads match. Metadata and visual correctness require separate review.')
    except (ValueError, OSError, KeyError, sqlite3.Error, subprocess.SubprocessError) as error:
        parser.exit(1, str(error) + '\n')

if __name__ == '__main__':
    main()
