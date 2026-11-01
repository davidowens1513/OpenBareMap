from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,gzip,time
ROOT=Path('/Users/davidowens/Documents/Codex/2026-10-25/i-x20/outputs/OpenBareMap')
REGION=ROOT/'regions/england-wales/garmin';OLD=REGION/'work';TMP=Path('/private/tmp/openbaremap-ew-garmin-final')
TMP.mkdir(exist_ok=True)
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def copy(src,dst):
 dst.parent.mkdir(parents=True,exist_ok=True)
 if dst.exists() and dst.stat().st_size==src.stat().st_size and dst.stat().st_size>0:return sha(dst)
 print('Recovering '+src.name,flush=True)
 for attempt in range(4):
  try:
   subprocess.run(['/bin/cp',str(src),str(dst)],check=True,timeout=90)
   if dst.stat().st_size!=src.stat().st_size:raise ValueError('Incomplete '+str(src))
   return sha(dst)
  except (subprocess.SubprocessError,OSError):
   if attempt==3:raise
   print('Retry '+src.name,flush=True)
def write(p,obj):p.write_text(json.dumps(obj,indent=2)+'\n')
log=(OLD/'compile.log').read_text();failed=set(re.findall(r'Bad file format: .*/([0-9]+)\.osm\.pbf',log))
expected={p.name[:8] for p in (OLD/'split').glob('[0-9]*.osm.pbf')};built={p.stem for p in (OLD/'compile').glob('[0-9]*.img')}
assert expected-built==failed and failed
receipt={'cause':'Cloud-offloaded build files could not be read by the initial compiler. Verified regular local copies are used for recovery.','expectedSections':len(expected),'recompiledSections':sorted(failed),'copiedImages':{},'sourceChunks':{}}
compiled=TMP/'compiled';compiled.mkdir(exist_ok=True);pbf=TMP/'pbf';pbf.mkdir(exist_ok=True);style=TMP/'style';style.mkdir(exist_ok=True);hgt=TMP/'hgt';hgt.mkdir(exist_ok=True)
for p in sorted((OLD/'compile').glob('[0-9]*.img')):receipt['copiedImages'][p.name]=copy(p,compiled/p.name)
print('Preserved',len(built),'complete map sections',flush=True)
for ident in sorted(failed):receipt['sourceChunks'][ident]=copy(OLD/'split'/(ident+'.osm.pbf'),pbf/(ident+'.osm.pbf'))
for p in (REGION/'style').iterdir():
 if p.is_file():copy(p,style/p.name)
copy(REGION/'coverage.poly',TMP/'coverage.poly');copy(REGION/'copyright.txt',TMP/'copyright.txt')
copy(ROOT/'garmin/tools/mkgmap-r4924/mkgmap.jar',TMP/'mkgmap.jar')
for dependency in (ROOT/'garmin/tools/mkgmap-r4924/lib').glob('*.jar'):copy(dependency,TMP/'lib'/dependency.name)
for lockpath in [ROOT/'regions/england-wales/terrain-sources.lock.json',REGION/'dem-padding.lock.json']:
 for item in json.loads(lockpath.read_text())['assets']:
  original=ROOT/item['path'];src=TMP/'sources'/original.name
  copy(original,src)
  if sha(src)!=item['sha256']:raise ValueError('Elevation source changed')
  dst=hgt/src.stem
  with gzip.open(src,'rb') as inp,dst.open('wb') as out:shutil.copyfileobj(inp,out,1024*1024)
  if dst.stat().st_size!=3601*3601*2:raise ValueError('Incomplete elevation grid')
print('Local elevation grids ready',flush=True)
args=TMP/'repair.args';args.write_text(''.join(f'mapname: {ident}\ndescription: OpenBareMap England & Wales\ninput-file: {pbf/(ident+".osm.pbf")}\n\n' for ident in sorted(failed)))
config=json.loads((REGION/'config.json').read_text());opts=[]
for item in config['compilerOptions']:
 if item=='--gmapsupp':continue
 for key,value in [('--style-file=',style),('--dem=',hgt),('--dem-poly=',TMP/'coverage.poly'),('--copyright-file=',TMP/'copyright.txt')]:
  if item.startswith(key):item=key+str(value);break
 opts.append(item)
java=Path(os.environ.get('JAVA_HOME','/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home'))/'bin/java'
command=[str(java),'-Xmx6g','-jar',str(TMP/'mkgmap.jar'),'--output-dir='+str(compiled),*opts,'-c',str(args),str(style/'OBM4832.txt')]
with (TMP/'repair.log').open('w') as out:subprocess.run(command,stdout=out,stderr=subprocess.STDOUT,check=True)
text=(TMP/'repair.log').read_text()
if 'Bad file format:' in text or re.search(r'Number of (?:MapFailedExceptions|ExitExceptions): [1-9]',text):raise ValueError('Map section recovery failed')
actual={p.stem for p in compiled.glob('[0-9]*.img')}
if actual!=expected:raise ValueError('Missing map sections: '+str(expected-actual))
print('All',len(actual),'map sections compiled',flush=True)
combine=TMP/'combined';combine.mkdir(exist_ok=True);command=[str(java),'-Xmx3g','-jar',str(TMP/'mkgmap.jar'),'--output-dir='+str(combine),'--gmapsupp',*opts,*map(str,sorted(compiled.glob('[0-9]*.img'))),str(style/'OBM4832.txt')]
with (TMP/'combine.log').open('w') as out:subprocess.run(command,stdout=out,stderr=subprocess.STDOUT,check=True)
image=combine/'gmapsupp.img'
if not image.exists() or not 0<image.stat().st_size<4*1024**3:raise ValueError('Missing/oversized combined map')
copy(image,compiled/'gmapsupp.img')
copy(ROOT/'garmin/InspectMap.java',TMP/'InspectMap.java')
subprocess.run([str(java.with_name('javac')),'-cp',str(TMP/'mkgmap.jar'),'-d',str(TMP),str(TMP/'InspectMap.java')],check=True)
with (TMP/'inspection.json').open('w') as out:subprocess.run([str(java),'-Xmx2g','-cp',str(TMP)+':'+str(TMP/'mkgmap.jar'),'InspectMap',str(compiled),'London','Cardiff','Newcastle upon Tyne','Plymouth','Carlisle'],stdout=out,check=True)
inspection=json.loads((TMP/'inspection.json').read_text())
if inspection['tiles']!=len(expected):raise ValueError('Section count mismatch')
dist=REGION/'dist';dist.mkdir(exist_ok=True);target=dist/'OpenBareMap-England-Wales.img'
if target.exists():raise FileExistsError(target)
copy(image,target)
for name in ('terrain-attribution.md','terrain-data-sources.md'):copy(ROOT/'data'/name,dist/name)
copy(REGION/'copyright.txt',dist/'ATTRIBUTION.txt')
(dist/'INSTALL.txt').write_text('OpenBareMap England & Wales 2.0\n\nCopy OpenBareMap-England-Wales.img into the Garmin folder on your device or memory card. Enable OpenBareMap England & Wales. Its family ID is 4832, separate from Ireland (4831), so both maps can coexist. Display-only; no turn-by-turn routing. Set elevation units to metres.\n\nHardware visual testing remains pending.\n')
write(REGION/'inspection.json',inspection);write(REGION/'recovery-report.json',receipt)
write(REGION/'build-report.json',{'status':'compiled and structurally inspected; hardware rendering pending','familyId':4832,'routing':False,'output':{'path':str(target.relative_to(ROOT)),'bytes':target.stat().st_size,'sha256':sha(target)},'inspection':inspection,'recovery':'recovery-report.json','expectedSections':len(expected)})
print('Complete Garmin map verified:',target,target.stat().st_size,flush=True)
