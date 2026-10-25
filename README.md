# OpenBareMap

An independent offline topographic map build for the whole island of Ireland, including Northern Ireland and offshore islands. All real-data builds use full-island coverage; there is no sample-area stage. The old 1.1 map bundle is retained outside this project as a visual reference.

## Current map

The development map includes fresh OSM roads, paths, tracks, buildings, water and land cover; settlement labels; official OSM coastal land polygons; and new contours and shaded relief. Contours are generated at 10-metre intervals from approximately 30-metre composite elevation data. The displayed interval changes with zoom to show 100-metre, then 50-metre, then 10-metre detail.

The selected databases are recorded with checksums in `active-map.json`:

| Content | Selected file |
| --- | --- |
| Base vectors | `build/ireland-a/basemap.mbtiles` |
| Coastal land and contours | `build/topography-a/topography.mbtiles` |
| Corrected hillshade | `build/hillshade-a/hillshade.mbtiles` |

This is a development map, not a finished OpenBareMap release. Road labels, summit and hiking features, routes, cliff detail, bridge/tunnel ordering, and other acceptance checks remain pending.

## Open the viewer

From this project folder:

```sh
python3 scripts/serve.py
```

Open http://127.0.0.1:8765 while that process is running. The server is restricted to this Mac's loopback address and verifies selected database checksums at startup. It exposes XYZ tile requests and converts rows to MBTiles TMS addressing. It does not change the databases.

The reference style is `style/openbaremap.json`. The server resolves resource addresses against its local origin; it does not repair schema or cartography. Coast geometry is stored through zoom 12 and deliberately uses a separate capped source to overzoom at higher magnifications while contours continue through zoom 14.

Renderer, stylesheet, glyph and tile requests are local. Attribution links are external only when followed. MapLibre GL JS 5.6.1 assets are vendored with their license and checksums. Open Sans glyphs are temporarily reused from the old bundle with their Apache license and recorded provenance; a fresh glyph generation recipe remains pending. See `viewer-assets.lock.json`.

`topography-preview.png` shows mountain detail; `coast-preview.png` shows Kerry's coast. The older `viewer-preview.png` records the vector-only stage.

## Recorded source data

The base OSM extract is the complete Geofabrik Ireland and Northern Ireland source dated 2026-10-24. Its download matched Geofabrik's published checksum, and its SHA-256 is recorded in `sources.lock.json`.

The coast source is the official OSM split land-polygons archive in WGS84. Its checksums and HTTP publication information are recorded in `coast-sources.lock.json`. Publication time is not claimed to be an exact OSM snapshot timestamp.

Elevation uses 30 one-degree Mapzen / Terrain Tiles skadi grids covering longitude -11 to -5 and latitude 51 to 56. This is a composite elevation product, not pure SRTM. Each compressed grid has been checked for gzip integrity, expected dimensions and SHA-256. See `terrain-sources.lock.json`, `source-documents.lock.json` and the viewer's terrain attribution page.

Keep the actual source files durably. Mutable download URLs cannot guarantee future recovery of identical snapshots. No source is silently replaced when its checksum changes.

## Rebuild

The following commands are for fresh output directories. Existing build folders are never overwritten; archive or rename a prior run before reusing its name.

```sh
python3 scripts/fetch_coast.py
python3 scripts/fetch_terrain.py
python3 scripts/openbaremap.py build ireland-a --accept-toolchain
python3 scripts/openbaremap.py build ireland-b
python3 scripts/openbaremap.py compare
python3 scripts/build_topography.py topography-a --accept-toolchain
python3 scripts/build_topography.py topography-b
python3 -m unittest discover -s tests -v
```

The registered OSM source must already be present. For a new source registration, use `openbaremap.py register /absolute/path/input.osm.pbf --url ACTUAL_SOURCE_URL --date YYYY-MM-DD`. Existing source locks are intentionally protected against replacement.

The complete topography builder generates the land clip, projected elevation, contours, vector tiles and the corrected, canonically packaged hillshade. Its raster stage can also be rebuilt independently from a recorded elevation checkpoint:

```sh
python3 scripts/build_hillshade.py topography-a hillshade-a
python3 scripts/build_hillshade.py topography-b hillshade-b
```

The selected current hillshade comes from those independent raster builds, after a visual check identified and corrected no-data transparency. Earlier outputs and failed-run logs are retained under `build/` as diagnostics and are not selected by the viewer. Build records remain immutable; visual review is recorded separately in `visual-review.json`.

Builds use the installed Tilemaker and QGIS-bundled GDAL tools. The scripts record executable identities and explicitly locate QGIS's GDAL and PROJ data. `topography-toolchain.lock.json` includes hashes of those data files. This proves local repeatability; a portable container with all shared libraries pinned remains pending.

## Validation and remaining work

Two base builds match byte-for-byte. Two coast/contour builds also match byte-for-byte. The final hillshade builds use identical elevation checkpoints and produce identical tiles, metadata and complete archive bytes after canonical SQLite packaging. Canonical packaging sorts metadata and tile rows into a fresh database so incidental storage layout does not affect a release checksum. It does not alter tile pixels.

See `build-report.json` and `topography-report.json`. Actual vector layer presence was checked by parsing tile contents. Representative elevation checks cover upland locations in Kerry, Wicklow, the Mournes and Donegal; sea no-data and final raster transparency were checked separately. These are sanity checks, not a survey of vertical accuracy. Representative coast and mountain views were inspected in the viewer.

Next work is cartographic completeness and full acceptance: hiking and summit features, route relations, labels and language policy, road structure ordering, legend consistency, source/style compatibility, broader visual review, fresh font generation, portable dependency pinning, and a release package independent of any particular consuming app.

References: [Tilemaker](https://github.com/systemed/tilemaker/tree/master/docs), [OSM land polygons](https://osmdata.openstreetmap.de/data/land-polygons.html), [Terrain Tiles](https://registry.opendata.aws/terrain-tiles/), [GDAL](https://gdal.org/en/stable/), [MapLibre style specification](https://maplibre.org/maplibre-style-spec/).
