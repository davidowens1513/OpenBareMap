#!/usr/bin/env python3
"""Export the active map legend to scalable SVG and 2x PNG (Pillow required)."""
from pathlib import Path
import base64,hashlib,html,io,json,math
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'app-legend';OUT.mkdir(exist_ok=True)
STYLE=json.loads((ROOT/'style/openbaremap.json').read_text());LAYERS={l['id']:l for l in STYLE['layers']}
ATLAS=Image.open(ROOT/'viewer/sprites/outdoors.png').convert('RGBA');INDEX=json.loads((ROOT/'viewer/sprites/outdoors.json').read_text())
W,H,S=1000,1320,2
canvas=Image.new('RGB',(W*S,H*S),'white');draw=ImageDraw.Draw(canvas)
svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">','<rect width="100%" height="100%" fill="white"/>']
REG='/System/Library/Fonts/Supplemental/Arial.ttf';BOLD='/System/Library/Fonts/Supplemental/Arial Bold.ttf'
def text(x,y,label,size=16,color='#33453d',bold=False):
 draw.text((x*S,y*S),label,font=ImageFont.truetype(BOLD if bold else REG,round(size*S)),fill=color,anchor='lt')
 # Arial top-bearing is included in the SVG baseline offset.
 svg.append(f'<text x="{x}" y="{y+size*.91}" font-family="Arial, Helvetica, sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" fill="{color}">{html.escape(label)}</text>')
def line(x1,y1,x2,y2,color,width=1,opacity=1,dash=None):
 c=tuple(round(int(color[i:i+2],16)*opacity+255*(1-opacity)) for i in (1,3,5))
 if dash:
  dist=math.hypot(x2-x1,y2-y1);pos=0;k=0
  while pos<dist:
   end=min(dist,pos+dash[k%len(dash)])
   if k%2==0:draw.line(((x1+(x2-x1)*pos/dist)*S,(y1+(y2-y1)*pos/dist)*S,(x1+(x2-x1)*end/dist)*S,(y1+(y2-y1)*end/dist)*S),fill=c,width=max(1,round(width*S)))
   pos=end;k+=1
 else:draw.line((x1*S,y1*S,x2*S,y2*S),fill=c,width=max(1,round(width*S)))
 svg.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{width}" opacity="{opacity}"'+(f' stroke-dasharray="{" ".join(map(str,dash))}"' if dash else '')+'/>')
def image(im,x,y,w,h):
 buf=io.BytesIO();im.save(buf,format='PNG');data=base64.b64encode(buf.getvalue()).decode()
 canvas.paste(im.resize((round(w*S),round(h*S)),Image.Resampling.LANCZOS),(round(x*S),round(y*S)),im.resize((round(w*S),round(h*S)),Image.Resampling.LANCZOS).getchannel('A'))
 svg.append(f'<image x="{x}" y="{y}" width="{w}" height="{h}" href="data:image/png;base64,{data}"/>')
def value(v,cl=None,z=14):
 if not isinstance(v,list):return v
 if v[0]=='match':
  for i in range(2,len(v)-1,2):
   if v[i]==cl or isinstance(v[i],list) and cl in v[i]:return value(v[i+1],cl,z)
  return value(v[-1],cl,z)
 if v[0]=='interpolate':
  if z<=v[3]:return value(v[4],cl,z)
  for i in range(5,len(v),2):
   if z<=v[i]:
    a=value(v[i-1],cl,z);b=value(v[i+1],cl,z);return a+(b-a)*(z-v[i-2])/(v[i]-v[i-2])
  return value(v[-1],cl,z)
 if v[0]=='step':
  selected=v[2]
  for i in range(3,len(v),2):
   if z>=v[i]:selected=v[i+1]
  return selected
 raise ValueError(v)
def texture(name,w=96,h=24):
 a=INDEX[name];im=ATLAS.crop((a['x'],a['y'],a['x']+a['width'],a['y']+a['height']));im=im.resize((round(a['width']/a['pixelRatio']*S),round(a['height']/a['pixelRatio']*S)),Image.Resampling.LANCZOS)
 tile=Image.new('RGBA',(w*S,h*S))
 for y in range(0,tile.height,im.height):
  for x in range(0,tile.width,im.width):tile.alpha_composite(im,(x,y))
 return tile

def heading(x,y,label):
 text(x,y,label,19,'#243e32',True);line(x,y+32,x+424,y+32,'#d8dfd9')
def fillrow(x,y,label,layer,cl=None,pattern=None):
 paint=LAYERS[layer]['paint'];sw=Image.new('RGBA',(96*S,24*S),'#f3efe6')
 col=Image.new('RGBA',sw.size,value(paint['fill-color'],cl));col.putalpha(round(255*value(paint.get('fill-opacity',1),cl)));sw=Image.alpha_composite(sw,col)
 if pattern:
  p=LAYERS[pattern]['paint'];tile=texture(value(p['fill-pattern']));tile.putalpha(tile.getchannel('A').point(lambda a:round(a*value(p.get('fill-opacity',1)))));sw=Image.alpha_composite(sw,tile)
 image(sw,x,y,96,24);text(x+114,y+3,label)
def linerow(x,y,label,layer,cl=None,casing=None):
 p=LAYERS[layer]['paint'];width=value(p.get('line-width',1))*1.6
 if casing:
  c=LAYERS[casing]['paint'];line(x,y+12,x+96,y+12,value(c['line-color'],cl),value(c['line-width'])*1.6,value(c.get('line-opacity',1)))
 line(x,y+12,x+96,y+12,value(p['line-color'],cl),width,value(p.get('line-opacity',1)),[d*width for d in p['line-dasharray']] if 'line-dasharray' in p else None)
 text(x+114,y+3,label)
text(48,38,'OpenBareMap 2.0',36,'#213d30',True);text(49,88,'MAP LEGEND',13,'#647b6c',True)
line(48,123,952,123,'#d8dfd9')
heading(48,153,'Landscape')
rows=[('Woodland / forest','landcover','wood',None),('Scrub','landcover','scrub',None),('Grassland / meadow','landcover','grass',None),('Farmland','landcover','farmland',None),('Heath','landcover','heath',None),('Wetland','landcover','wetland',None),('Bog','landcover','bog','bog-texture'),('Peat workings','landcover','peat_cutting','bog-texture'),('Bare rock','bare-rock',None,'bare-rock-stipple'),('Scree','scree-and-shingle','scree','scree-stipple'),('Shingle','scree-and-shingle','shingle','scree-stipple'),('Beach','landcover','beach',None),('Sand','landcover','sand',None),('Water','water',None,None),('Buildings','land-cover-buffer',None,None)]
for i,(label,layer,cl,pattern) in enumerate(rows):fillrow(48,204+i*36,label,layer,cl,pattern)
heading(528,153,'Roads & routes')
rows=[('Major road','roads-major','primary','roads-casing-major'),('Minor road','roads-minor','residential','roads-casing-minor'),('Service road','roads-minor','service','roads-casing-minor'),('Road bridge','roads-major--bridge-1','primary','roads-casing-major--bridge-1'),('Tunnel','roads-major--tunnel--1','primary',None),('Track','tracks',None,None),('Path / footway','paths',None,None),('Bridleway','bridleways',None,None),('Cycleway','cycleways',None,None),('Steps','steps',None,None),('Walking route','hiking-routes',None,None),('Cycling route','cycling-routes',None,None),('Railway','railways',None,None),('Ferry','ferry-routes',None,None),('Watercourse','waterway',None,None)]
for i,(label,layer,cl,casing) in enumerate(rows):linerow(528,204+i*36,label,layer,cl,casing)
heading(48,786,'Terrain')
linerow(48,830,'100 m index contour','contours');linerow(48,869,'20 m intermediate contour','contour-intermediate-lines')
cliff=texture('cliff-teeth',96,6);opacity=value(LAYERS['cliffs-and-crags']['paint']['line-opacity']);cliff.putalpha(cliff.getchannel('A').point(lambda a:round(a*opacity)));image(cliff,48,951,96,value(LAYERS['cliffs-and-crags']['paint']['line-width']));text(162,945,'Cliff / crag')
# Illustrative relief swatch, clearly distinct from mapped feature patterns.
shade=Image.new('RGBA',(96*S,24*S))
for x in range(shade.width):
 c=round(238-70*(math.sin(x/shade.width*math.pi)**2));ImageDraw.Draw(shade).line((x,0,x,shade.height),fill=(c,c,c,255))
image(shade,48,977,96,24);text(162,980,'Hillshade')
heading(528,786,'Boundaries & grid')
for i,(label,layer) in enumerate([('National boundary','administrative-boundaries'),('County boundary','county-boundaries'),('Irish Grid · 10 km','irish-grid-10km'),('Irish Grid · 1 km','irish-grid-1km')]):linerow(528,837+i*36,label,layer)
heading(48,1065,'Points')
# Use actual summit paint and actual parking atlas artwork.
p=LAYERS['summit-dots-natural-labels']['paint'];cx,cy=96,1128;rad=p['circle-radius']*1.6
draw.ellipse(((cx-rad)*S,(cy-rad)*S,(cx+rad)*S,(cy+rad)*S),fill=p['circle-color']);svg.append(f'<circle cx="{cx}" cy="{cy}" r="{rad}" fill="{p["circle-color"]}"/>');text(162,1119,'Summit')
a=INDEX['outdoor-parking'];im=ATLAS.crop((a['x'],a['y'],a['x']+a['width'],a['y']+a['height']));image(im,84,1161,24,24);text(162,1164,'Parking')
heading(528,1065,'Feature labels')
draw.ellipse((572*S,1125*S,578*S,1131*S),fill='#596957');svg.append('<circle cx="575" cy="1128" r="3" fill="#596957"/>');text(642,1119,'Outdoor facility')
text(528,1164,'Names identify places and mapped features.',13,'#647b6c')
line(48,1232,952,1232,'#d8dfd9');text(48,1252,'20 m contours  ·  Colours and patterns from the active map style',13,'#647b6c');text(48,1277,'Relief shading changes apparent colours. Line samples enlarged for clarity.',12,'#7a897f')
svg.append('</svg>');(OUT/'openbaremap-legend.svg').write_text('\n'.join(svg)+'\n');canvas.save(OUT/'openbaremap-legend@2x.png',optimize=True);canvas.resize((W,H),Image.Resampling.LANCZOS).save(OUT/'openbaremap-legend.png',optimize=True)
(OUT/'legend-manifest.json').write_text(json.dumps({'style_sha256':hashlib.sha256((ROOT/'style/openbaremap.json').read_bytes()).hexdigest(),'reference_zoom':14,'logical_size':[W,H],'png_2x_size':[W*S,H*S],'note':'SVG is self-contained with embedded pattern/symbol PNGs and system sans-serif text. Hillshade swatch is illustrative. Line strokes enlarged 1.6x for legibility; map dash ratios preserved.','outputs':['openbaremap-legend.svg','openbaremap-legend.png','openbaremap-legend@2x.png']},indent=2)+'\n')
print(OUT)
