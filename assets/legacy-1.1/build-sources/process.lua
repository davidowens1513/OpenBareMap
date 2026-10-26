-- OpenBareMap 1.1 processing schema.
-- Preserve useful OSM classifications so presentation can be varied in the app.

node_keys = {
  "amenity", "historic", "leisure", "natural", "place", "railway", "shop", "tourism"
}

way_keys = {
  "amenity", "boundary", "building", "highway", "historic", "landuse", "leisure",
  "natural", "railway", "route", "shop", "tourism", "water", "waterway", "wetland"
}

local function attribute_if_present(key, output_key)
  local value = Find(key)
  if value ~= "" then Attribute(output_key or key, value) end
end

local function name_attributes()
  attribute_if_present("name")
  attribute_if_present("name:ga", "name_ga")
  attribute_if_present("name:en", "name_en")
  attribute_if_present("official_name")
  attribute_if_present("short_name")
  attribute_if_present("ref")
end

local function access_attributes()
  attribute_if_present("access")
  attribute_if_present("foot")
  attribute_if_present("bicycle")
  attribute_if_present("horse")
end

local function structure_attributes()
  attribute_if_present("bridge")
  attribute_if_present("tunnel")
  attribute_if_present("layer")
end

local landcover_classes = {
  forest = "wood", farmland = "farmland", farm = "farmland", meadow = "grass",
  grass = "grass", village_green = "grass", recreation_ground = "grass",
  wood = "wood", grassland = "grass", heath = "heath", scrub = "scrub",
  wetland = "wetland", beach = "beach", sand = "sand", bog = "bog"
}

local function landcover_class()
  local landuse = Find("landuse")
  local natural = Find("natural")
  local wetland = Find("wetland")
  if wetland == "bog" or natural == "bog" then return "bog", wetland end
  if landcover_classes[landuse] then return landcover_classes[landuse], landuse end
  if landcover_classes[natural] then return landcover_classes[natural], natural end
  if natural == "wetland" then return "wetland", wetland end
  return nil, nil
end

function relation_scan_function()
  local relation_type = Find("type")
  local route = Find("route")
  if relation_type == "route" and
      (route == "hiking" or route == "foot" or route == "walking" or route == "bicycle") then
    Accept()
  elseif relation_type == "boundary" and Find("boundary") == "administrative" then
    Accept()
  end
end

function relation_function()
  if Find("type") ~= "route" then return end
  local route = Find("route")
  if route == "hiking" or route == "foot" or route == "walking" then
    Layer("hiking_route", false)
  elseif route == "bicycle" then
    Layer("cycling_route", false)
  else
    return
  end
  Attribute("class", route)
  attribute_if_present("network")
  attribute_if_present("operator")
  attribute_if_present("symbol")
  attribute_if_present("colour")
  name_attributes()
end

function node_function()
  local place = Find("place")
  if place ~= "" then
    Layer("place")
    Attribute("class", place)
    name_attributes()
    if place == "city" then MinZoom(3)
    elseif place == "town" then MinZoom(6)
    elseif place == "village" then MinZoom(10)
    elseif place == "hamlet" then MinZoom(11)
    else MinZoom(10) end
  end

  local natural = Find("natural")
  if natural == "peak" or natural == "volcano" or natural == "saddle" then
    Layer("natural")
    Attribute("class", natural)
    name_attributes()
    attribute_if_present("ele")
    MinZoom(9)
  end

  local railway = Find("railway")
  if railway == "station" or railway == "halt" or railway == "tram_stop" then
    Layer("station")
    Attribute("class", railway)
    name_attributes()
    attribute_if_present("operator")
    attribute_if_present("network")
  end

  local amenity = Find("amenity")
  local shop = Find("shop")
  local tourism = Find("tourism")
  local historic = Find("historic")
  local leisure = Find("leisure")
  local poi_class = amenity
  local category = "amenity"
  if poi_class == "" then poi_class = shop; category = "shop" end
  if poi_class == "" then poi_class = tourism; category = "tourism" end
  if poi_class == "" then poi_class = historic; category = "historic" end
  if poi_class == "" then poi_class = leisure; category = "leisure" end
  if poi_class ~= "" then
    Layer("poi")
    Attribute("class", poi_class)
    Attribute("category", category)
    name_attributes()
    access_attributes()
  end
end

function way_function()
  local highway = Find("highway")
  if highway ~= "" then
    Layer("transportation", false)
    Attribute("class", highway)
    attribute_if_present("surface")
    attribute_if_present("tracktype")
    attribute_if_present("smoothness")
    attribute_if_present("sac_scale")
    attribute_if_present("trail_visibility")
    attribute_if_present("oneway")
    attribute_if_present("maxspeed")
    access_attributes()
    structure_attributes()
    local name = Find("name")
    if name ~= "" or Find("ref") ~= "" then
      Layer("transportation_name", false)
      Attribute("class", highway)
      name_attributes()
    end
  end

  local waterway = Find("waterway")
  if waterway == "stream" or waterway == "river" or waterway == "canal" or
      waterway == "drain" or waterway == "ditch" then
    Layer("waterway", false)
    Attribute("class", waterway)
    name_attributes()
    attribute_if_present("intermittent")
    attribute_if_present("tidal")
  end

  local natural = Find("natural")
  local water = Find("water")
  if natural == "water" then
    Layer("water", true)
    Attribute("class", water ~= "" and water or "water")
    name_attributes()
    attribute_if_present("intermittent")
    if Find("name") ~= "" then
      LayerAsCentroid("water_name")
      Attribute("class", water ~= "" and water or "water")
      name_attributes()
    end
  end

  local cover_class, cover_subclass = landcover_class()
  if cover_class and IsClosed() then
    Layer("landcover", true)
    Attribute("class", cover_class)
    if cover_subclass and cover_subclass ~= "" then Attribute("subclass", cover_subclass) end
    name_attributes()
  end

  if natural == "cliff" then
    Layer("natural", false)
    Attribute("class", "cliff")
    name_attributes()
  elseif natural == "peak" or natural == "volcano" or natural == "saddle" then
    LayerAsCentroid("natural")
    Attribute("class", natural)
    name_attributes()
    attribute_if_present("ele")
  end

  if natural == "coastline" then
    Layer("coastline", false)
    Attribute("class", "coastline")
    name_attributes()
  end

  local railway = Find("railway")
  if railway ~= "" and railway ~= "station" and railway ~= "halt" and railway ~= "tram_stop" then
    Layer("railway", false)
    Attribute("class", railway)
    name_attributes()
    attribute_if_present("service")
    attribute_if_present("usage")
    attribute_if_present("operator")
    access_attributes()
    structure_attributes()
  elseif railway == "station" or railway == "halt" or railway == "tram_stop" then
    LayerAsCentroid("station")
    Attribute("class", railway)
    name_attributes()
  end

  if Find("route") == "ferry" then
    Layer("ferry", false)
    Attribute("class", "ferry")
    name_attributes()
    attribute_if_present("operator")
    attribute_if_present("duration")
    access_attributes()
  end

  local building = Find("building")
  if building ~= "" and IsClosed() then
    Layer("building", true)
    Attribute("class", building)
    name_attributes()
    attribute_if_present("building:levels", "levels")
    attribute_if_present("height")
  end

  local best_admin_level = nil
  local boundary_name = nil
  if Find("boundary") == "administrative" then
    local way_admin_level = Find("admin_level")
    if way_admin_level ~= "" and tonumber(way_admin_level) then
      best_admin_level = way_admin_level
      boundary_name = Find("name")
    end
  end
  while true do
    local relation_id = NextRelation()
    if not relation_id then break end
    if FindInRelation("boundary") == "administrative" then
      local candidate = FindInRelation("admin_level")
      if candidate ~= "" and tonumber(candidate) and
          (not best_admin_level or tonumber(candidate) < tonumber(best_admin_level)) then
        best_admin_level = candidate
        boundary_name = FindInRelation("name")
      end
    end
  end
  if best_admin_level and best_admin_level ~= "" then
    Layer("boundary", false)
    Attribute("class", "administrative")
    Attribute("admin_level", best_admin_level)
    if boundary_name and boundary_name ~= "" then Attribute("name", boundary_name) end
  end
end
