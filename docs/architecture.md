# OpenBareMap build architecture

OpenBareMap owns its source recipes, data schema, cartography and package format. Consuming applications own GPS, tracks, user controls and the transport adapter that exposes packaged resources to a renderer. No package field requires a particular host application or application version.

## Build boundaries

Inputs are immutable snapshots with provenance, acquisition date, snapshot date, exact content checksums and retrieval instructions. Tool versions and full runtime dependencies must be fixed. Generated outputs are never hand edited. Any cartographic correction must be expressed in a tracked input, transformation or style rule.

The all-Ireland schema includes water, land cover, waterways, transportation, buildings, place points, mountains, outdoor POIs, walking-route relations and cliff lines. Their class attributes preserve source classifications; styling is separate. Settlement labels are now present in the reference viewer. Coastal land, contours, hillshade and settlement labels are now available. Direct walking-route relations, summits and hiking amenities are also implemented. Road labels, nested route semantics and full cartographic acceptance remain unfinished. Polygon relation behavior needs fixture-based and real-world verification with the chosen Tilemaker version.

Do not carry forward separate overlay databases merely because the old package used them. Split physical databases only for distinct update cycles, size or rendering requirements. Vector basemap and raster hillshade are natural candidates; contour packaging remains a decision to test.

## Package contract to implement

A release needs a format version, map version, coverage, source snapshot identities, resource inventory, checksums and attribution. Layer and property names form a versioned schema. Resource locations must resolve consistently from the package root; the build must validate every referenced resource. Applications may substitute a transport base URL, but must not repair layer names, filters or individual missing paths.

Choose MBTiles and/or PMTiles after proving offline access in the target renderers. A format alone does not provide an offline transport implementation. Do not introduce a supposedly universal custom URL scheme without testing it on each renderer.

## Acceptance gates

A clean build must reject missing inputs and changed checksums. Two runs from the same locked inputs must produce matching logical tiles; compare stable metadata separately and explain any permitted archive-byte differences. Build failures must remain failures.

Automated validation must check database integrity, coordinate ranges, nonempty output, expected tile layers and properties, geographic coverage, all packaged resources and attribution. Implemented checks include database integrity, coordinate ranges, nonempty dataset validation, logical tile comparison, actual MVT layer inventory, source and asset checksums, tile-row conversion, canonical archive packaging, elevation grid coverage, representative elevation values and sea transparency. Complete geometry and geographic completeness checks remain pending.

Visual review must cover mountains, towns, coast and islands, bog, dense woodland, paths, bridges, tunnels and borders at fixed camera positions and zooms. Confirm contours, hillshade, labels, language rules, collision behavior and a consistent legend. Test in an entirely disconnected reference viewer and then representative Apple and Android consumers.

## Historical reference

The supplied 1.1 bundle records an OSM Ireland and Northern Ireland extract dated 2026-08-25, SRTM 1 Arc-Second Global Version 3 elevation, OSM land polygons and OpenMapTiles Open Sans fonts. These statements identify historical provenance, not complete reproducible inputs. Do not silently substitute newly downloaded data while claiming to reproduce 1.1.

## Geographic scope

Every real-data build targets the complete island of Ireland, including Northern Ireland and offshore islands, using the source extract extent. No Wicklow crop or sampling build is part of the workflow. Repeatability comparisons run on two complete builds.

## Topography processing

Official OSM land polygons supply a sea mask and coastal fill. Elevation grids are mosaicked, bilinearly reprojected into EPSG:2157 at 30-metre spacing, and masked to land. Contours are generated every 10 metres and simplified by 3 metres before transformation to WGS84 vector geometry. Hillshade uses multidirectional lighting with a 45-degree altitude and metre-based scaling. Its no-data value is explicitly transparent; valid shadow values start at 1. Raster tiles are projected to Web Mercator at zoom 12, with lower-zoom overviews.

Raster and vector builds record their inputs separately. Current corrected raster artifacts are generated from recorded, identical elevation checkpoints without repeating unchanged contour processing. Raster archives are canonically packaged into fresh SQLite databases with fixed schema and row ordering. This removes file-layout differences without changing pixels. SQLite runtime version is recorded.

The active development viewer selects three checksum-verified databases via active-map.json. Build records are preserved separately from later visual review. A portable fully pinned runtime and a final release package remain pending.

## Outdoor schema 0.2

Outdoor features are produced in the same OSM build as the base map, rather than patched into separate hand-maintained overlays. The new layers are mountain, hiking_poi, hiking_route and natural_line. Elevations retain their source strings and numeric metre values separately. OSM summit heights and DEM-derived contours have distinct provenance. Style expressions and sprite assets provide presentation; source classification does not embed icon or colour choices.

Processing fixtures cover elevation parsing, unnamed summits, saddles, area POIs, access attributes, disused features and route acceptance. An inventory reads actual highest-zoom MVT features and deduplicates IDs to report emitted classes and example geometry. This is build-output evidence, not an independent audit of OSM completeness. Atlas tests verify symbol completeness, bounds, resolution variants and asset integrity.
