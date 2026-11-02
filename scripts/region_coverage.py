"""Canonical union of complete Geofabrik region outlines for Garmin tools."""
import json
from pathlib import Path
from openbaremap import ROOT,digest,write
from regions import profile,region_path

def polygon_union(region,destination):
    from shapely.geometry import Polygon,Point
    from shapely.ops import unary_union
    p=profile(region);lock=json.loads(region_path(region,'sources.lock.json').read_text());geometries=[]
    for item in lock['polygons']:
        path=ROOT/item['path']
        if digest(path)!=item['sha256']:raise ValueError('Coverage source changed')
        rows=iter(path.read_text().splitlines()[1:]);positive=[];negative=[]
        for row in rows:
            label=row.strip()
            if not label:continue
            if label=='END':break
            coords=[]
            for row in rows:
                if row.strip()=='END':break
                coords.append(tuple(map(float,row.split())))
            ring=Polygon(coords)
            if not ring.is_valid:raise ValueError('Invalid source coverage ring: '+str(path))
            (negative if label.startswith('!') else positive).append(ring)
        geometry=unary_union(positive)
        if negative:geometry=geometry.difference(unary_union(negative))
        geometries.append(geometry)
    geometry=unary_union(geometries)
    if not geometry.is_valid or geometry.is_empty:raise ValueError('Invalid combined coverage')
    for name,(lon,lat,zoom) in p['destinations'].items():
        if not geometry.covers(Point(lon,lat)):raise ValueError('Coverage excludes '+name)
    polygons=[geometry] if geometry.geom_type=='Polygon' else list(geometry.geoms)
    output=[p['label']]
    for index,poly in enumerate(polygons,1):
        for label,ring in [(str(index),poly.exterior)]+[(f'!{index}-{i}',ring) for i,ring in enumerate(poly.interiors,1)]:
            output.append(label);output.extend(f'  {x:.8f}  {y:.8f}' for x,y in ring.coords);output.append('END')
    output.append('END');destination.write_text('\n'.join(output)+'\n')
    write(destination.with_suffix('.json'),{'operation':'Geometric union of complete upstream region outlines; overlapping buffers dissolved','inputs':lock['polygons'],'bounds':list(geometry.bounds),'areaSquareDegrees':geometry.area,'polygons':len(polygons),'sha256':digest(destination),'knownDestinationsCovered':list(p['destinations'])})
