#!/usr/bin/env python3
"""Conservative corner cutting for uncut source geometry, before tile clipping."""
import math
METRES_PER_DEGREE=111195.08

def smooth_line(coords,max_cut_m,fraction=.18,closed=False):
    if len(coords)<(4 if closed else 3):return coords
    points=coords[:-1] if closed and coords[0]==coords[-1] else coords
    if len(points)<3:return coords
    output=[]
    for i,b in enumerate(points):
        if not closed and i in (0,len(points)-1):output.append(list(b));continue
        a,c=points[i-1],points[(i+1)%len(points)]
        sx=METRES_PER_DEGREE*math.cos(math.radians(b[1]));sy=METRES_PER_DEGREE
        u=((a[0]-b[0])*sx,(a[1]-b[1])*sy);v=((c[0]-b[0])*sx,(c[1]-b[1])*sy)
        la,lc=math.hypot(*u),math.hypot(*v)
        if min(la,lc)<.05:output.append(list(b));continue
        turn=180-math.degrees(math.acos(max(-1,min(1,(u[0]*v[0]+u[1]*v[1])/(la*lc)))))
        if not 8<=turn<=150:output.append(list(b));continue
        cut=min(max_cut_m,fraction*la,fraction*lc)
        for p,length in ((a,la),(c,lc)):
            output.append([round(b[0]+(p[0]-b[0])*cut/length,7),round(b[1]+(p[1]-b[1])*cut/length,7)])
    if closed:output.append(output[0])
    return output

def smooth_polygon_geometry(geometry,max_cut_m):
    polygons=[geometry['coordinates']] if geometry['type']=='Polygon' else geometry['coordinates']
    result=[[smooth_line(ring,max_cut_m,closed=True) for ring in rings] for rings in polygons]
    return {'type':geometry['type'],'coordinates':result[0] if geometry['type']=='Polygon' else result}
