import java.awt.geom.Path2D;
import uk.me.parabola.imgfmt.app.map.MapReader;
/** Assert that a known land coordinate survives every configured content level. */
public class ProbeLand {
 public static void main(String[] args)throws Exception{
  double lon=Double.parseDouble(args[1]),lat=Double.parseDouble(args[2]);
  try(var reader=new MapReader(args[0])){
   for(int level=0;level<5;level++){
    boolean found=false;
    for(var poly:reader.shapesForLevel(level,false))if(poly.getType()==0x54){
     var path=new Path2D.Double();boolean first=true;
     for(var p:poly.getPoints()){if(first){path.moveTo(p.getLonDegrees(),p.getLatDegrees());first=false;}else path.lineTo(p.getLonDegrees(),p.getLatDegrees());}path.closePath();
     if(path.contains(lon,lat))found=true;
    }
    if(!found)throw new IllegalStateException("Land missing at level "+level);
   }
  }
 }
}
