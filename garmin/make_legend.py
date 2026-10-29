#!/usr/bin/env python3
"""Montana profile legend using the actual generated TYP pattern definitions."""
from pathlib import Path
import importlib.util,json
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('typgen',R/'generate_typ.py');typ=importlib.util.module_from_spec(spec);spec.loader.exec_module(typ)
W,H,S=1100,1320,2
im=Image.new('RGB',(W*S,H*S),'#fffdf8');d=ImageDraw.Draw(im)
regular='/System/Library/Fonts/Supplemental/Arial.ttf';bold='/System/Library/Fonts/Supplemental/Arial Bold.ttf'
def text(x,y,s,size=17,strong=False,color='#35483d'):d.text((x*S,y*S),s,font=ImageFont.truetype(bold if strong else regular,size*S),fill=color)
def heading(x,y,s):text(x,y,s,21,True);d.line((x*S,(y+36)*S,(x+470)*S,(y+36)*S),fill='#d8dfd6',width=2)
text(50,35,'OpenBareMap 2.0 · Ireland',36,True);text(50,88,'MONTANA 750i · GPSMAP 67i  /  DISPLAY-ONLY MAP',14,True);heading(50,145,'Landscape');heading(590,145,'Ways & terrain')
land=[x for x in typ.polygons if x[1] not in ['Background','Land','Sea']]
for i,(code,name,color,order,pattern) in enumerate(land):
 y=202+i*43;sw=Image.new('RGB',(96,32),color)
 if pattern:
  p=sw.load()
  for yy in range(32):
   for xx in range(96):
    if typ.polygon_pattern(pattern,xx%32,yy):p[xx,yy]=(142,130,95)
 im.paste(sw.resize((96*S,32*S)),(50*S,y*S));text(166,y+4,name)
for i,(code,name,color,width,dash,border) in enumerate(typ.lines):
 y=202+i*36
 if dash:
  sw=Image.new('RGBA',(96,width),(0,0,0,0));p=sw.load();rgb=tuple(int(color[j:j+2],16) for j in (1,3,5))
  for yy in range(width):
   for xx in range(96):
    on=(yy==1 or yy>1 and xx%8==yy) if dash=='cliff' else xx%sum(dash)<dash[0]
    if on:p[xx,yy]=(*rgb,255)
  sw=sw.resize((96*S,width*S));im.paste(sw,(590*S,(y+11-width//2)*S),sw)
 else:
  if border:d.line((590*S,(y+11)*S,686*S,(y+11)*S),fill='#8f806b',width=(width+2*border)*S)
  d.line((590*S,(y+11)*S,686*S,(y+11)*S),fill=color,width=width*S)
 text(706,y,name,16)
heading(50,900,'Names & points')
text(50,958,'•  Summit / saddle',18);text(50,1002,'•  Outdoor facility',18)
d.rectangle((50*S,1050*S,74*S,1074*S),fill='#0057b8');text(56,1047,'P',20,True,'white');text(90,1050,'Parking',18)
text(50,1102,'Native Garmin fonts and detail levels.',14);text(50,1130,'Day and night use the same palette.',14)
d.line((50*S,1215*S,1050*S,1215*S),fill='#d8dfd6',width=2)
text(50,1240,'20 m contour geometry · DEM-based relief shading · No turn-by-turn routing',15)
text(50,1273,'Device settings influence text size, visibility and relief shading. Line samples enlarged for clarity.',12)
im.save(R/'dist/Montana-750i-Legend.png',optimize=True)
