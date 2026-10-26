-- OpenBareMap schema 0.4. Cartographic presentation belongs in the style.
node_keys = {"place", "natural", "tourism", "amenity", "highway", "information", "emergency", "railway", "shop", "historic", "leisure", "mountain_pass"}
way_keys = {"highway", "waterway", "natural", "landuse", "building", "tourism", "amenity", "information", "emergency", "railway", "route", "boundary", "place", "shop", "historic", "leisure", "mountain_pass"}

local function attribute(key, target)
  local value = Find(key)
  if value ~= "" then Attribute(target or key, value) end
end


local function names()
  attribute("name")
  attribute("name:en", "name_en")
  attribute("name:ga", "name_ga")
  attribute("official_name"); attribute("short_name")
end

local function elevation()
  local raw = Find("ele")
  if raw == "" then return nil end
  Attribute("ele_raw", raw)
  local number, unit = raw:match("^%s*([+-]?%d+%.?%d*)%s*([%a']*)%s*$")
  if not number then return nil end
  unit = unit:lower()
  local metres = tonumber(number)
  if unit == "ft" or unit == "feet" or unit == "'" then
    metres = metres * 0.3048
  elseif unit ~= "" and unit ~= "m" then
    return nil
  end
  AttributeNumeric("ele_m", metres)
  Attribute("ele_label", string.format("%.0f m", metres))
  return metres
end

local function hiking_class()
  if Find("disused") == "yes" or Find("abandoned") == "yes" then return nil end
  if Find("mountain_pass") == "yes" then return "pass" end
  local tourism, amenity = Find("tourism"), Find("amenity")
  if Find("emergency") == "mountain_rescue" or amenity == "mountain_rescue" then return "rescue" end
  if tourism == "alpine_hut" or tourism == "wilderness_hut" then return "hut" end
  if amenity == "shelter" then return "shelter" end
  if Find("highway") == "trailhead" or Find("information") == "trailhead" then return "trailhead" end
  if tourism == "viewpoint" then return "viewpoint" end
  if tourism == "camp_site" or tourism == "camp_pitch" then return "campsite" end
  if amenity == "drinking_water" then return "drinking_water" end
  if amenity == "toilets" then return "toilets" end
  if Find("information") == "guidepost" then return "guidepost" end
  if amenity == "parking" then return "parking" end
  return nil
end

local function hiking_point(is_area)
  local class = hiking_class()
  if not class then return end
  if is_area then LayerAsCentroid("hiking_poi") else Layer("hiking_poi") end
  Attribute("class", class)
  names()
  elevation()
  for _, key in ipairs({"access", "foot", "wheelchair", "operator", "opening_hours", "drinking_water", "fee", "backcountry", "shelter_type", "ref"}) do attribute(key) end
  if class == "hut" or class == "rescue" then MinZoom(10)
  elseif class == "shelter" or class == "trailhead" or class == "pass" then MinZoom(11)
  elseif class == "viewpoint" or class == "campsite" then MinZoom(12)
  elseif class == "parking" then MinZoom(14)
  else MinZoom(13) end
end

function relation_scan_function()
  local relation_type = Find("type")
  local route = Find("route")
  if relation_type == "route" and Find("state") ~= "proposed" and
      (route == "hiking" or route == "foot" or route == "walking" or route == "bicycle") then
    Accept()
  elseif relation_type == "boundary" and Find("boundary") == "administrative" then
    Accept()
  end
end

function relation_function()
  if Find("type") ~= "route" or Find("state") == "proposed" then return end
  local route = Find("route")
  if route == "hiking" or route == "foot" or route == "walking" then
    Layer("hiking_route", false)
  elseif route == "bicycle" then
    Layer("cycling_route", false)
  else
    return
  end
  Attribute("class", route)
  attribute("network")
  attribute("ref")
  attribute("operator")
  attribute("symbol")
  attribute("osmc:symbol"); attribute("access"); attribute("foot")
  attribute("colour")
  names()
  if Find("network") == "iwn" or Find("network") == "nwn" then MinZoom(8) else MinZoom(11) end
end

function node_function()
  local natural = Find("natural")
  if natural == "peak" or natural == "saddle" or natural == "volcano" then
    Layer("mountain")
    Attribute("class", natural)
    names()
    local metres = elevation()
    if natural == "saddle" then MinZoom(12)
    elseif metres and metres >= 600 then MinZoom(9)
    elseif metres and metres >= 300 then MinZoom(10)
    else MinZoom(11) end
  end
  hiking_point(false)
  local railway = Find("railway")
  if railway == "station" or railway == "halt" or railway == "tram_stop" then
    Layer("station")
    Attribute("class", railway)
    names()
    attribute("operator")
    attribute("network")
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
    names()
    attribute("access"); attribute("foot")
  end
  if Find("place") ~= "" then
    Layer("place")
    Attribute("class", Find("place"))
    attribute("name")
    attribute("name:en", "name_en")
    attribute("name:ga", "name_ga")
  end
  if Find("place") == "island" or Find("place") == "islet" then Layer("island_name"); Attribute("class",Find("place")); names() end
end

function way_function()
  if Find("natural") == "cliff" then
    Layer("natural_line", false)
    Attribute("class", "cliff")
    names()
    MinZoom(11)
  end
  if IsClosed() then hiking_point(true) end
  if Find("highway") ~= "" then
    Layer("transportation", false)
    Attribute("class", Find("highway"))
    for _, key in ipairs({"name", "ref", "surface", "tracktype", "access", "foot", "bridge", "tunnel", "layer"}) do
      attribute(key)
    end
  end
  if Find("waterway") ~= "" then
    Layer("waterway", false)
    Attribute("class", Find("waterway"))
    attribute("name")
    attribute("intermittent")
  end
  if IsClosed() then
    if Find("natural") == "water" then
      Layer("water", true)
      Attribute("class", Find("water") ~= "" and Find("water") or "water")
      attribute("name")
    end
    local classes = {wood="wood", forest="wood", farm="farmland", village_green="grass", recreation_ground="grass", heath="heath", scrub="scrub", grassland="grass", meadow="grass", grass="grass", farmland="farmland", wetland="wetland", beach="beach", sand="sand", shingle="shingle"}
    local class = classes[Find("landuse")] or classes[Find("natural")]
    -- Explicit terrain classes take precedence over broad land-use tags.
    local natural, wetland = Find("natural"), Find("wetland")
    if Find("landuse") == "peat_cutting" then class = "peat_cutting"
    elseif natural == "bare_rock" or natural == "scree" or natural == "shingle" then class = natural
    elseif natural == "bog" or (natural == "wetland" and (wetland == "bog" or wetland == "string_bog")) then class = "bog" end
    if class then
      Layer("landcover", true)
      Attribute("class", class)
      attribute("wetland")
      attribute("natural")
      attribute("landuse")
      names()
    end
    if Find("building") ~= "" then
      Layer("building", true)
      Attribute("class", Find("building"))
    end
  end
  local railway = Find("railway")
  if railway ~= "" and railway ~= "station" and railway ~= "halt" and railway ~= "tram_stop" then
    Layer("railway", false)
    Attribute("class", railway)
    names()
    attribute("service")
    attribute("usage")
    attribute("operator")
    attribute("access"); attribute("foot")
    attribute("bridge"); attribute("tunnel"); attribute("layer")
  elseif railway == "station" or railway == "halt" or railway == "tram_stop" then
    LayerAsCentroid("station")
    Attribute("class", railway)
    names()
  end

  if Find("route") == "ferry" then
    Layer("ferry", false)
    Attribute("class", "ferry")
    names()
    attribute("operator")
    attribute("duration")
    attribute("access"); attribute("foot")
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
  if Find("highway") ~= "" and (Find("name") ~= "" or Find("ref") ~= "") then
    Layer("transportation_name",false); Attribute("class",Find("highway")); names(); attribute("ref")
  end
  if IsClosed() and Find("natural") == "water" and Find("name") ~= "" then
    LayerAsCentroid("water_name"); names()
  end
  if IsClosed() and (Find("place") == "island" or Find("place") == "islet") then
    LayerAsCentroid("island_name"); Attribute("class",Find("place")); names()
  end
end
