"""Platform-neutral capped coast packaging from the selected terrain database."""
import json
import sqlite3

def build_capped_coast(top, coast):
    src=sqlite3.connect(top.as_uri()+'?mode=ro',uri=True);dst=sqlite3.connect(coast)
    metadata=dict(src.execute('SELECT name,value FROM metadata'));metadata['maxzoom']='12';metadata['name']='OpenBareMap capped coast source';metadata['description']='Unchanged topography tile payloads through zoom 12, packaged for coastline overzoom'
    schema=json.loads(metadata['json'])
    for layer in schema['vector_layers']:layer['maxzoom']=min(12,layer['maxzoom'])
    metadata['json']=json.dumps(schema,separators=(',',':'))
    dst.execute('CREATE TABLE metadata (name TEXT NOT NULL,value TEXT)')
    dst.execute('CREATE TABLE tiles (zoom_level INTEGER NOT NULL,tile_column INTEGER NOT NULL,tile_row INTEGER NOT NULL,tile_data BLOB NOT NULL,PRIMARY KEY(zoom_level,tile_column,tile_row))')
    dst.executemany('INSERT INTO metadata VALUES (?,?)',sorted(metadata.items()))
    dst.executemany('INSERT INTO tiles VALUES (?,?,?,?)',src.execute('SELECT zoom_level,tile_column,tile_row,tile_data FROM tiles WHERE zoom_level<=12 ORDER BY zoom_level,tile_column,tile_row'));dst.commit();dst.close();src.close()
