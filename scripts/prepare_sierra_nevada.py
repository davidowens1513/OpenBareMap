#!/usr/bin/env python3
"""Prepare the official park footprint and the regional profile from pinned source data."""
import sys,json,math,hashlib,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
import os
os.chdir(ROOT)
sys.path.insert(0,str(ROOT/'work/python'))
from shapely.geometry import Polygon,mapping,box
from shapely.ops import unary_union,transform
from pyproj import Transformer
root=Path('regions/sierra-nevada');root.mkdir(exist_ok=True,parents=True)
ns={'k':'http://www.opengis.net/kml/2.2'}
kml=Path('data/regions/sierra-nevada/boundary/Limites_PPNN.kml')
if not kml.exists():
 import urllib.request,subprocess
 archive=kml.parent/'limites-red.rar';archive.parent.mkdir(parents=True,exist_ok=True)
 if not archive.exists():
  urllib.request.urlretrieve('https://www.miteco.gob.es/content/dam/miteco/es/parques-nacionales-oapn/red-parques-nacionales/sig/limites_red_tcm30-452281.rar',archive)
 if hashlib.sha256(archive.read_bytes()).hexdigest()!='1fabbc05057b35d2ac7f367ed2478b110b5fdbd45108c1dc3a139da01433fc03':raise ValueError('Official boundary archive differs from the pinned source')
 subprocess.run(['bsdtar','-xf',str(archive),'-C',str(kml.parent)],check=True)
 subprocess.run(['bsdtar','-xf',str(kml.parent/'limites_red/Limites_PPNN.rar'),'-C',str(kml.parent)],check=True)
if hashlib.sha256(kml.read_bytes()).hexdigest()!='bbf44fc4fe22eb036154b94aaa789907dcabb7b9a077415b8a2c445efa385093':raise ValueError('Official boundary KML changed')
parks=[p for p in ET.parse(kml).findall('.//k:Placemark',ns) if 'Sierra Nevada' in p.findtext('k:name','',ns)]
assert len(parks)==1,[p.findtext('k:name','',ns) for p in parks]
def coords(e):return [tuple(map(float,t.split(',')[:2])) for t in e.text.split()]
polys=[]
for p in parks[0].findall('.//k:Polygon',ns):
 outer=coords(p.find('k:outerBoundaryIs/k:LinearRing/k:coordinates',ns))
 holes=[coords(e) for e in p.findall('k:innerBoundaryIs/k:LinearRing/k:coordinates',ns)]
 polys.append(Polygon(outer,holes))
park=unary_union(polys);assert park.is_valid
forward=Transformer.from_crs(4326,25830,always_xy=True).transform
back=Transformer.from_crs(25830,4326,always_xy=True).transform
metric=transform(forward,park);buffer=metric.buffer(25000,quad_segs=64);coverage=transform(back,buffer)
assert coverage.covers(park)
for name,g,title in [('park-boundary',park,'Sierra Nevada National Park'),('coverage',coverage,'National park + 25 km')]:
 (root/(name+'.geojson')).write_text(json.dumps({'type':'FeatureCollection','features':[{'type':'Feature','properties':{'name':title,'source':'Organismo Autónomo Parques Nacionales; CC BY 4.0'},'geometry':mapping(g)}]},ensure_ascii=False))
(root/'coverage-mask.geojson').write_text(json.dumps({'type':'FeatureCollection','features':[{'type':'Feature','properties':{},'geometry':mapping(box(-180,-85,180,85).difference(coverage))}]}))
bounds=list(coverage.bounds);terrain=[math.floor(bounds[0]),math.floor(bounds[1]),math.ceil(bounds[2]),math.ceil(bounds[3])]
w,s,e,n=buffer.bounds
p={'id':'sierra-nevada','name':'OpenBareMap Sierra Nevada','label':'Sierra Nevada · Spain','mapVersion':'2.0.0','minzoom':4,'maxzoom':14,'coverage':'Official Sierra Nevada National Park boundary with a 25 km buffer measured in ETRS89 / UTM 30N; complete source ways and polygons retained at the edge. Rectangular tile envelope includes additional context.','bounds':bounds,'terrainBounds':terrain,'coastContextBounds':bounds,'projectedCRS':'EPSG:25830','gridCRS':'EPSG:25830','gridName':'ETRS89 / UTM 30N','gridSource':'utm-grid','townlands':False,'contourIntervalMetres':20,'sourceDate':'2026-10-31','sourceSlugs':['andalucia'],'sourceBaseURL':'https://download.geofabrik.de/europe/spain/','nativeLanguage':'es','minorWaterwayMinzoom':10,'clipBasemap':True,'boundaryPreview':False,'coverageBoundary':True,'garminFamilyId':4835,'garminTileStartId':48350001,'garminFilename':'OpenBareMap-Sierra-Nevada.img','garminPackageRevision':'2.0.0-garmin-r1','styleRevision':'2.0.0-sierra-nevada-r1','garminContextBounds':[-4.4,36.2,-1.8,38],'inspectionNames':['Granada','Capileira','Trevélez','Mulhacén'],'gridExtent':[math.floor(w/10000)*10000,math.ceil(e/10000)*10000,math.floor(s/10000)*10000,math.ceil(n/10000)*10000],'destinations':{'island':[-3.15,37.06,9],'mulhacen':[-3.3114,37.0547,13],'veleta':[-3.3656,37.0504,13],'capileira':[-3.358,36.961,13],'trevelez':[-3.265,37.002,13],'granada':[-3.5986,37.1765,12],'puerto-de-la-ragua':[-3.031,37.114,13]}}
(root/'region.json').write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n')
record={'sourceURL':'https://www.miteco.gob.es/content/dam/miteco/es/parques-nacionales-oapn/red-parques-nacionales/sig/limites_red_tcm30-452281.rar','sourcePage':'https://www.miteco.gob.es/es/parques-nacionales-oapn/red-parques-nacionales/sig/sig-descargas.html','attribution':'Fuente: Organismo Autónomo Parques Nacionales','license':'CC BY 4.0','sourcePageBoundaryRevision':'February 2023','boundaryKMLSHA256':hashlib.sha256(kml.read_bytes()).hexdigest(),'parkAreaKm2':metric.area/1e6,'bufferMetres':25000,'bufferCRS':'EPSG:25830','bufferAreaKm2':buffer.area/1e6,'bounds':bounds,'parkCovered':coverage.covers(park),'note':'The national park proper, not its peripheral protection zone or surrounding Natural Park. Planar 25 km buffer in local metre CRS; tile envelope adds context outside the curved buffer.'}
(root/'boundary-source.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
