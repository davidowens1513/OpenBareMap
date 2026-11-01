const viewport=document.getElementById('legend-viewport');
const canvas=document.getElementById('legend-canvas');
const image=document.getElementById('legend-image');
const output=document.getElementById('zoom-level');
const plus=document.getElementById('zoom-in'),minus=document.getElementById('zoom-out');
let scale=1,mode='width',drag=null;
const baseWidth=()=>image.naturalWidth/2,baseHeight=()=>image.naturalHeight/2;
function setZoom(next,keepCentre=true){
  if(!image.naturalWidth)return;
  const x=(viewport.scrollLeft+viewport.clientWidth/2-image.offsetLeft)/(baseWidth()*scale);
  const y=(viewport.scrollTop+viewport.clientHeight/2-image.offsetTop)/(baseHeight()*scale);
  scale=Math.max(.1,Math.min(4,next));
  image.style.width=baseWidth()*scale+'px';
  canvas.style.width=Math.max(viewport.clientWidth,baseWidth()*scale+48)+'px';
  canvas.style.height=Math.max(viewport.clientHeight,baseHeight()*scale+48)+'px';
  if(keepCentre){viewport.scrollLeft=image.offsetLeft+x*baseWidth()*scale-viewport.clientWidth/2;viewport.scrollTop=image.offsetTop+y*baseHeight()*scale-viewport.clientHeight/2;}
  else{viewport.scrollLeft=0;viewport.scrollTop=0;}
  output.value=Math.round(scale*100)+'%';plus.disabled=scale>=4;minus.disabled=scale<=.1;
}
function fit(kind){mode=kind;setZoom(Math.min(1,(viewport.clientWidth-48)/baseWidth(),kind==='page'?(viewport.clientHeight-48)/baseHeight():Infinity),false);}
plus.addEventListener('click',()=>{mode=null;setZoom(scale*1.25)});
minus.addEventListener('click',()=>{mode=null;setZoom(scale/1.25)});
document.getElementById('fit-page').addEventListener('click',()=>fit('page'));
document.getElementById('actual-size').addEventListener('click',()=>{mode=null;setZoom(1)});
viewport.addEventListener('keydown',e=>{if(e.ctrlKey||e.metaKey||e.altKey)return;if(['+','=','-','0'].includes(e.key)){e.preventDefault();if(e.key==='-')minus.click();else if(e.key==='0')document.getElementById('actual-size').click();else plus.click();}});
viewport.addEventListener('pointerdown',e=>{if(e.pointerType!=='mouse'||e.button!==0)return;drag={x:e.clientX,y:e.clientY,left:viewport.scrollLeft,top:viewport.scrollTop};viewport.setPointerCapture(e.pointerId);viewport.classList.add('dragging');e.preventDefault();});
viewport.addEventListener('pointermove',e=>{if(drag){viewport.scrollLeft=drag.left+drag.x-e.clientX;viewport.scrollTop=drag.top+drag.y-e.clientY;}});
function release(){drag=null;viewport.classList.remove('dragging');}
viewport.addEventListener('pointerup',release);viewport.addEventListener('pointercancel',release);viewport.addEventListener('lostpointercapture',release);
window.addEventListener('resize',()=>{if(mode)fit(mode);else setZoom(scale)});
if(image.complete&&image.naturalWidth)fit('width');else image.addEventListener('load',()=>fit('width'),{once:true});
