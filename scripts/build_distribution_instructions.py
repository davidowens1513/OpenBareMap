#!/usr/bin/env python3
"""One device-independent Garmin instruction format for all public map editions."""
from pathlib import Path
import json,shutil
from openbaremap import ROOT,digest,write
from regions import profile

TITLES={'ireland':'Ireland','england-wales':'England-Wales','scotland':'Scotland','sierra-nevada':'Sierra-Nevada','pyrenees':'Pyrenees','dolomites':'Dolomites','faroe-islands':'Faroe-Islands'}
def garmin_instructions(region,filename=None):
    p=profile(region);identity=json.loads((ROOT/'garmin/map-identities.json').read_text())[region]
    text=(ROOT/'distribution/templates/garmin-instructions.txt').read_text()
    for key,value in {'LABEL':p['label'],'VERSION':p['mapVersion'],'REVISION':json.loads((ROOT/('garmin/config.json' if region=='ireland' else 'regions/'+region+'/garmin/config.json')).read_text())['garminPackageRevision'],'FILENAME':filename or 'OpenBareMap-'+TITLES[region]+'.img','FAMILY':identity['familyId'],'SLUG':region}.items():text=text.replace('{{'+key+'}}',str(value))
    if '{{' in text:raise ValueError('Unresolved Garmin instruction')
    return text

def build():
    for region,title in TITLES.items():
        source=ROOT/'garmin/dist' if region=='ireland' else ROOT/'regions'/region/'garmin/dist'
        filename='OpenBareMap-'+title+'.img';image=source/filename
        sha=digest(image);text=garmin_instructions(region,filename)
        (source/'INSTALL.txt').write_text(text)
        sums=source/'SHA256SUMS.txt'
        if sums.exists():
            lines=[]
            for line in sums.read_text().splitlines():
                old,name=line.split('  ',1);lines.append((digest(source/name) if name=='INSTALL.txt' else old)+'  '+name+'\n')
            sums.write_text(''.join(lines))
        dest=ROOT/'distribution/app-bundles-v1/garmin'/region;dest.mkdir(parents=True,exist_ok=True)
        (dest/'instructions.txt').write_text(text);(dest/'SHA256SUMS.txt').write_text(sha+'  '+filename+'\n')
        shutil.copyfile(source/'ATTRIBUTION.txt',dest/'ATTRIBUTION.txt')
        for name in ['terrain-attribution.md','terrain-data-sources.md']:shutil.copyfile(ROOT/'data'/name,dest/name)
        record={'region':region,'downloadURL':'https://downloads.appsbyonzy.dev/Garmin/'+filename,'instructionsURL':'https://downloads.appsbyonzy.dev/Garmin/'+('instructions.txt' if region=='ireland' else region+'-instructions.txt'),'imageSHA256':sha,'instructionsSHA256':digest(dest/'instructions.txt')}
        boundary=source/'boundary-source.json'
        if boundary.exists():
            shutil.copyfile(boundary,dest/boundary.name)
            record.update(boundarySourceURL='https://downloads.appsbyonzy.dev/Garmin/'+region+'/'+boundary.name,boundarySourceSHA256=digest(boundary))
        write(dest/'manifest.json',record)
if __name__=='__main__':build()
