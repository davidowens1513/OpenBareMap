# Maintaining regional editions

## Norway editions

The coverage plan is recorded in `config/norway-editions.json`. It defines three
independent downloads for mainland Norway and its coastal islands, excluding
Svalbard and Jan Mayen. The 13 November 2026 OSM snapshot, Copernicus GLO-30
elevation and Garmin DEM padding have been acquired for all three editions.
All three local map builds, iOS and Android integration kits, Garmin images and
browser previews are complete and validated. All three editions are published,
phone and Garmin public downloads have passed complete checksum verification,
and the production website has been checked live.

| Edition | Latitude range | Main coverage |
| --- | --- | --- |
| Southern Norway | 57.8–63.5°N | Oslo, Stavanger, Bergen, Jotunheimen and Trondheim |
| Central Norway | 63.0–67.5°N | Trondheim, Helgeland and Bodø |
| Northern Norway | 67.0–71.5°N | Bodø, Lofoten, Tromsø, Finnmark and Kirkenes |

Adjacent editions overlap by 0.5° latitude, approximately 56 km, around Trondheim
and Bodø. Both maps must retain full detail throughout each shared strip, with
the same source snapshot, contours and cartography. The configured rectangles
select from Norwegian source coverage. They do not imply full coverage of Sweden
or Finland. Verify the complete Norwegian coastal outline before building.

The three editions use a shared ETRS89 / UTM 33N grid and aligned 30 m terrain
pixels. Their native Garmin families are 4839 (south), 4840 (central) and 4841
(north). Source locks, outputs and mobile packages remain independent under
`regions/norway-south/`, `regions/norway-central/` and `regions/norway-north/`.
Each complete build uses `scripts/run_full_region.py --region <edition>`.

After acquiring the sources and padding for all three sections, run
`scripts/prepare_norway_shared_terrain.py` before building topography. It derives
each HGT cell once from the union of the verified COGs at a fixed, aligned angular
resolution, then installs identical shared cells in neighbouring source locks.
The GDAL VRT default average resolution differs with the selected latitude range
and must not be used to derive independent Norway overlap cells. Original DEM
files and pre-alignment locks are retained locally for comparison.

For an offline browser export, use `scripts/build_web_previews.py` with
`--cached-preview work/faroe-islands-web-2.0.0`. This reuses the existing preview's
PMTiles 4.5.0 library only after checking its version and release checksum, and
copies its licence alongside the new export. The Norway preview's shared origin
is `https://downloads.appsbyonzy.dev/OpenBareMap/norway/2.0.0/preview`.

`scripts/prepare_norway_publication.py` checks every completed edition and stages
its delivery files. Norway's source extracts, elevation pixels, generated Garmin
geometry, databases and split database payloads are excluded from Git and LFS.
Source references, configuration, checksums and small build records remain in Git
as provenance of the published release. The local bulk files are retained, and
future builds may use a fresh source snapshot rather than reconstructing the exact
historical release. Historical selections and checksum records do not mean that
the corresponding bulk payloads are present in a fresh checkout. Public integration
ZIPs and Garmin images remain available through their R2 download manifests.

From a Terminal with network access and the existing rclone configuration, run:

```sh
PYTHONPATH=work/python python3 scripts/publish_norway_release.py --publish --website
```

The website option requires Wrangler or Node.js/npx and Cloudflare Pages access.
It checks the existing `appsbyonzy` project's production branch before uploading.
The publisher uploads map assets, verifies complete public download checksums,
then publishes preview navigation and the website. Without `--publish`, it only
prints the prepared plan. Without `--website`, it publishes and verifies the maps
and navigation; `work/norway-website-20261114.zip` is also ready for a manual upload
to the existing Pages project after the map checks pass. Publication verification
is recorded in `web-preview/verification/norway-publication.json`. Git commit and
push remain separate from publication.

OpenBareMap uses one repository and shared cartography for Ireland, England/Wales, Scotland and Sierra Nevada. Each edition selects its own source snapshots, coordinate grid, map databases and platform packages. A regional release does not replace another edition's resources or require it to be released at the same time.

Ireland remains the default for existing build, viewer and packaging commands. Its selected map stays in the root `active-map.json`. The accepted Ireland inputs and outputs are recorded in `regions/ireland/preservation-baseline.json`; regional validation verifies their checksums.

## England/Wales scope

The edition uses the three complete Geofabrik England, Wales and Isle of Man extracts, merged by OSM object identity/version. It includes the Isle of Man, Isles of Scilly, Anglesey and other offshore islands. It is not a pilot or a sample. Terrain acquisition covers every one-degree cell in longitude −7 to +3 and latitude 49 to 56. Surrounding coastal land/terrain is context; the OSM coverage follows the source extracts.

It shares the Ireland edition's colours, symbols, transport passes, hillshade processing, 20 m contours, 100 m index contours and bounded geometry smoothing. In the England/Wales overview, rivers and canals remain visible while smaller waterways appear from zoom 10; all source features remain in the databases. Surrounding coastlines extend beyond the country coverage so the map has no rectangular land cutoffs. Welsh `name:cy` values replace the Ireland-specific Irish-language fallback in this edition's processing/style. Source `name` and English names are retained. The transport schema also retains OSM designation, horse/bicycle/foot access, trail visibility and hiking difficulty for inspection; these tags do not certify a legal right of way.

The generated British National Grid uses EPSG:27700, with 1 km/10 km lines and projected metre-coordinate labels. Its exact transformation, library version and stated accuracy are recorded in `grid-provenance.json` in the geometry build. It is a cartographic overlay. Empty multipolygon assemblies in the OSM source are recorded explicitly in the geometry report; missing locations or failed nonempty geometry remain build errors. The grid overlay is included in the browser and mobile packages; the Garmin export does not embed grid lines. Ireland retains its pinned Irish Grid and townland points; neither is included in England/Wales packages.

## Scotland scope

Scotland uses the complete Geofabrik extract dated 31 October 2026, with its own
source lock. Coverage includes the Hebrides, Orkney, Shetland, St Kilda and Rockall.
The profile bounds contain the entire upstream coverage outline. Terrain cells
span longitude −15 to +1 and latitude 54 to 62, with an additional Garmin DEM
padding ring. The large ocean extent is intentional to include Rockall.

Scottish Gaelic `name:gd` is retained alongside source and English names. The
British National Grid overlay extends through Shetland and uses negative projected
eastings in the far west; it is a cartographic overlay, not a survey guarantee.
Scotland uses the same 20 m contours, land-cover smoothing and overview waterway
rules as England/Wales. Ireland's townland data is not included.

All Scotland-specific paths follow the England/Wales layout with `scotland` in
place of `england-wales`: `regions/scotland/`, `data/regions/scotland/`,
`releases/scotland/2.0.0/` and temporary `build/scotland-*` stages. Its Garmin family
is **4834**, product 1, with tiles reserved from **48340001 to 48349999**. Family
4832 remains reserved for the private personal-track layer.

Run `PYTHONPATH=work/python python3 scripts/run_full_region.py --region scotland`
for a complete build. The standalone `regions/scotland/ios/` and
`regions/scotland/android/` exports are built without modifying BareGPS app projects.
Use `scripts/serve.py --region scotland --port 8767` for the local viewer.

## Paths and release independence

| Resource | Ireland | England/Wales |
| --- | --- | --- |
| Edition settings | `regions/ireland/region.json` | `regions/england-wales/region.json` |
| Active selection | `active-map.json` | `regions/england-wales/active-map.json` |
| OSM and terrain locks | Root lock files | `regions/england-wales/*-sources.lock.json` and `sources.lock.json` |
| Build outputs | Existing `build/` selections | `build/england-wales-*` |
| iOS resources | `ios/package/` | `regions/england-wales/ios/` |
| Android import package | `android/package/` | `regions/england-wales/android/` |
| Garmin | Family 4831 | Family 4833, tiles starting 48330001 |
| Release records | `releases/2.0.0/` | `releases/england-wales/2.0.1/` |

The Garmin family and tile identifiers differ, allowing both images to coexist. England/Wales Garmin intermediates use a local temporary build cache (override with `OPENBAREMAP_BUILD_ROOT`) so cloud storage cannot offload files during compilation. Accepted maps remain in the repository release folders. Both Garmin editions are display-only. The Android resource loader installs map packages by manifest hash and preserves older versions. Consuming applications choose which map to load; this map build does not modify BareGPS applications. The iOS resources use the same loader, with an edition-specific bundle identifier; a host app decides which bundle or installed resource directory to load.

## Complete build

The current source date is selected explicitly in the edition profile. Downloads are verified against upstream MD5 and then recorded with SHA-256. England, Wales and Isle of Man must have identical replication timestamps. A locked source is never silently refreshed.

Install the additional Python packages into the ignored local runtime:

```sh
python3 -m pip install --target work/python -r scripts/requirements-regions.txt
```

The existing Tilemaker, QGIS/GDAL and Garmin Java toolchain locks still apply. The regional requirements include the shared legend generator’s pinned Pillow version. The build uses the existing downloaded Garmin archives and Android Studio Java when available.

Run every stage for the complete edition:

```sh
PYTHONPATH=work/python python3 scripts/run_full_region.py --region england-wales
```

This acquires and locks full inputs, builds the basemap/terrain, smooths complete source geometry, generates the grid, selects display detail, packages iOS/Android resources, compiles Garmin and validates outputs. Existing completed stages are reused only where their recorded checks pass. Incomplete stages are errors; inspect their records before choosing a new destination or removing an unsuccessful generated directory. Accepted outputs are not silently overwritten.

Individual stages remain available:

```sh
PYTHONPATH=work/python python3 scripts/fetch_region.py --region england-wales
python3 scripts/build_topography.py england-wales-topography --region england-wales
PYTHONPATH=work/python python3 scripts/build_region.py --region england-wales
PYTHONPATH=work/python python3 scripts/build_region_garmin.py --region england-wales
python3 scripts/validate_region.py --region england-wales
```

Platform packaging can be repeated into fresh destinations with `--region england-wales --output /absolute/new/directory`. Default Ireland commands retain their existing meaning.

For future data updates, retain the prior release manifest and locked inputs. Select a new snapshot/release and fresh build/output names rather than replacing a released database in place. The first England/Wales orchestration uses fixed, edition-specific stage names; subsequent source releases must use new names before starting. Shared styling or software changes can be made once, then packaged and released for either edition independently.

## Local viewing

```sh
python3 scripts/serve.py --region england-wales --port 8766
python3 scripts/serve.py --port 8765
```

Accepted regional databases are copied into the versioned release directory; intermediate stages remain under `build/`.

The first command serves England/Wales; the second serves Ireland. Both use local assets and checksum-verified selected map databases. The viewer's destinations and initial extent follow the edition.

## Acceptance records

`releases/england-wales/2.0.0/validation.json` checks detailed coverage around geographically distributed anchors, all contour intervals, selected boundaries, SQLite integrity, package checksums and Ireland preservation. The Garmin inspector requires the distinct family configuration, contours, DEM, TYP, summit/bog features, city labels and absence of routing sections. Release manifests pin exact artifact hashes.

Automated checks do not establish geographic completeness of OpenStreetMap, legal access, or native-device appearance. Browser visual review and mobile/Garmin device testing have separate records. No hardware installation is performed by the build.

Scotland retains the small build records under `releases/scotland/2.0.0/build-records/`. Accepted-release validation can read its archived geometry report after redundant raw intermediates are removed. The selected map databases, source locks, native resources and Garmin image remain separate from those temporary stages.

The 2.0.1 England/Wales extension preserves every prior mainland vector feature and retains the accepted terrain, contours, hillshade and grid byte-for-byte. `scripts/verify_isle_of_man.py` verifies the island anchors and semantic preservation of features in changed tiles. Source and baseline records are under `releases/england-wales/2.0.1/build-records/isle-of-man/`. The full native image is recompiled from the three-extract union and extended coverage polygon, with shared 4-pixel hiking strokes at resolution 24.

A rectangular photographic patch can come from separately enabled BirdsEye imagery. The Sierra Nevada public image was checked against the affected installation; the map checksum and source elevation data were intact. Its conflicting satellite layer was disabled with an inactive backup retained. No clean Sierra map data was changed for that device-layer fault.

## Pyrenees scope

The Pyrenees edition covers longitude −2.2 to +3.4 and latitude 41.9 to 43.9,
including Bayonne with northern margin, both coastal ends, the French and Spanish
slopes and Andorra. Dated 31 October 2026 Geofabrik Aquitaine, Midi-Pyrénées,
Languedoc-Roussillon, Catalonia, Aragon, Navarra, Basque Country and Andorra inputs
are checksum-verified and must share a replication timestamp. Complete edge ways,
relations and their backward references are extracted before duplicate objects
are merged by version. The original extracts and extraction checkpoints are retained.

Terrain uses the same Terrain Tiles composite DEM, 30 m projected processing,
20 m contours, 100 m index contours, bounded smoothing, multidirectional hillshade
and warm transparent shading as the accepted editions. The map shares the existing
transport colours, line weights, symbols and visibility rules. ETRS89 / UTM 31N
provides one continuous metre grid across the range; it is a cartographic overlay.
Source place names are retained with French fallback; no translation is inferred.

Run `PYTHONPATH=work/python python3 scripts/run_full_region.py --region pyrenees`.
The profile, source locks, active selection and exports use `regions/pyrenees/`;
selected databases use `releases/pyrenees/2.0.0/maps/`. Garmin family **4836**, tiles
**48360001–48369999**, is reserved for this edition. Native background and land
cover use the requested crop rather than entire source administrative regions.
Use `scripts/serve.py --region pyrenees --port 8769` for local viewing.

The reviewed Pyrenees map uses storage revision `2.0.0-pyrenees-r4`, with a wider
coastal land background so the initial viewport has no false straight coastline.
The context revision preserves every contour layer payload. Earlier generated
mobile resources are retained under the ignored local `work/pyrenees-resources-r3/`.
For merged cropped inputs, the Garmin splitter derives bounds from actual nodes
(`--ignore-osm-bounds=true`) before applying the requested coverage polygon. A
split-plan check requires every destination anchor before native compilation;
this prevents a primary input's inherited PBF header bounds truncating the union.


## Dolomites scope

The Dolomites edition uses the approved rectangle 10.65–13.10°E, 45.70–47.00°N.
The dated 4 November 2026 Nord-Est, Nord-Ovest and Austria Geofabrik extracts
are verified against upstream checksums and a shared replication timestamp.
Complete features and their references are retained at the crop before merging.
Nord-Ovest supplies the small southwest corner of the rectangle.

It uses the shared 20 m contours, 100 m index contours, multidirectional warm
hillshade, transport colours, line weights and visibility rules. The metre grid
is ETRS89 / UTM 32N. Original place names use Italian fallback.

Run `PYTHONPATH=work/python python3 scripts/run_full_region.py --region dolomites`.
Regional resources and locks use `regions/dolomites/`, selected databases use
`releases/dolomites/2.0.0/maps/`, and native family 4837 reserves tile IDs
48370001–48379999. Native backgrounds use the approved rectangular crop.
All public previews share the shared edition catalog in `config/preview-regions.json`;
Region changes edition and Explore selects a destination within that edition.


## Faroe Islands scope

The Faroe Islands edition covers the whole archipelago, including all 18 main
islands and outlying coast features, within 7.85–6.10°W and 61.30–62.50°N.
The complete 4 November 2026 Geofabrik Faroe Islands extract is retained and
verified against its upstream checksum. Faroese names and character glyphs are
retained. ETRS89 / UTM 29N supplies the metre grid. Native family 4838 reserves
map tile IDs 48380001–48389999.

The elevation source is Copernicus DEM GLO-30 Public from the pinned AWS 2021
release, using orthometric EGM2008 heights. Original COGs and conversion records
are retained. HGT conversion provides point-aligned signed integer degree cells;
missing ocean cells are zero, based on the pinned official public tile inventory.
The shared 30 m projected processing, 20 m contours, bounded smoothing and warm
multidirectional hillshade are preserved. The usual composite source was rejected
for this edition after its summit sample was about 90 m below the source summit
height. The selected DEM samples approximately 874 m at the 880 m summit.

All 18 main islands have independent detailed land checks; major island interiors
are also checked at overview zooms. There are no station or bog-tagged features
in the locked source; their absence is recorded rather than inventing features.
The regional terrain notice and full Copernicus licence are included in exports.
Use `scripts/run_full_region.py --region faroe-islands` for the complete build.

Faroe native land checks cover all 18 islands at every native detail level. At resolutions 18 and 16, a half-grid-cell tolerance accounts for coarse coordinate quantization; finer levels require the actual interior point to be inside the compiled land polygon.

## Mediterranean island editions

The Balearic Islands, Corsica, Sardinia and Sicily are four independently
buildable maps. Sardinia and Sicily each crop the shared Geofabrik Isole
extract. The Balearic Islands and Corsica use their respective Geofabrik
extracts. All four use the 17 November 2026 OSM snapshots, Copernicus GLO-30
and 20 m contours. Sicily uses the source outline for its transparent Garmin
background along the Strait of Messina.

Build each edition with scripts/run_full_region.py --region REGION. Validate
the selected datasets and native packages before assembling the integration
kits and exporting PMTiles with the shared browser preview. All editions use
the same region selector and map-key layout.

As with Norway, source extracts, elevation tiles and working databases are
rebuildable local data. Git carries configurations, source locks, validation
records and public download manifests. Cloudflare R2 serves the finished
integration kits, Garmin images and browser previews. The R2 delivery inventory
records the exact sizes and checksums of the downloadable kits and images.
