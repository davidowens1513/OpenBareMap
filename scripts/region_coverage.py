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
    if p.get('clipSource') or p.get('garminCoverageBounds'):
        from shapely.geometry import box
        footprint=box(*p.get('garminCoverageBounds',p['bounds']))
        for name,xy in p['destinations'].items():
            if not geometry.covers(Point(*xy[:2])):raise ValueError('Source outline excludes '+name)
        geometry=footprint
    if p.get('coverageBoundary'):
        from shapely.geometry import shape
        footprint=shape(json.loads(region_path(region,'coverage.geojson').read_text())['features'][0]['geometry'])
        if not geometry.covers(footprint):raise ValueError('Upstream source does not cover the full buffered park')
        # Native Garmin tiles are rectangular. A conservative convex selection
        # envelope avoids Java Area failures on near-tangent concave buffer arcs,
        # includes the entire 25 km footprint, and keeps the exact outline as an overlay.
        geometry=footprint.convex_hull
        if not geometry.covers(footprint):raise ValueError('Garmin envelope excludes requested coverage')
    if not geometry.is_valid or geometry.is_empty:raise ValueError('Invalid combined coverage')
    for name,(lon,lat,zoom) in p['destinations'].items():
        if not geometry.covers(Point(lon,lat)):raise ValueError('Coverage excludes '+name)
    polygons=[geometry] if geometry.geom_type=='Polygon' else list(geometry.geoms)
    output=[p['label']]
    for index,poly in enumerate(polygons,1):
        for label,ring in [(str(index),poly.exterior)]+[(f'!{index}-{i}',ring) for i,ring in enumerate(poly.interiors,1)]:
            output.append(label);output.extend(f'  {x:.8f}  {y:.8f}' for x,y in ring.coords);output.append('END')
    output.append('END');destination.write_text('\n'.join(output)+'\n')
    write(destination.with_suffix('.json'),{'operation':'Requested rectangular crop; source outlines cover all destination anchors' if p.get('clipSource') or p.get('garminCoverageBounds') else 'Conservative convex tile-selection envelope covering official park plus 25 km; exact boundaries retained in map overlays' if p.get('coverageBoundary') else 'Geometric union of complete upstream region outlines; overlapping buffers dissolved','inputs':lock['polygons'],'bounds':list(geometry.bounds),'areaSquareDegrees':geometry.area,'polygons':len(polygons),'sha256':digest(destination),'exactFootprint':'regions/'+region+'/coverage.geojson' if p.get('coverageBoundary') else None,'entireRequestedFootprintCovered':True,'knownDestinationsCovered':list(p['destinations'])})
