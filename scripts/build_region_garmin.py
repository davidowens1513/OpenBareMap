#!/usr/bin/env python3
"""Build an independently identified, display-only Garmin regional edition."""
import argparse
import gzip
import json
from pathlib import Path
import shutil
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'garmin'))
from openbaremap import ROOT,digest,write
from regions import profile,region_path,garmin_work
from build import java_path,tools,run
from identities import validate_config,write_tile_args

def compress(source,target):
    with source.open('rb') as src,target.open('wb') as raw,gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0,compresslevel=4) as dst:shutil.copyfileobj(src,dst)
    return {'path':str(target.relative_to(ROOT)),'sha256':digest(target),'uncompressedSHA256':digest(source)}

def main(region):
    from fetch_region import fetch_dem_padding
    fetch_dem_padding(region)
    p=profile(region);dest=ROOT/'regions'/region/'garmin';dest.mkdir(parents=True,exist_ok=True)
    work=garmin_work(region);work.mkdir(parents=True,exist_ok=True)
    inputs=dest/'inputs';inputs.mkdir(exist_ok=True)
    lock=dest/'inputs.lock.json'
    geometry=ROOT/'build'/(region+'-geometry')
    geometry_report=json.loads((geometry/'geometry-report.json').read_text())
    for name,expected in geometry_report['outputs'].items():
        if digest(geometry/name)!=expected:raise ValueError('Geometry checkpoint changed: '+name)
    if not lock.exists():
        records=[]
        for name,path in [('contours',ROOT/'build'/(region+'-geometry')/'contours.geojson'),('landcover',ROOT/'build'/(region+'-geometry')/'landcover.geojson'),('land',ROOT/'build'/(region+'-topography')/'land.geojson')]:records.append(compress(path,inputs/(name+'.geojson.gz')))
        write(lock,{'region':region,'inputs':records})
    for item in json.loads(lock.read_text())['inputs']:
        if digest(ROOT/item['path'])!=item['sha256']:raise ValueError('Garmin input changed')
    style=dest/'style'
    if not style.exists():
        shutil.copytree(ROOT/'garmin/style',style)
        for file in style.iterdir():
            if file.is_file():file.write_text(file.read_text().replace('name:ga','name:cy').replace('OpenBareMap Ireland',p['name']).replace('Full Ireland',p['label']))
        typ=style/'OBM4831.txt';text=typ.read_text().replace('FID=4831','FID='+str(p['garminFamilyId']));typ.unlink();(style/('OBM'+str(p['garminFamilyId'])+'.txt')).write_text(text)
        lines=style/'lines';lines.write_text(lines.read_text().replace('admin_level=2 [','(admin_level=2 | admin_level=4) ['))
    # Coast/background geometry must survive low-detail polygon size filtering.
    polygons=style/'polygons'
    rules=polygons.read_text().replace('obm:sea=yes [','obm:sea=yes { set mkgmap:skipSizeFilter=true } [').replace('natural=land [','natural=land { set mkgmap:skipSizeFilter=true } [')
    polygons.write_text(rules)
    # Dissolve overlapping source buffers into valid outer rings for Java readers.
    from region_coverage import polygon_union
    polygon=dest/'coverage.poly'
    if not polygon.exists():polygon_union(region,polygon)
    copyright_file=dest/'copyright.txt'
    copyright_file.write_text((ROOT/'garmin/copyright.txt').read_text().replace('Ireland',p['label']).replace('Townlands','Inherited font and pattern assets'))
    options=['--max-jobs=2','--style-file='+str(style),'--family-id='+str(p['garminFamilyId']),'--product-id=1','--family-name='+p['name'],'--series-name=OpenBareMap Garmin 2.0','--description='+p['name']+' 2.0','--code-page=1252','--lower-case','--name-tag-list=name:en,name,name:cy','--levels=0:24,1:22,2:20,3:18,4:16','--gmapsupp','--add-pois-to-areas','--dem='+str(work/'hgt'),'--dem-poly='+str(polygon),'--dem-dists=3312,13248,26512,53024,106048','--dem-interpolation=bilinear','--copyright-file='+str(copyright_file)]
    config={'routing':False,'coverage':p['coverage'],'contourIntervalMetres':20,'familyId':p['garminFamilyId'],'tileStartId':p['garminTileStartId'],'compilerOptions':options,'garminPackageRevision':p.get('garminPackageRevision',p['mapVersion'])}
    validate_config(region,config)
    write(dest/'config.json',config);tools()
    if not (work/'prepared.json').exists():run([sys.executable,'garmin/prepare_inputs.py','--region',region],work/'prepare.log')
    if digest(work/'overlays.osm.gz')!=json.loads((work/'prepared.json').read_text())['overlay_sha256']:raise ValueError('Prepared overlay changed')
    if not (work/'combined.osm.pbf').exists():run([sys.executable,'garmin/merge_inputs.py','--region',region],work/'merge.log')
    merged=json.loads((work/'merge-record.json').read_text())
    if digest(work/'combined.osm.pbf')!=merged['combinedSHA256'] or digest(work/'overlays.osm.gz')!=merged['overlaySHA256'] or json.loads(region_path(region,'sources.lock.json').read_text())['osm']['sha256']!=merged['osmSHA256']:raise ValueError('Merged Garmin source changed')
    split=work/'split'
    if not split.exists():
        split.mkdir();run([java_path(),'-Xmx6g','-jar',str(ROOT/'garmin/tools/splitter-r654/splitter.jar'),'--mapid='+str(p['garminTileStartId']),'--description='+p['name'],'--max-nodes=1000000','--max-threads=2','--keep-complete=true','--output=pbf','--polygon-file='+str(polygon),'--output-dir='+str(split),str(work/'combined.osm.pbf')],work/'splitter.log')
    elif not (split/'template.args').exists():raise ValueError('Incomplete split stage')
    # Cached split chunks retain their old source names after an identity change.
    # Assign output map IDs from the current reserved range, not template.args.
    source_tiles=sorted(split.glob('[0-9]*.osm.pbf'))
    if not source_tiles:raise ValueError('No split sources')
    compile_args=work/'compile-tiles.args'
    expected=write_tile_args(source_tiles,compile_args,region,p['name'])
    compile_dir=work/'compile'
    if not compile_dir.exists():
        compile_dir.mkdir();command=[java_path(),'-Xmx6g','-jar',str(ROOT/'garmin/tools/mkgmap-r4924/mkgmap.jar'),'--output-dir='+str(compile_dir),*options,'-c',str(compile_args),str(style/('OBM'+str(p['garminFamilyId'])+'.txt'))]
        write(compile_dir/'build.json',{'status':'started','command':command,'osm':json.loads(region_path(region,'sources.lock.json').read_text())['osm'],'demPaddingLockSHA256':digest(dest/'dem-padding.lock.json'),'combinedSourceSHA256':merged['combinedSHA256'],'inputsLockSHA256':digest(lock),'style':{f.name:digest(f) for f in style.iterdir() if f.is_file()}})
        run(command,work/'compile.log')
        compiled=json.loads((compile_dir/'build.json').read_text());compiled.update(status='compiled; inspection pending',outputSHA256=digest(compile_dir/'gmapsupp.img'))
        write(compile_dir/'build.json',compiled)
    else:
        compiled=json.loads((compile_dir/'build.json').read_text())
        if compiled['status']!='compiled; inspection pending' or digest(compile_dir/'gmapsupp.img')!=compiled['outputSHA256']:raise ValueError('Existing Garmin compile is incomplete or changed')
    actual={p.stem for p in compile_dir.glob('[0-9]*.img')}
    if expected!=actual:raise ValueError('Garmin sections missing: '+str(sorted(expected-actual)))
    image=compile_dir/'gmapsupp.img'
    if not image.is_file() or not 0<image.stat().st_size<4*1024**3:raise ValueError('Missing image or exceeds FAT32 single-file limit')
    java=Path(java_path());javac=java.with_name('javac');jar=ROOT/'garmin/tools/mkgmap-r4924/mkgmap.jar'
    subprocess.run([str(javac),'-cp',str(jar),'-d',str(work),str(ROOT/'garmin/InspectMap.java')],check=True)
    command=[str(java),'-Xmx2g','-cp',str(work)+':'+str(jar),'InspectMap',str(compile_dir),'London','Cardiff','Newcastle upon Tyne','Plymouth','Carlisle']
    with (dest/'inspection.json').open('w') as out:subprocess.run(command,stdout=out,check=True)
    # Inspect the prospective binary together with the other installed products.
    subprocess.run([str(javac),'-cp',str(jar),'-d',str(work),str(ROOT/'garmin/ValidateMapSet.java')],check=True)
    companions=[f for f in [ROOT/'garmin/dist/OpenBareMap-Ireland.img',ROOT/'garmin/dist/OpenBareMap-My-Tracks.img'] if f.exists()]
    with (dest/'map-set-validation.txt').open('w') as out:subprocess.run([str(java),'-Djava.awt.headless=true','-Xmx2g','-cp',str(work)+':'+str(jar),'ValidateMapSet',*map(str,companions),str(image)],stdout=out,check=True)
    dist=dest/'dist';dist.mkdir(exist_ok=True);output=dist/'OpenBareMap-England-Wales.img'
    if output.exists():raise FileExistsError(output)
    shutil.copyfile(image,output)
    if digest(output)!=digest(image):raise ValueError('Distribution copy mismatch')
    (dist/'INSTALL.txt').write_text('OpenBareMap England & Wales 2.0\n\nCopy OpenBareMap-England-Wales.img into the Garmin folder on your device or memory card. Enable OpenBareMap England & Wales. This map has a different family ID from Ireland; both may be installed. Display-only: no turn-by-turn routing. Use metres for contour labels.\n\nDevice rendering has not yet been reviewed.\n')
    shutil.copyfile(copyright_file,dist/'ATTRIBUTION.txt')
    for name in ('terrain-attribution.md','terrain-data-sources.md'):shutil.copyfile(ROOT/'data'/name,dist/name)
    write(dest/'build-report.json',{'status':'compiled and structurally inspected; hardware rendering pending','familyId':p['garminFamilyId'],'garminPackageRevision':config['garminPackageRevision'],'routing':False,'output':{'path':str(output.relative_to(ROOT)),'bytes':output.stat().st_size,'sha256':digest(output)},'inspection':json.loads((dest/'inspection.json').read_text())})

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--region',choices=['england-wales'],required=True);args=parser.parse_args();main(args.region)
