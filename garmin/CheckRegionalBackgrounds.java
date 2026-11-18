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
   case "faroe-islands" -> new double[][]{{-3.188,55.953},{-1.25,60.3},{-21.94,64.15},{5.32,60.39},{-8.1,62.0},{-5.9,62.0}};
   case "norway-south" -> new double[][]{{18.06,59.33},{25.784,71.1725},{15.65,78.22}};
   case "norway-central" -> new double[][]{{10.7522,59.9139},{18.9553,69.6492},{15.65,78.22}};
   case "norway-north" -> new double[][]{{10.3951,63.4305},{24.94,60.17},{15.65,78.22}};
   case "balearic-islands" -> new double[][]{{-0.376,39.47},{2.173,41.385},{8.738,41.926}};
   case "corsica" -> new double[][]{{9.413,41.219},{9.33,40.32},{10.31,42.81}};
   case "sardinia" -> new double[][]{{9.16,41.39},{9.151,42.304},{13.36,38.12}};
   case "sicily" -> new double[][]{{15.65,38.11},{14.51,35.90},{10.18,36.81}};
   case "crete" -> new double[][]{{25.43,36.42},{22.95,36.15},{26.92,35.42}};
   case "cyprus" -> new double[][]{{32.50,36.08},{35.10,35.93},{34.62,33.89}};
   case "malta" -> new double[][]{{14.81,36.73},{12.60,35.50},{12.87,35.86}};
   case "canary-islands" -> new double[][]{{-16.909,32.650},{-15.872,30.144},{-13.20,27.66}};
   case "madeira" -> new double[][]{{-16.60,28.31},{-15.59,27.97},{-13.61,29.03}};
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
