"""Platform-neutral land-only capped coast source, preserving land MVT payloads."""
import json
import sqlite3
from build_cartography_2 import layers, encode

def build_capped_coast(top, coast):
    if coast.exists():raise FileExistsError(coast)
    src=sqlite3.connect(top.as_uri()+'?mode=ro',uri=True);dst=sqlite3.connect(coast)
    metadata=dict(src.execute('SELECT name,value FROM metadata'));metadata['maxzoom']='12';metadata['name']='OpenBareMap capped coast source';metadata['description']='Land-only topography layer through zoom 12 for coastline overzoom'
    schema=json.loads(metadata['json']);schema['vector_layers']=[layer for layer in schema['vector_layers'] if layer['id']=='land']
    for layer in schema['vector_layers']:layer['maxzoom']=min(12,layer['maxzoom'])
    metadata['json']=json.dumps(schema,separators=(',',':'))
    dst.execute('CREATE TABLE metadata (name TEXT NOT NULL,value TEXT)')
    dst.execute('CREATE TABLE tiles (zoom_level INTEGER NOT NULL,tile_column INTEGER NOT NULL,tile_row INTEGER NOT NULL,tile_data BLOB NOT NULL,PRIMARY KEY(zoom_level,tile_column,tile_row))')
    dst.executemany('INSERT INTO metadata VALUES (?,?)',sorted(metadata.items()))
    for z,x,y,data in src.execute('SELECT zoom_level,tile_column,tile_row,tile_data FROM tiles WHERE zoom_level<=12 ORDER BY zoom_level,tile_column,tile_row'):
        land=[(name,raw) for name,raw in layers(data) if name=='land']
        # Keep explicit empty tiles so clients cannot fall back to coarser land.
        dst.execute('INSERT INTO tiles VALUES (?,?,?,?)',(z,x,y,encode(land)))
    dst.commit();dst.close();src.close()
