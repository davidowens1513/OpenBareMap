import Foundation

/// Resolves an OpenBareMap resource bundle into a MapLibre Native style URL.
/// No localhost server or fixed application sandbox path is required.
public enum OpenBareMapResources {
    public enum ResourceError: Error {
        case missingBundle, missingResource(String), invalidManifest, invalidStyle
    }

    public static func bundled(in application: Bundle = .main) throws -> Bundle {
        guard let url = application.url(forResource: "OpenBareMap", withExtension: "bundle"),
              let bundle = Bundle(url: url) else { throw ResourceError.missingBundle }
        return bundle
    }

    public static func prepareStyle(in bundle: Bundle) throws -> URL {
        let root = bundle.bundleURL
        let manifestURL = root.appendingPathComponent("manifest.json")
        guard let manifest = try JSONSerialization.jsonObject(with: Data(contentsOf: manifestURL)) as? [String: Any],
              let sourceFiles = manifest["sourceFiles"] as? [String: String] else {
            throw ResourceError.invalidManifest
        }
        guard var style = try JSONSerialization.jsonObject(with: Data(contentsOf: root.appendingPathComponent("style.json"))) as? [String: Any],
              var sources = style["sources"] as? [String: [String: Any]] else {
            throw ResourceError.invalidStyle
        }
        for (name, relativePath) in sourceFiles {
            let file = root.appendingPathComponent(relativePath)
            guard FileManager.default.fileExists(atPath: file.path), var source = sources[name] else {
                throw ResourceError.missingResource(relativePath)
            }
            source.removeValue(forKey: "tiles")
            // file:///... -> mbtiles:///...; retain percent-encoding in sandbox paths.
            source["url"] = "mbtiles://" + String(file.absoluteString.dropFirst("file://".count))
            sources[name] = source
        }
        guard var townlands = sources["townlands"] else { throw ResourceError.invalidStyle }
        townlands["data"] = root.appendingPathComponent("townlands.geojson").absoluteString
        sources["townlands"] = townlands
        style["sources"] = sources
        style["glyphs"] = root.appendingPathComponent("fonts").absoluteString + "/{fontstack}/{range}.pbf"
        style["sprite"] = root.appendingPathComponent("sprites/outdoors").absoluteString
        // Write only the small resolved style; the large databases remain in the bundle.
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent("OpenBareMap-" + UUID().uuidString, isDirectory: true)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let destination = directory.appendingPathComponent("style.json")
        try JSONSerialization.data(withJSONObject: style, options: [.sortedKeys]).write(to: destination, options: .atomic)
        return destination
    }
}
