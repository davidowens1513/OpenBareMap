#!/usr/bin/env python3
"""Export both complete selected editions as static PMTiles browser previews."""
import argparse,hashlib,json,shutil,sqlite3,sys,tarfile,urllib.request
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from regions import ROOT,active_map,profile,region_style
from pmtiles.convert import mbtiles_to_pmtiles
from pmtiles.reader import Reader,MmapSource
from package_resources import build_capped_coast

def digest(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')
def build(output,origin):
 if output.exists():raise FileExistsError(output)
 output.mkdir(parents=True);assets=output/'assets';assets.mkdir();maps=output/'data';maps.mkdir()
 for folder in ['fonts','sprites']:shutil.copytree(ROOT/'viewer'/folder,assets/folder)
 for file in ['maplibre-gl.js','maplibre-gl.css','LICENSE.txt']:shutil.copyfile(ROOT/'viewer/vendor'/file,assets/file)
 shutil.copyfile(ROOT/'viewer/terrain-attribution.html',assets/'terrain-attribution.html')
 shutil.copyfile(ROOT/'viewer/townlands.geojson',assets/'townlands.geojson')
 package=output/'pmtiles.tgz';urllib.request.urlretrieve('https://registry.npmjs.org/pmtiles/-/pmtiles-4.5.0.tgz',package)
 with tarfile.open(package) as archive:
  for member in archive.getmembers():
   if member.name=='package/dist/pmtiles.js':(assets/'pmtiles.js').write_bytes(archive.extractfile(member).read())
 if not (assets/'pmtiles.js').is_file():raise ValueError('Missing browser protocol library')
 package.unlink()
 urllib.request.urlretrieve('https://raw.githubusercontent.com/protomaps/PMTiles/main/LICENSE',assets/'PMTiles-LICENSE.txt')
 for file in ['preview.js','preview.css']:shutil.copyfile(ROOT/'web-preview'/file,assets/file)
 jobs=[];records={}
 for region in ['ireland','england-wales']:
  p=profile(region);active=active_map(region);directory=output/region;directory.mkdir();(maps/region).mkdir();records[region]={}
  style=region_style(region)
  for name,item in active['datasets'].items():
   source=ROOT/item['path']
   if digest(source)!=item['sha256']:raise ValueError('Selected input changed: '+str(source))
   target=maps/region/(name+'.pmtiles');jobs.append((region,name,source,target,item['sha256']))
  coast=output/('coast-'+region+'.mbtiles')
  build_capped_coast(ROOT/active['datasets']['topography']['path'],coast)
  jobs.append((region,'coast',coast,maps/region/'coast.pmtiles',digest(coast)))
  for source_name,source in style['sources'].items():
   if source['type']=='vector' or source['type']=='raster':
    name='grid' if source_name in ['irish-grid','british-grid'] else source_name
    source.pop('tiles',None);source['url']='pmtiles://'+origin.rstrip('/')+'/data/'+region+'/'+name+'.pmtiles'
   elif source_name=='townlands':source['data']=origin.rstrip('/')+'/assets/townlands.geojson'
  style['glyphs']=origin.rstrip('/')+'/assets/fonts/{fontstack}/{range}.pbf';style['sprite']=origin.rstrip('/')+'/assets/sprites/outdoors'
  write(directory/'style.json',style);write(directory/'region.json',p)
  page=(ROOT/'web-preview/index.html').read_text().replace('{{REGION}}',p['label']).replace('{{ID}}',region)
  (directory/'index.html').write_text(page)
 def convert(job):
  region,name,source,target,sha=job;print('Converting',region,name,flush=True)
  mbtiles_to_pmtiles(str(source),str(target),None)
  with target.open('rb') as f:
   reader=Reader(MmapSource(f));header=reader.header()
  with sqlite3.connect(source) as db:count=db.execute('SELECT COUNT(*) FROM tiles').fetchone()[0]
  if header['addressed_tiles_count']!=count:raise ValueError('Tile count changed')
  return region,name,{'sourceSHA256':sha,'bytes':target.stat().st_size,'sha256':digest(target),'tiles':count}
 with ThreadPoolExecutor(max_workers=2) as pool:
  for region,name,record in pool.map(convert,jobs):records[region][name]=record
 for region in ['ireland','england-wales']:(output/('coast-'+region+'.mbtiles')).unlink()
 write(output/'manifest.json',{'regions':records,'pmtilesPython':'3.8.1','pmtilesJS':'4.5.0','librarySHA256':digest(assets/'pmtiles.js'),'dataOrigin':origin,'scope':'Complete selected map tiles; no regional or zoom sampling.'})
 print('Both full-region previews exported:',output,flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--origin',required=True);args=p.parse_args();build(args.output.resolve(),args.origin)
