-- OpenBareMap schema 0.3. Cartographic presentation belongs in the style.
node_keys = {"place", "natural", "tourism", "amenity", "highway", "information", "emergency"}
way_keys = {"highway", "waterway", "natural", "landuse", "building", "tourism", "amenity", "information", "emergency"}

local function attribute(key, target)
  local value = Find(key)
  if value ~= "" then Attribute(target or key, value) end
end


local function names()
  attribute("name")
  attribute("name:en", "name_en")
  attribute("name:ga", "name_ga")
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
  elseif class == "shelter" or class == "trailhead" then MinZoom(11)
  elseif class == "viewpoint" or class == "campsite" then MinZoom(12)
  elseif class == "parking" then MinZoom(14)
  else MinZoom(13) end
end

function relation_scan_function()
  local route = Find("route")
  if Find("type") == "route" and Find("state") ~= "proposed" and
      (route == "hiking" or route == "foot" or route == "walking") then Accept() end
end

function relation_function()
  local route = Find("route")
  if Find("type") ~= "route" or (route ~= "hiking" and route ~= "foot" and route ~= "walking") or Find("state") == "proposed" then return end
  Layer("hiking_route", false)
  Attribute("class", route)
  names()
  for _, key in ipairs({"ref", "network", "operator", "colour", "osmc:symbol", "access", "foot", "state"}) do attribute(key) end
  if Find("network") == "iwn" or Find("network") == "nwn" then MinZoom(8) else MinZoom(11) end
end

function node_function()
  local natural = Find("natural")
  if natural == "peak" or natural == "saddle" then
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
  if Find("place") ~= "" then
    Layer("place")
    Attribute("class", Find("place"))
    attribute("name")
    attribute("name:en", "name_en")
    attribute("name:ga", "name_ga")
  end
end

function way_function()
  if Find("natural") == "cliff" then
    Layer("natural_line", false)
    Attribute("class", "cliff")
    names()
    MinZoom(12)
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
    local classes = {wood="wood", forest="wood", heath="heath", scrub="scrub", grassland="grass", meadow="grass", grass="grass", farmland="farmland", wetland="wetland", beach="beach"}
    local class = classes[Find("landuse")] or classes[Find("natural")]
    -- Explicit terrain classes take precedence over broad land-use tags.
    local natural, wetland = Find("natural"), Find("wetland")
    if Find("landuse") == "peat_cutting" then class = "peat_cutting"
    elseif natural == "bare_rock" or natural == "scree" then class = natural
    elseif natural == "wetland" and (wetland == "bog" or wetland == "string_bog") then class = "bog" end
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
end
