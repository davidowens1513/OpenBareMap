#!/usr/bin/env python3
"""Loopback-only offline reference viewer and read-only MBTiles transport."""
import argparse
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import html
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
        match = re.fullmatch(r'/tiles/(?:(topography|hillshade|grid)/)?(\d+)/(\d+)/(\d+)\.(?:pbf|png)', path)
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
        if path in ['/tiles.json','/topography.json','/hillshade.json','/grid.json']:
            dataset={'/tiles.json':'basemap','/topography.json':'topography','/hillshade.json':'hillshade','/grid.json':'grid'}[path]
            if dataset not in self.server.datasets:
                self.reply(404)
                return
            metadata=self.server.datasets[dataset]['metadata']
            prefix='' if dataset=='basemap' else dataset+'/'
            suffix='png' if dataset=='hillshade' else 'pbf'
            attribution='© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'
            if dataset=='grid':attribution=self.server.grid_attribution
            if dataset=='hillshade':
                attribution='Terrain Tiles / Mapzen · Copernicus EU-DEM · USGS · NOAA · <a href="/terrain-attribution.html">Terrain attribution</a>'
            data={'tilejson':'3.0.0','name':metadata.get('name',dataset),'scheme':'xyz','tiles':[origin+'/tiles/'+prefix+'{z}/{x}/{y}.'+suffix],'minzoom':int(metadata['minzoom']),'maxzoom':int(metadata['maxzoom']),'bounds':list(map(float,metadata['bounds'].split(','))),'attribution':attribution}
            self.reply(200,json.dumps(data).encode(),'application/json')
            return
        if path == '/style/openbaremap.json':
            from regions import region_style
            style = region_style(self.server.region)
            base=origin+'/style/openbaremap.json'
            for source in style['sources'].values():
                if 'url' in source:source['url']=urljoin(base,source['url'])
                if 'data' in source and isinstance(source['data'],str):source['data']=urljoin(base,source['data'])
                if 'tiles' in source:source['tiles']=[urljoin(base,url) for url in source['tiles']]
            style['glyphs']=urljoin(base,style['glyphs'])
            if 'sprite' in style:style['sprite']=urljoin(base,style['sprite'])
            self.reply(200, json.dumps(style).encode(), 'application/json')
            return
        if path in ('/park-boundary.geojson','/coverage.geojson','/coverage-mask.geojson'):
            from regions import profile, region_path
            if not (profile(self.server.region).get('coverageBoundary') or profile(self.server.region).get('boundaryPreview')):
                self.reply(404); return
            self.reply(200,region_path(self.server.region,path[1:]).read_bytes(),'application/geo+json'); return
        if path == '/region.json':
            from regions import profile
            self.reply(200,json.dumps(profile(self.server.region)).encode(),'application/json')
            return
        name = 'index.html' if path == '/' else path.lstrip('/')
        target = (ROOT/'viewer'/name).resolve()
        if not target.is_relative_to((ROOT/'viewer').resolve()) or not target.is_file():
            self.reply(404)
            return
        body=target.read_bytes()
        if name == 'index.html' and self.server.region != 'ireland':
            from regions import profile
            p=profile(self.server.region);label=p['label']
            body=body.decode().replace('IRELAND & NORTHERN IRELAND',html.escape(label.upper())).replace('Ireland',html.escape(label)).replace('Irish Grid', html.escape(p['gridName'])).replace('irish-grid-', p['gridSource']+'-').encode()
        if name == 'index.html':
            from regions import profile
            if profile(self.server.region).get('coverageBoundary') or profile(self.server.region).get('boundaryPreview'):
                body=body.replace(b'County border',b'Province border')
                body=body.replace(b'<div class="legend">',b'<details class="preview-key"><summary>Map key</summary><div class="legend">').replace(b'</div>\n<p class="note">',b'</div></details>\n<p class="note">')
                body=body.replace(b'</head>',b'<style>.preview-key{margin-top:14px}.preview-key summary{cursor:pointer;font-size:12px}@media(max-width:600px){aside{width:calc(100% - 70px);max-height:300px}.badge{margin-bottom:4px}aside p{margin:8px 0}.preview-key{margin-top:10px}}</style></head>')
                body=body.replace('Version 2.0 · 20 m contours'.encode(),'Local preview · 20 m contours'.encode())
                body=body.replace(b'<label for="location">',b'<p style="font-size:12px"><span style="color:#8c278b">&#9473;</span> National park &nbsp; &#9476; 25 km boundary</p><label for="location">')
        self.reply(200,body, mimetypes.guess_type(target)[0] or 'application/octet-stream')

class MapServer(ThreadingHTTPServer):
    # MapLibre requests many independent tiles together; retain the full burst.
    request_queue_size = 128

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--region',choices=['ireland','england-wales','scotland','sierra-nevada','pyrenees'],default='ireland')
    parser.add_argument('--database',type=Path,help='Optional override for the base vector database')
    args=parser.parse_args()
    from regions import active_map, profile
    manifest=active_map(args.region)
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
    server=MapServer(('127.0.0.1',args.port),Handler)
    server.datasets=datasets
    server.region=args.region
    p=profile(args.region)
    server.grid_attribution=p['gridName']+' ('+p['gridCRS']+') · OpenBareMap'
    print(f'OpenBareMap viewer: http://127.0.0.1:{server.server_port}',flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__=='__main__':
    main()
