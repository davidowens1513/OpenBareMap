# OpenBareMap for Garmin Montana 750i

Display-only, full-island Ireland and Northern Ireland map. The deliverable is `dist/OpenBareMap-Ireland.img` (249.5 MB). Copy instructions are in `dist/INSTALL.txt`. No map has been installed on a device by this build.

Includes roads, tracks, footways, bridleways, cycleways, steps, walking/cycling overlays, water, land cover, buildings, boundaries, townlands, place names, summit dots, parking P symbols, bog texture and cliff teeth. Contours retain the shared 10 m geometry. Native DEM elevation data supports Garmin's terrain rendering. No routing network or turn instructions are generated.

## Native cartography

Garmin renders its own fonts, labels and detail levels. This is a native adaptation, not pixel-identical to the MapLibre map. SmallFont is used for most names, NormalFont for cities; device settings affect actual size. Text has no custom halo. Day and night palettes currently match. Bog/rock patterns are native two-colour bitmaps. The supplied legend is generated from the same palette and patterns.

| Detail level | Garmin resolution | Contours |
| --- | --- | --- |
| 0, closest | 24 | 10 m, 50 m and 100 m |
| 1 | 22 | 50 m and 100 m |
| 2 | 20 | 100 m |
| 3 | 18 | None |
| 4, overview | 16 | None |

These are Garmin resolution bits, not web zoom numbers. Native contour elevation attributes use feet, as required by Garmin; set device elevation units to metres. The underlying spacing remains 10 m. Irish Grid lines are not exported in this version. Bridges and tunnels do not yet receive a distinct Garmin rendering. MapLibre raster hillshade, pixel text sizes and label spacing do not transfer directly.

## Source and tool records

- Shared `sources.lock.json`, `terrain-sources.lock.json` and townland data remain authoritative.
- `inputs.lock.json`: exact compressed shared contour geometry and full-island coast mask.
- `dem-padding.lock.json`: five adjacent eastern elevation cells needed by DEM interpolation.
- `toolchain.lock.json`: pinned mkgmap r4924, splitter r654 and macOS ARM Python 3.12 osmium wheel. Archives retain their upstream licence notices.
- `config.json`, `style/`, `generate_typ.py`: native map profile and custom symbols.
- `build-report.json`: output checksums, source counts, binary read-back and repeat-build comparison.
- `work/`: ignored intermediate files; `dist/`: installable map and notices.

## Rebuild

Run from the repository root after `git lfs pull`. Use Java 17 or newer and Python 3.12 with osmium 4.2.0. The builder uses JAVA_HOME, Android Studio's bundled Java on macOS, or Java on PATH. Set JAVA_HOME explicitly for other environments. Allow roughly 15 GB working space and at least 8 GB RAM.

On macOS ARM with Python 3.12:

```sh
python3.12 -m pip install --no-deps --target garmin/work/python garmin/tools/osmium-4.2.0-cp312-cp312-macosx_11_0_arm64.whl
python3.12 garmin/build.py --name compile-release
```

On other platforms install the pinned osmium version for that Python/platform. Pillow is needed only to regenerate the legend (`make_legend.py`). The builder verifies pinned tool archives and extracts them locally. It prepares the full contour/coast/townland overlay, merges it with the locked OSM snapshot, splits complete features and compiles the map. Existing split/build directories cause an error: preserve or move an old work directory before a fresh build, then reinstall the local Python dependency. The build never silently overwrites a previous compiled map.

Read back the compiled files before publishing:

```sh
javac -cp garmin/tools/mkgmap-r4924/mkgmap.jar -d garmin/work garmin/InspectMap.java
java -Xmx2g -cp garmin/work:garmin/tools/mkgmap-r4924/mkgmap.jar InspectMap garmin/work/compile-release > garmin/work/inspection.json
```

Use the platform classpath separator on Windows. The inspector requires embedded DEM/TYP, all three contour types, summit/bog features, known place names, and no NET/NOD routing sections. After successful inspection, copy that build's `gmapsupp.img` into `dist/OpenBareMap-Ireland.img` and refresh checksums/report.

## Validation and limitations

Two complete compiles succeeded with no compiler exceptions or missing elevation files. Binary read-back verified 70 tiles, DEM, custom TYP, progressive contours and names including Carrauntoohil, Belfast and Dublin. All 20 repository Python tests passed.

The two compiles are not byte-for-byte identical, even after excluding creation timestamps: RGN payload sizes differ by 76 bytes and some encoded line instances differ. Source inputs, tools and style are pinned, but strict binary reproducibility remains unresolved. Both inspections passed. The full comparison is recorded rather than hidden.

No Montana hardware rendering or performance test has been performed. Font readability, contour label units, texture density, terrain shading and map selection should be checked on the actual 750i before treating this as a finished device release.
