#!/usr/bin/env python3
"""Inventory actual MVT layer names and feature counts in every generated tile."""
import collections
from contextlib import closing
import gzip
import json
from pathlib import Path
import sqlite3
import sys


def varint(data, offset):
    value = 0
    shift = 0
    while offset < len(data) and shift < 70:
        b = data[offset]
        offset += 1
        value |= (b & 127) << shift
        if b < 128:
            return value, offset
        shift += 7
    raise ValueError('Invalid protobuf varint')


def fields(data):
    offset = 0
    while offset < len(data):
        key, offset = varint(data, offset)
        number, wire = key >> 3, key & 7
        if number == 0:
            raise ValueError('Invalid protobuf field')
        if wire == 0:
            value, offset = varint(data, offset)
        elif wire == 2:
            length, offset = varint(data, offset)
            end = offset + length
            if end > len(data):
                raise ValueError('Truncated protobuf field')
            value, offset = data[offset:end], end
        elif wire in (1, 5):
            end = offset + (8 if wire == 1 else 4)
            if end > len(data):
                raise ValueError('Truncated protobuf field')
            value, offset = data[offset:end], end
        else:
            raise ValueError('Unsupported protobuf wire type')
        yield number, wire, value


def audit(path, expected=None):
    counts = collections.Counter()
    zooms = collections.Counter()
    with closing(sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True)) as db:
        metadata = dict(db.execute('SELECT name,value FROM metadata'))
        for zoom, payload in db.execute('SELECT zoom_level,tile_data FROM tiles'):
            zooms[zoom] += 1
            if payload[:2] == b'\x1f\x8b':
                payload = gzip.decompress(payload)
            for number, wire, layer in fields(payload):
                if number == 3 and wire == 2:
                    name = None
                    features = 0
                    for number, wire, value in fields(layer):
                        if number == 1 and wire == 2:
                            name = value.decode('utf-8')
                        elif number == 2 and wire == 2:
                            features += 1
                    if name is None:
                        raise ValueError('MVT layer lacks a name')
                    counts[name] += features
    if expected is None:
        expected = set(json.loads((Path(__file__).resolve().parents[1] / 'config/tilemaker.json').read_text())['layers'])
    expected=set(expected)
    missing = expected - counts.keys()
    if missing:
        raise ValueError('Missing generated layers: ' + ', '.join(sorted(missing)))
    return {'metadata': metadata, 'tiles_by_zoom': dict(sorted(zooms.items())), 'feature_instances_by_layer': dict(sorted(counts.items())), 'note': 'Feature instances include repetition across tiles and zooms; not unique OSM objects. This checks MVT framing and layer presence, not geometry or cartographic correctness.'}


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('database')
    parser.add_argument('--layers',nargs='+')
    args=parser.parse_args()
    print(json.dumps(audit(args.database,args.layers),indent=2))
