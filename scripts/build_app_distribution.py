#!/usr/bin/env python3
"""Create complete regional integration kits without changing installed resources/apps."""
import argparse,json,shutil,sys,zipfile,hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from regions import ROOT,profile,active_map
from openbaremap import digest,write
from package_resources import copy_map_file

VERSION='app-bundles-v1'
BASE='https://downloads.appsbyonzy.dev/'

def render(name,p):
    text=(ROOT/'distribution/templates'/name).read_text()
    lon,lat,zoom=p.get('destinations',{'island':[-8.15,53.4,7]})['island']
    for key,value in {'LABEL':p['label'],'LAT':lat,'LON':lon,'ZOOM':zoom}.items():text=text.replace('{{'+key+'}}',str(value))
    if '{{' in text:raise ValueError('Unresolved instruction template')
    return text

def package_root(region,platform):
    return ROOT/platform/'package' if region=='ireland' else ROOT/'regions'/region/platform

def verify_resources(root,region,platform):
    manifest=json.loads((root/'manifest.json').read_text());active=active_map(region)
    if manifest.get('region','ireland')!=region:raise ValueError('Wrong resource edition')
    for name,item in active['datasets'].items():
        records=manifest['datasets'] if platform=='ios' else manifest['databases']
        if records[name]['sha256']!=item['sha256']:raise ValueError('Outdated resource '+name)
    listed=set()
    for line in (root/'SHA256SUMS.txt').read_text().splitlines():
        sha,name=line.split('  ',1);path=(root/name).resolve()
        if not path.is_relative_to(root.resolve()) or digest(path)!=sha:raise ValueError('Resource checksum: '+name)
        listed.add(name)
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}-{'SHA256SUMS.txt'}
    if listed!=actual:raise ValueError('Unlisted/missing map resources')
    return manifest

def clone(src,dst):copy_map_file(Path(src),Path(dst));return str(dst)

def archive_tree(payload,target):
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_STORED,allowZip64=True) as archive:
        for path in sorted(payload.rglob('*')):
            if not path.is_file():continue
            entry=zipfile.ZipInfo(path.relative_to(payload).as_posix(),date_time=(2026,11,2,0,0,0));entry.external_attr=0o100644<<16
            with path.open('rb') as src,archive.open(entry,'w',force_zip64=path.stat().st_size>=2**31) as dst:shutil.copyfileobj(src,dst,1024*1024)
    with zipfile.ZipFile(target) as archive:
        if archive.testzip():raise ValueError('Archive CRC failure')

def build_one(region,output):
    p=profile(region);records={};title={'ireland':'Ireland','england-wales':'England-Wales','scotland':'Scotland','sierra-nevada':'Sierra-Nevada'}[region]
    directory=output/region;directory.mkdir(parents=True,exist_ok=False)
    for platform,folder in [('ios','OpenBareMap.bundle'),('android','OpenBareMap')]:
        print(region,platform,'verifying resources',flush=True)
        source=package_root(region,platform);manifest=verify_resources(source/folder,region,platform)
        dest=directory/platform;dest.mkdir();payload=dest/'payload';payload.mkdir();support=payload/'integration';support.mkdir()
        instructions=render(platform+'-instructions.txt',p)
        (payload/'INSTRUCTIONS.txt').write_text(instructions);(dest/'instructions.txt').write_text(instructions)
        if platform=='ios':
            shutil.copytree(source/folder,payload/folder,copy_function=clone)
            shutil.copyfile(ROOT/'ios/OpenBareMapResources.swift',payload/'OpenBareMapResources.swift')
            # The canonical map bundle remains unchanged; the kit instructions take precedence.
            (payload/'OpenBareMapViewController.swift').write_text(render('ios-example.swift',p))
            (support/'dependencies.swift.txt').write_text('.package(url: "https://github.com/maplibre/maplibre-gl-native-distribution", exact: "7.0.0")\n// Add product MapLibre to the application target.\n')
        else:
            inner=source/'OpenBareMap-Android.zip'
            if not inner.exists():raise FileNotFoundError('Generate native import archive first: '+str(inner))
            # Match every ZIP member with the already-verified runtime directory.
            with zipfile.ZipFile(inner) as z:
                expected={f.relative_to(source/folder).as_posix() for f in (source/folder).rglob('*') if f.is_file()}
                if set(z.namelist())!=expected:raise ValueError('Stale inner archive inventory')
                for info in z.infolist():
                    with z.open(info) as stream:sha=hashlib.file_digest(stream,'sha256').hexdigest()
                    if sha!=digest(source/folder/info.filename):raise ValueError('Stale inner archive '+info.filename)
            clone(inner,payload/'OpenBareMap-Resources.zip')
            shutil.copyfile(ROOT/'android/loader/build/outputs/aar/loader-release.aar',support/'openbaremap-loader-release.aar')
            shutil.copyfile(ROOT/'android/loader/src/main/java/org/openbaremap/android/OpenBareMapResources.kt',support/'OpenBareMapResources.kt')
            with zipfile.ZipFile(support/'openbaremap-loader-release.aar') as z:
                if 'classes.jar' not in z.namelist() or z.testzip():raise ValueError('Invalid Android loader')
            example=payload/'example';example.mkdir()
            text=(ROOT/'android/app/src/main/java/org/openbaremap/demo/MainActivity.kt').read_text()
            lon,lat,zoom=p.get('destinations',{'island':[-8.15,53.4,7]})['island'];text=text.replace('LatLng(53.4, -8.15)).zoom(7.0)',f'LatLng({float(lat)}, {float(lon)})).zoom({float(zoom)})')
            (example/'MainActivity.kt').write_text(text)
            (example/'AndroidManifest.xml').write_text('<manifest xmlns:android="http://schemas.android.com/apk/res/android"><application><activity android:name="org.openbaremap.demo.MainActivity" android:exported="false" /></application></manifest>\n')
            (example/'dependencies.gradle.kts').write_text('dependencies {\n    implementation(files("libs/openbaremap-loader-release.aar"))\n    implementation("org.maplibre.gl:android-sdk-opengl:13.6.1")\n    implementation("org.jetbrains.kotlin:kotlin-stdlib:2.2.10")\n}\n')
        write(payload/'BUNDLE.json',{'format':'openbaremap-app-integration-bundle-v1','region':region,'platform':platform,'mapVersion':p['mapVersion'],'storageRevision':manifest['storageRevision'],'mapManifestSHA256':digest(source/folder/'manifest.json'),'rendererDependency':{'ios':'MapLibre Native iOS 7.0.0 via Swift Package Manager','android':'org.maplibre.gl:android-sdk-opengl:13.6.1'}[platform],'nativeAppProjectsModified':False})
        (payload/'CHECKSUMS.txt').write_text(''.join(digest(f)+'  '+f.relative_to(payload).as_posix()+'\n' for f in sorted(payload.rglob('*')) if f.is_file()))
        filename=f'OpenBareMap-{title}-'+('iOS' if platform=='ios' else 'Android')+'-Bundle.zip'
        print(region,platform,'assembling integration kit',flush=True)
        archive_tree(payload,dest/filename)
        prefix=f'OpenBareMap/{region}/{p["mapVersion"]}/{VERSION}/{platform}/'
        item={'url':BASE+prefix+filename,'instructionsURL':BASE+prefix+'instructions.txt','r2Key':prefix+filename,'localPath':str((dest/filename).relative_to(ROOT)),'bytes':(dest/filename).stat().st_size,'sha256':digest(dest/filename),'instructionsSHA256':digest(dest/'instructions.txt'),'mapManifestSHA256':digest(source/folder/'manifest.json'),'datasets':manifest.get('datasets',manifest.get('databases'))}
        records[platform]=item
        (dest/'SHA256SUMS.txt').write_text(item['sha256']+'  '+filename+'\n'+item['instructionsSHA256']+'  instructions.txt\n')
        write(dest/'manifest.json',item)
        print(region,platform,'complete',item['bytes'],flush=True)
    write(directory/'manifest.json',records)
    return region,records

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'work'/VERSION);parser.add_argument('--regions',nargs='+',choices=['ireland','england-wales','scotland','sierra-nevada'],default=['ireland','england-wales','scotland','sierra-nevada']);args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    with ThreadPoolExecutor(max_workers=2) as pool:records=dict(pool.map(lambda r:build_one(r,args.output),args.regions))
    records={region:json.loads((args.output/region/'manifest.json').read_text()) for region in ['ireland','england-wales','scotland','sierra-nevada'] if (args.output/region/'manifest.json').exists()}
    dest=ROOT/'distribution'/VERSION;dest.mkdir(exist_ok=True)
    existing=json.loads((dest/'catalog.json').read_text())['regions'] if (dest/'catalog.json').exists() else {}
    records={**existing,**records}
    write(dest/'catalog.json',{'format':'openbaremap-app-bundle-catalog-v1','mapVersion':'2.0.0','regions':records,'sourceCommit':__import__('subprocess').check_output(['git','rev-parse','HEAD'],text=True).strip()})
    print('All regional app integration bundles complete',flush=True)
