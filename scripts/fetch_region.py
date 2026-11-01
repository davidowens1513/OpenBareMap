#!/usr/bin/env python3
"""Acquire full regional sources and immutable locks, then merge border duplicates."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import sys
import urllib.request
from openbaremap import ROOT, digest, write
from regions import profile, region_path

sys.path.insert(0, str(ROOT/'work/python'))

def download(url, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        part = path.with_name(path.name+'.part')
        with urllib.request.urlopen(url, timeout=120) as src, part.open('wb') as out:
            shutil.copyfileobj(src, out)
        part.rename(path)
    return {'path': str(path.relative_to(ROOT)), 'url': url, 'bytes': path.stat().st_size, 'sha256': digest(path)}

def verify(lock):
    for item in lock:
        if digest(ROOT/item['path']) != item['sha256']:
            raise ValueError('Locked source changed: '+item['path'])

def fetch_osm(region):
    import osmium
    p=profile(region);lockpath=region_path(region,'sources.lock.json')
    if lockpath.exists():
        existing=json.loads(lockpath.read_text());verify(existing['inputs']+[existing['osm']]);return
    directory=ROOT/'data/regions'/region;stamp=p['sourceDate'].replace('-','')[2:]
    inputs=[]
    for slug in p['sourceSlugs']:
        name=f'{slug}-{stamp}.osm.pbf';url='https://download.geofabrik.de/europe/united-kingdom/'+name
        path=directory/name
        if not path.exists():
            from download_ranges import fetch
            fetch(url,path)
        with urllib.request.urlopen(url+'.md5',timeout=60) as response:expected=response.read().decode().split()[0]
        with path.open('rb') as stream:actual=hashlib.file_digest(stream,'md5').hexdigest()
        if actual!=expected:raise ValueError('Source MD5 does not match upstream: '+name)
        item=download(url,path)
        with osmium.io.Reader(str(ROOT/item['path'])) as reader:
            item['replicationTimestamp']=reader.header().get('osmosis_replication_timestamp')
        inputs.append(item)
    timestamps={item['replicationTimestamp'] for item in inputs}
    if len(timestamps)!=1 or not next(iter(timestamps)):
        raise ValueError('England and Wales must share the same OSM snapshot timestamp')
    polygons=[download('https://download.geofabrik.de/europe/united-kingdom/'+slug+'.poly',directory/(slug+'.poly')) for slug in p['sourceSlugs']]
    # Only Wales is buffered; the much larger England extract streams from disk.
    output=directory/('england-wales-'+stamp+'.osm.pbf')
    if output.exists():raise FileExistsError('Unregistered merged input: '+str(output))
    merger=osmium.MergeInputReader();merger.add_file(str(ROOT/inputs[1]['path']))
    with osmium.io.Reader(str(ROOT/inputs[0]['path'])) as reader:
        header=reader.header();header.set('osmosis_replication_timestamp',next(iter(timestamps)))
        writer=osmium.io.Writer(str(output),header)
        try:merger.apply_to_reader(reader,writer)
        finally:writer.close()
    merged={'path':str(output.relative_to(ROOT)),'sha256':digest(output),'bytes':output.stat().st_size,'snapshot_date':p['sourceDate'],'replicationTimestamp':next(iter(timestamps)),'operation':'libosmium sorted merge; duplicate OSM objects resolved by version','url':None}
    write(lockpath,{'osm':merged,'inputs':inputs,'polygons':polygons,'accessed_utc':datetime.now(timezone.utc).isoformat()})
    print('Full England/Wales OSM source locked.',flush=True)

def fetch_terrain(region):
    p=profile(region);lockpath=region_path(region,'terrain-sources.lock.json')
    if lockpath.exists():verify(json.loads(lockpath.read_text())['assets']);return
    west,south,east,north=p['terrainBounds']
    directory=ROOT/'data/regions'/region/'elevation'
    def fetch(cell):
        lat,lon=cell;ns='N' if lat>=0 else 'S';ew='E' if lon>=0 else 'W'
        name=f'{ns}{abs(lat):02d}{ew}{abs(lon):03d}.hgt.gz'
        item=download(f'https://elevation-tiles-prod.s3.amazonaws.com/skadi/{ns}{abs(lat):02d}/{name}',directory/name)
        if len(gzip.decompress((ROOT/item['path']).read_bytes()))!=3601*3601*2:
            raise ValueError('Invalid elevation cell: '+name)
        print(name+' verified',flush=True);return item
    with ThreadPoolExecutor(max_workers=4) as pool:
        assets=list(pool.map(fetch,[(lat,lon) for lat in range(south,north) for lon in range(west,east)]))
    write(lockpath,{'dataset':'Mapzen/Terrain Tiles skadi composite elevation, not pure SRTM','coverage':p['terrainBounds'],'grid':'3601 by 3601 signed 16-bit heights per degree tile','accessed_utc':datetime.now(timezone.utc).isoformat(),'documentation':'https://github.com/tilezen/joerd/tree/master/docs','assets':assets})

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--region',choices=['england-wales'],required=True);parser.add_argument('--stage',choices=['osm','terrain','all'],default='all');args=parser.parse_args()
    if args.stage in ('terrain','all'):fetch_terrain(args.region)
    if args.stage in ('osm','all'):fetch_osm(args.region)
