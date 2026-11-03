#!/usr/bin/env python3
"""Keep native Garmin background polygons inside each edition's source footprint."""
import argparse,json
from pathlib import Path
from shapely.geometry import Polygon,Point,box,shape,mapping
from shapely.ops import unary_union
from shapely.prepared import prep
from shapely import make_valid
from openbaremap import ROOT,digest,write
from regions import profile,region_path

def base_path(region):
    return ROOT/'garmin' if region=='ireland' else ROOT/'regions'/region/'garmin'

def read_poly(path):
    rows=iter(Path(path).read_text().splitlines()[1:]);positive=[];negative=[]
    for row in rows:
        label=row.strip()
        if not label:continue
        if label=='END':break
        coords=[]
        for row in rows:
            if row.strip()=='END':break
            coords.append(tuple(map(float,row.split())))
        polygon=Polygon(coords)
        if not polygon.is_valid:raise ValueError('Invalid coverage ring: '+str(path))
        (negative if label.startswith('!') else positive).append(polygon)
    result=unary_union(positive)
    if negative:result=result.difference(unary_union(negative))
    return result

def generate(region):
    p=profile(region);base=base_path(region)
    context=[-11,51,-5,56] if region=='ireland' else p.get('garminContextBounds',p['bounds'])
    if region=='ireland':
        records=[json.loads((base/'render-coverage-sources/ireland-source.json').read_text())]
    elif p.get('coverageBoundary'):
        source=region_path(region,'coverage.geojson');records=[{'path':str(source.relative_to(ROOT)),'sha256':digest(source),'purpose':'Exact official park plus 25 km footprint; not its rectangular tile envelope'}]
    else:records=json.loads(region_path(region,'sources.lock.json').read_text())['polygons']
    for item in records:
        if digest(ROOT/item['path'])!=item['sha256']:raise ValueError('Regional outline changed: '+item['path'])
    if p.get('coverageBoundary'):geometry=shape(json.loads((ROOT/records[0]['path']).read_text())['features'][0]['geometry'])
    else:geometry=unary_union([read_poly(ROOT/item['path']) for item in records])
    geometry=geometry.intersection(box(*context))
    if not geometry.is_valid or geometry.is_empty:raise ValueError('Invalid regional rendering footprint')
    anchors={n:xy[:2] for n,xy in p.get('destinations',{}).items() if n!='island'}
    if region=='ireland':anchors={'Dublin':[-6.2603,53.3493],'Belfast':[-5.93,54.6],'Cork':[-8.47,51.9],'Malin Head':[-7.34,55.38],'Tory Island':[-8.23,55.26],'Aran Islands':[-9.76,53.12],'Great Blasket':[-10.54,52.10],'Skellig Michael':[-10.54,51.77],'Fastnet':[-9.60,51.389]}
    for name,xy in anchors.items():
        if not geometry.covers(Point(*xy)):raise ValueError('Rendering footprint excludes '+name)
    path=base/'render-coverage.geojson'
    write(path,{'type':'FeatureCollection','features':[{'type':'Feature','properties':{'region':region,'purpose':'Limit opaque native background and land-cover polygons; retain complete accepted OSM and terrain inputs'},'geometry':mapping(geometry)}]})
    record={'format':'openbaremap-garmin-render-footprint-v1','region':region,'inputs':records,'contextEnvelope':context,'bounds':list(geometry.bounds),'geometry':{'path':str(path.relative_to(ROOT)),'bytes':path.stat().st_size,'sha256':digest(path)},'knownDestinationsCovered':anchors,'transparentNativeMap':True,'drawPriority':25,'purpose':'Rectangular Garmin tiles may overlap other countries. Do not fill their padding with sea, land or land-cover polygons.'}
    write(base/'render-coverage.lock.json',record)
    return record

def load(region):
    record=json.loads((base_path(region)/'render-coverage.lock.json').read_text());assert record['region']==region
    for item in [*record['inputs'],record['geometry']]:
        if digest(ROOT/item['path'])!=item['sha256']:raise ValueError('Rendering footprint source changed: '+item['path'])
    return shape(json.loads((ROOT/record['geometry']['path']).read_text())['features'][0]['geometry']),record

def polygon_parts(geometry):
    if geometry.is_empty:return
    if geometry.geom_type=='Polygon':
        if geometry.area>0:yield mapping(geometry)['coordinates']
    elif hasattr(geometry,'geoms'):
        for part in geometry.geoms:yield from polygon_parts(part)

class CoverageClipper:
    def __init__(self,footprint):
        if not footprint.is_valid or footprint.is_empty:raise ValueError('Invalid footprint')
        self.footprint=footprint;self.prepared=prep(footprint);self.stats={}
    def polygons(self,geometry,kind):
        c=self.stats.setdefault(kind,{'input':0,'inside':0,'clipped':0,'excluded':0,'repaired':0,'emitted':0});c['input']+=1
        g=shape(geometry);repaired=not g.is_valid
        if repaired:g=make_valid(g);c['repaired']+=1
        if g.is_empty or not self.prepared.intersects(g):c['excluded']+=1;return
        if self.prepared.covers(g):
            c['inside']+=1
            if geometry['type']=='Polygon' and not repaired:parts=[geometry['coordinates']]
            elif geometry['type']=='MultiPolygon' and not repaired:parts=geometry['coordinates']
            else:parts=polygon_parts(g)
        else:c['clipped']+=1;parts=polygon_parts(g.intersection(self.footprint))
        for rings in parts:c['emitted']+=1;yield rings

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--regions',nargs='+',default=['ireland','england-wales','scotland','sierra-nevada']);args=parser.parse_args()
    for region in args.regions:print(region,generate(region)['geometry']['sha256'],flush=True)
