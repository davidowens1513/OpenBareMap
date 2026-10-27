import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;
import uk.me.parabola.imgfmt.sys.ImgFS;
import uk.me.parabola.imgfmt.fs.*;
import uk.me.parabola.imgfmt.app.map.MapReader;
import uk.me.parabola.imgfmt.app.trergn.*;

/** Read the compiled Garmin filesystem and feature records; never modifies output. */
public class InspectMap {
    static String quote(String s) { return "\""+s.replace("\\","\\\\").replace("\"","\\\"").replace("\n","\\n").replace("\r","\\r")+"\""; }
    static String mapJson(Map<String,? extends Number> m) { StringJoiner j=new StringJoiner(",","{","}");m.forEach((k,v)->j.add(quote(k)+":"+v));return j.toString(); }
    static void count(Map<String,Long> map,int type) { map.merge(String.format("0x%x",type),1L,Long::sum); }
    static String logicalHash(Path file,Map<String,Long> sizes) throws Exception {
        MessageDigest digest=MessageDigest.getInstance("SHA-256");
        try (uk.me.parabola.imgfmt.fs.FileSystem fs=ImgFS.openFs(file.toString())) {
            List<DirectoryEntry> entries=new ArrayList<>(fs.list());entries.sort(Comparator.comparing(DirectoryEntry::getFullName));
            for (DirectoryEntry entry:entries) {
                if (entry.isSpecial()) continue;
                String name=entry.getFullName();sizes.merge(entry.getExt(),(long)entry.getSize(),Long::sum);
                digest.update(name.getBytes(StandardCharsets.UTF_8));digest.update(ByteBuffer.allocate(8).putLong(entry.getSize()).array());
                try (ImgChannel in=fs.open(name,"r")) {
                    byte[] bytes=new byte[65536];int offset=0,remaining=entry.getSize();
                    while(remaining>0) {
                        ByteBuffer buffer=ByteBuffer.wrap(bytes,0,Math.min(bytes.length,remaining));int n=in.read(buffer);
                        if(n<=0)throw new IllegalStateException("Truncated Garmin subfile: "+name);
                        // All CommonHeader creation timestamps occupy bytes 14..20.
                        if(Set.of("TRE","RGN","LBL","DEM","TYP","NET","NOD").contains(entry.getExt()))
                            for(int i=Math.max(0,14-offset);i<Math.min(n,21-offset);i++)bytes[i]=0;
                        digest.update(bytes,0,n);offset+=n;remaining-=n;
                    }
                }
            }
        }
        return HexFormat.of().formatHex(digest.digest());
    }
    public static void main(String[] args) throws Exception {
        Path directory=Path.of(args[0]);Map<String,Long> lines=new TreeMap<>(),polygons=new TreeMap<>(),points=new TreeMap<>(),sizes=new TreeMap<>();
        SortedMap<String,String> anchors=new TreeMap<>(),hashes=new TreeMap<>();
        Map<Integer,Map<String,Long>> contourLevels=new TreeMap<>();
        int tiles=0;double minLat=90,minLon=180,maxLat=-90,maxLon=-180;List<String> bounds=new ArrayList<>();
        List<Path> files;
        try(var paths=Files.list(directory)) {files=paths.filter(p->p.getFileName().toString().matches("[0-9]{8}\\.img")).sorted().toList();}
        for(Path file:files) {
            hashes.put(file.getFileName().toString(),logicalHash(file,new TreeMap<>()));
            try(MapReader reader=new MapReader(file.toString())) {
                var area=reader.getTreBounds();double unit=360.0/(1<<24);
                minLat=Math.min(minLat,area.getMinLat()*unit);minLon=Math.min(minLon,area.getMinLong()*unit);maxLat=Math.max(maxLat,area.getMaxLat()*unit);maxLon=Math.max(maxLon,area.getMaxLong()*unit);
                for(Zoom level:reader.getLevels()) {
                    if(level.getLevel()<=4) {
                        Map<String,Long> cc=contourLevels.computeIfAbsent(level.getLevel(),k->new TreeMap<>());
                        for(Polyline line:reader.linesForLevel(level.getLevel())) {
                            if(level.getLevel()==0)count(lines,line.getType());
                            if(Set.of(0x20,0x21,0x22,0x10008,0x10009).contains(line.getType()))count(cc,line.getType());
                        }
                    }
                }
                for(Polygon polygon:reader.shapesForLevel(0,true))count(polygons,polygon.getType());
                for(Point point:reader.pointsForLevel(0,true)) {
                    count(points,point.getType());String name=point.getLabel()!=null ? point.getLabel().getText() : point.getPOIRecord()!=null && point.getPOIRecord().getNameLabel()!=null ? point.getPOIRecord().getNameLabel().getText() : "";
                    for(String target:List.of("Carrauntoohil","Dublin","Belfast","Galway","Cork","Letterkenny"))
                        if(name.equalsIgnoreCase(target))anchors.put(target,name);
                }
            }
            tiles++;
        }
        String combined=logicalHash(directory.resolve("gmapsupp.img"),sizes);
        if(tiles==0 || sizes.getOrDefault("DEM",0L)==0 || sizes.getOrDefault("TYP",0L)==0)throw new IllegalStateException("Missing tiles, DEM or TYP");
        if(sizes.containsKey("NET")||sizes.containsKey("NOD"))throw new IllegalStateException("Unexpected routing network");
        for(String type:List.of("0x20","0x21","0x22"))if(!lines.containsKey(type))throw new IllegalStateException("Missing contour type "+type);
        if(!polygons.containsKey("0x10107")||!points.containsKey("0x6616"))throw new IllegalStateException("Missing bog or summit features");
        for(String name:List.of("Carrauntoohil","Dublin","Belfast","Galway","Cork"))if(!anchors.containsKey(name))throw new IllegalStateException("Missing anchor label: "+name);
        StringJoiner anchorsJson=new StringJoiner(",","{","}");anchors.forEach((k,v)->anchorsJson.add(quote(k)+":"+quote(v)));
        StringJoiner levelsJson=new StringJoiner(",","{","}");contourLevels.forEach((k,v)->levelsJson.add(quote(k.toString())+":"+mapJson(v)));
        StringJoiner hashJson=new StringJoiner(",","{","}");hashes.forEach((k,v)->hashJson.add(quote(k)+":"+quote(v)));
        System.out.println("{\"tiles\":"+tiles+",\"bounds\":["+minLon+","+minLat+","+maxLon+","+maxLat+"],\"subfileBytes\":"+mapJson(sizes)+",\"lineInstancesAtHighestDetail\":"+mapJson(lines)+",\"polygonInstancesAtHighestDetail\":"+mapJson(polygons)+",\"pointInstancesAtHighestDetail\":"+mapJson(points)+",\"contoursByLevel\":"+levelsJson+",\"anchorLabels\":"+anchorsJson+",\"logicalCombinedSHA256\":"+quote(combined)+",\"logicalTileSHA256\":"+hashJson+",\"logicalHashNote\":\"Internal file names, sizes and payloads; only CommonHeader creation-date bytes 14..20 are zeroed for hashing. IMG archive headers are excluded. Output bytes are never modified.\",\"routing\":false}");
    }
}
