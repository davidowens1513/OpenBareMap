#!/usr/bin/env python3
"""Create deterministic OSM overlays and uncompressed HGT from locked shared inputs."""
from pathlib import Path
import argparse,gzip,hashlib,json,shutil,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from regions import profile,region_path,garmin_work
from xml.sax.saxutils import escape,quoteattr
ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'garmin/work'
def digest(path):
 with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def features(path):
 with gzip.open(path,'rt') as f:
  for line in f:
   if line.lstrip().startswith('{ "type": "Feature",') or line.lstrip().startswith('{"type":"Feature",'):
    yield json.loads(line.strip().rstrip(','))
def prepare(region='ireland'):
 global WORK
 p=profile(region)
 WORK=garmin_work(region)
 WORK.mkdir(parents=True,exist_ok=True)
 config=json.loads((ROOT/'garmin/config.json' if region=='ireland' else ROOT/'regions'/region/'garmin/config.json').read_text());contour_step=config['contourIntervalMetres']
 lock=json.loads((ROOT/'garmin/inputs.lock.json' if region=='ireland' else ROOT/'regions'/region/'garmin/inputs.lock.json').read_text())
 for item in lock['inputs']:
  if digest(ROOT/item['path'])!=item['sha256']:raise ValueError('Garmin input checksum changed')
 from garmin_render_coverage import load,CoverageClipper
 footprint,footprint_record=load(region);clipper=CoverageClipper(footprint)
 result=WORK/'overlays.osm.gz'
 if result.exists():raise FileExistsError(result)
 nodefile=WORK/'overlay-nodes.xml';wayfile=WORK/'overlay-ways.xml';relfile=WORK/'overlay-relations.xml'
 counts={'contours':0,'land_polygons':0,'landcover_polygons':0,'townlands':0,'nodes':0,'ways':0,'relations':0,'contour_intervals':{},'coverage':[-11,51,-5,56] if region=='ireland' else p.get('garminContextBounds',p['bounds'])}
 nodes=nodefile.open('w');ways=wayfile.open('w');rels=relfile.open('w')
 next_node=30000000000;next_way=30000000000;next_relation=30000000000
 def tags(values):return ''.join('<tag k='+quoteattr(k)+' v='+quoteattr(str(v))+'/>' for k,v in values.items())
 def node(coord,values=None):
  nonlocal next_node
  identifier=next_node;next_node+=1;counts['nodes']+=1
  nodes.write(f'<node id="{identifier}" lat="{coord[1]:.7f}" lon="{coord[0]:.7f}" version="1">'+tags(values or {})+'</node>\n');return identifier
 def line(coords,values,closed=False):
  nonlocal next_way
  ids=[node(c) for c in (coords[:-1] if closed and coords[0]==coords[-1] else coords)]
  if closed:ids.append(ids[0])
  emitted=[]
  for start in range(0,len(ids)-1,1799):
   part=ids[start:start+1800]
   if len(part)<2:continue
   identifier=next_way;next_way+=1;counts['ways']+=1;emitted.append(identifier)
   ways.write(f'<way id="{identifier}" version="1">'+''.join(f'<nd ref="{n}"/>' for n in part)+tags(values)+'</way>\n')
  return emitted
 def emit_polygon(rings,values):
  nonlocal next_relation
  members=[]
  for i,ring in enumerate(rings):
   if len(ring)<4:continue
   members += [(w,'outer' if i==0 else 'inner') for w in line(ring,{},True)]
  if not members:return
  identifier=next_relation;next_relation+=1;counts['relations']+=1
  rels.write(f'<relation id="{identifier}" version="1">'+''.join(f'<member type="way" ref="{w}" role="{role}"/>' for w,role in members)+tags({'type':'multipolygon',**values})+'</relation>\n')
 def polygon(rings,values):
  kind=values.get('obm:landcover','sea' if 'obm:sea' in values else 'land')
  for clipped in clipper.polygons({'type':'Polygon','coordinates':rings},kind):emit_polygon(clipped,values)
 for f in features(ROOT/'garmin/inputs/contours-10m.geojson.gz' if region=='ireland' else ROOT/'regions'/region/'garmin/inputs/contours.geojson.gz'):
  ele=int(round(f['properties']['elevation']))
  if ele<=0 or ele%contour_step:continue
  interval=100 if ele%100==0 else contour_step
  geometry=f['geometry'];parts=[geometry['coordinates']] if geometry['type']=='LineString' else geometry['coordinates']
  for part in parts:line(part,{'contour':'elevation','ele':ele,'obm:interval':interval});counts['contours']+=1
  counts['contour_intervals'][interval]=counts['contour_intervals'].get(interval,0)+1
 for f in features(ROOT/'garmin/inputs/land-ireland.geojson.gz' if region=='ireland' else ROOT/'regions'/region/'garmin/inputs/land.geojson.gz'):
  g=f['geometry'];polys=[g['coordinates']] if g['type']=='Polygon' else g['coordinates']
  for rings in polys:polygon(rings,{'natural':'land'});counts['land_polygons']+=1
 for f in features(ROOT/'garmin/inputs/landcover-smoothed.geojson.gz' if region=='ireland' else ROOT/'regions'/region/'garmin/inputs/landcover.geojson.gz'):
  g=f['geometry'];polys=[g['coordinates']] if g['type']=='Polygon' else g['coordinates']
  for rings in polys:polygon(rings,{'obm:landcover':f['properties']['class']});counts['landcover_polygons']+=1
 if p.get('coverageBoundary'):
  for name,tag in [('park-boundary','obm:park_boundary'),('coverage','obm:coverage_boundary')]:
   data=json.loads(region_path(region,name+'.geojson').read_text())
   for f in data['features']:
    g=f['geometry'];polys=[g['coordinates']] if g['type']=='Polygon' else g['coordinates']
    for rings in polys:
     for ring in rings:line(ring,{tag:'yes','name':'Sierra Nevada National Park' if name=='park-boundary' else '25 km coverage limit'},closed=True)
 west,south,east,north=counts['coverage']
 polygon([[[west,south],[east,south],[east,north],[west,north],[west,south]]],{'obm:sea':'yes'})
 if p['townlands']:
  towns=json.loads((ROOT/'viewer/townlands.geojson').read_text())
  for f in towns['features']:
   node(f['geometry']['coordinates'],{'obm:townland':'yes','name':f['properties']['name'].upper()});counts['townlands']+=1
 for file in (nodes,ways,rels):file.close()
 if not all(counts[k]>0 for k in (['contours','land_polygons','townlands'] if p['townlands'] else ['contours','land_polygons'])):raise ValueError('Missing overlay data')
 with result.open('wb') as raw,gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0,compresslevel=4) as out:
  out.write(b'<?xml version="1.0" encoding="UTF-8"?>\n<osm version="0.6" generator="OpenBareMap Garmin">\n')
  for path in [nodefile,wayfile,relfile]:
   with path.open('rb') as src:shutil.copyfileobj(src,out)
  out.write(b'</osm>\n')
 for path in [nodefile,wayfile,relfile]:path.unlink()
 hgt=WORK/'hgt';hgt.mkdir(exist_ok=True)
 for item in json.loads(region_path(region,'terrain-sources.lock.json').read_text())['assets'] + (json.loads((ROOT/'garmin/dem-padding.lock.json').read_text())['assets'] if region=='ireland' else json.loads((ROOT/'regions'/region/'garmin/dem-padding.lock.json').read_text())['assets']):
  src=ROOT/item['path']
  if digest(src)!=item['sha256']:raise ValueError('Elevation source changed: '+str(src))
  dest=hgt/src.stem
  if dest.exists():
   with gzip.open(src,'rb') as inp:expected=hashlib.file_digest(inp,'sha256').hexdigest()
   if digest(dest)==expected:continue
  with gzip.open(src,'rb') as inp,dest.open('wb') as out:shutil.copyfileobj(inp,out)
  if dest.stat().st_size!=3601*3601*2:raise ValueError('Invalid HGT size')
 counts['overlay_sha256']=digest(result);counts['overlay_bytes']=result.stat().st_size
 counts['renderFootprintSHA256']=footprint_record['geometry']['sha256'];counts['polygonClipping']=clipper.stats
 (WORK/'prepared.json').write_text(json.dumps(counts,indent=2)+'\n');print(json.dumps(counts,indent=2))
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--region',choices=['ireland','england-wales','scotland','sierra-nevada','pyrenees','dolomites'],default='ireland');args=parser.parse_args();prepare(args.region)
