"""Retain coastal polygon areas while removing zero-area clipping remnants."""
import json
from openbaremap import digest

def polygon_parts(geometry):
    if geometry is None:
        return []
    kind = geometry['type']
    if kind == 'Polygon':
        return [geometry['coordinates']]
    if kind == 'MultiPolygon':
        return geometry['coordinates']
    if kind == 'GeometryCollection':
        return [part for child in geometry['geometries'] for part in polygon_parts(child)]
    if kind in ('Point', 'MultiPoint', 'LineString', 'MultiLineString'):
        return []
    raise ValueError('Unexpected coastal geometry type: ' + kind)

def polygonal_coast(path, *, repair_invalid=False):
    if repair_invalid:
        from shapely import make_valid
        from shapely.geometry import mapping, shape

    original_sha = digest(path)
    data = json.loads(path.read_text())
    output = []; removed = 0; collections = 0; repaired = 0
    for feature in data['features']:
        geometry = feature.get('geometry')
        parts = polygon_parts(geometry)
        if parts and repair_invalid:
            polygon = shape({'type': 'MultiPolygon', 'coordinates': parts})
            if not polygon.is_valid:
                parts = polygon_parts(mapping(make_valid(polygon)))
                geometry = {'type': 'MultiPolygon', 'coordinates': parts}
                feature = {**feature, 'geometry': geometry}
                repaired += 1
        if not parts:
            removed += 1
            continue
        if geometry['type'] == 'GeometryCollection':
            feature = {**feature, 'geometry': {'type': 'MultiPolygon', 'coordinates': parts}}
            collections += 1
        output.append(feature)
    if not output:
        raise ValueError('Coastline crop contains no polygon areas')
    if removed or collections or repaired:
        backup = path.with_name('land-unfiltered.geojson')
        if backup.exists():
            raise FileExistsError(backup)
        path.rename(backup)
        with path.open('w') as stream:
            # Native overlay readers stream one Feature per line.
            header = json.dumps({k: v for k, v in data.items() if k != 'features'}, separators=(',', ':'))
            stream.write(header[:-1] + ',"features":[\n')
            for index, feature in enumerate(output):
                if index:
                    stream.write(',\n')
                json.dump(feature, stream, separators=(',', ':'))
            stream.write('\n]}\n')
    return {'sourceSHA256': original_sha, 'outputSHA256': digest(path),
            'removedZeroAreaFeatures': removed, 'extractedPolygonCollections': collections,
            'retainedPolygonFeatures': len(output),
            **({'repairedInvalidFeatures': repaired} if repair_invalid else {}),
            'operation': 'Repair invalid clipped polygons and retain their polygon parts' if repair_invalid
            else 'Retain every polygon ring; discard only point/line clipping remnants'}
