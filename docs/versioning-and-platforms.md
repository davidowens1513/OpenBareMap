# Map versioning and platform adaptations

OpenBareMap's map release is **2.0.0**, identified by Git tag **v2.0.0** and the [release manifest](../releases/2.0.0/manifest.json). The manifest pins the shared map selection, source/style records, platform profiles, package checksums and validation scope. Release identity and byte-for-byte recompilation are different guarantees.

## What is locked

| Component | Release control |
| --- | --- |
| OpenStreetMap data | Exact extract and checksum in [sources.lock.json](../sources.lock.json); snapshot dated 24 October 2026. |
| Coastline and elevation inputs | Exact inputs in [coast-sources.lock.json](../coast-sources.lock.json) and [terrain-sources.lock.json](../terrain-sources.lock.json). |
| Smoothed geometry | Contour and land-cover snapshots and the [geometry report](../releases/2.0.0/geometry-report.json), with bounded smoothing and polygon validity/area guards. |
| Selected shared map databases | Paths and checksums in [active-map.json](../active-map.json), also captured in the release manifest. |
| Shared MapLibre appearance | [style/openbaremap.json](../style/openbaremap.json), with source hash and legend records. |
| iOS package | Map version 2.0.0, code revision, source-style hash, resource checksums and inventory under [ios/package/OpenBareMap.bundle](../ios/package/OpenBareMap.bundle/). |
| Android package | Map version 2.0.0, code revision, source-style hash and resource checksums under [android/package/OpenBareMap](../android/package/OpenBareMap/). |
| Garmin basemap | Exact IMG checksum, source/tool locks, profile hashes and [binary inspection report](../garmin/build-report.json). |
| Personal-track overlay | Independently maintained local map, outside the published basemap release. |

The release manifest refers to an implementation commit and hashes the files and package records that define the release. The original `v2.0.0` tag points to its complete release snapshot, including its manifest and platform deliverables. The current manifest also records Garmin package revision `2.0.0-20m`, a subsequent platform-only adaptation; checking out the original tag restores the original Garmin artifact. A code revision recorded inside a package need not equal the final release commit, which also contains generated outputs and documentation.

The selected shared detail revision is `2.0.0-20m`, with storage revision `2.0.0-storage-r3` and map version 2.0.0. Browser, iOS and Android use 20 m contours with 100 m index lines, national borders and county borders. Local border lines are omitted; townland and settlement names remain. Contour segments intersecting the tile plus a 128-pixel buffer retain their original coordinates and attributes; distant segments are omitted. Other feature geometry is unchanged. The [detail report](../releases/2.0.0/detail-report.json) pins the selected inputs and outputs; [map-detail configuration](../config/map-detail-2.0.json) and the detail builder reproduce the selection from preserved 10 m source databases. The land-only coast archive retains its empty tile positions. Earlier storage measurements are retained in the [storage report](../releases/2.0.0/storage-report.json).

Garmin package revision `2.0.0-20m` uses 20 m contours with 100 m index lines, national/county borders and no local borders. Existing mobile app installations need updated resources to use the selected shared map.

The iOS and Android packages use matching map-database hashes and styling layers, verified during release validation. Retain their manifests and resource checksums alongside any distributed packages.

An exact release artifact can be restored and verified by checksum without recompiling it. Strict binary recompilation is not guaranteed. Garmin has documented repeated-build differences beyond creation timestamps; the release pins its distributed bytes rather than claiming identical regenerated output. Portable toolchain and inherited resource-generation limitations remain documented in the platform guides.

## How the map varies by application

| Application | Shared content | Platform adaptation |
| --- | --- | --- |
| Browser | Selected databases, MapLibre style, fonts, symbols and townland points. | A local server supplies resources to MapLibre GL JS. |
| iOS | The same selected databases and shared MapLibre cartography. | A resource bundle and Swift loader resolve local URLs for MapLibre Native. |
| Android | The same selected databases and shared MapLibre cartography. | A ZIP resource package and Kotlin loader install, verify and resolve local URLs for MapLibre Native. |
| Garmin | Locked OSM and terrain sources, shared smoothed contour/land-cover geometry and townland points. | Separate compilation into native Garmin geometry, elevation data, fonts, symbols, textures and detail levels. |

### Browser, iOS and Android

The MapLibre applications share intended cartography. Native package builders copy the selected databases and visual resources, create a zoom-capped coast archive, and adapt resource URLs and attribution fields. Application loaders resolve those URLs to local files. Label collision, text rendering, performance and other renderer/device behaviour can differ.

Packages are snapshots. A shared-style or database change requires reassembly, validation and distribution of each affected package. Existing installations do not change automatically when the repository changes.

### Garmin

Garmin's presentation is maintained under [garmin/style](../garmin/style/), [garmin/generate_typ.py](../garmin/generate_typ.py) and [garmin/config.json](../garmin/config.json). These specify native colours, patterns, symbols, fonts, progressive contour types and detail levels. They are not automatically derived from the MapLibre style.

A shared MapLibre style change requires an explicit corresponding Garmin decision. Version 2.0 uses fine, pale overview strokes for 100 m contours and a fine cliff pattern. Native close-detail contours support the device's elevation-unit setting; overview contour labels are suppressed. Garmin omits the Irish Grid and distinct bridge/tunnel presentation. Native DEM rendering supplies terrain shading.

The Garmin distribution targets the Montana 750i, GPSMAP 67i and GPSMAP H1; per-device installed revisions and full read-back checks are recorded separately. Their settings for map detail, point text, imagery layers and day/night appearance add variation without modifying that file. The Garmin-only `2.0.0-20m` profile uses standard region-text points for townlands, NormalFont and muted grey-brown. Uppercase source names do not guarantee uppercase device rendering. The Montana rendering has been accepted; the 67i and H1 require visual review. See [device installation records](../garmin/device-installations.json).

### Personal tracks

Recorded tracks form a separate transparent Garmin layer. They can be updated or disabled independently of the basemap and are versioned outside this release. The local personal package has 355 Irish tracks as purple lines and green start markers, without names. It does not import tracks into the device's saved-track library. Personal source files and binaries are not included in the published release.

## Release maintenance

- Preserve each release identifier and its artifacts. Publish a map change under a new identifier.
- Record shared data/style hashes, platform profile hashes, tool versions, artifact checksums and validation scope in the release manifest.
- Keep map-release versions independent of consuming application versions and personal-track overlay versions.
- Record a device installation's map release, exact installed-file checksum, platform profile and any optional overlay version.

[Development history and build workflow](development-history.md) records development and build details. [Back to the README](../README.md).

Contour storage is pinned by [configuration](../config/contour-padding-2.0.json) and the [full-island report](../releases/2.0.0/contour-padding-report.json). `scripts/trim_contour_padding.py` reproduces the selected topography database from the preserved 20 m source. Segments crossing the padded tile are retained whole, including their original endpoints; no curve simplification or intersection coordinates are introduced. Tile positions, empty tiles and other layer bytes are preserved. At a 512-pixel tile size the buffer is 128 pixels (1024 of 4096 tile coordinate units). Native device rendering acceptance remains pending.

The Garmin 20 m profile retains national and county boundaries, townland labels, summit names, native DEM relief, bog texture and cliff markings. Local boundary lines and the former 50 m contour class are omitted. The personal-track overlay remains independent.
