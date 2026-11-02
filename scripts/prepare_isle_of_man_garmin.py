#!/usr/bin/env python3
"""Extend the pinned Garmin land-cover input with the smoothed Isle of Man source."""
from pathlib import Path
import gzip,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'work/python')]
from openbaremap import digest,write
from build_region_geometry import features
from package_resources import copy_map_file

def main():
 base=ROOT/'regions/england-wales/garmin';lockpath=base/'inputs.lock.json';lock=json.loads(lockpath.read_text());work=ROOT/'work/isle-of-man';land=work/'landcover.geojson'
 if lock.get('sourceExtension',{}).get('region')=='isle-of-man':
  assert all(digest(ROOT/x['path'])==x['sha256'] for x in lock['inputs']);print('Native Isle of Man land cover already verified.');return
 assert land.exists();target=base/'inputs/landcover.geojson.gz';expected=next(x['sha256'] for x in lock['inputs'] if x['path']==str(target.relative_to(ROOT)));assert digest(target)==expected
 write(work/'previous-garmin-inputs.lock.json',lock);old=work/'previous-landcover.geojson.gz';copy_map_file(target,old)
 addition=base/'inputs/isle-of-man-landcover.geojson.gz'
 with land.open('rb') as src,addition.open('wb') as raw,gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0,compresslevel=4) as out:shutil.copyfileobj(src,out)
 tmp=target.with_name(target.name+'.next');count=0
 with gzip.open(target,'rb') as src,tmp.open('wb') as raw,gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0,compresslevel=4) as out:
  tail=b''
  while chunk:=src.read(1024*1024):
   data=tail+chunk;out.write(data[:-4096]);tail=data[-4096:]
  end=tail.rfind(b']');assert end>=0 and tail[end:].strip() in (b']}',b']\n}')
  out.write(tail[:end].rstrip())
  for feature in features(land):out.write(b',\n'+json.dumps(feature,ensure_ascii=False,separators=(',',':')).encode());count+=1
  out.write(b'\n]}\n')
 assert count>0;tmp.replace(target)
 for item in lock['inputs']:
  if item['path']==str(target.relative_to(ROOT)):item.update(sha256=digest(target),uncompressedSHA256=None)
 lock['inputs'].append({'path':str(addition.relative_to(ROOT)),'sha256':digest(addition)})
 lock['sourceExtension']={'region':'isle-of-man','snapshotDate':'2026-10-30','featuresAdded':count,'sourceSHA256':digest(ROOT/'data/regions/england-wales/isle-of-man-261030.osm.pbf'),'previousLandcoverSHA256':expected,'smoothedLandcoverSHA256':digest(addition),'builderSHA256':digest(Path(__file__))};write(lockpath,lock)
 config=json.loads((base/'config.json').read_text());config['garminPackageRevision']='2.0.1-isle-of-man-r1';config['coverage']='England, Wales and Isle of Man, including offshore islands';write(base/'config.json',config)
 copyright=base/'copyright.txt';text=copyright.read_text()
 if 'Coverage includes the Isle of Man.' not in text:copyright.write_text(text+'\nCoverage includes the Isle of Man.\n')
 print('Native smoothed Isle of Man land cover appended:',count,'features.',flush=True)
if __name__=='__main__':main()
