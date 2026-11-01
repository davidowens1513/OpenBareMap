#!/usr/bin/env python3
"""Publish a locally validated Garmin revision into the existing regional distribution."""
import argparse,hashlib,json,os,re,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--work',type=Path,required=True);a=parser.parse_args();work=a.work.resolve();region=ROOT/'regions/england-wales/garmin';release=ROOT/'releases/england-wales/2.0.0'
 record=json.loads((work/'build.json').read_text());image=work/'compiled/gmapsupp.img';config=json.loads((region/'config.json').read_text())
 if record['outputSHA256']!=sha(image):raise ValueError('Compiled map changed')
 if record['configSHA256']!=sha(region/'config.json'):raise ValueError('Config changed after compilation')
 for name,expected in record['styleSHA256'].items():
  if sha(region/'style'/name)!=expected:raise ValueError('Style changed after compilation')
 for path,expected in record['preservedMaps'].items():
  if sha(ROOT/path)!=expected:raise ValueError('Companion map changed')
 validation=(work/'map-set-validation.txt').read_text()
 expected_files=1+len(record['preservedMaps'])
 expected_sections=318+sum(91 if path.endswith('OpenBareMap-Ireland.img') else 1 for path in record['preservedMaps'])
 if f'PASS: {expected_files} map files; {expected_sections} unique sections;' not in validation or '80 England/Wales land checks.' not in validation:raise ValueError('Missing full map-set/land verification')
 inspection=json.loads((work/'inspection.json').read_text())
 if inspection['tiles']!=318:raise ValueError('Incomplete map')
 if len(json.loads((work/'dem-checks.json').read_text()))!=108:raise ValueError('Missing elevation validation')
 previous=json.loads((region/'build-report.json').read_text());output=region/'dist/OpenBareMap-England-Wales.img'
 if sha(output)!=previous['output']['sha256']:raise ValueError('Current distributed map differs from previous record')
 backup=region/'work/replaced-r1';backup.mkdir(parents=True,exist_ok=True)
 if not (backup/output.name).exists():shutil.copyfile(output,backup/output.name)
 if sha(backup/output.name)!=previous['output']['sha256']:raise ValueError('Backup mismatch')
 write(backup/'build-report.json',previous)
 staged=output.with_suffix('.img.replacing');shutil.copyfile(image,staged)
 if sha(staged)!=record['outputSHA256']:raise ValueError('Staged output mismatch')
 os.replace(staged,output)
 output_record={'path':str(output.relative_to(ROOT)),'bytes':output.stat().st_size,'sha256':sha(output)}
 report={'status':'compiled and binary/land/map-set validated; hardware visual review pending','familyId':4833,'tileStartId':48330001,'garminPackageRevision':record['revision'],'routing':False,'output':output_record,'inspection':inspection,'expectedSections':318,'validation':{'mapSet':'map-set-validation.txt','landProbes':80,'detailLevels':5,'verifiedElevationGrids':108,'regressionTests':9},'buildRecord':'../../../releases/england-wales/2.0.0/build-records/garmin-r2-build.json','previousOutput':previous['output'],'preservedMaps':record['preservedMaps'],'cause':'England/Wales reused My Tracks family/product, tile identity and appearance filename; regional edition now uses reserved family 4833. Coast/background polygons also bypass the size filter.'}
 write(region/'build-report.json',report);write(region/'inspection.json',inspection)
 shutil.copyfile(work/'map-set-validation.txt',region/'map-set-validation.txt')
 records=release/'build-records';records.mkdir(exist_ok=True)
 record.update(status='compiled and binary/land/map-set validated; hardware review pending',output=output_record)
 for src,name in [('compile.log','garmin-r2-compile.log'),('dem-checks.json','garmin-r2-dem-checks.json'),('map-set-validation.txt','garmin-r2-map-set-validation.txt'),('regression.log','garmin-r2-regression.log')]:shutil.copyfile(work/src,records/name)
 if (work/'old-land-checks.log').exists():shutil.copyfile(work/'old-land-checks.log',records/'garmin-r1-affected-land-checks.txt')
 write(records/'garmin-r2-build.json',record)
 manifest=json.loads((release/'manifest.json').read_text());manifest['garmin']=output_record;manifest['garminPackageRevision']=record['revision'];write(release/'manifest.json',manifest)
 validation_path=release/'validation.json';v=json.loads(validation_path.read_text());v['garmin']=report;write(validation_path,v)
 devices=json.loads((region/'device-installations.json').read_text());devices['availableRevision']={'garminPackageRevision':record['revision'],'familyId':4833,'sha256':output_record['sha256'],'bytes':output_record['bytes'],'installationStatus':'Replacement on Montana 750i and GPSMAP 67i pending; existing device entries record the superseded build.'};write(region/'device-installations.json',devices)
 (region/'dist/SHA256SUMS.txt').write_text(output_record['sha256']+'  '+output.name+'\n')
 (region/'dist/INSTALL.txt').write_text('OpenBareMap England & Wales 2.0 — Garmin revision r2\n\nReplace the existing OpenBareMap-England-Wales.img in the Garmin folder on the device or memory card with this file, then restart the device. Keep backups outside the Garmin folder; do not leave an old England & Wales IMG alongside this replacement.\n\nThis edition uses family 4833, separate from Ireland (4831) and My Tracks (4832). Ireland and personal-track files need no changes. Display-only; no turn-by-turn routing. Set elevation units to metres.\n\nThe rebuilt map has passed binary inspection, map-identity checks and 80 land checks across five detail levels, including the photographed inland areas. Hardware visual review remains pending.\n')
 print(json.dumps(output_record,indent=2))
if __name__=='__main__':main()
