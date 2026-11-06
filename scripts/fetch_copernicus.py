"""Fetch and derive pinned one-degree HGT cells from public Copernicus GLO-30 COGs."""
import gzip,json,os,shutil,subprocess,tempfile,datetime
from pathlib import Path
from openbaremap import ROOT,digest,write
from regions import profile,region_path

BASE='https://copernicus-dem-30m.s3.amazonaws.com/'
def fetch(region,padding=False):
 from fetch_region import download,verify
 p=profile(region);folder=ROOT/'data/regions'/region;out=folder/'elevation';out.mkdir(parents=True,exist_ok=True)
 lock=region_path(region,'garmin/dem-padding.lock.json' if padding else 'terrain-sources.lock.json')
 if lock.exists():
  record=json.loads(lock.read_text());verify(record['assets']+record.get('sourceAssets',[]));return
 index=download(BASE+'tileList.txt',folder/'copernicus/tileList.txt');available=set((ROOT/index['path']).read_text().splitlines())
 west,south,east,north=p['terrainBounds'];cells=[(la,lo) for la in range(south,north) for lo in range(west,east)]
 if padding:cells=[(la,lo) for la in range(south-1,north+1) for lo in range(west-1,east+1) if (la,lo) not in cells]
 sources=[];cogs={}
 for la,lo in cells:
  stem=f'Copernicus_DSM_COG_10_N{la:02d}_00_{"W" if lo<0 else "E"}{abs(lo):03d}_00_DEM'
  if stem in available or stem+'/' in available:
   item=download(BASE+stem+'/'+stem+'.tif',folder/'copernicus'/(stem+'.tif'));sources.append(item);cogs[(la,lo)]=ROOT/item['path']
 toolchain=json.loads((ROOT/'topography-toolchain.lock.json').read_text());tools={n:toolchain[n]['path'] for n in ['gdalwarp','gdal_translate','gdalbuildvrt']}
 for n,path in tools.items():
  if digest(path)!=toolchain[n]['sha256']:raise ValueError('DEM conversion tool changed: '+n)
 assets=[];commands=[];ocean_review=[]
 env=os.environ.copy();env['PROJ_DATA']=str(Path(toolchain['proj_database']['path']).parent)
 with tempfile.TemporaryDirectory(prefix='OpenBareMap-Copernicus-') as temporary:
  temp=Path(temporary);vrt=temp/'source.vrt'
  if cogs:
   command=[tools['gdalbuildvrt'],str(vrt),*map(str,cogs.values())];subprocess.run(command,env=env,check=True,stdout=subprocess.DEVNULL);commands.append(command)
  for la,lo in cells:
   name=f'N{la:02d}{"W" if lo<0 else "E"}{abs(lo):03d}.hgt';raw=temp/name;target=out/(name+'.gz')
   if target.exists():raise FileExistsError('Unregistered Copernicus cell: '+str(target))
   if (la,lo) in cogs:
    tif=temp/(name+'.tif');half=1/7200
    command=[tools['gdalwarp'],'-q','-overwrite','-of','GTiff','-ot','Int16','-t_srs','EPSG:4326','-te',*map(str,[lo-half,la-half,lo+1+half,la+1+half]),'-ts','3601','3601','-r','bilinear','-dstnodata','0',str(vrt),str(tif)];subprocess.run(command,env=env,check=True);commands.append(command)
    command=[tools['gdal_translate'],'-q','-of','SRTMHGT','-a_nodata','-32768',str(tif),str(raw)];subprocess.run(command,env=env,check=True);commands.append(command)
   else:
    from shapely.geometry import shape,box
    from shapely.ops import unary_union
    land_path=ROOT/'build'/(region+'-topography')/'land.geojson'
    if not land_path.exists():raise ValueError('A missing DEM tile requires an independent coastal land check')
    cell=box(lo,la,lo+1,la+1)
    if not box(*p['coastContextBounds']).covers(cell):raise ValueError('Ocean cell extends outside checked coastal context')
    land=unary_union([shape(f['geometry']) for f in json.loads(land_path.read_text())['features']])
    if land.intersection(cell).area>1e-12:raise ValueError('Missing public Copernicus tile contains land: '+name)
    ocean_review.append({'cell':name,'coastalLandSHA256':digest(land_path),'landIntersectionSquareDegrees':0})
    raw.write_bytes(bytes(3601*3601*2))
   with raw.open('rb') as src,target.open('wb') as stream,gzip.GzipFile(filename='',mode='wb',fileobj=stream,mtime=0) as dst:shutil.copyfileobj(src,dst)
   assets.append({'path':str(target.relative_to(ROOT)),'sha256':digest(target),'bytes':target.stat().st_size,'url':None,'operation':'Bilinear resampling of Copernicus GLO-30 to point-aligned Int16 HGT, EGM2008 heights' if (la,lo) in cogs else 'Zero ocean cell: no tile in the pinned official GLO-30 public inventory'})
   print(name,'Copernicus terrain' if (la,lo) in cogs else 'ocean zero cell',flush=True)
 record={'dataset':'Copernicus DEM GLO-30 Public, AWS 2021 release','verticalDatum':'EGM2008 orthometric metres','sourceDocumentation':'https://registry.opendata.aws/copernicus-dem/','grid':'3601 by 3601 signed 16-bit point-aligned HGT cells; ocean cells zero','coverage':[west-1,south-1,east+1,north+1] if padding else p['terrainBounds'],'assets':assets,'sourceAssets':[index,*sources],'commands':commands,'oceanCellReview':ocean_review,'toolchain':{n:toolchain[n] for n in tools},'accessed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 lock.parent.mkdir(parents=True,exist_ok=True);write(lock,record)
