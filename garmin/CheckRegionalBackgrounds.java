import java.awt.geom.Path2D;
import java.util.*;
import uk.me.parabola.imgfmt.sys.ImgFS;
import uk.me.parabola.imgfmt.fs.ImgChannel;
import uk.me.parabola.imgfmt.app.trergn.*;
import uk.me.parabola.imgfmt.app.lbl.LBLFileReader;

/** Inspect the installable binary, including every native detail level. */
public class CheckRegionalBackgrounds {
 static class Reader extends TREFileReader {
  Reader(ImgChannel channel) { super(channel); }
  TREHeader header() { return (TREHeader)getHeader(); }
 }
 public static void main(String[] args) throws Exception {
  if(args.length!=2)throw new IllegalArgumentException("region image");
  double[][] excluded=switch(args[0]) {
   case "england-wales" -> new double[][]{{-6.2603,53.3493},{-5.93,54.60}};
   case "ireland" -> new double[][]{{-5.606,55.426},{-3.179,51.482},{-3.188,55.953}};
   case "scotland" -> new double[][]{{-5.93,54.60},{-6.2603,53.3493},{-.128,51.507}};
   case "sierra-nevada" -> new double[][]{{-3.8,37.4},{-2.7,37.4},{-3.7038,40.4168},{-4.4214,36.7213}};
   case "pyrenees" -> new double[][]{{-3.7038,40.4168},{2.3522,48.8566},{-2.3,43.0},{0.0,44.0},{3.5,42.5}};
   case "dolomites" -> new double[][]{{9.19,45.46},{12.5,41.9},{10.4,46.3},{13.4,46.3},{11.8,47.3}};
   default -> throw new IllegalArgumentException(args[0]);
  };
  int tiles=0,polygons=0;Set<Integer> resolutions=new TreeSet<>();
  var flagsMethod=TREHeader.class.getDeclaredMethod("getPoiDisplayFlags");flagsMethod.setAccessible(true);
  try(var fs=ImgFS.openFs(args[1])) {
   for(var e:fs.list())if(e.getExt().equals("TRE")) {
    tiles++;
    try(var tc=fs.open(e.getFullName(),"r");var rc=fs.open(e.getName()+".RGN","r");var lc=fs.open(e.getName()+".LBL","r")) {
     var tre=new Reader(tc);var header=tre.header();
     int flags=(int)flagsMethod.invoke(header);
     if((flags&TREHeader.POI_FLAG_TRANSPARENT)==0||header.getDisplayPriority()!=25)
      throw new IllegalStateException("Wrong transparency/priority: "+e.getName());
     var rgn=new RGNFileReader(rc);rgn.setLblFile(new LBLFileReader(lc));
     for(var zoom:tre.getMapLevels())if(zoom.getResolution()>=16) {
      resolutions.add(zoom.getResolution());
      for(var sub:tre.subdivForLevel(zoom.getLevel()))for(var polygon:rgn.shapesForSubdiv(sub,true)) {
       int type=polygon.getType();polygons++;
       if(type==0x4b)throw new IllegalStateException("Automatic rectangular background: "+e.getName());
       if(type!=0x32&&type!=0x54)continue;
       var path=new Path2D.Double(Path2D.WIND_EVEN_ODD);boolean first=true;
       for(var c:polygon.getPoints()) {
        if(first){path.moveTo(c.getLonDegrees(),c.getLatDegrees());first=false;}
        else path.lineTo(c.getLonDegrees(),c.getLatDegrees());
       }
       path.closePath();
       for(var xy:excluded)if(path.contains(xy[0],xy[1]))
        throw new IllegalStateException("Foreign background at "+Arrays.toString(xy)+", resolution "+zoom.getResolution()+", tile "+e.getName());
      }
     }
    }
   }
  }
  if(tiles==0||!resolutions.equals(Set.of(16,18,20,22,23,24)))throw new IllegalStateException("Missing tiles/detail levels");
  System.out.println("PASS: "+args[0]+"; "+tiles+" transparent sections at priority 25; "+polygons+" polygons checked across "+resolutions+"; no rectangular filler or backgrounds at foreign-region reference points.");
 }
}
