#!/usr/bin/env python3
"""Generate Montana TYP source from explicit colours and deterministic patterns."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent
polygons=[(0x4b,'Background','#f3efe6',1,None),(0x32,'Sea','#a8d7ff',2,None),(0x54,'Land','#f3efe6',3,None),(0x50,'Woodland','#afd190',4,None),(0x10101,'Farmland','#e4dfbd',4,None),(0x10102,'Grass','#dce7c6',4,None),(0x10103,'Heath','#d8cbb8',4,None),(0x10104,'Scrub','#cdd9b8',4,None),(0x51,'Wetland','#c4d8cc',4,None),(0x10105,'Beach','#f1dfae',5,None),(0x10106,'Sand','#ead9ae',5,None),(0x10107,'Bog','#b9aa92',5,'bog'),(0x10108,'Peat workings','#a58b70',5,'bog'),(0x10109,'Bare rock','#d0ccc2',6,'rock'),(0x1010a,'Scree','#c9c4b8',6,'scree'),(0x1010b,'Shingle','#d8d1c3',6,'scree'),(0x3c,'Water','#a8d7ff',7,None),(0x13,'Buildings','#898c8b',8,None)]
lines=[(1, 'Motorway', '#f39a3d', 4, None, 1), (2, 'Trunk', '#ee9d4a', 4, None, 1), (3, 'Primary', '#f0ad61', 3, None, 1), (4, 'Secondary', '#f4bf7b', 3, None, 1), (6, 'Minor road', '#e6cf98', 2, None, 1), (7, 'Service road', '#ffffff', 2, None, 1), (10, 'Track', '#8b6f47', 2, (6, 4), 0), (22, 'Path and footway', '#6a8f5a', 2, (3, 3), 0), (65539, 'Bridleway', '#867044', 2, (6, 3), 0), (65540, 'Cycleway', '#347bb7', 2, (5, 3), 0), (65541, 'Steps', '#6a8f5a', 2, (1, 2), 0), (65542, 'Cliffs', '#837c73', 3, 'cliff', 0), (20, 'Railway', '#68645f', 2, (6, 2), 0), (26, 'Ferry', '#468db6', 2, (7, 4), 0), (31, 'River', '#74b5e6', 2, None, 0), (24, 'Stream', '#74b5e6', 1, None, 0), (65544, '100 metre contour - overview', '#b8a68b', 1, None, 0), (32, '20 metre contour', '#9a8161', 1, None, 0), (34, '100 metre contour', '#8b6f47', 2, None, 0), (65537, 'Walking route', '#cc553d', 2, (6, 3), 0), (65538, 'Cycling route', '#347bb7', 2, None, 0), (30, 'National boundary', '#755778', 2, (8, 4), 0), (28, 'County boundary', '#927d96', 1, (6, 4), 0)]
def section(kind,code,name,font='SmallFont',color='#554b3d'):
 return [f'[_{kind}]',f'Type=0x{code:x}',f'String={name}',f'FontStyle={font}',f'DayCustomColor={color}',f'NightCustomColor={color}']
def polygon_pattern(kind,x,y):
 if kind=='bog':return (y%8==4 and x%10 in (2,3,4)) or (x%10==3 and y%8 in (2,3))
 if kind=='rock':return ((x*19+y*31)%97)<7 and (x+y)%3!=0
 return ((x*29+y*17+x*y)%101)<10

def main():
 out=['; -*- coding: UTF-8 -*-','; OpenBareMap Montana 750i display-only cartography.','[_id]','FID=4831','ProductCode=1','CodePage=1252','[end]','[_drawOrder]']
 for code,name,col,order,pattern in polygons:out.append(f'Type=0x{code:x},{order}')
 out+=['[end]']
 for code,name,col,order,pattern in polygons:
  out+=section('polygon',code,name,'NoLabel')
  if pattern:
   out+=['Xpm="32 32 2 1"',f'"a c {col}"','"b c #8e825f"']
   out += ['"'+''.join('b' if polygon_pattern(pattern,x,y) else 'a' for x in range(32))+'"' for y in range(32)]
  else:out+=['Xpm="0 0 1 0"',f'"a c {col}"']
  out+=['[end]']
 for code,name,col,width,dash,border in lines:
  out+=section('line',code,name,'NoLabel' if code in (0x10008,0x10009) else 'SmallFont')
  if dash:
   out+=['UseOrientation=Y',f'Xpm="32 {width} 2 1"',f'"a c {col}"','". c none"']
   for y in range(width):
    row=''.join('a' if (y==1 or (y>1 and x%8==y)) else '.' for x in range(32)) if dash=='cliff' else ''.join('a' if x%sum(dash)<dash[0] else '.' for x in range(32))
    out.append('"'+row+'"')
  else:
   out += [f'LineWidth={width}',f'BorderWidth={border}',f'Xpm="0 0 {2 if border else 1} 0"',f'"a c {col}"']
   if border:out+=['"b c #8f806b"']
  out+=['[end]']
 points=[(0x0100,'City','NormalFont'),(0x0600,'Town','SmallFont'),(0x0800,'Village','SmallFont'),(0x0b00,'Hamlet','SmallFont'),(0x0c00,'Locality','SmallFont'),(0x650c,'Island','SmallFont'),(0x6603,'Water name','SmallFont'),(0x10006,'Point of interest','SmallFont'),(0x6616,'Summit','SmallFont'),(0x6615,'Saddle','SmallFont'),(0x10001,'Hiking facility','SmallFont'),(0x10002,'Outdoor feature','SmallFont'),(0x10003,'Amenity','SmallFont'),(0x10004,'Station','SmallFont'),(0x1e00,'Townland','NormalFont')]
 for code,name,font in points:
  out+=section('point',code,name,font,'#817b70' if code==0x1e00 else '#554b3d')
  out+=['DayXpm="8 8 2 1"','"a c #554b3d"','". c none"']
  visible=code in (0x6616,0x6615,0x10001,0x10002,0x10003,0x10004)
  out+=['"'+''.join('a' if visible and (x-3.5)**2+(y-3.5)**2<4 else '.' for x in range(8))+'"' for y in range(8)];out+=['[end]']
 out+=section('point',0x2f0b,'Parking')+['DayXpm="12 12 3 1"','"b c #0057b8"','"w c #ffffff"','". c none"']
 for y in range(12):out.append('"'+''.join('w' if ((x in (3,4) and 2<=y<=9) or (y in (2,3,6) and 4<=x<=8) or (x in (8,9) and 3<=y<=5)) else 'b' for x in range(12))+'"')
 out+=['[end]']
 (ROOT/'style/OBM4831.txt').write_text('\n'.join(out)+'\n')
 (ROOT/'cartography.json').write_text(json.dumps({'polygons':polygons,'lines':lines,'points':points,'target':'Montana 750i','routing':False,'native_fonts':'Garmin SmallFont/NormalFont; no Open Sans pixel-size equivalence','night':'Same map colours in day and night for this first device profile'},indent=2)+'\n')
if __name__=='__main__':main()
