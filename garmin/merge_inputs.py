#!/usr/bin/env python3
"""Merge contour/coast/townland overlays with OSM using libosmium object sorting."""
from pathlib import Path
import json,hashlib,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'garmin/work/python'))
import osmium
work=ROOT/'garmin/work'
source=json.loads((ROOT/'sources.lock.json').read_text())['osm']
with (ROOT/source['path']).open('rb') as f:
 if hashlib.file_digest(f,'sha256').hexdigest()!=source['sha256']:raise ValueError('OSM source mismatch')
merger=osmium.MergeInputReader();size=merger.add_file(str(work/'overlays.osm.gz'));print('Overlay buffers:',size,flush=True)
with osmium.io.Reader(str(ROOT/source['path'])) as reader:
 writer=osmium.io.Writer(str(work/'combined.osm.pbf'),reader.header())
 try:merger.apply_to_reader(reader,writer)
 finally:writer.close()
print('Sorted full-island source written',flush=True)
