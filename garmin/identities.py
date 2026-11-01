"""Reserve disjoint Garmin product, tile and appearance-file identities."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def validate_registry(registry=None):
 registry=registry if registry is not None else json.loads((ROOT/'garmin/map-identities.json').read_text())
 items=list(registry.items())
 for index,(name,item) in enumerate(items):
  if not 0<item['familyId']<=65535 or item['tileStartId']>item['tileEndId']:raise ValueError('Invalid Garmin identity: '+name)
  for other,peer in items[:index]:
   if (item['familyId'],item['productId'])==(peer['familyId'],peer['productId']):raise ValueError('Garmin family/product collision: '+name+' / '+other)
   if max(item['tileStartId'],peer['tileStartId'])<=min(item['tileEndId'],peer['tileEndId']):raise ValueError('Garmin tile collision: '+name+' / '+other)
 return registry
def validate_config(name,config):
 expected=validate_registry()[name]
 for field in ['familyId','tileStartId']:
  if config[field]!=expected[field]:raise ValueError('Garmin config differs from reserved '+field+': '+name)
 if '--family-id='+str(expected['familyId']) not in config['compilerOptions']:raise ValueError('Wrong Garmin compiler family: '+name)
 return expected

def write_tile_args(sources,destination,name,description):
 """Keep cached source filenames independent of current output map identifiers."""
 reserved=validate_registry()[name]
 sources=list(sources)
 if not sources or len(sources)>reserved['tileEndId']-reserved['tileStartId']+1:raise ValueError('Invalid Garmin source section count')
 identifiers=[reserved['tileStartId']+i for i in range(len(sources))]
 destination.write_text(''.join(f'mapname: {identifier}\ndescription: {description}\ninput-file: {source}\n\n' for identifier,source in zip(identifiers,sources)))
 return {str(identifier) for identifier in identifiers}
