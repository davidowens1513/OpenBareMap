#!/usr/bin/env python3
"""Build a separate non-routing transparent layer of the user's Irish tracks."""
from pathlib import Path
import argparse,gzip,hashlib,importlib.util,json,math,subprocess,xml.etree.ElementTree as ET
from xml.sax.saxutils import quoteattr
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
BOUNDS=(-11,51,-5,56)
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read_segments(path):
 root=ET.parse(path).getroot();segments=[]
 for part in root.iter():
  kind=part.tag.split('}')[-1]
  if kind not in ('trkseg','rte'):continue
  pts=[]
  for p in part:
   if p.tag.split('}')[-1] not in ('trkpt','rtept'):continue
   x,y=float(p.attrib['lon']),float(p.attrib['lat'])
   if not(math.isfinite(x) and math.isfinite(y) and -180<=x<=180 and -90<=y<=90):raise ValueError('Invalid coordinate: '+str(path))
   pts.append([x,y])
  if pts:segments.append(pts)
 return segments
def in_ireland(segments):
 return bool(segments) and all(BOUNDS[0]<=x<=BOUNDS[2] and BOUNDS[1]<=y<=BOUNDS[3] for seg in segments for x,y in seg)
def snapshot(source,destination):
 titles={str(t['id']):t['title'] for t in json.loads((source/'tracks.json').read_text())}
 tracks=[];excluded=[];sources=[]
 files=sorted((source/'GPX').glob('*.gpx'))
 if not files:raise ValueError('No GPX files')
 for file in files:
  segments=read_segments(file);identifier=file.stem.removeprefix('MVTrack-')
  sources.append({'file':file.name,'sha256':sha(file)})
  if not in_ireland(segments):excluded.append(identifier);continue
  if not any(len(s)>=2 for s in segments):raise ValueError('Track has no line: '+file.name)
  tracks.append({'id':identifier,'name':titles.get(identifier,'Track '+identifier),'segments':segments})
 data={'coverageBounds':BOUNDS,'filter':'Retain whole GPX only when all recorded points lie in the shared Ireland extent; no foreign tracks clipped into Ireland.','tracks':tracks}
 destination.parent.mkdir(parents=True,exist_ok=True)
 with destination.open('wb') as raw,gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0) as stream:stream.write((json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n').encode())
 lock={'sourceFolderName':source.name,'sourceFiles':sources,'includedTrackIds':[t['id'] for t in tracks],'excludedTrackIds':excluded,'sourceCount':len(files),'includedCount':len(tracks),'excludedCount':len(excluded),'inputSHA256':sha(destination),'selection':data['filter'],'bounds':BOUNDS,'metadata':'Coordinates, titles and track IDs only; no photos, descriptions, timestamps or elevation.'}
 (HERE/'inputs.lock.json').write_text(json.dumps(lock,indent=2)+'\n');return data,lock

def osm(data,path):
 nodes=[];ways=[];nodeid=40000000000;wayid=40000000000
 def tag(k,v):return '<tag k='+quoteattr(k)+' v='+quoteattr(str(v))+'/>'
 for track in data['tracks']:
  first=True
  for segment in track['segments']:
   refs=[]
   for x,y in segment:
    nodeid+=1;refs.append(nodeid);tags=''
    if first:
     tags=tag('obm:track_start','yes');first=False
    nodes.append(f'<node id="{nodeid}" lat="{y:.7f}" lon="{x:.7f}" version="1">{tags}</node>')
   for start in range(0,len(refs)-1,1799):
    part=refs[start:start+1800]
    if len(part)<2:continue
    wayid+=1;ways.append(f'<way id="{wayid}" version="1">'+''.join(f'<nd ref="{i}"/>' for i in part)+tag('obm:personal_track','yes')+tag('obm:track_id',track['id'])+'</way>')
 path.write_text('<?xml version="1.0" encoding="UTF-8"?><osm version="0.6">\n'+'\n'.join(nodes+ways)+'\n</osm>\n')
 return {'sourceTracks':len(data['tracks']),'startPoints':len(data['tracks']),'sourceSegments':sum(len(t['segments']) for t in data['tracks']),'sourcePoints':len(nodes),'emittedWays':len(ways)}
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path);args=parser.parse_args()
 spec=importlib.util.spec_from_file_location('garmin_build',ROOT/'garmin/build.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper);helper.tools()
 sourcefile=HERE/'inputs/tracks-ireland.json.gz'
 if args.source:data,lock=snapshot(args.source,sourcefile)
 else:
  lock=json.loads((HERE/'inputs.lock.json').read_text())
  if sha(sourcefile)!=lock['inputSHA256']:raise ValueError('Track input checksum changed')
  with gzip.open(sourcefile,'rt') as f:data=json.load(f)
 work=ROOT/'garmin/work/my-tracks';work.mkdir(parents=True,exist_ok=True)
 output=work/'compiled'
 if output.exists():raise FileExistsError(output)
 output.mkdir();counts=osm(data,work/'tracks.osm')
 command=[helper.java_path(),'-Xmx2g','-jar',str(ROOT/'garmin/tools/mkgmap-r4924/mkgmap.jar'),'--output-dir='+str(output),'--mapname=48320001','--family-id=4832','--product-id=1','--family-name=OpenBareMap - My Tracks','--series-name=OpenBareMap - My Tracks','--description=Onzy Ireland tracks','--code-page=1252','--lower-case','--levels=0:24,1:22,2:20,3:18,4:16','--transparent','--draw-priority=31','--style-file='+str(HERE/'style'),'--gmapsupp',str(work/'tracks.osm'),str(HERE/'style/OBM4832.txt')]
 helper.run(command,work/'compile.log')
 image=output/'gmapsupp.img'
 if not image.exists():raise ValueError('Missing map')
 report={'counts':counts,'selection':{'included':lock['includedCount'],'excluded':lock['excludedCount']},'command':command,'routing':False,'transparent':True,'drawPriority':31,'outputBytes':image.stat().st_size,'outputSHA256':sha(image),'inputSHA256':sha(sourcefile),'hardwareRenderingTested':False}
 (work/'build-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
