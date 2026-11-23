#!/usr/bin/env python3
"""Prepare Latin-script cartographic names for regional app and Garmin maps."""
import argparse
import json
import re
import shutil
import subprocess
import unicodedata

import osmium

from openbaremap import ROOT, digest, write
from regions import NEPAL_REGIONS, region_path

DEVANAGARI = re.compile(r'[\u0900-\u097f]')
LABEL_FIELDS = ('name', 'official_name', 'short_name')
TRANSLITERATION = 'Devanagari-Latin; Latin-ASCII'
ARABIC = re.compile(r'[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff]')
LABEL_REGIONS = (*NEPAL_REGIONS, 'high-atlas-toubkal')


def prepare(region):
    arabic = region == 'high-atlas-toubkal'
    script = ARABIC if arabic else DEVANAGARI
    language = 'ar' if arabic else 'ne'
    rule = 'Arabic-Latin; Latin-ASCII' if arabic else TRANSLITERATION
    lock_path = region_path(region, 'sources.lock.json')
    lock = json.loads(lock_path.read_text())
    if 'labelPreparation' in lock:
        for item in (lock['clippedOSM'], lock['osm']):
            if digest(ROOT / item['path']) != item['sha256']:
                raise ValueError('Changed regional label input: ' + item['path'])
        return
    original = lock['osm']
    source = ROOT / original['path']
    if digest(source) != original['sha256']:
        raise ValueError(f'Changed clipped OpenStreetMap extract: {source}')
    target = source.with_name(source.name.removesuffix('.osm.pbf') + '.latin.osm.pbf')
    pending = target.with_name(target.name + '.part.pbf')
    uconv = shutil.which('uconv') or '/opt/homebrew/opt/icu4c/bin/uconv'
    names = sorted({
        value
        for obj in osmium.FileProcessor(str(source))
        for key in LABEL_FIELDS
        if (value := obj.tags.get(key)) and script.search(value)
    })
    if any('\n' in name or '\r' in name for name in names):
        raise ValueError('Unexpected newline in a label')
    result = subprocess.check_output([uconv, '-x', rule], input='\n'.join(names), text=True)
    translated = {
        name: ''.join(char for char in unicodedata.normalize('NFKD', label)
                      if not unicodedata.combining(char) and (not arabic or char.isascii())).strip()
        for name, label in zip(names, result.splitlines(), strict=True)
    }
    if any(not label or script.search(label) for label in translated.values()):
        raise ValueError('Incomplete regional name transliteration')
    with osmium.io.Reader(str(source)) as reader:
        header = reader.header()
    changed = 0
    with osmium.SimpleWriter(str(pending), header=header, overwrite=True) as writer:
        for obj in osmium.FileProcessor(str(source)):
            tags = dict(obj.tags)
            updates = {key: translated[tags[key]] for key in LABEL_FIELDS if tags.get(key) in translated}
            if updates:
                if 'name' in updates:
                    tags.setdefault('name:'+language, tags['name'])
                    latin = tags.get('name:en') or tags.get('name:'+language+'-Latn') or (tags.get('name:fr') if arabic else None)
                    if latin and not script.search(latin):
                        updates['name'] = latin
                tags.update(updates)
                writer.add(obj.replace(tags=tags))
                changed += 1
            else:
                writer.add(obj)
    pending.replace(target)
    lock['clippedOSM'] = original
    lock['osm'] = {**original, 'path': str(target.relative_to(ROOT)),
                   'sha256': digest(target), 'bytes': target.stat().st_size,
                   'operation': 'Complete-feature regional extract with Latin cartographic names'}
    lock['labelPreparation'] = {
        'transliterator': subprocess.check_output([uconv, '--version'], text=True).strip(),
        'rule': rule + ('; retain ASCII' if arabic else '; strip combining marks'), 'nameFields': list(LABEL_FIELDS),
        'updatedObjects': changed, ('uniqueArabicLabels' if arabic else 'uniqueDevanagariLabels'): len(names),
    }
    write(lock_path, lock)
    print(f'{region}: prepared Latin-script names on {changed} OSM objects', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--region', choices=LABEL_REGIONS, required=True)
    prepare(parser.parse_args().region)
