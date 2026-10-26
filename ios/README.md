# iOS resource bundle

The current all-Ireland bundle is assembled outside this repository at `../OpenBareMap-iOS/OpenBareMap.bundle`. Add the complete `.bundle` as an Xcode resource and add `OpenBareMapResources.swift` to the app target. See `INTEGRATION.txt` for the MapLibre Native loading example and attribution requirements.

The bundle includes the selected MBTiles, a dedicated zoom-capped coast archive, runtime style, townland points, Open Sans glyphs, sprites, app legend, provenance, checksums and `Info.plist`. It does not include the original large source snapshots or a renderer binary. Those source snapshots remain in the main repository via LFS. The bundle is roughly 2 GB; choose distribution/storage policy in the consuming app.

Build into a new directory (existing outputs are never overwritten):

```sh
python3 scripts/build_ios_bundle.py --output /absolute/path/to/new-package-folder
```

The Swift loader resolves runtime absolute paths without a tile web server. It writes a small temporary resolved style, leaving the map databases in the resource bundle. MapLibre Native must support `mbtiles:///absolute/path` source URLs. This is not a MapLibre offline-pack database.

Loader smoke test on macOS:

```sh
swiftc ios/OpenBareMapResources.swift ios/tests/main.swift -o /tmp/OpenBareMapLoaderCheck
/tmp/OpenBareMapLoaderCheck /absolute/path/to/OpenBareMap.bundle
```

The loader was also typechecked against the iOS Simulator SDK for arm64/iOS 15. `bundle-validation.json` records the resource/SQLite/loader checks. Actual MapLibre rendering, memory use and performance on a simulator/device remain unverified. No device acceptance is claimed.
