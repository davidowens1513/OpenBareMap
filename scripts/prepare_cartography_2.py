#!/usr/bin/env python3
"""Prepare full-island smoothed contour and land-cover source snapshots."""
from pathlib import Path
import ctypes,gzip,hashlib,json,sys,time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'garmin/work/python'))
import osmium
from smooth_geometry import smooth_line,smooth_polygon_geometry
from openbaremap import digest,write
DEST=ROOT/'build/cartography-2.0';DEST.mkdir(exist_ok=False)
CONFIG=json.loads((ROOT/'config/cartography-2.0.json').read_text())
GEOS=Path('/Applications/QGIS.app/Contents/Frameworks/libgeos_c.dylib')
g=ctypes.CDLL(str(GEOS));g.initGEOS.argtypes=[ctypes.c_void_p,ctypes.c_void_p];g.initGEOS(None,None)
for name,args,ret in [('GEOSGeoJSONReader_create',[],ctypes.c_void_p),('GEOSGeoJSONReader_readGeometry',[ctypes.c_void_p,ctypes.c_char_p],ctypes.c_void_p),('GEOSisValid',[ctypes.c_void_p],ctypes.c_byte),('GEOSArea',[ctypes.c_void_p,ctypes.POINTER(ctypes.c_double)],ctypes.c_int),('GEOSGeom_destroy',[ctypes.c_void_p],None)]:
 f=getattr(g,name);f.argtypes=args;f.restype=ret
reader=g.GEOSGeoJSONReader_create()
def measure(geometry):
 geom=g.GEOSGeoJSONReader_readGeometry(reader,json.dumps(geometry,separators=(',',':')).encode())
 if not geom:return False,0
 area=ctypes.c_double();valid=g.GEOSisValid(geom)==1;g.GEOSArea(geom,ctypes.byref(area));g.GEOSGeom_destroy(geom);return valid,area.value
counts={'contour_features':0,'landcover_features':0,'polygon_smoothed':0,'polygon_retained_by_guard':0,'landcover_classes':{}}
# A comma-free streaming collection using one feature held back avoids whole-map RAM.
class Collection:
 def __init__(self,path):self.file=path.open('w');self.file.write('{"type":"FeatureCollection","features":[\n');self.first=True
 def add(self,geometry,props):
  if not self.first:self.file.write(',\n')
  self.first=False;self.file.write(json.dumps({'type':'Feature','properties':props,'geometry':geometry},ensure_ascii=False,separators=(',',':')))
 def close(self):self.file.write('\n]}\n');self.file.close()
source=ROOT/'build/topography-a/contours.geojson'
expected='7196989bdcddefe7c600e2dc4cd83d8f4363388feac276570b69fcdea3ce7a70'
if not source.exists():
 source.parent.mkdir(parents=True,exist_ok=True)
 import shutil
 with gzip.open(ROOT/'releases/0.4.0/contours.geojson.gz','rb') as inp,source.open('wb') as dst:shutil.copyfileobj(inp,dst)
if digest(source)!=expected:raise ValueError('Original contour snapshot changed')
out=Collection(DEST/'contours.geojson')
with source.open() as f:
 for line in f:
  if not line.lstrip().startswith('{ "type": "Feature",'):continue
  feature=json.loads(line.strip().rstrip(','));geometry=feature['geometry'];parts=[geometry['coordinates']] if geometry['type']=='LineString' else geometry['coordinates']
  result=[smooth_line(part,CONFIG['smoothing']['contour_max_cut_m']) for part in parts]
  out.add({'type':geometry['type'],'coordinates':result[0] if geometry['type']=='LineString' else result},feature['properties']);counts['contour_features']+=1
out.close();print('Contours prepared:',counts['contour_features'],flush=True)
classes={'wood':'wood','forest':'wood','farm':'farmland','village_green':'grass','recreation_ground':'grass','heath':'heath','scrub':'scrub','grassland':'grass','meadow':'grass','grass':'grass','farmland':'farmland','wetland':'wetland','beach':'beach','sand':'sand','shingle':'shingle'}
def classify(tags):
 land,natural,wetland=tags.get('landuse',''),tags.get('natural',''),tags.get('wetland','');cl=classes.get(land) or classes.get(natural)
 if land=='peat_cutting':return 'peat_cutting'
 if natural in ('bare_rock','scree','shingle'):return natural
 if natural=='bog' or natural=='wetland' and wetland in ('bog','string_bog'):return 'bog'
 return cl
factory=osmium.geom.GeoJSONFactory();out=Collection(DEST/'landcover.geojson')
class Landcover(osmium.SimpleHandler):
 def area(self,a):
  tags=dict(a.tags);cl=classify(tags)
  if not cl:return
  try:original=json.loads(factory.create_multipolygon(a))
  except osmium.InvalidLocationError:raise
  candidate=smooth_polygon_geometry(original,CONFIG['smoothing']['landcover_max_cut_m'])
  valid,area=measure(candidate);old_valid,old_area=measure(original)
  if valid and old_valid and old_area and abs(area-old_area)/old_area<=CONFIG['smoothing']['maximum_polygon_area_change_fraction']:
   geometry=candidate;counts['polygon_smoothed']+=1
  else:geometry=original;counts['polygon_retained_by_guard']+=1
  props={k.replace(':','_') if k in ('name:en','name:ga') else k:v for k,v in tags.items() if k in ('wetland','natural','landuse','name','name:en','name:ga','official_name','short_name')};props['class']=cl
  out.add(geometry,props);counts['landcover_features']+=1;counts['landcover_classes'][cl]=counts['landcover_classes'].get(cl,0)+1
source=json.loads((ROOT/'sources.lock.json').read_text())['osm']
if digest(ROOT/source['path'])!=source['sha256']:raise ValueError('OSM snapshot changed')
Landcover().apply_file(str(ROOT/source['path']),locations=True,idx='flex_mem');out.close()
if not counts['contour_features'] or not counts['landcover_features']:raise ValueError('Missing geometry')
inputs=[]
for name in ('contours','landcover'):
 path=DEST/(name+'.geojson');compressed=ROOT/'releases/2.0.0'/(name+'.geojson.gz')
 with path.open('rb') as src,compressed.open('wb') as raw,gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0,compresslevel=4) as dst:
  import shutil;shutil.copyfileobj(src,dst)
 inputs.append({'path':str(compressed.relative_to(ROOT)),'sha256':digest(compressed),'uncompressed_sha256':digest(path)})
write(ROOT/'releases/2.0.0/geometry-report.json',{'version':'2.0.0','config':CONFIG,'counts':counts,'inputs':inputs,'osm_sha256':source['sha256'],'original_contour_sha256':expected,'builder_sha256':digest(Path(__file__)),'smoother_sha256':digest(Path(__file__).with_name('smooth_geometry.py')),'geos_library_sha256':digest(GEOS)})
print(json.dumps(counts,indent=2),flush=True)
