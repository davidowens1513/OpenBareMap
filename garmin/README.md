# OpenBareMap for Garmin

OpenBareMap supplies display-only Garmin maps for Ireland, England & Wales, Scotland and Sierra Nevada National Park in Spain with 25 km around its boundary. The Garmin package is **2.0.0-hiking-r1**, within map version 2.0.0. [Release manifest](releases/2.0.0-hiking-r1/manifest.json) records the exact downloads, identifiers and checksums. Generic installation instructions are supplied with every region.

## Native cartography

Green paths, brown tracks (including farm and forest access tracks) and red walking routes use equal **4-pixel dashed strokes**, transparent gaps and no white backing. Walking-route sections on roads use one red stroke. Ordinary roads remain visible before route markings appear. Tracks and paths describe mapped features; they do not establish public access rights.

All these hiking lines share the same resolution-24 threshold, two stored detail steps beyond resolution 22. Buildings are also limited to resolution 24. Garmin firmware, map themes, detail settings and screen characteristics determine the actual display scale; stored resolutions are not fixed metre-scale cutoffs.

| Native level | Resolution | Contours | Hiking lines | Buildings |
| --- | --- | --- | --- | --- |
| 0 | 24 | 20 m and 100 m | Yes | Yes |
| 1 | 23 | 20 m and 100 m | No | No |
| 2 | 22 | 100 m | No | No |
| 3 | 20 | 100 m overview | No | No |
| 4 | 18 | None | No | No |
| 5 | 16 | None | No | No |

Native DEM supports Garmin relief shading. Colours match in day and night mode. Fonts, labels, symbols and terrain rendering differ from the mobile/web maps. Contours retain their 20 m spacing; Garmin close-detail elevation attributes use feet, so select metric elevation units when needed. Irish Grid lines and MapLibre raster hillshade are not exported. No turn-by-turn routing is included.

The editions have separate map family, tile and appearance-file identities. England & Wales retains coast/land polygons at overview levels. Sierra Nevada includes the purple national park boundary and dashed 25 km coverage limit; its conservative Garmin tile envelope can show context beyond that limit.

## Sources and rebuilding

The locked OSM extracts, contour/land-cover inputs and elevation grids are authoritative. `config.json`, `style/`, `cartography.json` and `generate_typ.py` define the Ireland profile; other regional styles and configurations are in `regions/<region>/garmin/`. `map-identities.json` reserves disjoint identifiers. mkgmap r4924 and splitter r654 archives are pinned in `toolchain.lock.json`.

Restore sources with Git LFS before building. Use Java 21 and Python with the locked project's osmium dependency. The regional release builder verifies source and elevation checksums, creates complete source sections where needed, compiles the selected style, and inspects the native geometry, elevation, labels and hiking thresholds. Completed build checkpoints are verified before reuse.

```sh
export JAVA_HOME=/path/to/java-21
PYTHONPATH=work/python python3 scripts/build_garmin_hiking_release.py --region ireland
PYTHONPATH=work/python python3 scripts/build_garmin_hiking_release.py --region england-wales
PYTHONPATH=work/python python3 scripts/build_garmin_hiking_release.py --region scotland
PYTHONPATH=work/python python3 scripts/build_garmin_hiking_release.py --region sierra-nevada
```

Build intermediates are ignored. Inspection records, native-level checks and the map-set identity/land checks accompany the accepted release. Exact bytes are pinned by checksums; byte-identical recompilation is not claimed. [Installation records](device-installations.json) describe actual device copies separately from the release and from hardware visual review.
