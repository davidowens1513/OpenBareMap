#!/usr/bin/env python3
"""Prove existing vector features survive and the island has full map coverage."""
import collections,json,sqlite3
from pathlib import Path
from openbaremap import ROOT,write
from build_cartography_2 import layers
from audit import fields
from optimize_storage import packed
from validate_region import coverage,land_coverage,xyz
ANCHORS={'Douglas':[-4.48,54.15],'Ramsey':[-4.39,54.32],'Peel':[-4.69,54.223],'Castletown':[-4.65,54.074],'Snaefell':[-4.462,54.263],'Calf of Man':[-4.825,54.055],'Point of Ayre':[-4.37,54.409]}
def signatures(raw):
 fs=list(fields(raw));ks=[v for n,w,v in fs if n==3 and w==2];vs=[v for n,w,v in fs if n==4 and w==2]
 result=collections.Counter()
 for n,w,f in fs:
  if (n,w)!=(2,2):continue
  tags=next((packed(v) for n,w,v in fields(f) if (n,w)==(2,2)),[])
  sig=(tuple((n,w,v) for n,w,v in fields(f) if n!=2),tuple(sorted((ks[k],vs[val]) for k,val in zip(tags[::2],tags[1::2]))))
  result[sig]+=1
 return result

def main():
 record=ROOT/'releases/england-wales/2.0.1/build-records/isle-of-man'
 old=json.loads((record/'previous-active-map.json').read_text());active=json.loads((ROOT/'regions/england-wales/active-map.json').read_text());baseline=ROOT/old['datasets']['basemap']['path'];target=ROOT/active['datasets']['basemap']['path']
 unchanged=changed=features=0
 with sqlite3.connect(baseline) as src,sqlite3.connect(target) as dst:
  for z,x,y,payload in src.execute('SELECT zoom_level,tile_column,tile_row,tile_data FROM tiles'):
   row=dst.execute('SELECT tile_data FROM tiles WHERE zoom_level=? AND tile_column=? AND tile_row=?',(z,x,y)).fetchone();assert row,'Original tile lost'
   if payload==row[0]:unchanged+=1;continue
   changed+=1;updated=dict(layers(row[0]))
   for name,raw in layers(payload):
    assert name in updated
    before=signatures(raw);after=signatures(updated[name]);assert not before-after,('Original feature changed or removed',z,x,y,name);features+=sum(before.values())
 detailed=coverage(target,ANCHORS);land=land_coverage(ROOT/active['datasets']['topography']['path'],ANCHORS)
 hillshade={}
 with sqlite3.connect(ROOT/active['datasets']['hillshade']['path']) as db:
  for name,(lon,lat) in ANCHORS.items():
   x,y=xyz(lon,lat,12);row=db.execute('SELECT length(tile_data) FROM tiles WHERE zoom_level=12 AND tile_column=? AND tile_row=?',(x,2**12-1-y)).fetchone();assert row and row[0]>0;hillshade[name]=row[0]
 for name in ['topography','hillshade','grid']:assert active['datasets'][name]==old['datasets'][name]
 result={'originalTilesByteIdentical':unchanged,'changedOriginalTiles':changed,'originalFeaturesSemanticallyPreservedInChangedTiles':features,'detailedCoverage':detailed,'landCoverage':land,'hillshadeZoom12':hillshade,'terrainGridHillshadeUnchanged':True}
 write(record/'coverage-validation.json',result);print(json.dumps(result,indent=2))
if __name__=='__main__':main()
