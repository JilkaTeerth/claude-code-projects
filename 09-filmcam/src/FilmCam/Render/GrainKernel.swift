import CoreImage
import Foundation
import UIKit
import os

/// Loads and applies the custom grain kernel.
///
/// The kernel and its noise tile are both loaded once and held. Building a
/// `CIKernel` is not free, and doing it inside a frame callback would show up
/// as a hitch on every frame.
final class GrainKernel {
    private let kernel: CIKernel?
    private let noise: CIImage?
    private let log = Logger(subsystem: "app.filmcam", category: "Grain")

    /// True when both the kernel and the tile loaded. When false the caller
    /// skips grain entirely rather than silently substituting something wrong:
    /// a fallback that looks like digital noise is worse than no grain, because
    /// it would be judged as if it were the real thing.
    var isAvailable: Bool { kernel != nil && noise != nil }

    init() {
        kernel = Self.loadKernel()
        noise = Self.loadNoiseTile()
        if kernel == nil {
            log.error("grain kernel unavailable")
            // Narrow it down: does the simplest possible general kernel load?
            if let url = Bundle.main.url(forResource: "default", withExtension: "metallib"),
               let data = try? Data(contentsOf: url) {
                do {
                    _ = try CIKernel(functionName: "probeKernel", fromMetalLibraryData: data)
                    log.error("probe kernel LOADS -> build flags fine, filmGrain signature is the problem")
                } catch {
                    log.error("probe kernel also fails -> build/flags problem: \(error.localizedDescription, privacy: .public)")
                }
            }
        }
        if noise == nil { log.error("noise tile unavailable") }
    }

    private static func loadKernel() -> CIKernel? {
        // Core Image kernels compile into a default.metallib alongside the app,
        // produced by the -fcikernel compiler and linker flags.
        guard let url = Bundle.main.url(forResource: "default", withExtension: "metallib"),
              let data = try? Data(contentsOf: url) else {
            Logger(subsystem: "app.filmcam", category: "Grain").error("default.metallib not in bundle")
            return nil
        }
        do {
            // CIKernel, not CIColorKernel: this kernel reads a second texture at
            // computed coordinates, which a colour kernel cannot do.
            return try CIKernel(functionName: "filmGrain", fromMetalLibraryData: data)
        } catch {
            Logger(subsystem: "app.filmcam", category: "Grain")
                .error("kernel load failed: \(error.localizedDescription, privacy: .public)")
            return nil
        }
    }

    /// The tile is tiled infinitely so the kernel can sample at any coordinate
    /// without doing its own wrapping arithmetic.
    private static func loadNoiseTile() -> CIImage? {
        guard let url = Bundle.main.url(forResource: "noise_pink_512", withExtension: "png"),
              let image = UIImage(contentsOfFile: url.path),
              let cg = image.cgImage else {
            return nil
        }
        // Load without colour management: these are signed noise values encoded
        // into 0..1, not a picture. Letting Core Image apply a transfer function
        // to them would skew the distribution and break the zero mean.
        let raw = CIImage(cgImage: cg, options: [.colorSpace: NSNull()])
        return raw.applyingFilter("CIAffineTile", parameters: [
            kCIInputTransformKey: CGAffineTransform.identity
        ])
    }

    func apply(to image: CIImage, grain g: Grain, width: Float) -> CIImage {
        guard let kernel, let noise, g.amount > 0 else { return image }

        // Cell size derives from image width, never a pixel literal, so the
        // preview and a 48MP still produce identical apparent grain.
        let cell = max(g.sizePx1000 * width / 1000.0, 1.0)

        // A general kernel needs an ROI callback. Grain is a 1:1 point
        // operation on the source, and the noise image is infinitely tiled, so
        // the region needed from either input is exactly the destination rect.
        let output = kernel.apply(
            extent: image.extent,
            roiCallback: { _, rect in rect },
            arguments: [
                image,
                noise,
                g.amount,
                cell,
                g.mu,
                g.sigma,
                g.shadowFloor,
                g.chroma,
                Float(g.octaves),
            ]
        )
        return output?.cropped(to: image.extent) ?? image
    }
}
