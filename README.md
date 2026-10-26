# OpenBareMap

An offline topographic map for the whole island of Ireland, including Northern Ireland and offshore islands. Every real-data build covers the full source extract.

## Current map: 1.1 cartography, rebuilt data

Development version 0.4 restores OpenBareMap 1.1's palette, Open Sans typography, road/route styles, boundaries, naming layers and terrain textures. Text halos are omitted at the user’s request. The original 1.1 bundle is preserved selectively in `assets/legacy-1.1` as reference material; the runtime entry point is `style/openbaremap.json`.

The basemap is rebuilt from our locked 2026-10-24 full-island OSM snapshot. It includes roads, paths, tracks, water, land cover, buildings, settlements, summits and saddles, hiking facilities, walking and cycling relations, boundaries, railways, stations, ferries, road names, water names and island names. Hiking facilities use dots and words; parking retains the conventional white P on blue. Missing general POI icons from the old bundle are not referenced.

Contours retain **10-metre intervals** from our approximately 30-metre composite elevation data. The progressive 1.1 treatment shows 100 m index lines from zoom 8 and their labels from zoom 9; all intermediate 10 m lines enter at zoom 11 and their labels at zoom 12. This replaces the preceding 100/50/10 m display stages. Index and intermediate strokes and text scale differently. Contour label repeat spacing is 440 pixels for index labels and 360 pixels for intermediate labels, halving repeat placement opportunities relative to 1.1; collision handling affects actual visible counts. Hillshade is 46% opaque. Rock and scree fills and stipples draw above hillshade; cliffs use the copied teeth pattern. Bog textures now actually render, using low/mid/high patterns at zooms 9/12/14. Peat workings remain separately classified.

The 1.1 townland label points (50,380 features) and fixed Irish Grid are inherited assets with exact checksums, not claimed as newly regenerated data. Grid lines show 10 km spacing from zoom 10 and 1 km from zoom 12. Their provenance and all copied font/pattern/reference files are recorded in `legacy-assets.lock.json`. The old basemap, contours and hillshade are not reused. Glyph generation and grid/townland generation recipes remain to be recovered or replaced.

`classic-map-report.json` records the new builds and tile inventories. `classic-terrain-preview.png` and `classic-bog-preview.png` show the active cartography; earlier screenshots and reports are historical.

## Restore and view

The selected map databases and exact OSM, coast and elevation inputs are stored with Git LFS. Duplicate builds and intermediates are excluded.

```sh
git lfs install --local
git lfs pull
python3 scripts/serve.py
```

Open http://127.0.0.1:8765 while the server runs. It verifies `active-map.json` checksums, serves local resources, and converts XYZ requests to MBTiles TMS rows. Coast uses a separately capped source to overzoom its zoom-12 polygons while contours continue through zoom 14. The four selected databases are the fresh basemap, existing coast/contours, existing corrected hillshade, and copied grid. Their exact paths are in `active-map.json`.

MapLibre GL JS 5.6.1 and its stylesheet are vendored. All runtime map, glyph, sprite and townland requests are local. Attribution links are external only when followed. See `viewer-assets.lock.json`, `legacy-assets.lock.json` and the viewer's terrain attribution page.

The legend reads active style colours, opacity, dash lengths and textures. Hillshade and contour density still affect the apparent colours on the map. The archived illustrated 1.1 legend is reference material, not the runtime legend.

## Sources and rebuilding

The Geofabrik Ireland and Northern Ireland extract is dated 2026-10-24; its checksum is recorded in `sources.lock.json`. The OSM coast archive is recorded in `coast-sources.lock.json`. Elevation uses 30 Terrain Tiles skadi grids covering longitude -11 to -5 and latitude 51 to 56, with exact checksums in `terrain-sources.lock.json`. This elevation product is composite data, not pure SRTM. Mutable upstream URLs never silently replace locked source bytes.

Use fresh build names: existing output directories are never overwritten.

```sh
python3 scripts/openbaremap.py build ireland-classic-d
python3 scripts/openbaremap.py build ireland-classic-e
python3 scripts/openbaremap.py compare ireland-classic-d ireland-classic-e
python3 -m unittest discover -s tests -v
```

Build commands record the exact input, processor, configuration and Tilemaker binary. Restore the selected archives without rebuilding when those build names already exist. Terrain rebuild scripts are `scripts/build_topography.py` and `scripts/build_hillshade.py`; their records and locks retain the independent elevation provenance.

The sprite atlas is assembled from the checked-in original terrain textures and a generated parking P. Install `assets/requirements.txt` in an isolated Python environment and run `python3 scripts/build_sprites.py`. Output hashes and Pillow version are in `assets/sprites.lock.json`.

## Limits and remaining work

This remains development cartography. Independent land-cover completeness, directional cliff correctness, bridge/tunnel ordering, nested route semantics, language policy and cross-device acceptance remain unfinished. The copied cliff pattern follows geometry, but has not been verified as indicating the downhill side. OSM access tags do not establish public access or route safety. The inherited townlands and grid are pinned binary/source assets with incomplete generation recipes. A portable pinned toolchain, fresh font generation and an app-independent release package are still required.

Tests cover source classification and elevations, restored layer emission, tile integrity and row addressing, deterministic packaging, resource references, font/pattern availability, copied asset checksums and contour configuration. Reports distinguish build checks from independent geographic accuracy.

Mountain names now start two zoom levels later: 600 m+ at zoom 11, 300–599 m at zoom 12, lower or unrecorded heights at zoom 13, and saddles at zoom 14. These presentation rules use retained numeric OSM elevations and do not require rebuilding geometry.

Settlement names start at zoom 6 for cities, 8 for towns, 9 for villages and other localities, and 10 for hamlets. Townlands remain at zoom 12.

A further two-zoom delay applies to all text labels except townlands: cities 8, towns 10, villages/localities 11, hamlets 12; mountains 600 m+ 13, 300–599 m 14, lower/unknown 15, saddles 16. Townlands stay at 12. Road, water, island, amenity, grid and contour text also starts two zooms later than before this adjustment. Geometry and parking symbols keep their previous visibility thresholds; parking text is a separate layer.

The last global text delay is reduced from two zooms to one: cities 7, towns 9, villages/localities 10, hamlets 11; mountains 600 m+ 12, 300–599 m 13, lower/unknown 14, saddles 15. All other text from that adjustment also moves one zoom earlier. Townlands remain at 12.

Grid and local boundaries use stronger strokes: 10 km grid at 72% opacity from zoom 10; 1 km grid at 60% from zoom 12; local boundaries at 80% from zoom 10. The legend uses the same paint values.

Road visibility: major roads (motorway, trunk, primary and secondary) start at zoom 7. Minor/service roads, tracks and paths start at zoom 11. Walking and cycling route overlays, including national/international routes, also start at zoom 11. Matching casing layers use the same thresholds.
