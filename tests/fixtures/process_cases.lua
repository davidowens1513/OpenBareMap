local tags, emitted, current, closed, accepted
function Find(key) return tags[key] or "" end
function Layer(name, area) current={layer=name,area=area,attributes={}}; emitted[#emitted+1]=current end
function LayerAsCentroid(name) Layer(name, true); current.centroid=true end
function Attribute(key,value) current.attributes[key]=value end
function AttributeNumeric(key,value) assert(type(value)=="number"); Attribute(key,value) end
function MinZoom(zoom) current.minzoom=zoom end
function IsClosed() return closed end
function Accept() accepted=true end

dofile(arg[1])
local function run(kind, input, is_closed)
  tags=input;emitted={};current=nil;closed=is_closed or false;accepted=false
  if kind=="node" then node_function()
  elseif kind=="way" then way_function()
  else relation_scan_function();if accepted then relation_function() end end
  return emitted
end
local function find(layer)
  for _, item in ipairs(emitted) do if item.layer==layer then return item end end
  return nil
end

run("node",{natural="peak",name="Test mountain",["name:ga"]="Sliabh",ele="1038.6"})
local peak=find("mountain");assert(peak and peak.attributes.ele_m==1038.6 and peak.attributes.ele_label=="1039 m");assert(peak.attributes.name_ga=="Sliabh" and peak.minzoom==9)
run("node",{natural="peak",ele="3000 ft"});assert(math.abs(find("mountain").attributes.ele_m-914.4)<0.001)
run("node",{natural="peak",ele="1,038; unknown"});assert(find("mountain").attributes.ele_m==nil and find("mountain").attributes.ele_raw=="1,038; unknown")
run("node",{natural="saddle",ele="450 m"});assert(find("mountain").attributes.class=="saddle" and find("mountain").minzoom==12)
run("node",{natural="peak",name="No height"});assert(find("mountain").attributes.ele_label==nil)

for _, case in ipairs({
  {{tourism="wilderness_hut"},"hut"},{{amenity="shelter"},"shelter"},
  {{highway="trailhead"},"trailhead"},{{tourism="viewpoint"},"viewpoint"},
  {{tourism="camp_site"},"campsite"},{{amenity="drinking_water"},"drinking_water"},
  {{amenity="toilets"},"toilets"},{{information="guidepost"},"guidepost"},
  {{amenity="parking",access="private"},"parking"},{{emergency="mountain_rescue"},"rescue"}
}) do
  run("node",case[1]);assert(find("hiking_poi").attributes.class==case[2])
end
run("node",{amenity="parking",access="private"});assert(find("hiking_poi").attributes.access=="private")
run("node",{amenity="shelter",disused="yes"});assert(not find("hiking_poi"))
run("node",{tourism="hotel"});assert(not find("hiking_poi"))
run("way",{tourism="camp_site",name="Area campsite"},true);assert(find("hiking_poi").centroid)
run("way",{natural="cliff",name="Test cliff"},false);assert(find("natural_line").attributes.class=="cliff")
run("way",{highway="path",name="A path"},false);assert(find("transportation").attributes.name=="A path")
run("relation",{type="route",route="hiking",network="nwn",name="Long route",ref="TEST"});assert(accepted and find("hiking_route").attributes.ref=="TEST" and find("hiking_route").minzoom==8)
run("relation",{type="route",route="foot",network="lwn"});assert(find("hiking_route").minzoom==11)
run("relation",{type="route",route="hiking",state="proposed"});assert(not accepted and #emitted==0)
run("relation",{type="route",route="bicycle"});assert(not accepted and #emitted==0)
print("Outdoor classification, elevations, access attributes, area POIs and route rules passed.")

for _, case in ipairs({
  {{natural="wetland",wetland="bog"},"bog"},
  {{natural="wetland",wetland="string_bog",landuse="forest"},"bog"},
  {{natural="wetland",wetland="fen"},"wetland"},
  {{landuse="peat_cutting",natural="wetland",wetland="bog"},"peat_cutting"},
  {{natural="bare_rock",landuse="grass"},"bare_rock"},
  {{natural="scree"},"scree"}
}) do
  run("way",case[1],true)
  assert(find("landcover").attributes.class==case[2])
  assert(find("landcover").attributes.natural==case[1].natural)
end
run("way",{natural="scree"},false);assert(not find("landcover"))
run("way",{highway="track",surface="gravel"},true);assert(not find("landcover"))
print("Bog, peat workings, rock and scree classification passed.")
