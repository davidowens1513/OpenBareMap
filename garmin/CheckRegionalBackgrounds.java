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
   case "alps-west" -> new double[][]{{4.90,45.65},{7.72,44.70},{8.952,46.004}};
   case "alps-central" -> new double[][]{{10.60,45.22},{8.95,47.60},{11.404,47.266}};
   case "alps-tyrol-bavaria" -> new double[][]{{9.90,47.86},{13.60,48.14},{11.1211,46.0679}};
   case "alps-east" -> new double[][]{{14.50,45.70},{16.61,48.10},{12.30,46.619}};
   case "us-yosemite" -> new double[][]{{-120.482,37.302},{-118.972,38.113}};
   case "us-great-smoky-mountains" -> new double[][]{{-83.921,35.961},{-83.204,35.318}};
   case "us-zion" -> new double[][]{{-113.584,37.097},{-112.526,37.048}};
   case "us-yellowstone-grand-teton" -> new double[][]{{-111.797,44.076},{-109.476,44.524}};
   case "us-grand-canyon" -> new double[][]{{-111.658,35.198},{-112.527,36.814}};
   case "us-rocky-mountain" -> new double[][]{{-105.084,40.585},{-105.508,39.938}};
   case "us-acadia" -> new double[][]{{-68.772,44.802},{-67.704,44.537}};
   case "us-olympic" -> new double[][]{{-122.444,47.251},{-123.001,47.956}};
   case "us-glacier" -> new double[][]{{-114.312,48.195},{-113.905,49.108}};
   case "picos-de-europa" -> new double[][]{{-5.67,43.36},{-4.12,43.37},{-4.84,42.69}};
   case "high-tatras" -> new double[][]{{19.47,49.20},{20.67,49.23},{20.14,49.61}};
   case "canadian-rockies-banff" -> new double[][]{{-114.06,51.05},{-118.08,52.87},{-113.90,49.05}};
   case "canadian-rockies-jasper" -> new double[][]{{-115.57,51.18},{-116.04,53.58},{-121.0,53.01}};
   case "canadian-rockies-kananaskis-waterton" -> new double[][]{{-113.98,48.91},{-116.18,51.43},{-114.06,51.05}};
   case "iceland-southern-highlands" -> new double[][]{{-21.94,64.15},{-17.96,64.06},{-19.49,63.27}};
   case "patagonia-torres-del-paine" -> new double[][]{{-72.89,-49.33},{-72.26,-50.34},{-73.03,-51.91}};
   case "patagonia-el-chalten" -> new double[][]{{-72.51,-51.73},{-73.09,-51.07},{-72.77,-48.75}};
   case "nepal-everest" -> new double[][]{{86.72,27.48},{87.06,27.84},{86.72,28.20}};
   case "nepal-annapurna" -> new double[][]{{83.36,28.65},{84.61,28.45},{83.94,29.02}};
   case "camino-frances" -> new double[][]{{-5.9,43.3},{-4.7,42.0},{-8.7,42.4}};
   case "cinque-terre" -> new double[][]{{9.06,44.35},{10.04,44.14},{9.45,44.53}};
   case "amalfi-bay-of-naples" -> new double[][]{{13.75,40.73},{14.90,40.67},{14.25,40.94}};
   case "cusco-inca-trail" -> new double[][]{{-72.75,-13.33},{-71.73,-13.52},{-72.23,-13.73}};
   case "kilimanjaro" -> new double[][]{{36.83,-3.18},{37.82,-3.28},{37.34,-3.52}};
   case "fiordland" -> new double[][]{{167.48,-45.42},{168.86,-45.03},{168.17,-44.47}};
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
