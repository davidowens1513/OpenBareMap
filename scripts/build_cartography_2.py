#!/usr/bin/env python3
"""Retile smoothed source layers; preserve every unrelated vector-layer payload."""
from pathlib import Path
import gzip,hashlib,json,shutil,sqlite3,subprocess
from openbaremap import ROOT,digest,inspect_tiles,write
from audit import fields
D=ROOT/'build/cartography-2.0'
def vint(n):
 out=bytearray()
 while n>127:out.append((n&127)|128);n>>=7
 out.append(n);return bytes(out)
def layer_name(layer):return next(v.decode() for n,w,v in fields(layer) if n==1 and w==2)
def layers(payload):
 if payload[:2]==b'\x1f\x8b':payload=gzip.decompress(payload)
 return [(layer_name(v),v) for n,w,v in fields(payload) if n==3 and w==2]
def encode(parts):return gzip.compress(b''.join(b'\x1a'+vint(len(v))+v for _,v in parts),compresslevel=6,mtime=0)
def rebuild(old,new,replacement,target):
 if new.exists():raise FileExistsError(new)
 shutil.copyfile(old,new);src=sqlite3.connect(replacement);db=sqlite3.connect(new)
 keys=set(src.execute('SELECT zoom_level,tile_column,tile_row FROM tiles'));keys.update(db.execute('SELECT zoom_level,tile_column,tile_row FROM tiles'))
 before=hashlib.sha256();after=hashlib.sha256();changed=0;feature_count=0
 for z,x,y in sorted(keys):
  coord=(z,x,y);original=db.execute('SELECT tile_data FROM tiles WHERE zoom_level=? AND tile_column=? AND tile_row=?',coord).fetchone();incoming=src.execute('SELECT tile_data FROM tiles WHERE zoom_level=? AND tile_column=? AND tile_row=?',coord).fetchone()
  oldparts=layers(original[0]) if original else [];newparts=[(n,v) for n,v in layers(incoming[0]) if n==target] if incoming else []
  other=[(n,v) for n,v in oldparts if n!=target]
  for n,v in other:before.update(f'{z}/{x}/{y}/{n}:'.encode());before.update(v)
  if not newparts and not any(n==target for n,_ in oldparts):
   for n,v in other:after.update(f'{z}/{x}/{y}/{n}:'.encode());after.update(v)
   continue
  result=[];placed=False
  for n,v in oldparts:
   if n==target:
    if not placed:result.extend(newparts);placed=True
   else:result.append((n,v))
  if not placed:result.extend(newparts)
  for n,v in result:
   if n!=target:after.update(f'{z}/{x}/{y}/{n}:'.encode());after.update(v)
  db.execute('DELETE FROM tiles WHERE zoom_level=? AND tile_column=? AND tile_row=?',coord)
  if result:db.execute('INSERT INTO tiles VALUES (?,?,?,?)',(*coord,encode(result)))
  changed+=1
  for _,v in newparts:feature_count+=sum(n==2 and w==2 for n,w,_ in fields(v))
 if before.digest()!=after.digest():raise ValueError('Unrelated layers changed')
 db.execute("DELETE FROM metadata WHERE name='version'");db.execute("INSERT INTO metadata VALUES ('version','2.0.0')");db.commit();db.close();src.close()
 return {'path':str(new.relative_to(ROOT)),'sha256':digest(new),'validation':inspect_tiles(new),'changed_tiles':changed,'replacement_feature_instances':feature_count,'unchanged_other_layers_sha256':before.hexdigest()}
def main():
 report=json.loads((ROOT/'releases/2.0.0/geometry-report.json').read_text())
 for item in report['inputs']:
  if digest(ROOT/item['path'])!=item['sha256']:raise ValueError('Geometry input changed')
 config={'layers':{'landcover':{'minzoom':4,'maxzoom':14,'source':str(D/'landcover.geojson'),'source_columns':['class','wetland','natural','landuse','name','name_en','name_ga','official_name','short_name'],'simplify_below':14,'simplify_level':0.000008,'simplify_ratio':2},'contour':{'minzoom':8,'maxzoom':14,'source':str(D/'contours.geojson'),'source_columns':['elevation'],'simplify_below':13,'simplify_level':0.00001}},'settings':{'minzoom':4,'maxzoom':14,'basezoom':14,'bounding_box':[-16.30824,47.96052,0,56.86553],'include_ids':False,'compress':'gzip','description':'OpenBareMap 2.0 bounded source geometry smoothing','name':'OpenBareMap 2.0 smoothed geometry','version':'2.0.0'}}
 write(D/'tilemaker.json',config);(D/'process.lua').write_text('node_keys={}\nway_keys={}\nfunction node_function() end\nfunction way_function() end\n')
 tool=shutil.which('tilemaker');expected=json.loads((ROOT/'toolchain.lock.json').read_text())['tilemaker']['sha256']
 if digest(tool)!=expected:raise ValueError('Tilemaker changed')
 command=[tool,'--output',str(D/'geometry.mbtiles'),'--config',str(D/'tilemaker.json'),'--process',str(D/'process.lua'),'--threads','1']
 with (D/'tilemaker.log').open('w') as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
 outputs={}
 active=json.loads((ROOT/'active-map.json').read_text())
 for name,target in [('basemap','landcover'),('topography','contour')]:
  old=ROOT/active['datasets'][name]['path']
  if digest(old)!=active['datasets'][name]['sha256']:raise ValueError('Original map changed')
  outputs[name]=rebuild(old,D/(name+'.mbtiles'),D/'geometry.mbtiles',target)
 write(ROOT/'releases/2.0.0/vector-build-report.json',{'version':'2.0.0','geometry_report_sha256':digest(ROOT/'releases/2.0.0/geometry-report.json'),'builder_sha256':digest(Path(__file__)),'toolchain_sha256':expected,'command':command,'outputs':outputs})
 print(json.dumps(outputs,indent=2),flush=True)
if __name__=='__main__':main()
