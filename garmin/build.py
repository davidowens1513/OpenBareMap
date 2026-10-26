#!/usr/bin/env python3
"""Pinned full-island Garmin pipeline; no route network is generated."""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'garmin/work'
def sha(path):
 with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def java_path():
 home=os.environ.get('JAVA_HOME')
 if home:return str(Path(home)/'bin/java')
 studio=Path('/Applications/Android Studio.app/Contents/jbr/Contents/Home/bin/java')
 return str(studio) if studio.exists() else shutil.which('java')
def tools():
 for item in json.loads((ROOT/'garmin/toolchain.lock.json').read_text())['tools']:
  file=ROOT/item['path']
  if sha(file)!=item['sha256']:raise ValueError('Tool archive changed: '+str(file))
  if file.suffix=='.zip':
   with zipfile.ZipFile(file) as archive:
    for member in archive.namelist():
     if member.endswith('.jar'):
      path=ROOT/'garmin/tools'/member
      if path.exists() and hashlib.sha256(archive.read(member)).hexdigest()!=sha(path):raise ValueError('Extracted tool changed: '+str(path))
    if any(not (ROOT/'garmin/tools'/n).exists() for n in archive.namelist() if n.endswith('.jar')):archive.extractall(ROOT/'garmin/tools')
def run(command,log):
 print('Running',log.name,flush=True)
 with log.open('w') as out:subprocess.run(command,cwd=ROOT,stdout=out,stderr=subprocess.STDOUT,check=True)
 text=log.read_text(errors='replace')
 if 'Number of MapFailedExceptions:' in text and not re.search(r'Number of MapFailedExceptions: 0\b',text):raise ValueError('Map compile failed; inspect '+str(log))
 if 'Number of ExitExceptions:' in text and not re.search(r'Number of ExitExceptions: 0\b',text):raise ValueError('Compiler exit exceptions; inspect '+str(log))
def compile_map(name):
 if not re.fullmatch('[a-z0-9-]+',name):raise ValueError('Unsafe build name')
 config=json.loads((ROOT/'garmin/config.json').read_text())
 if config['routing'] or any(a.startswith('--route') for a in config['compilerOptions']):raise ValueError('Display-only profile cannot enable routing')
 destination=WORK/name
 if destination.exists():raise FileExistsError(destination)
 destination.mkdir()
 command=[java_path(),'-Xmx6g','-jar','garmin/tools/mkgmap-r4924/mkgmap.jar','--output-dir='+str(destination.relative_to(ROOT)),*config['compilerOptions'],'-c','garmin/work/split/template.args','garmin/style/OBM4831.txt']
 record={'command':command,'configSHA256':sha(ROOT/'garmin/config.json'),'styleSHA256':{p.name:sha(p) for p in sorted((ROOT/'garmin/style').iterdir()) if p.is_file()},'javaVersion':subprocess.run([java_path(),'-version'],capture_output=True,text=True).stderr,'pythonVersion':sys.version,'osm':json.loads((ROOT/'sources.lock.json').read_text())['osm'],'garminInputsLockSHA256':sha(ROOT/'garmin/inputs.lock.json'),'demPaddingLockSHA256':sha(ROOT/'garmin/dem-padding.lock.json'),'combinedInputSHA256':sha(WORK/'combined.osm.pbf'),'status':'started'}
 (destination/'build.json').write_text(json.dumps(record,indent=2)+'\n')
 run(command,WORK/(name+'.log'))
 image=destination/'gmapsupp.img'
 if not image.is_file() or image.stat().st_size==0:raise ValueError('Missing Garmin map')
 if image.stat().st_size>=4*1024**3:raise ValueError('Map exceeds FAT32 individual-file limit')
 record.update(status='compiled; binary validation required',outputSHA256=sha(image),outputBytes=image.stat().st_size)
 (destination/'build.json').write_text(json.dumps(record,indent=2)+'\n')
 print(json.dumps({'output':str(image),'bytes':image.stat().st_size,'sha256':record['outputSHA256']},indent=2))
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=['all','prepare','merge','split','compile'],default='all');parser.add_argument('--name',default='compile-release');args=parser.parse_args();WORK.mkdir(exist_ok=True);tools()
 if args.stage in ['all','prepare']:run([sys.executable,'garmin/prepare_inputs.py'],WORK/'prepare.log')
 if args.stage in ['all','merge']:run([sys.executable,'garmin/merge_inputs.py'],WORK/'merge.log')
 if args.stage in ['all','split']:
  split=WORK/'split'
  if split.exists():raise FileExistsError(split)
  split.mkdir();run([java_path(),'-Xmx6g','-jar','garmin/tools/splitter-r654/splitter.jar','--mapid=48310001','--description=OpenBareMap Ireland','--max-nodes=1000000','--max-threads=2','--keep-complete=true','--output=pbf','--polygon-file=garmin/ireland.poly','--output-dir=garmin/work/split','garmin/work/combined.osm.pbf'],WORK/'splitter.log')
 if args.stage in ['all','compile']:
  subprocess.run([sys.executable,'garmin/generate_typ.py'],cwd=ROOT,check=True);compile_map(args.name)
if __name__=='__main__':main()
