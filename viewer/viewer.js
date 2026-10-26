const status = document.getElementById('status');
const map = new maplibregl.Map({container:'map',style:'/style/openbaremap.json',bounds:[[-10.9,51.25],[-5.35,55.5]],fitBoundsOptions:{padding:innerWidth<600?{top:225,bottom:35,left:25,right:25}:{top:35,bottom:35,left:330,right:45}},minZoom:4,maxZoom:18,hash:true,renderWorldCopies:false,attributionControl:false});
window.referenceMap = map;
window.mapErrors = [];
map.addControl(new maplibregl.NavigationControl(), 'top-right');
map.addControl(new maplibregl.ScaleControl({unit:'metric'}), 'bottom-left');
map.addControl(new maplibregl.AttributionControl({compact:false}), 'bottom-right');
map.on('error', event => { const message=event.error?.message || 'Map loading error'; window.mapErrors.push(message); status.textContent=message; });
map.on('idle',()=>{ if(!window.mapErrors.length) status.textContent=`Local map · zoom ${map.getZoom().toFixed(1)} · ready`; });
const destinations={island:[-8.15,53.4,6.5],wicklow:[-6.32,53.04,12],kerry:[-9.54,52.00,12],donegal:[-8.11,55.03,12],belfast:[-5.93,54.60,12],dublin:[-6.26,53.35,12],aran:[-9.72,53.12,12]};
document.getElementById('location').addEventListener('change',event=>{const [lng,lat,zoom]=destinations[event.target.value];if(event.target.value==='island'){map.fitBounds([[-10.9,51.25],[-5.35,55.5]],{padding:innerWidth<600?{top:225,bottom:35,left:25,right:25}:{top:35,bottom:35,left:330,right:45}});}else{map.flyTo({center:[lng,lat],zoom,duration:1000});}});
map.on('click',event=>{const features=map.queryRenderedFeatures([[event.point.x-6,event.point.y-6],[event.point.x+6,event.point.y+6]]);if(!features.length)return;const feature=features.find(f=>['mountain','hiking_poi','hiking_route','natural_line'].includes(f.sourceLayer))||features.find(f=>f.layer.type!=='symbol')||features[0];const box=document.createElement('div');const title=document.createElement('strong');title.textContent=feature.properties.name_en||feature.properties.name||feature.properties.class||feature.sourceLayer;const details=document.createElement('pre');details.textContent=JSON.stringify({layer:feature.sourceLayer,...feature.properties},null,2);box.append(title,details);new maplibregl.Popup().setLngLat(event.lngLat).setDOMContent(box).addTo(map);});

// Legend swatches read the actual map paint values. MapLibre dash lengths are
// measured in line-width units, so SVG lengths must be multiplied by width.
function legendLineWidth(value, zoom) {
  if (typeof value === 'number') return value;
  if (Array.isArray(value) && value[0] === 'interpolate' && value[1][0] === 'linear' && value[2][0] === 'zoom') {
    if (zoom <= value[3]) return value[4];
    for (let i = 5; i < value.length; i += 2) {
      if (zoom <= value[i]) return value[i-1] + (value[i+1]-value[i-1])*(zoom-value[i-2])/(value[i]-value[i-2]);
    }
    return value[value.length-1];
  }
  throw new Error('Unsupported legend line-width expression');
}
function updateLineLegend() {
  for (const svg of document.querySelectorAll('[data-map-line]')) {
    const id = svg.dataset.mapLine;
    if (!map.getLayer(id)) continue;
    const width = legendLineWidth(map.getPaintProperty(id,'line-width') ?? 1,map.getZoom());
    const dash = map.getPaintProperty(id,'line-dasharray');
    const line = document.createElementNS('http://www.w3.org/2000/svg','line');
    for (const [key,value] of Object.entries({x1:0,x2:32,y1:6,y2:6,stroke:map.getPaintProperty(id,'line-color'),'stroke-width':width,'stroke-opacity':map.getPaintProperty(id,'line-opacity') ?? 1,'stroke-linecap':map.getLayoutProperty(id,'line-cap') ?? 'butt'})) line.setAttribute(key,String(value));
    if (dash) line.setAttribute('stroke-dasharray',dash.map(length => length*width).join(' '));
    svg.replaceChildren(line);
  }
}
map.on('load',updateLineLegend);
map.on('zoomend',updateLineLegend);

// Resolve the current categorical land-cover colours instead of copying hex codes.
function updateFillLegend() {
  for (const swatch of document.querySelectorAll('[data-map-fill]')) {
    const id = swatch.dataset.mapFill;
    let colour = map.getPaintProperty(id, 'fill-color');
    if (Array.isArray(colour) && colour[0] === 'match') {
      const category = swatch.dataset.mapClass;
      let selected = colour[colour.length - 1];
      for (let i = 2; i < colour.length - 1; i += 2) {
        if (colour[i] === category) { selected = colour[i + 1]; break; }
      }
      colour = selected;
    }
    swatch.style.backgroundColor = colour;
    swatch.style.opacity = map.getPaintProperty(id, 'fill-opacity') ?? 1;
  }
}
map.on('load', updateFillLegend);
map.on('styledata', () => { if (map.isStyleLoaded()) updateFillLegend(); });
