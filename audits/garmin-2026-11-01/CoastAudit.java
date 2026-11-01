import java.nio.*;import java.nio.file.*;import java.io.*;import java.util.*;
import uk.me.parabola.imgfmt.sys.ImgFS;import uk.me.parabola.imgfmt.FileSystemParam;import uk.me.parabola.imgfmt.fs.*;import uk.me.parabola.imgfmt.app.map.MapReader;import uk.me.parabola.imgfmt.app.trergn.*;
public class CoastAudit {
 public static void main(String[] args)throws Exception{
  Path dest=Path.of(args[1]);Files.createDirectories(dest);String region=args[2];
  double west=region.equals("ireland")?-11:-7.2,east=region.equals("ireland")?-5:2.5,south=region.equals("ireland")?51:49.5,north=region.equals("ireland")?56:56.2;
  java.awt.image.BufferedImage[] masks=new java.awt.image.BufferedImage[5];java.awt.Graphics2D[] pens=new java.awt.Graphics2D[5];
  for(int i=0;i<5;i++){masks[i]=new java.awt.image.BufferedImage(1000,1000,java.awt.image.BufferedImage.TYPE_INT_RGB);pens[i]=masks[i].createGraphics();pens[i].setColor(java.awt.Color.WHITE);}

  try(var fs=ImgFS.openFs(args[0]);var out=Files.newBufferedWriter(dest.resolve(region+"-coast.ndjson"));var meta=Files.newBufferedWriter(dest.resolve(region+"-tiles.ndjson"))){
   TreeSet<String> names=new TreeSet<>();for(var e:fs.list())if(e.getExt().equals("TRE"))names.add(e.getName());
   for(String name:names){
    try(var treChannel=fs.open(name+".TRE","r");var rgnChannel=fs.open(name+".RGN","r");var lblChannel=fs.open(name+".LBL","r")){
     var reader=new TREFileReader(treChannel);var rgn=new RGNFileReader(rgnChannel);rgn.setLblFile(new uk.me.parabola.imgfmt.app.lbl.LBLFileReader(lblChannel));
     var header=(TREHeader)reader.getHeader();var bounds=reader.getBounds();double u=360.0/(1<<24);meta.write("{\"priority\":"+header.getDisplayPriority()+",\"tile\":\""+name+"\",\"bounds\":["+bounds.getMinLong()*u+","+bounds.getMinLat()*u+","+bounds.getMaxLong()*u+","+bounds.getMaxLat()*u+"]}\n");
     for(var zoom:reader.getMapLevels())for(var subdivision:reader.subdivForLevel(zoom.getLevel()))for(var poly:rgn.shapesForSubdiv(subdivision,true))if(Set.of(0x32,0x54,0x3c).contains(poly.getType())){
      if(poly.getType()==0x54&&zoom.getLevel()<5){java.awt.geom.Path2D.Double path=new java.awt.geom.Path2D.Double();boolean firstPoint=true;for(var c:poly.getPoints()){double x=(c.getLonDegrees()-west)/(east-west)*1000,y=(north-c.getLatDegrees())/(north-south)*1000;if(firstPoint){path.moveTo(x,y);firstPoint=false;}else path.lineTo(x,y);}path.closePath();pens[zoom.getLevel()].fill(path);}
      out.write("{\"tile\":\""+name+"\",\"level\":"+zoom.getLevel()+",\"resolution\":"+zoom.getResolution()+",\"type\":"+poly.getType()+",\"points\":[");boolean first=true;
      for(var c:poly.getPoints()){if(!first)out.write(",");first=false;out.write("["+c.getLonDegrees()+","+c.getLatDegrees()+"]");}out.write("]}\n");
     }
    }
   }
   var image=new java.awt.image.BufferedImage(2000,1080,java.awt.image.BufferedImage.TYPE_INT_RGB);var g=image.createGraphics();g.setColor(java.awt.Color.WHITE);g.fillRect(0,0,2000,1080);g.setFont(new java.awt.Font("SansSerif",java.awt.Font.PLAIN,22));g.setColor(java.awt.Color.BLACK);g.drawString(region+" / decoded land, closest detail (24 bits)",20,28);g.drawString("Low detail (16 bits); red = land lost from closest detail",1020,28);
   for(int y=0;y<1000;y++)for(int x=0;x<1000;x++){boolean hi=(masks[0].getRGB(x,y)&0xffffff)!=0,lo=(masks[4].getRGB(x,y)&0xffffff)!=0;image.setRGB(x,y+50,hi?0xf3efe6:0xa8d7ff);image.setRGB(x+1000,y+50,lo?0xf3efe6:hi?0xd63838:0xa8d7ff);}
   javax.imageio.ImageIO.write(image,"png",dest.resolve(region+"-land-comparison.png").toFile());
   System.err.println(region+": read "+names.size()+" tiles directly from distributed IMG");
  }
 }
}
