#!/usr/bin/env python3
"""Assemble terrain textures, a periodic cliff pattern and conventional parking P."""
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

def cliff_teeth(ratio):
    """Four identical teeth in a 16 x 6 logical-pixel periodic cell.

    Both atlas resolutions have power-of-two widths (64/128 pixels).
    Draw beyond either edge before cropping so antialiasing wraps seamlessly.
    """
    density=4*ratio
    supersample=4
    scale=density*supersample
    image=Image.new('RGBA',(48*scale,6*scale))
    draw=ImageDraw.Draw(image)
    points=[(x*scale,(2 if x%4==0 else 4)*scale) for x in range(0,49,2)]
    draw.line(points,fill='#5f584f',width=scale,joint='curve')
    image=image.crop((16*scale,0,32*scale,6*scale))
    return image.resize((16*density,6*density),Image.Resampling.LANCZOS)

def main():
    paths=[]
    for ratio,suffix in [(1,''),(2,'@2x')]:
        base=ROOT/'viewer/sprites'/('outdoors'+suffix)
        legacy=ROOT/'assets/legacy-1.1/sprites/baregps-bog27'
        original=Image.open(legacy.with_suffix('.png')).convert('RGBA')
        atlas=Image.new('RGBA',((original.width+24+64)*ratio,original.height*ratio))
        atlas.paste(original.resize((original.width*ratio,original.height*ratio),Image.Resampling.NEAREST),(0,0))
        atlas.paste(parking(ratio),(original.width*ratio,0))
        atlas.paste(cliff_teeth(ratio),((original.width+24)*ratio,0))
        image=base.with_suffix('.png');atlas.save(image,compress_level=9)
        index=json.loads(legacy.with_suffix('.json').read_text())
        for item in index.values():
            for key in ['x','y','width','height','pixelRatio']:item[key]*=ratio
        index['cliff-teeth']={'x':(original.width+24)*ratio,'y':0,'width':64*ratio,'height':24*ratio,'pixelRatio':4*ratio}
        index['outdoor-parking']={'x':original.width*ratio,'y':0,'width':24*ratio,'height':24*ratio,'pixelRatio':ratio}
        description=base.with_suffix('.json')
        description.write_text(json.dumps(index,indent=2,sort_keys=True)+'\n')
        paths.extend([image,description])
    lock={'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'pillow_version':PIL.__version__,'assets':[{'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]}
    (ROOT/'assets/sprites.lock.json').write_text(json.dumps(lock,indent=2)+'\n')
if __name__=='__main__':main()
