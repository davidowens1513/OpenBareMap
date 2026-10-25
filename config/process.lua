-- Initial schema. All cartographic presentation belongs in the style.
node_keys = {"place"}
way_keys = {"highway", "waterway", "natural", "landuse", "building"}

local function attribute(key, target)
  local value = Find(key)
  if value ~= "" then Attribute(target or key, value) end
end

function node_function()
  if Find("place") ~= "" then
    Layer("place")
    Attribute("class", Find("place"))
    attribute("name")
    attribute("name:en", "name_en")
    attribute("name:ga", "name_ga")
  end
end

function way_function()
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
    if class then
      Layer("landcover", true)
      Attribute("class", class)
      attribute("wetland")
    end
    if Find("building") ~= "" then
      Layer("building", true)
      Attribute("class", Find("building"))
    end
  end
end
