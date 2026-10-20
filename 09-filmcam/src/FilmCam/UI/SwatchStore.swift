import SwiftUI
import UIKit

/// Loads and caches the per-camera swatches.
///
/// The swatches live in a folder reference inside the bundle rather than an
/// asset catalog, because `filmlab` regenerates them on every look change and a
/// plain directory needs no catalog bookkeeping. That means `UIImage(named:)`
/// will not find them and they have to be resolved by bundle URL.
enum SwatchStore {
    private static var cache: [String: UIImage] = [:]
    private static let lock = NSLock()

    static func image(for id: String) -> UIImage? {
        lock.lock()
        defer { lock.unlock() }
        if let hit = cache[id] { return hit }

        let url = Bundle.main.url(forResource: id, withExtension: "jpg", subdirectory: "swatches")
            ?? Bundle.main.url(forResource: id, withExtension: "jpg")
        guard let url, let image = UIImage(contentsOfFile: url.path) else { return nil }
        cache[id] = image
        return image
    }
}
