#!/usr/bin/env python3
"""Derive coastal walking corridors from pinned OpenStreetMap route relations."""

import argparse
import hashlib
import json
from math import ceil, floor

import osmium
from pyproj import Geod, Transformer
from shapely import line_merge, transform, union_all
from shapely.geometry import LineString, Point, box, mapping
from shapely.ops import nearest_points

from fetch_region import download
from garmin_render_coverage import read_poly
from openbaremap import ROOT, digest, write
from regions import profile, region_path, route_overlay_id


ROUTES = {
    'rota-vicentina': (
        (20810829, 'Fishermen’s Trail', (200, 255), ('sao-torpes', 'lagos', 'odeceixe')),
        (7592697, 'Historical Way', (230, 315), ('santiago-do-cacem', 'cabo-de-sao-vicente', 'saboia')),
    ),
    'lycian-way': (
        (51855, 'Lycian Way', (405, 690), ('ovacik', 'kas', 'finike', 'geyikbayiri')),
    ),
}


def part_lines(geometry):
    return [geometry] if geometry.geom_type == 'LineString' else list(geometry.geoms)


def feature(name, geometry):
    return {'type': 'Feature', 'properties': {'name': name}, 'geometry': mapping(geometry)}


def collection(features):
    return {'type': 'FeatureCollection', 'features': features}


def acquire(edition):
    region = edition['id']
    slug, = edition['sourceSlugs']
    base = edition['sourceBaseURL']
    stamp = edition['sourceDate'].replace('-', '')[2:]
    filename = f'{slug}-{stamp}.osm.pbf'
    directory = ROOT / 'data/regions' / region
    source = directory / filename
    url = base + filename
    if not source.exists():
        from download_ranges import fetch
        fetch(url, source, workers=4)
    checksum = directory / (filename + '.md5')
    download(url + '.md5', checksum)
    with source.open('rb') as stream:
        actual = hashlib.file_digest(stream, 'md5').hexdigest()
    if actual != checksum.read_text().split()[0]:
        raise ValueError(f'{region} source does not match Geofabrik’s MD5')
    outline = directory / (slug + '.poly')
    download(base + outline.name, outline)
    return source, outline, url


def relation_geometry(source, roots):
    relations = {}
    for relation in osmium.FileProcessor(source, osmium.osm.RELATION):
        if relation.tags.get('route') in {'hiking', 'foot', 'walking'} or relation.tags.get('type') == 'superroute':
            relations[relation.id] = (relation.version, tuple((m.type, m.ref) for m in relation.members))

    def member_ways(root):
        remaining = [root]
        visited, ways = set(), set()
        while remaining:
            relation = remaining.pop()
            if relation in visited:
                continue
            if relation not in relations:
                raise ValueError(f'Walking relation {root} refers to missing or unsupported relation {relation}')
            visited.add(relation)
            for kind, reference in relations[relation][1]:
                if kind == 'r':
                    remaining.append(reference)
                elif kind == 'w':
                    ways.add(reference)
        return ways, visited

    members = {root: member_ways(root) for root in roots}
    required_ways = set.union(*(m[0] for m in members.values()))
    ways = {way.id: tuple(n.ref for n in way.nodes)
            for way in osmium.FileProcessor(source, osmium.osm.WAY) if way.id in required_ways}
    if required_ways != ways.keys():
        raise ValueError('The source is missing route ways')
    required_nodes = {node for refs in ways.values() for node in refs}
    nodes = {node.id: (node.location.lon, node.location.lat)
             for node in osmium.FileProcessor(source, osmium.osm.NODE) if node.id in required_nodes}
    if required_nodes != nodes.keys():
        raise ValueError('The source is missing route node coordinates')
    lines = {way: LineString([nodes[n] for n in refs]) for way, refs in ways.items() if len(refs) >= 2}
    return {
        root: (line_merge(union_all([lines[way] for way in sorted(ways_for_root) if way in lines])),
               {str(relation): relations[relation][0] for relation in sorted(nested)})
        for root, (ways_for_root, nested) in members.items()
    }


def prepare(region):
    edition = profile(region)
    source, outline, source_url = acquire(edition)
    routes = ROUTES[region]
    geometries = relation_geometry(source, [root for root, *_ in routes])
    crs = edition['projectedCRS']
    project = Transformer.from_crs(4326, crs, always_xy=True).transform
    unproject = Transformer.from_crs(crs, 4326, always_xy=True).transform
    geod = Geod(ellps='WGS84')
    compared, projected, overlays = [], [], []
    for root, name, (minimum, maximum), stops in routes:
        route, versions = geometries[root]
        length = geod.geometry_length(route) / 1000
        if not minimum <= length <= maximum:
            raise ValueError(f'{name} relation {root} has unexpected length {length:.1f} km')
        metric = transform(route, project, interleaved=False)
        for stop in stops:
            point = transform(Point(edition['validationAnchors'][stop]), project, interleaved=False)
            if point.distance(metric) > 2500:
                raise ValueError(f'{name} does not reach {stop}')
        projected.append(metric)
        for part in part_lines(metric.simplify(5)):
            overlays.append(feature(name, transform(part, unproject, interleaved=False)))
        compared.append({'name': name, 'relation': f'https://www.openstreetmap.org/relation/{root}',
                         'relationVersions': versions, 'lengthKilometres': round(length, 2)})
        print(f'{name}: {length:.1f} km of distinct mapped route ways', flush=True)

    buffer_metres = edition['routeBufferMetres']
    buffer = union_all(projected).buffer(buffer_metres, quad_segs=16)
    coverage = transform(buffer, unproject, interleaved=False).intersection(read_poly(outline))
    if not coverage.is_valid or coverage.geom_type not in {'Polygon', 'MultiPolygon'}:
        raise ValueError('Invalid clipped walking corridor')
    if not all(coverage.covers(geometry[0]) for geometry in geometries.values()):
        raise ValueError('The source outline cuts through the walking route')
    for stop, coordinate in edition['validationAnchors'].items():
        if not coverage.covers(Point(coordinate)):
            raise ValueError(f'{region} corridor excludes {stop}')
    lon, lat, zoom = edition['destinations']['island']
    centre = Point(lon, lat)
    if not coverage.covers(centre):
        network = union_all([geometry[0] for geometry in geometries.values()])
        centre = nearest_points(network, centre)[0]
        edition['destinations']['island'] = [centre.x, centre.y, zoom]
    coverage_metric = transform(coverage, project, interleaved=False)
    xmin, ymin, xmax, ymax = coverage_metric.bounds
    bounds = list(coverage.bounds)
    edition.update(bounds=bounds, garminContextBounds=bounds,
                   gridExtent=[floor(xmin / 10000) * 10000, ceil(xmax / 10000) * 10000,
                               floor(ymin / 10000) * 10000, ceil(ymax / 10000) * 10000])
    out = region_path(region, 'region.json').parent
    route_path = out / (route_overlay_id(edition) + '.geojson')
    write(route_path, collection(overlays))
    write(out / 'coverage.geojson', collection([feature(edition['coverageBoundaryLabel'], coverage)]))
    write(out / 'coverage-mask.geojson', collection([feature('Outside map coverage', box(-180, -85, 180, 85).difference(coverage))]))
    write(out / 'park-boundary.geojson', collection([]))
    area = coverage_metric.area / 1e6
    write(out / 'boundary-source.json', {
        'sources': [{'url': source_url, 'sha256': digest(source), 'attribution': edition['boundaryAttribution']},
                    {'url': edition['sourceBaseURL'] + outline.name, 'sha256': digest(outline)}],
        'routes': compared,
        'changes': 'Nested OSM walking relations expanded, overlapping ways dissolved, and a projected buffer clipped to the source coverage. Display paths simplified to 5 m.',
        'bufferMetres': buffer_metres, 'bufferCRS': crs,
        'routeLengthKilometres': round(sum(route['lengthKilometres'] for route in compared), 2),
        'coverageSquareKilometres': round(area, 1),
        'coverageSHA256': digest(out / 'coverage.geojson'), 'routeSHA256': digest(route_path),
    })
    write(out / 'region.json', edition)
    print(f'{region}: verified {area:,.0f} km² of map coverage', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--region', choices=ROUTES, required=True)
    prepare(parser.parse_args().region)
