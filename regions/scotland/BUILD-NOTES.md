# OpenBareMap Scotland 2.0.0

The complete Geofabrik Scotland extract dated 31 October 2026 is built with
20 m contours, hillshade, British National Grid and Scottish Gaelic name support.
Coverage includes the Hebrides, Orkney, Shetland, St Kilda and Rockall.

Current selected databases and release evidence: `releases/scotland/2.0.0/`.
The selected storage revision is `2.0.0-scotland-r3`. Source archives and elevation
cells are pinned under `data/regions/scotland/`, with locks in this directory.

Standalone iOS resources: `ios/OpenBareMap.bundle` and loader in this directory.
Standalone Android resources: `android/OpenBareMap`. Distribution archives are
in `exports/`. Neither BareGPS app project has been modified.

Garmin distribution: `garmin/dist/OpenBareMap-Scotland.img`, revision
`2.0.0-garmin-r1`, family 4834, product 1, 85 sections starting at 48340001.
It is display-only and contains native DEM. Identity checks include Ireland,
England/Wales and the private track layer. Device rendering remains unreviewed.

Public R2 locations:
- `Garmin/OpenBareMap-Scotland.img`, `Garmin/scotland-instructions.txt` and
  attribution under `Garmin/scotland/`.
- `OpenBareMap/scotland/2.0.0/ios/` and `android/` for standalone resource ZIPs,
  with manifest and checksums at the version root.
- `OpenBareMap/preview-v2/scotland/`, `data/scotland/` and the shared preview assets.

appsbyonzy.dev now has the Scotland section parallel to England/Wales. The README
and public preview link the matching, separate zoomable legend.

Redundant generated terrain, geometry and Garmin compile files have been removed
after checksum verification. Small build records are retained in the release’s
`build-records/`; active databases, pinned sources, bundles and exports remain.
The source-clipped cross-border relation warnings in the splitter log did not
produce compiler failures; full-source outline and island coverage checks pass.
See release `validation.json`, `publication.json`, `cleanup.json` and
`browser-verification.json` for the actual verified scope and checksums.
