import json,collections,math,gzip
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
probes={'Dublin':(-6.2603,53.3498),'Belfast':(-5.9301,54.5973),'Cork':(-8.4756,51.8985),'Galway':(-9.0568,53.2707),'Athlone':(-7.94,53.42),'Wicklow uplands':(-6.35,53.05),'Snowdon':(-4.076,53.068),'Cardiff':(-3.1791,51.4816),'London':(-.1276,51.5072),'Carlisle':(-2.938,54.892),'Plymouth':(-4.1427,50.3755),'Dartmoor':(-3.94,50.58),'Scilly':(-6.31,49.92),'Newcastle':(-1.6178,54.9783),'Edinburgh':(-3.1883,55.9533)}
def contains(pts,x,y):
 inside=False
 a=pts[-1]
 for b in pts:
  if (a[1]>y)!=(b[1]>y) and x < (b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:inside=not inside
  a=b
 return inside
def analyze(region):
 levels={};counts=collections.Counter()
 for line in (HERE/(region+'-coast.ndjson')).open():
  f=json.loads(line);pts=f['points'];level=str(f['level']);typ=hex(f['type'])
  d=levels.setdefault(level,{'resolution':f['resolution'],'types':{},'probes':{}})
  entry=d['types'].setdefault(typ,{'polygons':0,'sumAreaSquareDegrees':0,'tiles':set()});entry['polygons']+=1;entry['tiles'].add(f['tile'])
  if len(pts)<3:continue
  entry['sumAreaSquareDegrees']+=abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(pts,pts[1:]+pts[:1])))/2
  w=min(c[0] for c in pts);e=max(c[0] for c in pts);s=min(c[1] for c in pts);n=max(c[1] for c in pts)
  for name,(x,y) in probes.items():
   if w<=x<=e and s<=y<=n and contains(pts,x,y):d['probes'].setdefault(name,{}).setdefault(typ,[]).append(f['tile'])
 for d in levels.values():
  for e in d['types'].values():e['tiles']=len(e['tiles'])
 return levels
report={r:analyze(r) for r in ['ireland','england-wales']}
(HERE/'coast-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
for r,ls in report.items():
 for l,d in ls.items():print(r,l,d['resolution'],{t:(x['polygons'],round(x['sumAreaSquareDegrees'],5),x['tiles']) for t,x in d['types'].items()},'no land:',[p for p,ts in d['probes'].items() if '0x32' in ts and '0x54' not in ts])
