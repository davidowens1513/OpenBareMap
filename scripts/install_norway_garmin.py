#!/usr/bin/env python3
"""Install the three Norway maps on Montana, H1 and 67i; verify full readbacks."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
REGIONS = ('norway-south', 'norway-central', 'norway-north')
WORK = ROOT / 'work/norway-device-install'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
    temporary.replace(path)


def helper(name):
    source = ROOT / 'garmin/tools' / (name + '.c')
    binary = WORK / name
    if not binary.exists() or source.stat().st_mtime > binary.stat().st_mtime:
        subprocess.run(['clang', '-Wno-deprecated-declarations', '-I/opt/homebrew/include',
                        '-L/opt/homebrew/lib', str(source), '-lmtp', '-o', str(binary)], check=True)
    return str(binary)


def devices(inventory, required):
    found, current = {}, None
    for line in inventory.splitlines():
        parts = line.split('\t')
        if parts[0] == 'DEVICE':
            current = parts[2]
            if current in found:
                raise ValueError('More than one attached device has model ' + current)
            found[current] = {'index': parts[1], 'storages': {}, 'folders': {}}
        elif current and parts[0] == 'STORAGE':
            found[current]['storages'][int(parts[2])] = int(parts[3])
        elif current and parts[0] == 'GARMIN':
            found[current]['folders'][int(parts[2])] = int(parts[3])
    targets = []
    for model in ('GPSMAP H1', 'GPSMAP 67i'):
        if model not in found:
            raise ValueError(model + ' is not visible through USB/MTP. Run this installer in your Mac Terminal.')
        d = found[model]
        choices = [(storage, folder) for storage, folder in d['folders'].items()
                   if d['storages'].get(storage, 0) > required + 64 * 1024 * 1024]
        # Match the previously accepted installation locations, but rediscover folder IDs.
        preferred = 65537 if model == 'GPSMAP H1' else 131073
        if any(storage == preferred for storage, _ in choices):
            choices = [(storage, folder) for storage, folder in choices if storage == preferred]
        if len(choices) != 1:
            raise ValueError('Cannot select one Garmin storage with enough space on ' + model)
        targets.append((model, *choices[0]))
    return targets


def record(region, item):
    path = ROOT / 'regions' / region / 'garmin/device-installations.json'
    data = json.loads(path.read_text()) if path.exists() else {'region': region, 'devices': []}
    data['devices'] = [r for r in data['devices'] if r.get('device') != item['device']] + [item]
    write(path, data)
    path = ROOT / 'garmin/device-installations.json'
    data = json.loads(path.read_text())
    data['devices'] = [r for r in data['devices']
                       if (r.get('region'), r.get('device')) != (region, item['device'])] + [item]
    data['lastInstallationUpdate'] = item['verifiedUTC'][:10]
    write(path, data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install', action='store_true', help='Copy after all device checks pass')
    parser.add_argument('--montana-volume', type=Path, default=Path('/Volumes/NO NAME'))
    args = parser.parse_args()
    WORK.mkdir(parents=True, exist_ok=True)
    sources = []
    for region in REGIONS:
        manifest = json.loads((ROOT / 'distribution/app-bundles-v1/garmin' / region / 'manifest.json').read_text())
        candidates = list((ROOT / 'regions' / region / 'garmin/dist').glob('OpenBareMap-Norway-*.img'))
        if len(candidates) != 1:
            raise ValueError('Expected one map image for ' + region)
        source = candidates[0]
        print('Checking source:', source.name, flush=True)
        if source.stat().st_size != manifest['bytes'] or digest(source) != manifest['imageSHA256']:
            raise ValueError('Source image does not match published checksum: ' + region)
        sources.append((region, source, manifest))
    required = sum(m['bytes'] for _, _, m in sources)
    montana_xml = Path('/Volumes/GARMIN/Garmin/GarminDevice.xml')
    model = ET.parse(montana_xml).find('.//{*}Model/{*}Description').text
    if model != 'Montana 750i':
        raise ValueError('Mounted Garmin is not the expected Montana 750i')
    folder = args.montana_volume / 'Garmin'
    if not folder.is_dir() or shutil.disk_usage(folder).free < required + 64 * 1024 * 1024:
        raise ValueError('Montana memory card is unavailable or lacks free space')
    print('Checking attached H1 and 67i (this may take a moment)', flush=True)
    result = subprocess.run([helper('mtp_inventory')], text=True, capture_output=True)
    (WORK / 'inventory-private.log').write_text(result.stdout + result.stderr)
    if result.returncode:
        raise ValueError('USB/MTP device inventory is unavailable in this session. '
                         'Run this installer in your Mac Terminal with the three Garmins connected.')
    targets = devices(result.stdout, required)
    if shutil.disk_usage(WORK).free < max(m['bytes'] for _, _, m in sources) + 64 * 1024 * 1024:
        raise ValueError('Not enough local space for one full map readback')
    print('All three devices checked; Norway maps total', required, 'bytes per device', flush=True)
    if not args.install:
        print('Preflight passed. Add --install to copy the maps.', flush=True)
        return
    installer = helper('mtp_install')
    for region, source, manifest in sources:
        expected = manifest['imageSHA256']
        common = {'region': region, 'file': source.name, 'bytes': manifest['bytes'],
                  'sha256': expected, 'mapVersion': '2.0.0',
                  'familyId': 4839 + REGIONS.index(region),
                  'garminPackageRevision': '2.0.1-trail-detail-r1',
                  'fullReadbackVerified': True,
                  'hardwareVisualReview': 'Pending restart and on-screen review'}
        print('Montana 750i:', source.name, flush=True)
        before = {p.name: p.stat().st_size for p in folder.iterdir() if p.is_file()}
        target = folder / source.name
        if not target.exists():
            staged = folder / (source.name + '.uploading')
            with source.open('rb') as src, staged.open('xb') as dst:
                copied, milestone = 0, 0
                while chunk := src.read(1024 * 1024):
                    dst.write(chunk); copied += len(chunk)
                    if copied - milestone >= 64 * 1024 * 1024:
                        print('  copied', copied, '/', manifest['bytes'], flush=True); milestone = copied
                dst.flush(); os.fsync(dst.fileno())
            if digest(staged) != expected:
                raise ValueError('Montana staged checksum mismatch; not activated')
            staged.rename(target)
        if digest(target) != expected:
            raise ValueError('Existing Montana image differs; no replacement performed')
        if not all((folder / name).stat().st_size == size for name, size in before.items()):
            raise ValueError('Existing Montana file size changed')
        record(region, {**common, 'device': 'Montana 750i', 'storage': str(folder),
                        'otherMapNamesAndSizesPreserved': True,
                        'verifiedUTC': datetime.now(timezone.utc).isoformat()})
        print('Montana full checksum verified', flush=True)
        for model, storage, folder_id in targets:
            slug = 'h1' if model == 'GPSMAP H1' else '67i'
            readback = WORK / ('readback-' + slug + '.img')
            print(model + ': ' + source.name + ' (copy, then full readback)', flush=True)
            process = subprocess.Popen([installer, model, str(storage), str(folder_id),
                                        str(source), str(readback), source.name],
                                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            installed = None
            with (WORK / (region + '-' + slug + '.log')).open('w') as log:
                for line in process.stdout:
                    log.write(line); log.flush(); print(line, end='', flush=True)
                    if line.startswith('INSTALLED\t'):
                        installed = line.rstrip().split('\t')
            if process.wait() or installed is None or digest(readback) != expected:
                raise ValueError('Transfer/readback failed for ' + model + '/' + region)
            record(region, {**common, 'device': model, 'storageId': storage, 'folderId': folder_id,
                            'objectId': int(installed[4]), 'otherMapNamesAndSizesPreserved': True,
                            'verifiedUTC': datetime.now(timezone.utc).isoformat()})
            readback.unlink()
            print(model, 'full checksum verified', flush=True)
    print('SUCCESS: all three Norway maps installed and fully verified on all three Garmins.', flush=True)


if __name__ == '__main__':
    main()
