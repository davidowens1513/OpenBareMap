#!/usr/bin/env python3
"""Generate the conventional parking P on a blue square at 1x and 2x."""
import hashlib
import json
from pathlib import Path
import PIL
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[1]

def parking(ratio):
    scale=4*ratio
    image=Image.new('RGBA',(24*scale,24*scale));draw=ImageDraw.Draw(image)
    def box(values):return tuple(round(x*scale) for x in values)
    blue='#0057b8';white='#ffffff'
    draw.rectangle(box((2,2,22,22)),fill=blue)
    draw.rectangle(box((7,5,10,20)),fill=white)
    draw.rounded_rectangle(box((8,5,18,14)),radius=round(4*scale),fill=white)
    draw.rounded_rectangle(box((10,8,15,11)),radius=round(1.5*scale),fill=blue)
    return image.resize((24*ratio,24*ratio),Image.Resampling.LANCZOS)

def main():
    paths=[]
    for ratio,suffix in [(1,''),(2,'@2x')]:
        base=ROOT/'viewer/sprites'/('outdoors'+suffix)
        image=base.with_suffix('.png');parking(ratio).save(image,compress_level=9)
        description=base.with_suffix('.json')
        description.write_text(json.dumps({'outdoor-parking':{'x':0,'y':0,'width':24*ratio,'height':24*ratio,'pixelRatio':ratio}},indent=2,sort_keys=True)+'\n')
        paths.extend([image,description])
    lock={'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'pillow_version':PIL.__version__,'assets':[{'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]}
    (ROOT/'assets/sprites.lock.json').write_text(json.dumps(lock,indent=2)+'\n')
if __name__=='__main__':main()
