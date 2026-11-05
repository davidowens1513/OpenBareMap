"""Reject native split plans that omit the edition's geographic anchors."""
import re
from openbaremap import digest,write

def validate_split(path,profile):
    boxes=[];unit=360/(1<<24)
    for line in path.read_text().splitlines():
        match=re.fullmatch(r'(\d+):\s*(-?\d+),(-?\d+)\s+to\s+(-?\d+),(-?\d+)',line)
        if match:
            tile,south,west,north,east=map(int,match.groups())
            if south>=north or west>=east:raise ValueError('Invalid native split bounds')
            boxes.append((west*unit,south*unit,east*unit,north*unit))
    if not boxes:raise ValueError('No native split areas')
    checked=[]
    for name,xy in profile['destinations'].items():
        lon,lat=xy[:2]
        if not any(w<=lon<=e and s<=lat<=n for w,s,e,n in boxes):
            raise ValueError('Native split plan excludes '+name)
        checked.append(name)
    return {'areas':len(boxes),'anchorsCovered':checked,'areasSHA256':digest(path)}
