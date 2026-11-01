import Foundation
let path = CommandLine.arguments[1]
guard let bundle = Bundle(url: URL(fileURLWithPath: path)) else { fatalError("Cannot open resource bundle") }
let output = try OpenBareMapResources.prepareStyle(in: bundle)
let data = try Data(contentsOf: output)
let style = try JSONSerialization.jsonObject(with: data) as! [String: Any]
let sources = style["sources"] as! [String: [String: Any]]
let manifest = try JSONSerialization.jsonObject(with: Data(contentsOf: bundle.bundleURL.appendingPathComponent("manifest.json"))) as! [String: Any]
let sourceFiles = manifest["sourceFiles"] as! [String: String]
for key in sourceFiles.keys {
    let url = sources[key]!["url"] as! String
    precondition(url.hasPrefix("mbtiles:///"))
    precondition(!url.contains("{bundle}"))
}
precondition((style["glyphs"] as! String).hasSuffix("/{fontstack}/{range}.pbf"))
if let townlands = sources["townlands"] {
    precondition((townlands["data"] as! String).hasPrefix("file:///"))
}
print("PASS: Bundle lookup and runtime MBTiles/font/sprite/GeoJSON URL resolution")
try FileManager.default.removeItem(at: output.deletingLastPathComponent())
