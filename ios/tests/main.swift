import Foundation
let path = CommandLine.arguments[1]
guard let bundle = Bundle(url: URL(fileURLWithPath: path)) else { fatalError("Cannot open resource bundle") }
let output = try OpenBareMapResources.prepareStyle(in: bundle)
let data = try Data(contentsOf: output)
let style = try JSONSerialization.jsonObject(with: data) as! [String: Any]
let sources = style["sources"] as! [String: [String: Any]]
for key in ["basemap", "topography", "coast", "hillshade", "irish-grid"] {
    let url = sources[key]!["url"] as! String
    precondition(url.hasPrefix("mbtiles:///"))
    precondition(!url.contains("{bundle}"))
}
precondition((style["glyphs"] as! String).hasSuffix("/{fontstack}/{range}.pbf"))
precondition((sources["townlands"]!["data"] as! String).hasPrefix("file:///"))
print("PASS: Bundle lookup and runtime MBTiles/font/sprite/GeoJSON URL resolution")
try FileManager.default.removeItem(at: output.deletingLastPathComponent())
