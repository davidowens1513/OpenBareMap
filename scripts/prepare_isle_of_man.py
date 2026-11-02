#!/usr/bin/env python3
"""Lock the complete Isle of Man source and extend the England/Wales OSM union."""
from pathlib import Path
import datetime,hashlib,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'work/python')]
import osmium
from openbaremap import digest,write

def main():
 work=ROOT/'work/isle-of-man';work.mkdir(exist_ok=True)
 lockpath=ROOT/'regions/england-wales/sources.lock.json';old=json.loads(lockpath.read_text())
 if any('/isle-of-man-' in x['path'] for x in old['inputs']):
  assert digest(ROOT/old['osm']['path'])==old['osm']['sha256'];print('Complete three-extract source already verified.');return
 write(work/'previous-sources.lock.json',old);write(work/'previous-active-map.json',json.loads((ROOT/'regions/england-wales/active-map.json').read_text()))
 source=Path('/private/tmp/isle-of-man-261030.osm.pbf');checksum=Path(str(source)+'.md5').read_text().split()[0]
 with source.open('rb') as f:assert hashlib.file_digest(f,'md5').hexdigest()==checksum
 directory=ROOT/'data/regions/england-wales';target=directory/source.name;shutil.copyfile(source,target);poly=directory/'isle-of-man.poly';shutil.copyfile('/private/tmp/isle-of-man.poly',poly)
 with osmium.io.Reader(str(target)) as reader:stamp=reader.header().get('osmosis_replication_timestamp')
 assert stamp==old['osm']['replicationTimestamp']
 item={'path':str(target.relative_to(ROOT)),'sha256':digest(target),'bytes':target.stat().st_size,'url':'https://download.geofabrik.de/europe/'+target.name,'replicationTimestamp':stamp}
 output=directory/'england-wales-isle-of-man-261030.osm.pbf';assert not output.exists()
 merger=osmium.MergeInputReader();merger.add_file(str(target))
 assert digest(ROOT/old['osm']['path'])==old['osm']['sha256']
 with osmium.io.Reader(str(ROOT/old['osm']['path'])) as reader:
  writer=osmium.io.Writer(str(output),reader.header())
  try:merger.apply_to_reader(reader,writer)
  finally:writer.close()
 new={**old,'osm':{'path':str(output.relative_to(ROOT)),'sha256':digest(output),'bytes':output.stat().st_size,'snapshot_date':'2026-10-30','replicationTimestamp':stamp,'operation':'Sorted libosmium union of complete England, Wales and Isle of Man extracts; duplicate objects resolved by version','url':None},'inputs':old['inputs']+[item],'polygons':old['polygons']+[{'path':str(poly.relative_to(ROOT)),'sha256':digest(poly),'bytes':poly.stat().st_size,'url':'https://download.geofabrik.de/europe/isle-of-man.poly'}],'previousAcceptedOSM':old['osm'],'accessed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()};write(lockpath,new)
 p=ROOT/'regions/england-wales/region.json';profile=json.loads(p.read_text());profile.update(mapVersion='2.0.1',coverage='Complete England, Wales and Isle of Man extracts, including offshore islands; no regional sampling',sourceSlugs=['england','wales','isle-of-man'],sourceBaseOverrides={'isle-of-man':'https://download.geofabrik.de/europe/'},sourceOutputStem='england-wales-isle-of-man',garminPackageRevision='2.0.1-isle-of-man-r1');profile['destinations']['isle-of-man']=[-4.53,54.23,10];write(p,profile)
 from region_coverage import polygon_union
 polygon_union('england-wales',ROOT/'regions/england-wales/garmin/coverage.poly')
 write(work/'source-extension.json',{'isleOfMan':item,'newCombinedOSM':new['osm'],'previousCombinedOSM':old['osm'],'sameReplicationTimestamp':True});print('Complete England/Wales/Isle of Man source union locked.',flush=True)
if __name__=='__main__':main()
