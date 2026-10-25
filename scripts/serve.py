#!/usr/bin/env python3
"""Loopback-only offline reference viewer and read-only MBTiles transport."""
import argparse
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import re
import sqlite3
from urllib.parse import unquote, urlsplit, urljoin

ROOT = Path(__file__).resolve().parents[1]

def read_tile(database, z, x, y):
    if not 0 <= z <= 14 or not (0 <= x < 2**z and 0 <= y < 2**z):
        raise ValueError('Invalid XYZ coordinates')
    tms_y = (1 << z) - 1 - y
    with closing(sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True)) as db:
        row = db.execute('SELECT tile_data FROM tiles WHERE zoom_level=? AND tile_column=? AND tile_row=?', (z,x,tms_y)).fetchone()
    return row[0] if row else None

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, status, body=b'', content_type='application/octet-stream', gzip=False):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('X-Content-Type-Options', 'nosniff')
        if gzip:
            self.send_header('Content-Encoding', 'gzip')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = unquote(urlsplit(self.path).path)
        origin = f'http://127.0.0.1:{self.server.server_port}'
        match = re.fullmatch(r'/tiles/(?:(topography|hillshade)/)?(\d+)/(\d+)/(\d+)\.(?:pbf|png)', path)
        if match:
            try:
                dataset = match.group(1) or 'basemap'
                if dataset not in self.server.datasets:
                    self.reply(404)
                    return
                payload = read_tile(self.server.datasets[dataset]['path'], *map(int, match.groups()[1:]))
            except ValueError:
                self.reply(400)
                return
            if payload is None:
                self.reply(204)
            else:
                self.reply(200, payload, 'image/png' if dataset == 'hillshade' else 'application/x-protobuf', payload[:2] == b'\x1f\x8b')
            return
        if path in ['/tiles.json','/topography.json','/hillshade.json']:
            dataset={'/tiles.json':'basemap','/topography.json':'topography','/hillshade.json':'hillshade'}[path]
            if dataset not in self.server.datasets:
                self.reply(404)
                return
            metadata=self.server.datasets[dataset]['metadata']
            prefix='' if dataset=='basemap' else dataset+'/'
            suffix='png' if dataset=='hillshade' else 'pbf'
            attribution='© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'
            if dataset=='hillshade':
                attribution='Terrain Tiles / Mapzen · Copernicus EU-DEM · USGS · NOAA · <a href="/terrain-attribution.html">Terrain attribution</a>'
            data={'tilejson':'3.0.0','name':metadata.get('name',dataset),'scheme':'xyz','tiles':[origin+'/tiles/'+prefix+'{z}/{x}/{y}.'+suffix],'minzoom':int(metadata['minzoom']),'maxzoom':int(metadata['maxzoom']),'bounds':list(map(float,metadata['bounds'].split(','))),'attribution':attribution}
            self.reply(200,json.dumps(data).encode(),'application/json')
            return
        if path == '/style/openbaremap.json':
            style = json.loads((ROOT/'style/openbaremap.json').read_text())
            base=origin+'/style/openbaremap.json'
            for source in style['sources'].values():
                if 'url' in source:source['url']=urljoin(base,source['url'])
                if 'tiles' in source:source['tiles']=[urljoin(base,url) for url in source['tiles']]
            style['glyphs']=urljoin(base,style['glyphs'])
            self.reply(200, json.dumps(style).encode(), 'application/json')
            return
        name = 'index.html' if path == '/' else path.lstrip('/')
        target = (ROOT/'viewer'/name).resolve()
        if not target.is_relative_to((ROOT/'viewer').resolve()) or not target.is_file():
            self.reply(404)
            return
        self.reply(200,target.read_bytes(), mimetypes.guess_type(target)[0] or 'application/octet-stream')

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--database',type=Path,help='Optional override for the base vector database')
    args=parser.parse_args()
    manifest=json.loads((ROOT/'active-map.json').read_text())
    datasets={}
    from openbaremap import digest
    for name,item in manifest['datasets'].items():
        path=ROOT/item['path']
        if name=='basemap' and args.database is not None:path=args.database
        if not path.is_file():parser.error('Missing selected map database: '+str(path))
        if not (name=='basemap' and args.database is not None) and digest(path)!=item['sha256']:
            parser.error('Selected database checksum mismatch: '+name)
        with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)) as db:
            datasets[name]={'path':path,'metadata':dict(db.execute('SELECT name,value FROM metadata'))}
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    server.datasets=datasets
    print(f'OpenBareMap viewer: http://127.0.0.1:{server.server_port}',flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__=='__main__':
    main()
