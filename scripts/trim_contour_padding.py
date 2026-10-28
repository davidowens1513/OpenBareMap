#!/usr/bin/env python3
"""Trim contour segments outside a generous tile buffer, preserving original coordinates.

No intersections are inserted: a segment touching the padded tile is retained whole.
Other layers, feature attributes and all tile positions are retained.
"""
from pathlib import Path
import argparse, collections, json, sqlite3
from audit import fields
from optimize_storage import packed, field, sha
from build_cartography_2 import layers, encode, vint
ROOT=Path(__file__).resolve().parents[1]
def decode(data):
 vals=packed(data);i=0;x=y=0;paths=[];points=None
 while i<len(vals):
  command=vals[i];i+=1;op=command&7;count=command>>3
  if op in (1,2):
   if op==1:
    if count!=1:raise ValueError('Unexpected multipoint command')
    points=[];paths.append([points,False])
   if points is None:raise ValueError('No MoveTo')
   for _ in range(count):
    dx,dy=vals[i:i+2];i+=2;x+=(dx>>1)^-(dx&1);y+=(dy>>1)^-(dy&1);points.append((x,y))
  elif op==7:
   if count!=1 or not paths:raise ValueError('Bad ClosePath')
   paths[-1][1]=True
  else:raise ValueError('Unexpected geometry command')
 return paths

def encode_paths(paths):
 vals=[];x=y=0
 for points,closed in paths:
  if not points:raise ValueError('Empty path')
  vals.append(9)
  for j,(xx,yy) in enumerate(points):
   if j==1:vals.append((len(points)-1)*8+2)
   dx,dy=xx-x,yy-y;vals.extend(((dx<<1)^(dx>>63),(dy<<1)^(dy>>63)));x,y=xx,yy
  if closed:vals.append(15)
 return b''.join(vint(v) for v in vals)

def intersects(a,b,lo,hi):
 x,y=a;dx=b[0]-x;dy=b[1]-y;start=0.;end=1.
 for p,q in [(-dx,x-lo),(dx,hi-x),(-dy,y-lo),(dy,hi-y)]:
  if not p:
   if q<0:return False
  elif p<0:start=max(start,q/p)
  else:end=min(end,q/p)
  if start>end:return False
 return True

def trim_layer(raw,padding=1024):
 extent=next((v for n,w,v in fields(raw) if n==5 and w==0),4096)
 if extent!=4096:raise ValueError("Expected pinned 4096-unit tile extent")
 out=[];stats=collections.Counter()
 for n,w,feature in fields(raw):
  if n!=2 or w!=2:out.append(field(n,w,feature));continue
  parts=list(fields(feature));typ=next((v for n,w,v in parts if n==3),None);geom=next((v for n,w,v in parts if n==4),None)
  if typ!=2 or not geom:out.append(field(n,w,feature));continue
  try:paths=decode(geom)
  except ValueError:out.append(field(n,w,feature));continue
  if any(closed for pts,closed in paths):out.append(field(n,w,feature));continue
  retained=[];removed=0
  for points,closed in paths:
   current=None
   for a,b in zip(points,points[1:]):
    stats['inputSegments']+=1
    if intersects(a,b,-padding,4096+padding):
     if current is None:current=[a,b];retained.append((current,False))
     else:assert current[-1]==a;current.append(b)
     stats['retainedSegments']+=1
    else:current=None;removed+=1
  if removed:
   stats['removedOutsideSegments']+=removed;stats['changedFeatures']+=1
   if not retained:stats['removedWhollyOutsideFeatures']+=1;continue
   data=encode_paths(retained);assert decode(data)==[[p,c] for p,c in retained]
   feature=b''.join(field(n,w,data if n==4 and w==2 else v) for n,w,v in parts)
  out.append(field(n,w,feature))
 return b''.join(out),stats


def build(config_path, destination):
 config=json.loads(config_path.read_text()); source=ROOT/config['input']['path']
 if sha(source)!=config['input']['sha256']:raise ValueError('Input checksum mismatch')
 if destination.exists():raise FileExistsError(destination)
 destination.parent.mkdir(parents=True,exist_ok=True)
 src=sqlite3.connect(source.as_uri()+'?mode=ro',uri=True); db=sqlite3.connect(destination)
 db.execute('CREATE TABLE metadata(name TEXT,value TEXT)')
 db.execute('CREATE TABLE tiles(zoom_level INTEGER,tile_column INTEGER,tile_row INTEGER,tile_data BLOB)')
 db.execute('CREATE UNIQUE INDEX tile_index ON tiles(zoom_level,tile_column,tile_row)')
 db.executemany('INSERT INTO metadata VALUES(?,?)',src.execute('SELECT name,value FROM metadata'))
 stats=collections.Counter(); count=0
 for z,x,y,data in src.execute('SELECT zoom_level,tile_column,tile_row,tile_data FROM tiles ORDER BY zoom_level,tile_column,tile_row'):
  result=[]; removed=0
  for name,raw in layers(data):
   if name=='contour':
    raw,s=trim_layer(raw,config['paddingTileUnits']); stats.update(s); removed+=s['removedOutsideSegments']
   result.append((name,raw))
  db.execute('INSERT INTO tiles VALUES(?,?,?,?)',(z,x,y,encode(result) if removed else data)); count+=1
 db.commit()
 assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
 assert count==src.execute('SELECT COUNT(*) FROM tiles').fetchone()[0]
 db.close(); src.close()
 report={'revision':config['revision'],'input':config['input'],'output':{'path':str(destination.relative_to(ROOT)),'sha256':sha(destination),'bytes':destination.stat().st_size},'sourceBytes':source.stat().st_size,'savedBytes':source.stat().st_size-destination.stat().st_size,'paddingTileUnits':config['paddingTileUnits'],'paddingPixelsAt512TileSize':128,'tileCount':count,'allTileCoordinatesPreserved':True,'visibleSegmentsPreservedWithoutCoordinateChanges':True,'otherLayersByteUnchanged':True,**stats}
 assert stats['inputSegments']==stats['retainedSegments']+stats['removedOutsideSegments']
 return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',type=Path,default=ROOT/'config/contour-padding-2.0.json');p.add_argument('--output',type=Path,default=ROOT/'build/padding-2.0/topography.mbtiles');p.add_argument('--report',type=Path,default=ROOT/'releases/2.0.0/contour-padding-report.json');a=p.parse_args()
 report=build(a.config,a.output.resolve());a.report.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
