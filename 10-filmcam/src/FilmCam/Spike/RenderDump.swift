import CoreImage
import Foundation
import UIKit
import os

/// Renders the bundled sample through every camera and writes the results to
/// Documents, so they can be pulled off the device or simulator and compared
/// numerically against `tools/filmlab/pipeline.py`.
///
/// This is the oracle check. The Python pipeline and the Swift graph are two
/// independent implementations of the same staged model, so agreement between
/// them is real evidence that both are right, and a large divergence points
/// straight at which stage is wrong.
///
/// Grain is deliberately excluded: it is stochastic and will never match
/// pixel-for-pixel between two implementations. Everything else should.
enum RenderDump {
    static func runIfRequested(library: CameraLibrary, engine: RenderEngine) {
        guard ProcessInfo.processInfo.arguments.contains("-dumpRenders") else { return }
        let log = Logger(subsystem: "app.filmcam", category: "RenderDump")

        // Two targets. The photo exercises the colour path; the highlight
        // scene exercises halation, which the photo cannot — only 1% of its
        // pixels clear the threshold, so halation on and off are
        // indistinguishable on it.
        let targets = ["sample", "sample_hi"]

        let outDir = CameraLibrary.documentsURL.appendingPathComponent("dump", isDirectory: true)
        try? FileManager.default.createDirectory(at: outDir, withIntermediateDirectories: true)

        // sRGB output, matching what filmlab writes, so the comparison is not
        // measuring a colour-space difference.
        let context = CIContext(options: [
            .workingColorSpace: CGColorSpace(name: CGColorSpace.extendedLinearSRGB)!,
            .outputColorSpace: CGColorSpace(name: CGColorSpace.sRGB)!,
        ])

        for target in targets {
          guard
            let url = Bundle.main.url(forResource: target, withExtension: "jpg"),
            let data = try? Data(contentsOf: url),
            // Tag explicitly. An untagged JPEG leaves Core Image to guess the
            // colour space, which would silently skew the whole comparison.
            let source = CIImage(data: data, options: [.colorSpace: CGColorSpace(name: CGColorSpace.sRGB)!])
          else {
            log.error("\(target, privacy: .public).jpg missing; skipping")
            continue
          }
          for camera in library.cameras {
            let out = engine.buildGraph(source, camera: camera, grainEnabled: false, quality: .full)
            guard let cg = context.createCGImage(
                out, from: out.extent,
                format: .RGBA8,
                colorSpace: CGColorSpace(name: CGColorSpace.sRGB)!
            ) else {
                log.error("render failed for \(camera.id, privacy: .public)")
                continue
            }
            let png = UIImage(cgImage: cg).pngData()
            let name = target == "sample" ? camera.id : "\(camera.id)__hi"
            try? png?.write(to: outDir.appendingPathComponent("\(name).png"))
          }
        }
        log.info("dumped renders to \(outDir.path, privacy: .public)")
    }
}
