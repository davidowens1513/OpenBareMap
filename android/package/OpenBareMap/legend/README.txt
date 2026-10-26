OpenBareMap app legend

openbaremap-legend.svg     Self-contained scalable graphic; embedded pattern/symbol images.
openbaremap-legend.png     1000 x 1320 pixels.
openbaremap-legend@2x.png  2000 x 2640 pixels; suitable for a 2x image asset.

White background. Use aspect-fit sizing; provide scrolling or zoom when showing the complete legend on a small screen. The SVG uses Arial/Helvetica/system sans-serif text rather than embedding a licensed font file. Terrain textures and the parking mark are embedded, so the SVG has no external image dependencies.

Colours and patterns come from the active style at reference zoom 14. Line widths and dash lengths are enlarged together by 1.6 for readability. The hillshade swatch is illustrative. The manifest records the style checksum used for this export.

Regenerate after changing map styling:
  python3 scripts/build_app_legend.py
Requires Pillow (assets/requirements.txt) and the macOS Arial font files named in the generator. Runtime use of the PNGs requires neither dependency.
