import UIKit
import CoreLocation
import MapLibre

final class OpenBareMapViewController: UIViewController {
    private var resolvedStyle: URL?
    override func viewDidLoad() {
        super.viewDidLoad()
        do {
            let resources = try OpenBareMapResources.bundled()
            let style = try OpenBareMapResources.prepareStyle(in: resources)
            resolvedStyle = style
            let map = MLNMapView(frame: view.bounds, styleURL: style)
            map.autoresizingMask = [.flexibleWidth, .flexibleHeight]
            map.setCenter(CLLocationCoordinate2D(latitude: {{LAT}}, longitude: {{LON}}), zoomLevel: {{ZOOM}}, animated: false)
            view.addSubview(map)
            // Add an accessible Credits view displaying the supplied attribution notices.
        } catch {
            let label = UILabel(frame: view.bounds)
            label.numberOfLines = 0
            label.text = "Unable to load OpenBareMap: \(error)"
            view.addSubview(label)
        }
    }
    // Retain the resolved style for the lifetime of the map. Clean its temporary
    // directory only after releasing the map; never delete the bundle databases.
}
