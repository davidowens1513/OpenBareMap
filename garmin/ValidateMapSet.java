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
 static final String[] NAMES={"London","Cardiff","Newcastle","Dartmoor","Snowdonia","Peak District","Anglesey","Isle of Wight","St Marys Scilly","Shrewsbury","Whitchurch","Wem","Bangor","Tywyn","Newtown","Hereford","Douglas","Snaefell","Peel","Calf of Man","Ramsey","Port Erin"};
 static final double[][] XY={{-.128,51.507},{-3.179,51.482},{-1.617,54.978},{-3.94,50.58},{-4.076,53.068},{-1.837,53.35},{-4.35,53.28},{-1.30,50.67},{-6.3113,49.9140},{-2.754,52.707},{-2.683,52.970},{-2.720,52.858},{-4.128,53.228},{-4.089,52.585},{-3.317,52.516},{-2.715,52.056},{-4.48,54.15},{-4.462,54.263},{-4.69,54.223},{-4.825,54.055},{-4.39,54.32},{-4.65,54.074}};
 public static void main(String[] args)throws Exception {
  Set<String> identities=new HashSet<>(),tiles=new HashSet<>(),types=new HashSet<>();int total=0,checked=0;
  for(String file:args)try(var fs=ImgFS.openFs(file)) {
   boolean ireland=false,ew=false,scotland=false,sierra=false,pyrenees=false,dolomites=false,faroe=false;int count=0;Set<Integer> families=new HashSet<>();
   for(var e:fs.list())if(e.getExt().equals("MPS"))try(var ch=fs.open(e.getFullName(),"r");var mps=new MpsFileReader(ch,1252)){
    for(var p:mps.getProducts()){String key=p.getFamilyId()+":"+p.getProductId();if(!identities.add(key))throw new IllegalStateException("Duplicate family/product "+key+" in "+file);families.add(p.getFamilyId());if(p.getDescription().contains("Ireland"))ireland=true;if(p.getDescription().contains("England"))ew=true;if(p.getDescription().contains("Scotland"))scotland=true;if(p.getDescription().contains("Sierra Nevada"))sierra=true;if(p.getDescription().contains("Pyrenees"))pyrenees=true;if(p.getDescription().contains("Dolomites"))dolomites=true;if(p.getDescription().contains("Faroe Islands"))faroe=true;}
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
      if((ew||scotland||sierra||pyrenees||dolomites||faroe)&&header.getInt(43)<=0)throw new IllegalStateException("England/Wales appearance file has no polygon palette");
      System.out.println(e.getFullName()+": family="+family+", product="+product+", polygonPaletteBytes="+header.getInt(43));
     }
    }
   }
   if(count==0||families.isEmpty())throw new IllegalStateException("Missing map metadata");
   for(int family:families)if(count!=Integer.getInteger("openbaremap.tiles."+family,count))throw new IllegalStateException("Compiled section count mismatch for family "+family);
   total+=count;
   if(ireland||ew||scotland||sierra||pyrenees||dolomites||faroe){
    String[] names=faroe?new String[]{"Streymoy","Eysturoy","Vágar","Suðuroy","Sandoy","Borðoy","Viðoy","Kalsoy","Svínoy","Fugloy","Kunoy","Mykines","Nólsoy","Skúgvoy","Hestur","Stóra Dímun","Koltur","Lítla Dímun"}:dolomites?new String[]{"Cortina","Brenta","Marmolada","Tre Cime","Val Gardena","Pale di San Martino","Friulian Dolomites","Bolzano","Trento","Belluno","Bressanone","Lienz"}:pyrenees?new String[]{"Bayonne","Hendaye","Pau","Pamplona","Jaca","Gavarnie","Aneto","Andorra","Perpignan","Girona","Cap de Creus"}:ireland?new String[]{"Dublin","Belfast","Cork","Malin Head","Tory Island","Aran Islands","Great Blasket"}:sierra?new String[]{"Granada","Mulhacen","Veleta","Capileira","Trevelez","Puerto de la Ragua","Guadix","Durcal","Orgiva","Fondon","Finana"}:scotland?new String[]{"Edinburgh","Glasgow","Inverness","Ben Nevis","Skye","Lewis","Orkney","Shetland","Unst","Borders","St Kilda"}:NAMES;
    double[][] xy=faroe?new double[][]{{-7.015882816156839,62.1237192},{-6.817845062972005,62.198870400000004},{-7.234584100845196,62.089898500000004},{-6.814186643797399,61.52106515},{-6.723989940433405,61.8333877},{-6.519960153215357,62.263797350000004},{-6.522562763215868,62.33562725},{-6.742989818875409,62.2981508},{-6.370266050279082,62.269355399999995},{-6.295083714926933,62.335528749999995},{-6.659841603548006,62.308899999999994},{-7.604653567580989,62.1045075},{-6.653136725815699,61.9854463},{-6.826961985197521,61.76644315},{-6.8906230651131,61.95078735},{-6.756602847705695,61.694632600000006},{-6.974831795485134,61.9874722},{-6.710878974728262,61.6332145}}:dolomites?new double[][]{{12.1357,46.5405},{10.89,46.17},{11.862,46.435},{12.3,46.619},{11.756,46.557},{11.85,46.28},{12.58,46.32},{11.3548,46.4983},{11.1211,46.0679},{12.2176,46.1391},{11.657,46.7167},{12.769,46.828}}:pyrenees?new double[][]{{-1.4748,43.4929},{-1.773,43.358},{-.3708,43.2951},{-1.6432,42.8125},{-.5499,42.571},{-.0105,42.732},{.6579,42.631},{1.5218,42.5063},{2.8954,42.6986},{2.8214,41.9794},{3.316,42.319}}:ireland?new double[][]{{-6.2603,53.3493},{-5.93,54.6},{-8.47,51.9},{-7.346887,55.369966},{-8.237640,55.264257},{-9.758652,53.128403},{-10.533848,52.095386}}:sierra?new double[][]{{-3.5986,37.1765},{-3.3114,37.0547},{-3.3656,37.0504},{-3.358,36.961},{-3.265,37.002},{-3.031,37.114},{-3.14,37.30},{-3.56,36.99},{-3.42,36.902},{-2.86,36.981},{-2.84,37.17}}:scotland?new double[][]{{-3.188,55.953},{-4.252,55.86},{-4.224,57.478},{-5.004,56.796},{-6.2,57.3},{-6.38,58.21},{-2.96,58.98},{-1.25,60.3},{-.84,60.75},{-2.45,55.6},{-8.58,57.814}}:XY;
    int family=faroe?4838:dolomites?4837:pyrenees?4836:ireland?4831:sierra?4835:scotland?4834:4833;
    if(!families.equals(Set.of(family)))throw new IllegalStateException("Unexpected regional family "+families);
    if(scotland&&count!=Integer.getInteger("openbaremap.scotland.tiles",count))throw new IllegalStateException("Scotland sections missing from installable image");
    if(ew&&count!=Integer.getInteger("openbaremap.england-wales.tiles",count))throw new IllegalStateException("England/Wales sections missing");
    int levelCount=0;
    for(var entry:fs.list())if(entry.getExt().equals("TRE")){
     try(var channel=fs.open(entry.getFullName(),"r")){
      for(var zoom:new TREFileReader(channel).getMapLevels())if(zoom.getResolution()>=16)levelCount=Math.max(levelCount,zoom.getLevel()+1);
     }break;
    }
    if(levelCount<5)throw new IllegalStateException("Missing native detail levels");
    boolean[][] hits=new boolean[levelCount][xy.length];int[] land=new int[levelCount];boolean rockallCovered=false;
    for(var e:fs.list())if(e.getExt().equals("TRE")){
     String name=e.getName();if(Integer.parseInt(name)<family*10000+1||Integer.parseInt(name)>(family*10000+9999))throw new IllegalStateException("Unreserved England/Wales tile "+name);
     try(var tc=fs.open(e.getFullName(),"r");var rc=fs.open(name+".RGN","r");var lc=fs.open(name+".LBL","r")){
      var tre=new TREFileReader(tc);var rgn=new RGNFileReader(rc);rgn.setLblFile(new LBLFileReader(lc));
      for(var z:tre.getMapLevels())if(z.getResolution()>=16)for(var sub:tre.subdivForLevel(z.getLevel()))for(var poly:rgn.shapesForSubdiv(sub,false))if(poly.getType()==0x54){
       int level=z.getLevel();land[level]++;Path2D.Double path=new Path2D.Double();boolean first=true;
       for(var c:poly.getPoints()){if(first){path.moveTo(c.getLonDegrees(),c.getLatDegrees());first=false;}else path.lineTo(c.getLonDegrees(),c.getLatDegrees());}path.closePath();
       for(int i=0;i<xy.length;i++){
        boolean covered=path.contains(xy[i][0],xy[i][1]);
        // At the two coarsest Faroe detail levels, coordinates are quantized
        // by hundreds of metres. Require the island within half a grid cell;
        // this cannot be supplied by its distant neighbouring islands.
        if(faroe&&z.getResolution()<=18){double cell=360.0/(1L<<z.getResolution());covered|=path.intersects(xy[i][0]-cell/2,xy[i][1]-cell/2,cell,cell);}
        if(covered)hits[level][i]=true;
       }
       if(scotland&&level==0&&path.contains(-13.687237,57.5962764))rockallCovered=true;
      }
     }
    }
    if(scotland&&!rockallCovered)throw new IllegalStateException("Rockall land missing at highest detail");
    if(scotland)System.out.println("Rockall land verified at highest detail");
    for(int level=0;level<levelCount;level++){
     if(land[level]==0)throw new IllegalStateException("No land at level "+level);
     for(int i=0;i<xy.length;i++)if(!hits[level][i])throw new IllegalStateException("Missing land at "+names[i]+", level "+level);
    }
    checked+=levelCount*xy.length;System.out.println((faroe?"Faroe Islands":dolomites?"Dolomites":pyrenees?"Pyrenees":ireland?"Ireland":sierra?"Sierra Nevada":scotland?"Scotland":"England/Wales")+" land polygons by level: "+Arrays.toString(land));
   }
  }
  System.out.println("PASS: "+args.length+" map files; "+total+" unique sections; unique product and appearance identities; "+checked+" regional land checks.");
 }
}
