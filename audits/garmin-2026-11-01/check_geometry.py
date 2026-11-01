import json,gzip,collections
from pathlib import Path
from shapely.geometry import shape,Polygon,box,mapping
from shapely import union_all,make_valid
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];report={};masks={}
for region,path in [('ireland','garmin/inputs/land-ireland.geojson.gz'),('england-wales','regions/england-wales/garmin/inputs/land.geojson.gz')]:
 with gzip.open(ROOT/path,'rt') as f:features=json.load(f)['features']
 geoms=[shape(f['geometry']) for f in features];source=union_all([make_valid(g) for g in geoms]);d={'sourceFeatures':len(geoms),'sourceInvalidGeometries':sum(not g.is_valid for g in geoms),'sourceBounds':list(source.bounds),'sourceUnionAreaSquareDegrees':source.area,'compiled':{}}
 polys=collections.defaultdict(list);water=[]
 for line in (HERE/(region+'-coast.ndjson')).open():
  f=json.loads(line)
  if len(f['points'])<3:continue
  if f['type']==84:polys[f['level']].append(make_valid(Polygon(f['points'])))
  if f['type']==60 and f['level']==0:water.append({'tile':f['tile'],'areaSquareDegrees':Polygon(f['points']).area,'bounds':list(Polygon(f['points']).bounds)})
 for level,items in polys.items():
  union=union_all(items);masks[(region,level)]=union;d['compiled'][level]={'unionAreaSquareDegrees':union.area,'sourceLandMissingSquareDegrees':source.difference(union).area,'outsideSourceSquareDegrees':union.difference(source).area}
 d['lowZoomLostFromClosestSquareDegrees']=masks[(region,0)].difference(masks[(region,4)]).area
 d['lowZoomLossPercentOfClosest']=100*d['lowZoomLostFromClosestSquareDegrees']/masks[(region,0)].area
 d['largestCloseWaterPolygons']=sorted(water,key=lambda x:x['areaSquareDegrees'],reverse=True)[:5]
 report[region]=d;print(region,'finished',flush=True)
# Land of one edition under another edition's opaque tile rectangles without its own land cover.
for a,b in [('ireland','england-wales'),('england-wales','ireland')]:
 tiles=union_all([box(*json.loads(l)['bounds']) for l in (HERE/(b+'-tiles.ndjson')).open()])
 for level in [0,4]:
  conflict=masks[(a,level)].intersection(tiles).difference(masks[(b,level)])
  report.setdefault('crossMapSeaMask',{})[a+'-under-'+b+'-level-'+str(level)]={'areaSquareDegrees':conflict.area,'bounds':list(conflict.bounds) if not conflict.is_empty else []}
(HERE/'geometry-checks.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
