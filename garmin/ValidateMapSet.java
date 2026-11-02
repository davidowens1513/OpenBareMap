import java.awt.geom.Path2D;
import java.nio.file.*;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.*;
import uk.me.parabola.imgfmt.sys.ImgFS;
import uk.me.parabola.imgfmt.mps.*;
import uk.me.parabola.imgfmt.app.trergn.*;
import uk.me.parabola.imgfmt.app.lbl.LBLFileReader;

/** Reject collisions across the actual installable binaries and missing low-detail land. */
public class ValidateMapSet {
 static final String[] NAMES={"London","Cardiff","Newcastle","Dartmoor","Snowdonia","Peak District","Anglesey","Isle of Wight","St Marys Scilly","Shrewsbury","Whitchurch","Wem","Bangor","Tywyn","Newtown","Hereford"};
 static final double[][] XY={{-.128,51.507},{-3.179,51.482},{-1.617,54.978},{-3.94,50.58},{-4.076,53.068},{-1.837,53.35},{-4.35,53.28},{-1.30,50.67},{-6.3113,49.9140},{-2.754,52.707},{-2.683,52.970},{-2.720,52.858},{-4.128,53.228},{-4.089,52.585},{-3.317,52.516},{-2.715,52.056}};
 public static void main(String[] args)throws Exception {
  Set<String> identities=new HashSet<>(),tiles=new HashSet<>(),types=new HashSet<>();int total=0,checked=0;
  for(String file:args)try(var fs=ImgFS.openFs(file)) {
   boolean ew=false,scotland=false,sierra=false;int count=0;Set<Integer> families=new HashSet<>();
   for(var e:fs.list())if(e.getExt().equals("MPS"))try(var ch=fs.open(e.getFullName(),"r");var mps=new MpsFileReader(ch,1252)){
    for(var p:mps.getProducts()){String key=p.getFamilyId()+":"+p.getProductId();if(!identities.add(key))throw new IllegalStateException("Duplicate family/product "+key+" in "+file);families.add(p.getFamilyId());if(p.getDescription().contains("England"))ew=true;if(p.getDescription().contains("Scotland"))scotland=true;if(p.getDescription().contains("Sierra Nevada"))sierra=true;}
    for(var m:mps.getMaps())if(!families.contains(m.getFamilyId()))throw new IllegalStateException("Map has wrong family");
   }
   for(var e:fs.list()){
    if(e.getExt().equals("TRE")){if(!tiles.add(e.getName()))throw new IllegalStateException("Duplicate tile "+e.getName());count++;}
    if(e.getExt().equals("TYP")){
     if(!types.add(e.getFullName()))throw new IllegalStateException("Duplicate appearance file "+e.getFullName());
     try(var channel=fs.open(e.getFullName(),"r")){
      // In the pinned TYP header: common header/code page + three 8-byte data sections.
      ByteBuffer header=ByteBuffer.allocate(51).order(ByteOrder.LITTLE_ENDIAN);
      while(header.hasRemaining())if(channel.read(header)<=0)throw new IllegalStateException("Truncated TYP header");
      int family=Short.toUnsignedInt(header.getShort(47)),product=Short.toUnsignedInt(header.getShort(49));
      if(!families.contains(family)||product!=1)throw new IllegalStateException("Appearance file belongs to wrong product");
      if((ew||scotland||sierra)&&header.getInt(43)<=0)throw new IllegalStateException("England/Wales appearance file has no polygon palette");
      System.out.println(e.getFullName()+": family="+family+", product="+product+", polygonPaletteBytes="+header.getInt(43));
     }
    }
   }
   if(count==0||families.isEmpty())throw new IllegalStateException("Missing map metadata");total+=count;
   if(ew||scotland||sierra){
    String[] names=sierra?new String[]{"Granada","Mulhacen","Veleta","Capileira","Trevelez","Puerto de la Ragua","Guadix","Durcal","Orgiva","Fondon","Finana"}:scotland?new String[]{"Edinburgh","Glasgow","Inverness","Ben Nevis","Skye","Lewis","Orkney","Shetland","Unst","Borders","St Kilda"}:NAMES;
    double[][] xy=sierra?new double[][]{{-3.5986,37.1765},{-3.3114,37.0547},{-3.3656,37.0504},{-3.358,36.961},{-3.265,37.002},{-3.031,37.114},{-3.14,37.30},{-3.56,36.99},{-3.42,36.902},{-2.86,36.981},{-2.84,37.17}}:scotland?new double[][]{{-3.188,55.953},{-4.252,55.86},{-4.224,57.478},{-5.004,56.796},{-6.2,57.3},{-6.38,58.21},{-2.96,58.98},{-1.25,60.3},{-.84,60.75},{-2.45,55.6},{-8.58,57.814}}:XY;
    int family=sierra?4835:scotland?4834:4833;
    if(!families.equals(Set.of(family)))throw new IllegalStateException("Unexpected regional family "+families);
    if(scotland&&count!=Integer.getInteger("openbaremap.scotland.tiles",count))throw new IllegalStateException("Scotland sections missing from installable image");
    if(ew&&count!=318)throw new IllegalStateException("England/Wales sections missing");
    boolean[][] hits=new boolean[5][xy.length];int[] land=new int[5];boolean rockallCovered=false;
    for(var e:fs.list())if(e.getExt().equals("TRE")){
     String name=e.getName();if(Integer.parseInt(name)<family*10000+1||Integer.parseInt(name)>(sierra?48359999:scotland?48349999:48330318))throw new IllegalStateException("Unreserved England/Wales tile "+name);
     try(var tc=fs.open(e.getFullName(),"r");var rc=fs.open(name+".RGN","r");var lc=fs.open(name+".LBL","r")){
      var tre=new TREFileReader(tc);var rgn=new RGNFileReader(rc);rgn.setLblFile(new LBLFileReader(lc));
      for(var z:tre.getMapLevels())if(z.getLevel()<=4)for(var sub:tre.subdivForLevel(z.getLevel()))for(var poly:rgn.shapesForSubdiv(sub,false))if(poly.getType()==0x54){
       int level=z.getLevel();land[level]++;Path2D.Double path=new Path2D.Double();boolean first=true;
       for(var c:poly.getPoints()){if(first){path.moveTo(c.getLonDegrees(),c.getLatDegrees());first=false;}else path.lineTo(c.getLonDegrees(),c.getLatDegrees());}path.closePath();
       for(int i=0;i<xy.length;i++)if(path.contains(xy[i][0],xy[i][1]))hits[level][i]=true;
       if(scotland&&level==0&&path.contains(-13.687237,57.5962764))rockallCovered=true;
      }
     }
    }
    if(scotland&&!rockallCovered)throw new IllegalStateException("Rockall land missing at highest detail");
    if(scotland)System.out.println("Rockall land verified at highest detail");
    for(int level=0;level<5;level++){
     if(land[level]==0)throw new IllegalStateException("No land at level "+level);
     for(int i=0;i<xy.length;i++)if(!hits[level][i])throw new IllegalStateException("Missing land at "+names[i]+", level "+level);
    }
    checked+=5*xy.length;System.out.println((sierra?"Sierra Nevada":scotland?"Scotland":"England/Wales")+" land polygons by level: "+Arrays.toString(land));
   }
  }
  System.out.println("PASS: "+args.length+" map files; "+total+" unique sections; unique product and appearance identities; "+checked+" regional land checks.");
 }
}
