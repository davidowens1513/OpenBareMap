import java.nio.file.*;
import java.util.*;
import uk.me.parabola.imgfmt.app.map.MapReader;
import uk.me.parabola.imgfmt.app.trergn.*;
import uk.me.parabola.imgfmt.app.*;
import uk.me.parabola.imgfmt.sys.ImgFS;

/** Read-back checks for the separate transparent personal track layer. */
public class InspectTracks {
 static class Header extends TREHeader {int flags(){return getPoiDisplayFlags();}}
 public static void main(String[] args)throws Exception {
  Path folder=Path.of(args[0]);int starts=0,lines=0;
  try(MapReader r=new MapReader(folder.resolve("48320001.img").toString())) {
   for(Point p:r.pointsForLevel(0,true)) {
    if(p.getType()!=0x10007)throw new IllegalStateException("Unexpected point type");
    String name=p.getLabel()!=null?p.getLabel().getText():p.getPOIRecord()!=null&&p.getPOIRecord().getNameLabel()!=null?p.getPOIRecord().getNameLabel().getText():"";
    if(!name.isEmpty())throw new IllegalStateException("Unexpected start label: "+name);
    starts++;
   }
   for(Polyline l:r.linesForLevel(0)) {
    if(l.getType()!=0x10007)throw new IllegalStateException("Unexpected line type");
    if(l.getLabel()!=null&&!l.getLabel().getText().isEmpty())throw new IllegalStateException("Unexpected track label");lines++;
   }
   if(!r.shapesForLevel(0,true).isEmpty())throw new IllegalStateException("Track layer has opaque polygons");
  }
  if(starts!=355||lines==0)throw new IllegalStateException("Unexpected starts/lines: "+starts+"/"+lines);
  int priority=0;boolean transparent=false,typ=false;
  try(var fs=ImgFS.openFs(folder.resolve("gmapsupp.img").toString())) {
   for(var entry:fs.list()) {
    String ext=entry.getExt();if(ext.equals("NET")||ext.equals("NOD"))throw new IllegalStateException("Unexpected routing");
    if(ext.equals("TYP"))typ=true;
    if(ext.equals("TRE"))try(var channel=fs.open(entry.getFullName(),"r");var reader=new BufferedImgFileReader(channel)) {
     Header h=new Header();h.readHeader(reader);priority=h.getDisplayPriority();transparent=(h.flags()&TREHeader.POI_FLAG_TRANSPARENT)!=0;
    }
   }
  }
  if(!transparent||priority!=31||!typ)throw new IllegalStateException("Missing transparency, priority or symbols");
  System.out.println("{\"startMarkers\":"+starts+",\"namesRemoved\":true,\"encodedLinePieces\":"+lines+",\"transparent\":true,\"drawPriority\":"+priority+",\"routing\":false,\"customSymbols\":true}");
 }
}
