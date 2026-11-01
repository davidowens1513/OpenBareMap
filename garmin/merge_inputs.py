#!/usr/bin/env python3
"""Merge complete OSM and region overlays with libosmium object sorting."""
from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'work/python'))
sys.path.insert(0,str(ROOT/'garmin/work/python'))
from openbaremap import digest,write
from regions import region_path,garmin_work

def merge(region='ireland'):
 import osmium
 work=garmin_work(region)
 source=json.loads(region_path(region,'sources.lock.json').read_text())['osm']
 if digest(ROOT/source['path'])!=source['sha256']:raise ValueError('OSM source mismatch')
 merger=osmium.MergeInputReader();size=merger.add_file(str(work/'overlays.osm.gz'));print('Overlay buffers:',size,flush=True)
 with osmium.io.Reader(str(ROOT/source['path'])) as reader:
  writer=osmium.io.Writer(str(work/'combined.osm.pbf'),reader.header())
  try:merger.apply_to_reader(reader,writer)
  finally:writer.close()
 write(work/'merge-record.json',{'osmSHA256':source['sha256'],'overlaySHA256':digest(work/'overlays.osm.gz'),'combinedSHA256':digest(work/'combined.osm.pbf')})
 print('Sorted complete regional source written',flush=True)
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--region',choices=['ireland','england-wales'],default='ireland');args=parser.parse_args();merge(args.region)
