#!/usr/bin/env python3
"""Add complete Isle of Man vector content while preserving accepted mainland tiles."""
from pathlib import Path
import collections,json,shutil,sqlite3,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'work/python')]
from openbaremap import digest,write,inspect_tiles
from regions import profile,process_script
from build_cartography_2 import layers,encode,vint,rebuild
from optimize_storage import field,packed
from audit import fields
from package_resources import copy_map_file
WORK=ROOT/'work/isle-of-man';BOUNDS=[-5.435,53.732,-3.688,54.671]

def merge_layer(base,incoming):
 a=list(fields(base));b=list(fields(incoming));extent=lambda fs:next((v for n,w,v in fs if n==5),4096)
 assert extent(a)==extent(b)
 keys=[v for n,w,v in a if n==3 and w==2];values=[v for n,w,v in a if n==4 and w==2];newkeys=[v for n,w,v in b if n==3 and w==2];newvalues=[v for n,w,v in b if n==4 and w==2]
 def signature(raw,ks,vs):
  tags=next((packed(v) for n,w,v in fields(raw) if n==2 and w==2),[])
  return tuple((n,w,v) for n,w,v in fields(raw) if n!=2),tuple(sorted((ks[k],vs[val]) for k,val in zip(tags[::2],tags[1::2])))
 features=[v for n,w,v in a if n==2 and w==2];seen={signature(v,keys,values) for v in features};added=0
 for n,w,feature in b:
  if n!=2 or w!=2:continue
  sig=signature(feature,newkeys,newvalues)
  if sig in seen:continue
  seen.add(sig);parts=[]
  for number,wire,value in fields(feature):
   if number==2 and wire==2:
    tags=packed(value);mapped=[]
    for key,val in zip(tags[::2],tags[1::2]):
     if newkeys[key] not in keys:keys.append(newkeys[key])
     if newvalues[val] not in values:values.append(newvalues[val])
     mapped.extend([keys.index(newkeys[key]),values.index(newvalues[val])])
    value=b''.join(vint(x) for x in mapped)
   parts.append(field(number,wire,value))
  features.append(b''.join(parts));added+=1
 result=b''.join(field(n,w,v) for n,w,v in a if n not in (2,3,4))
 result+=b''.join(field(2,2,x) for x in features)+b''.join(field(3,2,x) for x in keys)+b''.join(field(4,2,x) for x in values)
 return result,added

def main():
 p=profile('england-wales');assert p['mapVersion']=='2.0.1';source=ROOT/'data/regions/england-wales/isle-of-man-261030.osm.pbf';tool=shutil.which('tilemaker');assert digest(tool)==json.loads((ROOT/'toolchain.lock.json').read_text())['tilemaker']['sha256']
 raw=WORK/'isle-of-man-raw.mbtiles'
 if not raw.exists():
  config=json.loads((ROOT/'config/tilemaker.json').read_text());config['settings'].update(name=p['name']+' Isle of Man source extension',description=p['coverage'],version=p['mapVersion'],bounding_box=BOUNDS)
  write(WORK/'tilemaker.json',config);(WORK/'process.lua').write_text(process_script('england-wales'))
  with (WORK/'tilemaker.log').open('w') as log:subprocess.run([tool,'--input',str(source),'--output',str(raw),'--config',str(WORK/'tilemaker.json'),'--process',str(WORK/'process.lua'),'--threads','1'],stdout=log,stderr=subprocess.STDOUT,check=True)
 land=WORK/'landcover.geojson'
 if not land.exists():
  from build_region_geometry import landcover
  write(WORK/'landcover-processing.json',landcover(source,land,BOUNDS))
 geometry=WORK/'landcover.mbtiles'
 if not geometry.exists():
  config={'layers':{'landcover':{'minzoom':4,'maxzoom':14,'source':str(land),'source_columns':['class','wetland','natural','landuse','name','name_en','name_cy','official_name','short_name'],'simplify_below':14,'simplify_level':.000008,'simplify_ratio':2}},'settings':{'minzoom':4,'maxzoom':14,'basezoom':14,'bounding_box':BOUNDS,'include_ids':False,'compress':'gzip','name':p['name']+' Isle of Man smoothed land cover','description':p['coverage'],'version':p['mapVersion']}}
  write(WORK/'landcover-tilemaker.json',config);(WORK/'empty.lua').write_text('node_keys={}\nway_keys={}\nfunction node_function() end\nfunction way_function() end\n')
  with (WORK/'landcover-tilemaker.log').open('w') as log:subprocess.run([tool,'--output',str(geometry),'--config',str(WORK/'landcover-tilemaker.json'),'--process',str(WORK/'empty.lua'),'--threads','1'],stdout=log,stderr=subprocess.STDOUT,check=True)
 smooth=WORK/'isle-of-man-smoothed.mbtiles'
 if not smooth.exists():write(WORK/'landcover-replacement.json',rebuild(raw,smooth,geometry,'landcover'))
 selected=WORK/'isle-of-man-selected.mbtiles'
 if not selected.exists():
  from build_region import select_detail
  select_detail(smooth,selected,'2.0.1-england-wales-r3')
 baseline=WORK/'previous-active-map.json'
 if not baseline.exists():baseline=ROOT/'releases/england-wales/2.0.1/build-records/isle-of-man/previous-active-map.json'
 old=json.loads(baseline.read_text());original=ROOT/old['datasets']['basemap']['path']
 if not original.exists():
  from restore_map_parts import restore
  restore(original.with_name(original.name+'.parts.json'))
 assert digest(original)==old['datasets']['basemap']['sha256']
 dest=ROOT/'releases/england-wales/2.0.1/maps';dest.mkdir(parents=True,exist_ok=True);target=dest/'basemap.mbtiles'
 if target.exists():
  accepted=json.loads((ROOT/'regions/england-wales/active-map.json').read_text())
  assert digest(target)==accepted['datasets']['basemap']['sha256'];print('Accepted extension already verified.');return
 copy_map_file(original,target)
 counts=collections.Counter();coords=set()
 with sqlite3.connect(target) as db,sqlite3.connect(selected) as incoming:
  for z,x,y,data in incoming.execute('SELECT zoom_level,tile_column,tile_row,tile_data FROM tiles ORDER BY 1,2,3'):
   parts=layers(data)
   if not any(any(n==2 and w==2 for n,w,v in fields(raw)) for name,raw in parts):continue
   coord=(z,x,y);before=db.execute('SELECT tile_data FROM tiles WHERE zoom_level=? AND tile_column=? AND tile_row=?',coord).fetchone();oldparts=layers(before[0]) if before else [];result=list(oldparts);positions={name:i for i,(name,raw) in enumerate(result)};changed=False
   for name,raw in parts:
    if not any(n==2 and w==2 for n,w,v in fields(raw)):continue
    if name in positions:
     merged,added=merge_layer(result[positions[name]][1],raw)
     if added:result[positions[name]]=(name,merged);counts[name]+=added;changed=True
    else:result.append((name,raw));counts[name]+=sum(n==2 and w==2 for n,w,v in fields(raw));changed=True
   if changed:db.execute('INSERT OR REPLACE INTO tiles VALUES (?,?,?,?)',(*coord,encode(result)));coords.add(coord)
  metadata=dict(db.execute('SELECT name,value FROM metadata'));metadata.update(version='2.0.1',description=p['coverage'],openbaremap_storage_revision='2.0.1-england-wales-r3');db.execute('DELETE FROM metadata');db.executemany('INSERT INTO metadata VALUES (?,?)',metadata.items());db.commit()
 # Verify every pre-existing tile outside the change set remains byte-identical.
 preserved=0
 with sqlite3.connect(original) as src,sqlite3.connect(target) as dst:
  for z,x,y,data in src.execute('SELECT zoom_level,tile_column,tile_row,tile_data FROM tiles'):
   if (z,x,y) not in coords:assert dst.execute('SELECT tile_data FROM tiles WHERE zoom_level=? AND tile_column=? AND tile_row=?',(z,x,y)).fetchone()[0]==data;preserved+=1
 active={**old,'mapVersion':'2.0.1','storageRevision':'2.0.1-england-wales-r3','coverage':p['coverage'],'sourceExtension':'isle-of-man'};active['datasets']['basemap']={'path':str(target.relative_to(ROOT)),'bytes':target.stat().st_size,'sha256':digest(target),'validation':inspect_tiles(target)}
 write(ROOT/'regions/england-wales/active-map.json',active)
 from regions import region_style
 write(ROOT/'regions/england-wales/style.json',region_style('england-wales'))
 write(WORK/'map-extension.json',{'status':'complete source extension; coverage verification pending','addedFeatureInstances':dict(counts),'changedTiles':len(coords),'unchangedOriginalTilesVerified':preserved,'originalBasemap':old['datasets']['basemap'],'basemap':active['datasets']['basemap'],'terrainGridAndHillshadePreserved':{n:old['datasets'][n]['sha256'] for n in ('topography','hillshade','grid')},'isleOfManOSMSHA256':digest(source)})
 print('ISLE OF MAN VECTOR EXTENSION BUILT',dict(counts),'preserved tiles',preserved,flush=True)
if __name__=='__main__':main()
