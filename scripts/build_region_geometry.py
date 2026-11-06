#!/usr/bin/env python3
"""Smooth complete regional contours/landcover and build a metre-based grid."""
import argparse
import json
from pathlib import Path
import sys
from openbaremap import ROOT, digest, write
from regions import profile
from smooth_geometry import smooth_line, smooth_polygon_geometry
sys.path.insert(0,str(ROOT/'work/python'))

class Collection:
    def __init__(self,path):
        self.file=path.open('w');self.file.write('{"type":"FeatureCollection","features":[\n');self.first=True;self.count=0
    def add(self,geometry,properties):
        if not self.first:self.file.write(',\n')
        self.first=False;self.count+=1
        self.file.write(json.dumps({'type':'Feature','geometry':geometry,'properties':properties},ensure_ascii=False,separators=(',',':')))
    def close(self):self.file.write('\n]}\n');self.file.close()

def features(path):
    with path.open() as stream:
        for line in stream:
            if line.lstrip().startswith(('{ "type": "Feature",','{"type":"Feature",')):
                yield json.loads(line.strip().rstrip(','))

def contours(source,destination):
    out=Collection(destination)
    for feature in features(source):
        g=feature['geometry'];parts=[g['coordinates']] if g['type']=='LineString' else g['coordinates']
        result=[smooth_line(part,4) for part in parts]
        out.add({'type':g['type'],'coordinates':result[0] if g['type']=='LineString' else result},feature['properties'])
    out.close()
    if not out.count:raise ValueError('No contours')
    return out.count

def landcover(source,destination,bounds=None):
    import osmium
    from shapely.geometry import shape,box
    extent=box(*bounds) if bounds else None
    out=Collection(destination);factory=osmium.geom.GeoJSONFactory()
    classes={'wood':'wood','forest':'wood','farm':'farmland','village_green':'grass','recreation_ground':'grass','heath':'heath','scrub':'scrub','grassland':'grass','meadow':'grass','grass':'grass','farmland':'farmland','wetland':'wetland','beach':'beach','sand':'sand','shingle':'shingle'}
    counts={'smoothed':0,'retained':0,'empty_source_areas':[]}
    class Handler(osmium.SimpleHandler):
        def area(self,a):
            tags=dict(a.tags);land=tags.get('landuse','');natural=tags.get('natural','');wetland=tags.get('wetland','')
            cl=classes.get(land) or classes.get(natural)
            if land=='peat_cutting':cl='peat_cutting'
            if natural in ('bare_rock','scree','shingle'):cl=natural
            if natural=='bog' or natural=='wetland' and wetland in ('bog','string_bog'):cl='bog'
            if not cl:return
            try:
                original=json.loads(factory.create_multipolygon(a))
            except osmium.InvalidLocationError:
                raise
            except RuntimeError as error:
                rings=[len(ring) for ring in a.outer_rings()]
                if any(length>=4 for length in rings):
                    raise ValueError(f'Cannot assemble nonempty source area {a.id}; outer ring sizes {rings}') from error
                counts['empty_source_areas'].append({'area_id':a.id,'outer_ring_sizes':rings,'reason':str(error)})
                print(f'Empty, nondrawable source area recorded: {a.id}; outer rings {rings}',flush=True)
                return
            old=shape(original)
            if extent is not None and not extent.intersects(old):return
            candidate=smooth_polygon_geometry(original,6)
            new=shape(candidate)
            if old.is_valid and new.is_valid and old.area and abs(new.area-old.area)/old.area<=.02:
                geometry=candidate;counts['smoothed']+=1
            else:geometry=original;counts['retained']+=1
            props={k.replace(':','_'):v for k,v in tags.items() if k in ('wetland','natural','landuse','name','name:en','name:cy','name:gd','name:es','name:fr','name:it','name:de','name:fo','official_name','short_name')};props['class']=cl
            out.add(geometry,props)
    Handler().apply_file(str(source),locations=True,idx='flex_mem');out.close()
    if not out.count:raise ValueError('No landcover')
    return {'features':out.count,**counts}

def grid(region,destination):
    from pyproj import Transformer, __version__ as pyproj_version
    p=profile(region);transform=Transformer.from_crs(p['gridCRS'],'EPSG:4326',always_xy=True)
    counts={}
    for step,layer in [(1000,'grid_1km'),(10000,'grid_10km')]:
        out=Collection(destination/(layer+'.geojson'))
        # Projected metre rectangle from the edition profile; includes northern islands.
        west,east,south,north=p.get('gridExtent',[0,700000,0,650000])
        for axis,minimum,maximum,crossmin,crossmax in [('E',west,east,south,north),('N',south,north,west,east)]:
            for fixed in range(minimum,maximum+1,step):
                coords=[list(transform.transform(fixed,v) if axis=='E' else transform.transform(v,fixed)) for v in range(crossmin,crossmax+1,1000)]
                out.add({'type':'LineString','coordinates':coords},{'label':f'{fixed//1000} km {axis}','metres':fixed,'axis':axis})
        out.close();counts[layer]=out.count
    transform.transform((west+east)/2,(south+north)/2)
    operation=transform.get_last_used_operation()
    write(destination/'grid-provenance.json',{'crs':p['gridCRS'],'pyprojVersion':pyproj_version,'operation':operation.description,'statedOperationAccuracyMetres':operation.accuracy,'note':'Cartographic grid generated from projected metre coordinates; not a survey transformation guarantee.'})
    return counts

def build(region,topography):
    p=profile(region);dest=ROOT/'build'/(region+'-geometry');dest.mkdir(exist_ok=False)
    from regions import region_path
    source=json.loads(region_path(region,'sources.lock.json').read_text())['osm'];osm=ROOT/source['path']
    if digest(osm)!=source['sha256']:raise ValueError('OSM source changed')
    counts={'contours':contours(topography/'contours.geojson',dest/'contours.geojson'),'landcover':landcover(osm,dest/'landcover.geojson',p['bounds'] if p.get('clipBasemap') else None),'grid':grid(region,dest)}
    write(dest/'geometry-report.json',{'region':region,'counts':counts,'osm':source,'contoursSourceSHA256':digest(topography/'contours.geojson'),'outputs':{f.name:digest(f) for f in dest.glob('*.geojson')},'builderSHA256':digest(Path(__file__)),'smootherSHA256':digest(Path(__file__).with_name('smooth_geometry.py'))})
    print(json.dumps(counts),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--region',choices=['england-wales','scotland','sierra-nevada','pyrenees','dolomites','faroe-islands'],required=True);a=p.parse_args();build(a.region,ROOT/'build'/(a.region+'-topography'))
