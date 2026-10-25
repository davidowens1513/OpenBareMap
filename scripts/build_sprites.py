#!/usr/bin/env python3
"""Generate original outdoor map symbols at 1x and 2x, without system fonts."""
import hashlib
import json
from pathlib import Path
import PIL
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[1]
NAMES=['peak','saddle','hut','shelter','trailhead','viewpoint','campsite','drinking_water','toilets','guidepost','parking','rescue']

def icon(name,ratio):
    scale=4*ratio
    im=Image.new('RGBA',(24*scale,24*scale));d=ImageDraw.Draw(im)
    ink='#5c4939';white='#fffdf6';blue='#2e647d'
    def box(values):return tuple(round(x*scale) for x in values)
    def line(points,fill=ink,width=1.8):d.line([box(p) for p in points],fill=fill,width=round(width*scale),joint='curve')
    def poly(points,fill=white,outline=ink,width=1.8):d.polygon([box(p) for p in points],fill=fill,outline=outline,width=round(width*scale))
    def ellipse(bounds,fill=None,outline=ink,width=1.8):d.ellipse(box(bounds),fill=fill,outline=outline,width=round(width*scale))
    if name not in ['peak','saddle']:
        d.rounded_rectangle(box((2,2,22,22)),radius=round(4*scale),fill=white,outline='#bcb9ab',width=scale)
    if name=='peak':
        poly([(12,3),(22,21),(2,21)]);line([(8,14),(11,12),(14,16),(16,13)],width=1)
    elif name=='saddle':
        line([(3,6),(8,15),(16,15),(21,6)],fill=white,width=4);line([(3,6),(8,15),(16,15),(21,6)])
    elif name in ['hut','shelter']:
        line([(5,11),(12,5),(19,11)])
        if name=='hut':poly([(6,11),(18,11),(18,20),(6,20)]);d.rectangle(box((11,14,14,20)),fill=ink)
        else:line([(6,11),(6,20)]);line([(18,11),(18,20)]);line([(6,17),(18,17)])
    elif name in ['trailhead','guidepost']:
        line([(11,5),(11,21)])
        poly([(6,6),(16,6),(20,9),(16,12),(6,12)])
        if name=='guidepost':poly([(4,13),(16,13),(16,17),(4,17),(2,15)],width=1)
    elif name=='viewpoint':
        ellipse((4,7,20,17),outline=blue);ellipse((10,10,14,14),fill=blue,outline=blue)
    elif name=='campsite':
        poly([(12,5),(21,20),(3,20)],outline='#3e6751');line([(12,5),(12,20),(16,20)],fill='#3e6751')
    elif name=='drinking_water':
        poly([(12,4),(6,13),(6,17),(9,20),(15,20),(18,17),(18,13)],fill=blue,outline=blue,width=1);line([(9,13),(8,16),(10,18)],fill=white,width=1)
    elif name=='toilets':
        for x in [8,16]:
            ellipse((x-1.5,5,x+1.5,8),fill=blue,outline=blue,width=1);line([(x,10),(x,16)],fill=blue,width=2);line([(x-2,11),(x+2,11)],fill=blue,width=1);line([(x-1,16),(x-1,20)],fill=blue,width=1);line([(x+1,16),(x+1,20)],fill=blue,width=1)
    elif name=='parking':
        line([(8,20),(8,5),(13,5),(17,7),(17,11),(14,14),(8,14)],fill=blue,width=2)
    elif name=='rescue':
        poly([(10,5),(14,5),(14,10),(19,10),(19,14),(14,14),(14,19),(10,19),(10,14),(5,14),(5,10),(10,10)],fill='#9f403b',outline='#9f403b',width=1)
    return im.resize((24*ratio,24*ratio),Image.Resampling.LANCZOS)

def main():
    paths=[]
    for ratio,suffix in [(1,''),(2,'@2x')]:
        atlas=Image.new('RGBA',(96*ratio,72*ratio));index={}
        for i,name in enumerate(NAMES):
            x,y=(i%4)*24*ratio,(i//4)*24*ratio;atlas.paste(icon(name,ratio),(x,y))
            index['outdoor-'+name]={'x':x,'y':y,'width':24*ratio,'height':24*ratio,'pixelRatio':ratio}
        base=ROOT/'viewer/sprites'/('outdoors'+suffix)
        image=base.with_suffix('.png');atlas.save(image,compress_level=9)
        description=base.with_suffix('.json');description.write_text(json.dumps(index,indent=2,sort_keys=True)+'\n');paths.extend([image,description])
    lock={'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'pillow_version':PIL.__version__,'assets':[{'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]}
    (ROOT/'assets/sprites.lock.json').write_text(json.dumps(lock,indent=2)+'\n')
if __name__=='__main__':main()
