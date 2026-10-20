import CoreImage
import Foundation
import os

/// Loads cameras and their LUTs, and pre-warms the CIFilter instances.
///
/// Two behaviours here are deliberate and load-bearing.
///
/// **DEBUG hot reload.** In debug builds the library prefers a `looks.json` in
/// the app's Documents directory over the bundled one. On a 7-day free
/// provisioning certificate with no simulator, authoring 17 cameras with a
/// rebuild per tweak would be hundreds of build cycles. With file sharing
/// enabled you drag a new look set onto the device in Finder and pull to
/// refresh. This decouples look iteration from the build cycle entirely.
///
/// **Pre-warming.** Every LUT filter is constructed once at launch and cached.
/// Constructing a `CIColorCube` inside a frame callback causes allocation churn
/// and forces Core Image to recompile shaders, which shows up as a hitch every
/// time the filter rail moves. 17 cubes at 33³ is about 9.7 MB, which is
/// nothing, and it eliminates the whole class of problem.
@Observable
final class CameraLibrary {
    private(set) var cameras: [Camera] = []
    private(set) var loadError: String?

    /// Immutable cube payloads keyed by LUT content hash.
    ///
    /// Data, not a CIFilter. Handing out a shared filter and letting callers
    /// set its input image races the moment preview and capture render at the
    /// same time on different queues. The expensive part of a cube filter is
    /// Core Image's shader compilation, which it caches globally once
    /// pre-warmed, so constructing the filter per call costs almost nothing.
    struct Cube { let data: Data; let dimension: Int; let colorSpace: CGColorSpace }
    private var cubes: [String: Cube] = [:]
    private let log = Logger(subsystem: "app.filmcam", category: "CameraLibrary")

    /// Where the active look set was loaded from, surfaced in the debug HUD so
    /// there is never ambiguity about whether a hot reload actually took.
    private(set) var sourceDescription = "none"

    init() {
        reload()
    }

    /// Documents directory, used for DEBUG hot reload and for the roll.
    static var documentsURL: URL {
        FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
    }

    func reload() {
        guard let (fileURL, baseURL, origin) = Self.resolveLooksFile() else {
            loadError = "looks.json not found in Documents or bundle"
            log.error("\(self.loadError!, privacy: .public)")
            return
        }

        do {
            let data = try Data(contentsOf: fileURL)
            let parsed = try JSONDecoder().decode(CameraLibraryFile.self, from: data)
            cameras = parsed.looks
            sourceDescription = origin
            loadError = nil
            prewarm(baseURL: baseURL)
            log.info("loaded \(parsed.looks.count) cameras from \(origin, privacy: .public)")
        } catch {
            loadError = "looks.json decode failed: \(error)"
            log.error("\(self.loadError!, privacy: .public)")
        }
    }

    /// Prefer a hot-reloaded set in Documents, fall back to the bundled one.
    private static func resolveLooksFile() -> (file: URL, base: URL, origin: String)? {
        #if DEBUG
        let override = documentsURL.appendingPathComponent("looks.json")
        if FileManager.default.fileExists(atPath: override.path) {
            return (override, documentsURL, "Documents (hot reload)")
        }
        #endif
        if let bundled = Bundle.main.url(forResource: "looks", withExtension: "json") {
            return (bundled, bundled.deletingLastPathComponent(), "bundle")
        }
        return nil
    }

    /// Build every cube filter up front, and force shader compilation by
    /// rendering one tiny frame through each.
    private func prewarm(baseURL: URL) {
        cubes.removeAll(keepingCapacity: true)
        let warmContext = CIContext(options: [.cacheIntermediates: false])
        let probe = CIImage(color: .gray).cropped(to: CGRect(x: 0, y: 0, width: 8, height: 8))

        for camera in cameras {
            guard let cubeData = Self.loadCube(named: camera.lut.data, baseURL: baseURL) else {
                log.error("missing LUT \(camera.lut.data, privacy: .public) for \(camera.id, privacy: .public)")
                continue
            }

            // `CIColorCubeWithColorSpace`, NOT `CIColorCube`. The plain filter
            // applies the cube in the context's working space, which for us is
            // linear, but the LUTs are authored display-referred sRGB. That
            // mismatch is silent, ugly, and very hard to trace back.
            guard let filter = CIFilter(name: "CIColorCubeWithColorSpace") else { continue }
            filter.setValue(cubeData, forKey: "inputCubeData")
            filter.setValue(camera.lut.size, forKey: "inputCubeDimension")
            filter.setValue(CGColorSpace(name: CGColorSpace.sRGB), forKey: "inputColorSpace")
            cubes[camera.lut.sha256] = Cube(
                data: cubeData,
                dimension: camera.lut.size,
                colorSpace: CGColorSpace(name: CGColorSpace.sRGB)!
            )

            filter.setValue(probe, forKey: kCIInputImageKey)
            if let out = filter.outputImage {
                _ = warmContext.createCGImage(out, from: out.extent)
            }
        }
        log.info("pre-warmed \(self.cubes.count) cube filters")
    }

    /// Resolve a LUT whether or not its directory survived the build.
    ///
    /// `looks.json` refers to LUTs as `luts/<sha256>.cubedata`, which is right
    /// for the Documents hot-reload directory. But Xcode flattens a resource
    /// folder into the bundle root, so in an installed build the same file sits
    /// at `<bundle>/<sha256>.cubedata` with no `luts/` component.
    ///
    /// Getting this wrong fails *silently and invisibly*: the cube filter is
    /// simply absent, `buildGraph` skips the colour stage, and the preview
    /// still looks plausibly "filtered" because halation and vignette are
    /// unaffected. Every camera would have looked subtly identical with no
    /// error on screen.
    private static func loadCube(named path: String, baseURL: URL) -> Data? {
        if let data = try? Data(contentsOf: baseURL.appendingPathComponent(path)) {
            return data
        }
        let basename = (path as NSString).lastPathComponent
        if let data = try? Data(contentsOf: baseURL.appendingPathComponent(basename)) {
            return data
        }
        let stem = (basename as NSString).deletingPathExtension
        if let url = Bundle.main.url(forResource: stem, withExtension: "cubedata") {
            return try? Data(contentsOf: url)
        }
        return nil
    }

    /// The cached, immutable cube payload for a camera.
    func cubeData(for camera: Camera) -> Cube? {
        cubes[camera.lut.sha256]
    }

    /// How many cameras actually got a working LUT. Surfaced in the debug HUD:
    /// if this is not equal to the camera count, the colour stage is silently
    /// missing for some cameras and nothing else on screen would tell you.
    var loadedCubeCount: Int { cubes.count }

    /// Round-trips an identity cube through Core Image and reports the max
    /// absolute error.
    ///
    /// This is the Swift half of the test `filmlab check` runs in Python. If
    /// the cube byte layout is wrong — transposed axes, wrong channel order,
    /// wrong float width — the image comes out wildly wrong and it looks like
    /// a shader bug for hours. Catching it here takes a millisecond.
    static func identityCubeError(size: Int = 33) -> Float {
        var cube = [Float]()
        cube.reserveCapacity(size * size * size * 4)
        // Red varies fastest, then green, then blue. Alpha is always 1.
        for b in 0..<size {
            for g in 0..<size {
                for r in 0..<size {
                    cube.append(Float(r) / Float(size - 1))
                    cube.append(Float(g) / Float(size - 1))
                    cube.append(Float(b) / Float(size - 1))
                    cube.append(1.0)
                }
            }
        }

        guard let filter = CIFilter(name: "CIColorCubeWithColorSpace") else { return .nan }
        filter.setValue(cube.withUnsafeBufferPointer { Data(buffer: $0) }, forKey: "inputCubeData")
        filter.setValue(size, forKey: "inputCubeDimension")
        filter.setValue(CGColorSpace(name: CGColorSpace.sRGB), forKey: "inputColorSpace")

        // A deliberately asymmetric probe: an identity cube is symmetric under
        // an R/B transposition, so a grey ramp would pass even when wrong.
        let probe = CIImage(color: CIColor(red: 0.8, green: 0.4, blue: 0.2))
            .cropped(to: CGRect(x: 0, y: 0, width: 4, height: 4))
        filter.setValue(probe, forKey: kCIInputImageKey)
        guard let output = filter.outputImage else { return .nan }

        let context = CIContext(options: [.workingColorSpace: CGColorSpace(name: CGColorSpace.sRGB)!])
        var pixel = [UInt8](repeating: 0, count: 4)
        context.render(
            output,
            toBitmap: &pixel,
            rowBytes: 4,
            bounds: CGRect(x: 0, y: 0, width: 1, height: 1),
            format: .RGBA8,
            colorSpace: CGColorSpace(name: CGColorSpace.sRGB)
        )

        let got = [Float(pixel[0]) / 255, Float(pixel[1]) / 255, Float(pixel[2]) / 255]
        let want: [Float] = [0.8, 0.4, 0.2]
        return zip(got, want).map { abs($0 - $1) }.max() ?? .nan
    }
}
