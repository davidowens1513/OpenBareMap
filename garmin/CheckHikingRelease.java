import java.nio.file.*;
import java.util.*;
import uk.me.parabola.imgfmt.app.map.MapReader;

/** Read actual compiled levels: buildings closest only, contours retained between. */
public class CheckHikingRelease {
 public static void main(String[] args)throws Exception {
  Set<Integer> hiking=Set.of(0xa,0x16,0x10001,0x10002,0x10003,0x10004,0x10005,0x1000b);
  Set<Integer> required=Set.of(0xa,0x16,0x10001,0x10002,0x10004,0x10005,0x1000b);
  Map<Integer,Map<Integer,Long>> lines=new TreeMap<>(Comparator.reverseOrder());
  Map<Integer,Long> buildings=new TreeMap<>(),land=new TreeMap<>(),contours=new TreeMap<>();
  try(var paths=Files.list(Path.of(args[0]))){
   for(var p:paths.filter(p->p.getFileName().toString().matches("[0-9]{8}\\.img")).toList()){
    try(var map=new MapReader(p.toString())){
     for(var zoom:map.getLevels()){
      if(zoom.getLevel()>5)continue;
      int bits=zoom.getResolution();var counts=lines.computeIfAbsent(bits,k->new TreeMap<>());
      for(var line:map.linesForLevel(zoom.getLevel())){
       if(hiking.contains(line.getType()))counts.merge(line.getType(),1L,Long::sum);
       if(line.getType()==0x20)contours.merge(bits,1L,Long::sum);
      }
      for(var poly:map.shapesForLevel(zoom.getLevel(),false)){
       if(poly.getType()==0x13)buildings.merge(bits,1L,Long::sum);
       if(poly.getType()==0x54)land.merge(bits,1L,Long::sum);
      }
     }
    }
   }
  }
  if(!lines.keySet().equals(Set.of(24,23,22,20,18,16)))throw new IllegalStateException("Missing map level "+lines.keySet());
  for(int bits:lines.keySet()){
   if(bits>=24){for(int type:required)if((lines.get(bits).getOrDefault(type,0L)>0)!=true)throw new IllegalStateException("Incorrect hiking line threshold at resolution "+bits);}
   else if(!lines.get(bits).isEmpty())throw new IllegalStateException("Hiking clutter in overview");
   if((buildings.getOrDefault(bits,0L)>0)!=(bits==24))throw new IllegalStateException("Incorrect building threshold at "+bits);
   if(bits>=23&&contours.getOrDefault(bits,0L)==0)throw new IllegalStateException("Fine contour detail missing at "+bits);
   if(land.getOrDefault(bits,0L)==0)throw new IllegalStateException("Missing land at "+bits);
   System.out.println("Resolution "+bits+": buildings="+buildings.getOrDefault(bits,0L)+", fineContours="+contours.getOrDefault(bits,0L)+", hiking="+lines.get(bits));
  }
  System.out.println("PASS: six native detail levels; buildings only at 24; existing fine contour detail carried into 23; paths, tracks, walking/cycling routes, bridleways, cycleways and steps only at resolution 24; all absent at every lower-resolution level.");
 }
}
