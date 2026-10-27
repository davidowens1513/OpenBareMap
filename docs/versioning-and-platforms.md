# Map versioning and platform adaptations

Status assessed **27 October 2026**. This note describes the current version controls and how each application uses the map. The release recommendations below are proposals, not an implemented release policy.

## What is locked

OpenBareMap has a pinned map snapshot, but no single formally locked release covering all platforms. Source and output checksums identify exact files; they do not by themselves guarantee that every build can be reproduced byte for byte or that every platform renders identically.

| Component | Current control |
| --- | --- |
| OpenStreetMap data | Exact extract and checksum in [sources.lock.json](../sources.lock.json); snapshot dated 24 October 2026. |
| Coastline and elevation inputs | Exact inputs in [coast-sources.lock.json](../coast-sources.lock.json) and [terrain-sources.lock.json](../terrain-sources.lock.json). |
| Selected shared map databases | Four database paths and checksums in [active-map.json](../active-map.json). |
| Shared MapLibre appearance | Git-versioned [style/openbaremap.json](../style/openbaremap.json), with fonts, sprites and asset records. |
| iOS package | Version 0.4.0, source commit, source-style hash, resource checksums and inventory under [ios/package/OpenBareMap.bundle](../ios/package/OpenBareMap.bundle/). |
| Android package | Version 0.4.0, source commit, source-style hash and resource checksums under [android/package/OpenBareMap](../android/package/OpenBareMap/). |
| Garmin basemap | Checksum-pinned IMG, source/tool locks, style hashes and binary inspection in [garmin/build-report.json](../garmin/build-report.json). |
| Cross-platform release | No release tag or single release manifest tying all platform deliverables to one map release. |
| Personal-track overlay | Separate local package and build files; not committed or pushed at the date of this assessment. |

The iOS and Android packages were checked against each other: all five packaged map-database hashes match, including the derived coast archive. Their styling layers are identical and match the current shared style. Their source commits differ because the packages were assembled at different repository commits; their recorded source-style hashes match.

Garmin's distributed IMG is an identifiable, checksum-pinned artifact. Repeated compilation with the recorded inputs and style produces differences beyond creation timestamps, including a 76-byte difference in RGN payload sizes. Strict binary reproducibility is therefore unresolved. This is separate from being able to retain and verify the exact distributed file.

## How the map varies by application

| Application | Shared content | Platform adaptation |
| --- | --- | --- |
| Browser | Selected databases, MapLibre style, fonts, symbols and townland points. | A local server supplies resources to MapLibre GL JS. |
| iOS | The same selected databases and shared MapLibre cartography. | A resource bundle and Swift loader resolve local URLs for MapLibre Native. |
| Android | The same selected databases and shared MapLibre cartography. | A ZIP resource package and Kotlin loader install, verify and resolve local URLs for MapLibre Native. |
| Garmin | Locked OSM and terrain sources, shared contour geometry and townland points. | Separate compilation into native Garmin geometry, elevation data, fonts, symbols, textures and detail levels. |

### Browser, iOS and Android

The MapLibre applications use the same intended cartography. The native package builders copy the selected databases and shared visual resources, create a zoom-capped coast archive, and adapt resource URLs and attribution fields. The application loaders resolve those URLs to local files.

Packaging and integration differ; label collision, text rendering, performance and other renderer/device behaviour can still differ. Sharing a style is not proof of identical pixels or device acceptance.

Packages are snapshots. Editing the shared style or changing the selected databases does not update an existing iOS bundle or Android installation automatically. Each affected package must be assembled, validated and distributed again.

### Garmin

Garmin has a separately maintained presentation under [garmin/style](../garmin/style/), [garmin/generate_typ.py](../garmin/generate_typ.py) and [garmin/config.json](../garmin/config.json). These define native colours, patterns, symbols, fonts, contour treatment and detail levels. They are not automatically derived from the MapLibre style.

A colour, text or visibility change to the MapLibre style therefore does not change the Garmin edition. A corresponding Garmin change requires an explicit style update and compilation. Garmin omits the Irish Grid and distinct bridge/tunnel presentation; native DEM terrain rendering replaces the MapLibre raster hillshade presentation.

The Montana 750i and GPSMAP 67i use the same basemap IMG and the same optional personal-track IMG. Device settings for map detail, point text, imagery layers and day/night appearance add another level of variation without modifying either file.

### Personal tracks

Personal recorded tracks are a separate transparent Garmin layer. They can be updated or disabled independently of the basemap. The local package contains 355 Irish tracks as purple lines with green start markers and no track or start-point names. It does not alter the OpenBareMap basemap or import those tracks into the device's saved-track library.

The personal-track package is not part of the published basemap release or this documentation commit.

## Recommended release structure

The following would establish a formal, identifiable map release while retaining controlled platform differences:

1. **One map release identifier and Git tag.** Identify the shared map snapshot independently of host-app versions.
2. **One release manifest.** Record the shared data/style hashes, platform profile hashes, builder/tool versions, deliverable checksums and validation scope. A release tag should identify the committed snapshot referenced by that manifest.
3. **Explicit platform profiles.** Document which presentation rules are shared, adapted or omitted, particularly for Garmin.
4. **Independent overlay versions.** Version personal-track layers separately and record the basemap release used for their checks.
5. **Preserved release artifacts.** Publish changes as a new release rather than replacing the files associated with an existing release identifier.

A device installation record should identify the map release, platform profile, exact installed-file checksum and any optional overlay version. This would answer “which OpenBareMap version is on this device?” without implying that the host app, map data and personal tracks all share one version number.

[Back to the README](../README.md)
