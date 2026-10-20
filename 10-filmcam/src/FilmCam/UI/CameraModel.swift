import CoreImage
import SwiftUI
import UIKit
import os

@Observable
final class CameraModel {
    let preview = MetalPreviewView()
    private let session = CameraSession()
    private let library = CameraLibrary()
    private var engine: RenderEngine?
    private let log = Logger(subsystem: "app.filmcam", category: "CameraModel")

    private(set) var current: Camera?
    private(set) var shotCount = 0
    /// cameras with a working LUT / total. Anything but equal is a bug.
    var cubeStatus: String { "\(library.loadedCubeCount)/\(library.cameras.count)" }
    var cubesHealthy: Bool { library.loadedCubeCount == library.cameras.count && !library.cameras.isEmpty }
    /// Custom Core Image Metal kernels do not load in the iOS Simulator
    /// ("Metal DAG compiler disabled"); they work on device. Surfaced so a
    /// device-side failure is immediately obvious rather than silently
    /// producing grainless output.
    var grainAvailable: Bool { engine?.grainKernel.isAvailable ?? false }
    var healthy: Bool { cubesHealthy && grainAvailable }
    private(set) var isCapturing = false
    var grainOn = true
    var showZoomFrame = true

    /// Preserves the order the library declares, so the rack reads in the order
    /// the families were designed rather than alphabetically.
    var families: [String] {
        var seen = Set<String>()
        return library.cameras.compactMap { seen.insert($0.family).inserted ? $0.family : nil }
    }

    func cameras(in family: String) -> [Camera] {
        library.cameras.filter { $0.family == family }
    }

    func start() async {
        let engine = RenderEngine(library: library)
        self.engine = engine
        current = library.cameras.first
        RenderDump.runIfRequested(library: library, engine: engine)

        session.onFrame = { [weak self] image in self?.render(image) }

        if await session.configure() {
            session.start()
        } else {
            // No camera: either the simulator, or permission was refused.
            // Falling back to a still keeps the UI fully workable for layout
            // and look review, which is most of what the simulator is good for
            // anyway since it has no camera hardware to offer.
            log.notice("no capture device, using still fallback")
            startStillFallback()
        }
    }

    func stop() {
        session.stop()
        fallbackTimer?.invalidate()
        fallbackTimer = nil
    }

    func select(_ camera: Camera) {
        current = camera
        renderFallbackIfNeeded()
    }

    func flipCamera() { /* wired in M7 with the orientation work */ }

    func capture() {
        guard !isCapturing else { return }
        isCapturing = true
        shotCount += 1
        // M4 writes the shot directory here. For now this is just the shutter
        // feedback so the interaction can be felt and timed.
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.18) { [weak self] in
            self?.isCapturing = false
        }
    }

    private func render(_ image: CIImage) {
        guard let engine, let camera = current else { return }
        let quality: RenderEngine.Quality = switch ProcessInfo.processInfo.thermalState {
        case .nominal, .fair: .full
        case .serious: .reduced
        default: .minimal
        }
        preview.present(engine.buildGraph(image, camera: camera, grainEnabled: grainOn, quality: quality))
    }

    // MARK: - Still fallback

    private var fallbackImage: CIImage?
    private var fallbackTimer: Timer?

    private func startStillFallback() {
        fallbackImage = Self.loadSample()
        renderFallbackIfNeeded()
        // A slow repaint keeps grain resampling visible without spinning the
        // GPU; there is no live signal to keep up with here.
        fallbackTimer = Timer.scheduledTimer(withTimeInterval: 0.5, repeats: true) { [weak self] _ in
            self?.renderFallbackIfNeeded()
        }
    }

    private func renderFallbackIfNeeded() {
        guard let fallbackImage else { return }
        render(fallbackImage)
    }

    private static func loadSample() -> CIImage? {
        if let url = Bundle.main.url(forResource: "sample", withExtension: "jpg"),
           let data = try? Data(contentsOf: url),
           let image = CIImage(data: data) {
            return image
        }
        // Last resort so the UI is never a blank rectangle in a screenshot.
        return CIImage(color: CIColor(red: 0.42, green: 0.44, blue: 0.47))
            .cropped(to: CGRect(x: 0, y: 0, width: 1200, height: 1600))
    }
}
