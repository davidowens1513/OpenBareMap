# OpenBareMap 2.0 for iOS

The current all-Ireland bundle is stored in this repository at `ios/package/OpenBareMap.bundle`. Add the complete `.bundle` as an Xcode resource and add `OpenBareMapResources.swift` to the app target. See `INTEGRATION.txt` for the MapLibre Native loading example and attribution requirements.

The bundle includes the selected MBTiles, a dedicated zoom-capped coast archive, runtime style, townland points, Open Sans glyphs, sprites, app legend, provenance, checksums and `Info.plist`. It does not include the original large source snapshots or a renderer binary. Those source snapshots remain in the main repository via LFS. The bundle is a full-island offline dataset; choose distribution/storage policy in the consuming app.

Build into a new directory (existing outputs are never overwritten):

```sh
python3 ios/build_bundle.py --output /absolute/path/to/new-package-folder
```

The Swift loader resolves runtime absolute paths without a tile web server. It writes a small temporary resolved style, leaving the map databases in the resource bundle. MapLibre Native must support `mbtiles:///absolute/path` source URLs. This is not a MapLibre offline-pack database.

Loader smoke test on macOS:

```sh
swiftc ios/OpenBareMapResources.swift ios/tests/main.swift -o /tmp/OpenBareMapLoaderCheck
/tmp/OpenBareMapLoaderCheck /absolute/path/to/OpenBareMap.bundle
```

The loader was also typechecked against the iOS Simulator SDK for arm64/iOS 15. `bundle-validation.json` records the resource/SQLite/loader checks. Actual MapLibre rendering, memory use and performance on a simulator/device remain unverified. No device acceptance is claimed.

All iOS-specific code, integration notes, tests and packaged resources live under `ios/`. `package/` contains the ready-to-copy bundle, loader and instructions. Run `git lfs pull` after cloning to restore its MBTiles and townland GeoJSON. The default assembler destination is `ios/package`; pass a fresh `--output` directory when it already exists.

## Map storage revision

The current resource package uses `2.0.0-storage-r3`, approximately 1.01 GB. It preserves all-Ireland coverage, 20 m contours and national/county borders. Local border lines are omitted; townland and settlement names remain. Contour segments intersecting the tile plus a 128-pixel buffer retain their original coordinates and attributes; distant segments are omitted. Other feature geometry is unchanged. Overview tiles omit features the pinned style does not display. The capped coast archive contains only the unchanged land layer, with empty tile positions retained. Resource checksums and package validation identify the exact files. Existing app installations require a resource update. The BareGPS Android app includes these resources; the Samsung SM-A075F installation is verified. iOS device appearance comparison remains pending.

Cliffs use a shared periodic teeth pattern with 16 × 6 logical-pixel cells, supplied at both atlas resolutions. Cliff line weight and visibility start at zoom 11. Device appearance comparison remains pending.

The shared app legend uses bold dark labels, enlarged line samples and outlined colour swatches with enhanced contrast and saturation. These presentation adjustments aid reading; the map style is unchanged.
