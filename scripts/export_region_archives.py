#!/usr/bin/env python3
"""Export checksum-verified standalone mobile resources; never changes host apps."""
import argparse,json,shutil,zipfile
from pathlib import Path
from openbaremap import ROOT,digest,write
from regions import profile
from package_resources import copy_map_file

def verify(root,region):
    manifest=json.loads((root/'manifest.json').read_text())
    if manifest['region']!=region:raise ValueError('Wrong resource edition')
    for line in (root/'SHA256SUMS.txt').read_text().splitlines():
        expected,name=line.split('  ',1);path=(root/name).resolve()
        if not path.is_relative_to(root.resolve()) or digest(path)!=expected:
            raise ValueError('Resource checksum changed: '+name)

def export(region,output):
    p=profile(region);source=ROOT/'regions'/region
    for platform,folder in [('ios','OpenBareMap.bundle'),('android','OpenBareMap')]:verify(source/platform/folder,region)
    output.mkdir(parents=True,exist_ok=False);records={}
    stem='OpenBareMap-'+''.join(word.title() for word in region.split('-'))
    for platform in ('ios','android'):
        directory=output/platform;directory.mkdir()
        filename=stem+('-iOS.zip' if platform=='ios' else '-Android.zip');target=directory/filename
        if platform=='android':
            original=source/platform/'OpenBareMap-Android.zip'
            validation=json.loads((source/platform/'validation.json').read_text())
            if digest(original)!=validation['zip']['sha256']:raise ValueError('Android archive changed')
            copy_map_file(original,target)
        else:
            with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_STORED,allowZip64=True) as archive:
                for path in sorted((source/platform).rglob('*')):
                    if path.is_file():archive.write(path,path.relative_to(source/platform))
        with zipfile.ZipFile(target) as archive:
            if archive.testzip() is not None:raise ValueError('Archive CRC failed')
        if (source/platform/'INTEGRATION.txt').exists():
            shutil.copyfile(source/platform/'INTEGRATION.txt',directory/'INTEGRATION.txt')
        records[platform]={'path':str(target.relative_to(ROOT)),'bytes':target.stat().st_size,'sha256':digest(target),'url':f'https://downloads.appsbyonzy.dev/OpenBareMap/{region}/{p["mapVersion"]}/{platform}/{filename}'}
    write(output/'manifest.json',{'region':region,'mapVersion':p['mapVersion'],'kind':'standalone mobile map resources; not applications','hostAppsModified':False,'archives':records})
    (output/'SHA256SUMS.txt').write_text(''.join(f'{r["sha256"]}  {platform}/{Path(r["path"]).name}\n' for platform,r in records.items()))
    print(json.dumps(records,indent=2),flush=True)
    return records

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--region',choices=['england-wales','scotland','sierra-nevada'],required=True);args=parser.parse_args();export(args.region,ROOT/'regions'/args.region/'exports')
