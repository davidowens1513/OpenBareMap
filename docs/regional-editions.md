# Maintaining regional editions

## Sorrento, Amalfi & Bay of Naples

This Italian edition covers the Sorrento Peninsula and Amalfi Coast through Salerno,
the Monti Lattari ridge, Capri, Ischia, Procida and Vivara. It also includes the
Naples and Pozzuoli ferry gateways, Pompeii and Vesuvius. The geographic bounds
are 13.82°–14.86° E and 40.49°–40.90° N.

The build uses the 22 November 2026 Geofabrik southern Italy extract and Copernicus
GLO-30 elevation. The edition has 20 m contours, hillshade, a WGS 84 / UTM 33N
grid, and mapped ferry lines. Its Garmin family ID is 4876.

```sh
export PYTHONPATH=work/python
edition=amalfi-bay-of-naples
output="work/$edition-release"
python3 scripts/run_full_region.py --region "$edition"
python3 scripts/build_app_distribution.py --regions "$edition" \
  --output "$output/kits" --catalog "$output/catalog.json"
python3 scripts/build_web_previews.py --regions "$edition" --output "$output/preview" \
  --origin "https://downloads.appsbyonzy.dev/OpenBareMap/$edition/2.0.0/preview"
python3 scripts/stage_amalfi.py --website /path/to/AppsByOnzy-Website/site/index.html
```

## European walking editions

| Edition | Walking coverage | Geofabrik snapshot | Garmin family |
| --- | --- | --- | --- |
| Camino Francés | Saint-Jean-Pied-de-Port to Santiago de Compostela, with a 10 km buffer on each side of the main route | 22 November 2026 | 4874 |
| Cinque Terre & Portofino | Camogli, Portofino, Sestri Levante, Levanto, the five Cinque Terre villages, La Spezia and Portovenere | 4 November 2026 | 4875 |

The Camino footprint uses the FEAACS stages published by Spain's IGN from
Puente la Reina to Santiago and the OpenStreetMap-derived Open Pilgrimages
alignment from Saint-Jean-Pied-de-Port to Puente la Reina. The source lock
records the source URLs, attribution, hashes and processing. The verified
main alignment is approximately 765 km. Its ETRS89 / UTM 30N buffer is
10,000 metres and covers about 14,100 km². The build clips the elevation,
grid and basemap selection to the corridor and includes an offline map mask
and a line identifying the main Camino. Garmin's rectangular tiles may
include padding at the boundary.

The two editions use Copernicus GLO-30 for 20 m contours and hillshade.
The Ligurian edition reuses the pinned full Nord-Ovest extract and retains
the coastal and inland path network.

```sh
export PYTHONPATH=work/python
python3 scripts/prepare_camino_frances.py
for edition in camino-frances cinque-terre; do
  output="work/$edition-release"
  python3 scripts/run_full_region.py --region "$edition" || exit
  python3 scripts/build_app_distribution.py --regions "$edition" \
    --output "$output/kits" --catalog "$output/catalog.json" || exit
  python3 scripts/build_web_previews.py --regions "$edition" --output "$output/preview" \
    --origin "https://downloads.appsbyonzy.dev/OpenBareMap/$edition/2.0.0/preview" || exit
done
python3 scripts/stage_european_walks.py --website /path/to/AppsByOnzy-Website/site/index.html
```

Publish the R2 assets and verify byte-range access before deploying the Pages
archive or promoting the app and preview catalogues.

## Nepal trekking

The Nepal maps use a shared 22 November 2026 Geofabrik OpenStreetMap extract,
clipped with complete feature references. Its MD5 matched Geofabrik's
published checksum. Copernicus GLO-30 supplies terrain for 20 m contours,
hillshade and Garmin elevation. The ice layers use the source's glacier and
permanent snow classifications.

| Edition | Main walking coverage | Grid | Garmin family |
| --- | --- | --- | --- |
| Everest & Khumbu | Lukla, Namche Bazaar, Everest Base Camp, Gokyo and the Three Passes circuit | WGS 84 / UTM 45N | 4872 |
| Annapurna | Annapurna Circuit, Annapurna Base Camp, the Pokhara approaches and the Kali Gandaki valley | WGS 84 / UTM 44N | 4873 |

The build uses mapped Latin names when available and ICU transliteration for
Devanagari names otherwise. The source lock records the original clipped
extract and the Latin-label derivative. Keep the checked-in Open Sans glyph
sets and both ice symbols in the web and mobile packages.

The clipped OpenStreetMap source yielded 388 glacier polygons and one
permanent snowfield for Everest & Khumbu. Annapurna yielded 1,080 glacier
polygons and two permanent snowfields. These are source polygon counts.

```sh
export PYTHONPATH=work/python
for edition in nepal-everest nepal-annapurna; do
  output="work/$edition-release"
  python3 scripts/run_full_region.py --region "$edition" || exit
  python3 scripts/build_app_distribution.py --regions "$edition" \
    --output "$output/kits" --catalog "$output/catalog.json" || exit
  python3 scripts/build_web_previews.py --regions "$edition" --output "$output/preview" \
    --origin "https://downloads.appsbyonzy.dev/OpenBareMap/$edition/2.0.0/preview" || exit
done
python3 scripts/stage_nepal_trekking.py --website /path/to/AppsByOnzy-Website/site/index.html
```

Use the same command with `--publish-assets` from a release checkout with
R2 and network access. The publisher verifies the release objects and previews
before updating the online catalogues. The production Pages archive is
`work/nepal-publication/appsbyonzy-nepal-trekking.zip`.

## Iceland and Patagonia

The three editions use complete-feature Geofabrik OpenStreetMap extracts,
Copernicus GLO-30 elevation, 20 m contours, hillshade and separate symbols for
mapped glaciers and permanent snowfields. The Patagonia editions share the
Chile and Argentina raw downloads and source DEM tiles. Their map coverage
overlaps at the Southern Patagonian Ice Field.

| Edition | Walking coverage | Geofabrik extract date | Grid | Garmin family |
| --- | --- | --- | --- | --- |
| Iceland – Southern Highlands | Landmannalaugar, Laugavegur, Þórsmörk, Fimmvörðuháls, Skógar and the two ice caps | 21 November 2026 | WGS 84 / UTM 27N | 4869 |
| Torres del Paine | W and O circuits, Grey Glacier and road approaches from Puerto Natales | 22 November 2026 | WGS 84 / UTM 18S | 4870 |
| El Chaltén & Los Glaciares | Fitz Roy, Cerro Torre, Lago del Desierto, Perito Moreno Glacier and El Calafate | 22 November 2026 | WGS 84 / UTM 18S | 4871 |

Build sequentially when the Patagonia source cache is empty. The validation
report checks destination tiles, local glyphs across all three Open Sans
styles, ice geometry and release checksums. Check the report's ice counts
and compare the two classes with the map key during visual review.

The release reports record 28 glacier polygons for Iceland, 94 for Torres
del Paine and 204 for El Chaltén. None of the three OSM extracts contains
separately tagged permanent snowfield polygons inside the map coverage.
The shared permanent snowfield symbol remains in each key.

```sh
export PYTHONPATH=work/python
for edition in iceland-southern-highlands patagonia-torres-del-paine patagonia-el-chalten; do
  output="work/$edition-release"
  python3 scripts/run_full_region.py --region "$edition" || exit
  python3 scripts/build_app_distribution.py --regions "$edition" \
    --output "$output/kits" --catalog "$output/catalog.json" || exit
  python3 scripts/build_web_previews.py --regions "$edition" --output "$output/preview" \
    --origin "https://downloads.appsbyonzy.dev/OpenBareMap/$edition/2.0.0/preview" || exit
done
python3 scripts/stage_iceland_patagonia.py
```

Run `python3 scripts/stage_iceland_patagonia.py --publish-assets` from a
network-enabled release checkout with the configured R2 remote. It verifies
the uploaded files and PMTiles range responses before updating the app
catalogues and website checkout. The production Pages archive is
`work/iceland-patagonia-publication/appsbyonzy-iceland-patagonia.zip`.
Deploy it to the appsbyonzy Pages project and commit the website checkout,
the verified Worldwide catalogue and the OpenBareMap release records.

## Permanent ice updates

The 22 November 2026 audit screened the 37 editions published at the time
for glaciers and permanent snowfields. The locked OpenStreetMap extracts for 18
editions contained no polygons with those tags. Sixteen editions show ice
using OpenStreetMap outlines and classifications, including five Alpine,
three Norwegian, three Canadian Rockies and five US national park editions.
The other three received research-based follow-up reviews. The
[Pyrenees](#pyrenees-ice-review) moved to 2.0.2, the
[High Tatras](#snow-and-ice-review) moved to 2.0.1, and Picos de Europa
stayed on 2.0.0.

OpenBareMap 2.0.1 adds mapped glaciers and permanent snowfields to five US
National Parks editions, all five Alpine editions, the three Norway editions
and the Pyrenees. The map key distinguishes the two features. This release
preserves the accepted contours, hillshade, grids and non-ice basemap layers.
Permanent ice outlines come from the existing locked OpenStreetMap snapshots.
For the Pyrenees, the map attribution notes that the 2025 survey measured a
smaller active Aneto glacier than the mapped OpenStreetMap outline.

Run `PYTHONPATH=work/python python3 scripts/upgrade_permanent_ice.py <region>`
for an accepted 2.0.0 region. The script verifies the prior checksums, saves
the previous regional resources in `work/glacier-updates/previous/`, and stages
the new Garmin image, mobile bundles, previews and map key. The old map
versions remain available under their existing public URLs.

Upload and verify completed releases with
`scripts/stage_permanent_ice_updates.py --upload-wave <1–5>`. Once all waves
have built, run the same script without options to stage the website and
the updated nine-map US collection, then run it with `--publish-assets`
to verify the collections, check preview byte ranges and update the online
catalogues. Deploy the final website archive to the production Pages project.

### Pyrenees ice review

The 2.0.2 iOS, Android and Garmin downloads are published and verified on
Cloudflare R2. BareGPS Worldwide selects 2.0.2. The public preview keeps its
2.0.1 address and uses the reviewed ice overlay. See the
[mobile verification](../web-preview/verification/pyrenees-2.0.2-mobile-publication.json)
and [Garmin verification](../web-preview/verification/pyrenees-2.0.2-garmin-r2.json).

The 2.0.2 build uses 16 selected OpenStreetMap glacier polygons and 10
perennial ice-patch polygons. Some glaciers have multiple polygons. The
selection uses the 2023 survey and the 2024 OPCC inventory. It omits extinct
or unverified features and uses the permanent snowfield symbol for identified
ice patches such as La Paúl. The retained outlines are approximate. The 2026
Aneto field survey reported four separate ice bodies.
See the [2023 survey](https://doi.org/10.1007/s10113-024-02333-1),
[OPCC inventory](https://criosfera.opcc-ctp.org/en/origin-of-the-data/), and
[2026 Aneto field report](https://cadenaser.com/aragon/2026/11/04/el-glaciar-del-aneto-se-ha-fragmentado-en-cuatro-y-el-de-la-llardana-afronta-su-ultimo-ano-como-glaciar-radio-jaca-ser-pirineos/).

Build the release from the accepted 2.0.1 Pyrenees edition. The pipeline
preserves the original contours, hillshade, grid and non-ice basemap layers.

```sh
export PYTHONPATH=work/python
python3 scripts/upgrade_permanent_ice.py --review-pyrenees pyrenees
python3 scripts/stage_mountain_editions.py --pyrenees-ice-review
python3 scripts/stage_mountain_editions.py --pyrenees-ice-review --publish-assets
```

Deploy `work/pyrenees-ice-review/publication/appsbyonzy-pyrenees-ice-review.zip`
to the production Pages project after the public checks pass.

## Canadian Rockies

Three editions use park footprints and buffered approaches. Banff and Jasper
overlap on the Icefields Parkway between Saskatchewan River Crossing and the
Columbia Icefield. The southern edition overlaps Banff around Canmore and Spray
Valley and reaches the US Glacier edition at the 49th parallel.

| Edition | iOS bundle | Android bundle | Garmin image | Garmin family |
| --- | ---: | ---: | ---: | ---: |
| Banff, Yoho & Kootenay | 522 MB | 522 MB | 92 MB | 4866 |
| Jasper & Mount Robson | 536 MB | 536 MB | 100 MB | 4867 |
| Kananaskis & Waterton | 461 MB | 461 MB | 59 MB | 4868 |

Build inputs are the 20 November 2026 Geofabrik snapshots of Alberta and
British Columbia, Copernicus GLO-30 and park outlines from [Parks Canada],
[Alberta Parks] and [British Columbia]. The map displays generalized park
boundaries, 20 m contours and a WGS 84 / UTM 11N grid. Keep source and terrain
locks. The raw data, intermediate databases and device binaries are rebuildable.

The map key has separate entries for glaciers and permanent snowfields.
The November 2026 OpenStreetMap snapshot includes glacier polygons in all three
editions. It has no separately tagged permanent snowfields within their coverage.

```sh
export PYTHONPATH=work/python
python3 scripts/prepare_canadian_rockies.py
for edition in canadian-rockies-banff canadian-rockies-jasper canadian-rockies-kananaskis-waterton; do
  python3 scripts/run_full_region.py --region "$edition"
  output="work/$edition-release"
  python3 scripts/build_app_distribution.py --regions "$edition" \
    --output "$output/kits" --catalog "$output/catalog.json"
  python3 scripts/build_web_previews.py --regions "$edition" --output "$output/preview" \
    --origin "https://downloads.appsbyonzy.dev/OpenBareMap/$edition/2.0.0/preview"
done
python3 scripts/stage_canadian_rockies.py
python3 scripts/stage_canadian_rockies.py --publish-assets
```

After the downloads, previews and catalogues verify, deploy
`work/canadian-rockies-publication/appsbyonzy-canadian-rockies.zip` to Pages.
Copy the merged `worldwide-catalog-v1.json` from the same publication folder
to `Distribution/worldwide-catalog-v1.json` in BareGPS Worldwide.

[Parks Canada]: https://open.canada.ca/data/en/dataset/e1f0c975-f40c-4313-9be2-beb951e35f4e
[Alberta Parks]: https://open.canada.ca/data/en/dataset/936b1a57-c7de-4f42-b032-5d97bc541fe6
[British Columbia]: https://open.canada.ca/data/en/dataset/1130248f-f1a3-4956-8b2e-38d29d3e4af7

## Picos de Europa and High Tatras

Picos de Europa covers the three massifs and the approaches from Asturias,
Cantabria and León. The High Tatras edition joins the Polish and Slovak
trail networks in one map. Each edition clips the 20 November 2026 Geofabrik
snapshot to its own coverage envelope and uses Copernicus GLO-30 for
20 m contours, hillshade and Garmin elevation.

| Edition | OSM extracts | Grid | Garmin family |
| --- | --- | --- | --- |
| Picos de Europa | Asturias, Cantabria, Castilla y León | ETRS89 / UTM 30N | 4864 |
| High Tatras | Małopolskie, Slovakia | ETRS89 / UTM 34N | 4865 |

Build and validate either edition using the regional pipeline.

```sh
PYTHONPATH=work/python python3 scripts/run_full_region.py --region picos-de-europa
PYTHONPATH=work/python python3 scripts/run_full_region.py --region high-tatras
```

Each `regions/<edition>/region.json` records its coverage, source URLs and
validation anchors. The build records source checksums in that directory
and publishes local validation reports under `releases/<edition>/2.0.0/`.
The extracts, terrain tiles, working databases and device binaries can be
recreated with the build commands.

After both builds pass, stage each edition's mobile kits and PMTiles preview.

```sh
export PYTHONPATH=work/python
for edition in picos-de-europa high-tatras; do
  output="work/$edition-release"
  python3 scripts/build_app_distribution.py --regions "$edition" \
    --output "$output/kits" --catalog "$output/catalog.json"
  python3 scripts/build_web_previews.py --regions "$edition" --output "$output/preview" \
    --origin "https://downloads.appsbyonzy.dev/OpenBareMap/$edition/2.0.0/preview"
done
python3 scripts/stage_mountain_editions.py
python3 scripts/stage_mountain_editions.py --publish-assets
```

The last command verifies Cloudflare readbacks before updating the public
catalogues and site package. The production Pages archive is
`work/picos-tatras-publication/appsbyonzy-picos-de-europa-and-high-tatras.zip`.
Picos de Europa appears under France & Spain and the High Tatras under
Eastern Europe.

### Snow and ice review

The locked Picos de Europa extract contains one glacier-tagged polygon named
El Neverón. The [Picos de Europa National Park research proceedings](https://parquenacionalpicoseuropa.es/wp-content/uploads/2025/02/texto-completo-libro-actas-i-joernadas-investigacion-pnpe-2023.pdf)
describe remnant ice patches with no current glacier movement, and the
[IGME geological guide](https://web.igme.es/LibrosE/GuiasGeo/picosdeeuropa_sp/75/)
discusses the Neverón de Urriellu as a possible Little Ice Age glacier. The
review found no recent surveyed outline that confirmed the mapped polygon as
perennial. The Picos edition stays on 2.0.0.

The [High Tatras research](https://web.natur.cuni.cz/kfggsekr/rggg/pdf/dlabackova_ea_23.pdf)
describes surviving perennial snowfields and firn ice patches. The High
Tatras 2.0.1 build shows the 14 outlines from the locked OpenStreetMap extract
with the permanent snowfield symbol and identifies them in the attribution as
mapped patches with variable extent and persistence. The map key includes the
snowfield symbol. The build retains the 2.0.0 contours, hillshade and grid.

```sh
export PYTHONPATH=work/python
python3 scripts/upgrade_permanent_ice.py high-tatras
python3 scripts/stage_mountain_editions.py --tatras-snowfields
python3 scripts/stage_mountain_editions.py --tatras-snowfields --publish-assets
```

The staged website archive is
`work/glacier-updates/high-tatras-publication/appsbyonzy-high-tatras-snowfields.zip`.

## US National Parks

The series covers ten parks in nine maps. Each edition uses the National Park
Service boundary and a park-specific buffer that includes nearby trailheads,
gateway towns and principal approaches. Yellowstone and Grand Teton share an
edition linked by the John D. Rockefeller Jr. Memorial Parkway. The maps use
OpenStreetMap from Geofabrik's 20 November 2026 state extracts, Copernicus
GLO-30 elevation, 20 m contours, hillshade and a local WGS 84 / UTM grid.

| Edition | Garmin family |
| --- | --- |
| Yosemite | 4855 |
| Great Smoky Mountains | 4856 |
| Zion | 4857 |
| Yellowstone & Grand Teton | 4858 |
| Grand Canyon | 4859 |
| Rocky Mountain | 4860 |
| Acadia | 4861 |
| Olympic | 4862 |
| Glacier | 4863 |

Build using the installed regional Python dependencies. Pass `--regions` to
build selected editions or `--prepare-only` to verify the park boundaries.

```sh
PYTHONPATH=work/python python3 scripts/build_us_national_parks.py --source-date 2026-11-20
```

Once all nine editions pass validation, stage iOS, Android and Garmin
downloads, the three collection ZIPs, the website, the browser previews and
the BareGPS Worldwide catalogue.

```sh
PYTHONPATH=work/python python3 scripts/stage_us_national_parks.py
```

The output is in `work/us-national-parks-release/`. The collection downloads
are about 1.60 GB for iOS, 1.60 GB for Android and 286 MB for Garmin.

Publish from a network-enabled terminal with the production R2 remote
configured in rclone. The command checks public download hashes and preview
byte ranges, merges the nine releases into the live catalogues and refreshes
regional preview navigation. Successful readbacks are recorded in
`public-verification.json` so an interrupted upload can resume.

```sh
PYTHONPATH=work/python python3 scripts/stage_us_national_parks.py --publish-assets
```

After the upload command succeeds, deploy
`work/us-national-parks-release/appsbyonzy-us-national-parks.zip` to the
production Cloudflare Pages project. Verify the homepage and the US National
Parks links on the live site. Commit the updated homepage in the
[website repository](https://github.com/davidowens1513/AppsByOnzy-Website),
the release files in OpenBareMap, and the verified `worldwide-catalog-v1.json`
in the `Distribution/` directory of BareGPS Worldwide.

## Alps editions

The Alpine series uses five display names. **Alps - Dolomites** reuses the
existing Dolomites map, with its original region ID, package URLs and Garmin
family. The four new editions are built as a batch.

| Edition | Main coverage | Garmin family |
| --- | --- | --- |
| Alps - West | Mediterranean approaches, Mercantour, Écrins, Vanoise, Gran Paradiso and the Tour du Mont Blanc | 4851 |
| Alps - Central | Valais, Bernese Oberland, Ticino, Graubünden, Liechtenstein and adjoining valleys | 4852 |
| Alps - Tyrol & Bavaria | Arlberg, Innsbruck, the Bavarian Alps and Hohe Tauern | 4853 |
| Alps - East | Eastern Austrian Alps, Julian Alps and Karawanks | 4854 |

The new editions share a dated Geofabrik Alps extract, 20 m contours and one
aligned Copernicus GLO-30 terrain mosaic. The regions overlap at Mont Blanc,
Arlberg and Katschberg. Verify the transition to the existing Dolomites map
around Brenta, Brenner and Lienz. Each profile records destination points for
tile coverage checks. The bounds are build envelopes. Detailed OSM coverage
within them follows the Geofabrik extract.

From the repository on a machine with access to Geofabrik and Copernicus:

```sh
PYTHONPATH=work/python:scripts python3 scripts/build_alps.py
```

The batch builds and validates iOS, Android and Garmin outputs for each new
edition, then stages integration ZIPs and a local catalogue in
`work/alps-app-bundles-v1/` and browser previews in `work/alps-web-2.0.0/`.
The local previews use port 8768 and require an HTTP server that supports
byte-range requests. Production website and Worldwide catalogue entries are
released after the four sets of downloads and previews are verified.

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

The publisher uploads map assets, verifies complete public download checksums,
then publishes preview navigation. Without `--publish`, it only prints the
prepared plan. Publication verification is recorded in
`web-preview/verification/norway-publication.json`.

Update the homepage links in [AppsByOnzy-Website](https://github.com/davidowens1513/AppsByOnzy-Website)
after verifying the public downloads. To stage the committed site alongside
the Norway release, pass `--website-repo /absolute/path/to/AppsByOnzy-Website`
to `scripts/prepare_norway_publication.py`. This produces
`work/norway-website-20261114.zip` for manual upload to the existing
`appsbyonzy` Pages project. The publisher's optional `--website` flag deploys
that same archive after the map checks and requires Wrangler or Node.js/npx
with Cloudflare Pages access.

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

### Crete, Cyprus and Malta

Crete uses the 17 November 2026 Geofabrik Greece extract clipped to the
island group, including Gavdos. Cyprus and Malta use their own Geofabrik
extracts from the same date. Cyprus covers the whole island and Malta covers
Malta, Gozo and Comino in a single edition. The offline glyph range for
Greek labels is recorded in the viewer asset lock.

These editions use the same 20 m contours, Copernicus GLO-30, storage rules,
app integration kits and regional preview format as the other Mediterranean
island maps. Garmin family IDs are 4846, 4847 and 4848 respectively.

## Canary Islands and Madeira

The Canaries are a single edition covering all eight islands, plus Lobos and
smaller islets. Geofabrik supplies a dedicated extract. Madeira is a separate
edition covering Madeira, Porto Santo, the Desertas and the Selvagens.
Its OpenStreetMap data comes from the clipped Portugal extract. Both use
the 17 November 2026 snapshots, Copernicus GLO-30 and 20 m contours.
The Canaries use REGCAN95 / UTM 28N and Madeira uses PTRA08 / UTM 28N.
Garmin family IDs are 4849 and 4850 respectively.

The storage and publication workflows follow the existing island editions.
Git keeps configuration, verification and provenance. Rebuildable inputs
and working databases stay local. Cloudflare R2 serves the integration kits,
Garmin images and browser previews.
