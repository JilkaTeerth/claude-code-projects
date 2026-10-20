import CoreImage
import CoreImage.CIFilterBuiltins
import Foundation
import Metal

/// The one render graph. Preview and capture call this identically.
///
/// **Invariant A — no pixel constants.** Every resolution-dependent quantity is
/// derived from `input.extent.width`. Blur radii, grain cell size, vignette
/// radius, stamp size and margin are all fractions of image width, multiplied
/// at graph-build time. Any literal pixel value that leaks into a stage is a
/// parity bug and will make a 48MP still disagree with the 1080p preview.
///
/// **Invariant B — render from disk.** Capture writes the original first, then
/// loads it back and renders. The capture-time render and every later
/// re-render are then byte-identical code paths over identical input.
///
/// **Invariant C — no shared mutable filter state.** Every stage builds its
/// graph through `applyingFilter` or a locally-constructed filter. Nothing in
/// here mutates an object owned by anyone else, because preview and capture
/// render concurrently on different queues.
///
/// Stage order mirrors `tools/filmlab/pipeline.py`, which is the numpy oracle
/// this graph gets checked against.
struct RenderEngine {
    let library: CameraLibrary
    let grainKernel = GrainKernel()

    /// Working space is linear; output is sRGB. Halation runs in linear light
    /// because scatter is a physical process that happens before any tone
    /// mapping, and additive compositing only behaves correctly there.
    static func makeContext(commandQueue: (any MTLCommandQueue)? = nil) -> CIContext {
        let options: [CIContextOption: Any] = [
            .cacheIntermediates: false,
            .workingColorSpace: CGColorSpace(name: CGColorSpace.extendedLinearSRGB)!,
            .outputColorSpace: CGColorSpace(name: CGColorSpace.sRGB)!,
        ]
        if let queue = commandQueue {
            return CIContext(mtlCommandQueue: queue, options: options)
        }
        return CIContext(options: options)
    }

    /// Thermal adaptation ladder. Dropping halation scales is by far the
    /// cheapest way to shed GPU load, and at preview size it is nearly
    /// invisible.
    enum Quality {
        case full, reduced, minimal

        var scaleCount: Int {
            switch self {
            case .full: 3
            case .reduced: 2
            case .minimal: 1
            }
        }
    }

    // MARK: - The graph

    func buildGraph(
        _ input: CIImage,
        camera: Camera,
        grainEnabled: Bool = true,
        quality: Quality = .full
    ) -> CIImage {
        let extent = input.extent
        let width = Float(extent.width)
        var image = input

        // Stage 2 — halation, in linear light, before the grade.
        image = halation(image, camera.halation, width: width, quality: quality)

        // Stages 1/3/4 — exposure, balance, curve and colour, carried by the
        // LUT. Built fresh each call from cached cube data: the expensive part
        // is Core Image's shader compilation, which it caches globally once
        // pre-warmed, while the CIFilter object itself is cheap. Reusing one
        // shared filter instance and mutating its input would race between the
        // preview queue and the capture queue.
        if let cube = library.cubeData(for: camera) {
            image = image.applyingFilter("CIColorCubeWithColorSpace", parameters: [
                "inputCubeData": cube.data,
                "inputCubeDimension": cube.dimension,
                "inputColorSpace": cube.colorSpace,
            ])
        }

        // Stage 5 — grain, via the custom Metal kernel sampling the pink noise
        // tile. If the kernel is unavailable grain is skipped, never faked.
        if grainEnabled, camera.grain.amount > 0, grainKernel.isAvailable {
            image = grainKernel.apply(to: image, grain: camera.grain, width: width)
        }

        // Stage 6 — optics.
        if camera.optics.aberration > 0 {
            image = chromaticAberration(image, amount: camera.optics.aberration)
        }
        if camera.vignette.amount > 0 {
            image = vignette(image, camera.vignette)
        }

        return image.cropped(to: extent)
    }

    // MARK: - Stages

    /// Multi-scale red-orange bleed off blown highlights.
    ///
    /// The highlight mask is computed from **luminance**, matching the numpy
    /// reference. An earlier version thresholded each channel independently via
    /// a single colour matrix, which is cheaper but wrong: a saturated red at
    /// 0.9 would bloom while a neutral at 0.9 would not, so the Swift graph and
    /// the Python oracle disagreed on exactly the pixels halation is about.
    ///
    /// Multi-scale rather than one Gaussian: real halation is a tight hot core
    /// with a long low-amplitude tail, and a single blur gives a soft donut
    /// that reads as cheap bloom. Every scale is blurred on a progressively
    /// smaller downsample, which is both faster and visually indistinguishable
    /// at these radii, and is the single biggest thermal lever in the pipeline.
    private func halation(_ image: CIImage, _ p: Halation, width: Float, quality: Quality) -> CIImage {
        guard p.strength > 0 else { return image }
        let extent = image.extent
        let span = max(1.0 - p.threshold, 0.001)

        // luminance, replicated to all channels
        let luma = image.applyingFilter("CIColorMatrix", parameters: [
            "inputRVector": CIVector(x: 0.2126, y: 0.7152, z: 0.0722, w: 0),
            "inputGVector": CIVector(x: 0.2126, y: 0.7152, z: 0.0722, w: 0),
            "inputBVector": CIVector(x: 0.2126, y: 0.7152, z: 0.0722, w: 0),
            "inputAVector": CIVector(x: 0, y: 0, z: 0, w: 1),
        ])

        // mask = clamp((luma - threshold) / span), a linear stand-in for the
        // reference's smoothstep. Close enough that the oracle comparison
        // stays well inside tolerance, and one pass instead of three.
        let mask = luma
            .applyingFilter("CIColorMatrix", parameters: [
                "inputRVector": CIVector(x: CGFloat(1 / span), y: 0, z: 0, w: 0),
                "inputGVector": CIVector(x: 0, y: CGFloat(1 / span), z: 0, w: 0),
                "inputBVector": CIVector(x: 0, y: 0, z: CGFloat(1 / span), w: 0),
                "inputAVector": CIVector(x: 0, y: 0, z: 0, w: 1),
                "inputBiasVector": CIVector(
                    x: CGFloat(-p.threshold / span),
                    y: CGFloat(-p.threshold / span),
                    z: CGFloat(-p.threshold / span),
                    w: 0
                ),
            ])
            .applyingFilter("CIColorClamp", parameters: [
                "inputMinComponents": CIVector(x: 0, y: 0, z: 0, w: 0),
                "inputMaxComponents": CIVector(x: 1, y: 1, z: 1, w: 1),
            ])

        // glow seed = rgb * mask * tint
        let highlights = image
            .applyingFilter("CIMultiplyCompositing", parameters: [
                kCIInputBackgroundImageKey: mask
            ])
            .applyingFilter("CIColorMatrix", parameters: [
                "inputRVector": CIVector(x: CGFloat(p.tint[0]), y: 0, z: 0, w: 0),
                "inputGVector": CIVector(x: 0, y: CGFloat(p.tint[1]), z: 0, w: 0),
                "inputBVector": CIVector(x: 0, y: 0, z: CGFloat(p.tint[2]), w: 0),
            ])
            .cropped(to: extent)

        let baseRadius = p.radiusPct * width
        var glow: CIImage?
        var weightSum: Float = 0

        for i in 0..<min(quality.scaleCount, min(p.scales.count, p.weights.count)) {
            let scale = p.scales[i]
            let weight = p.weights[i]
            weightSum += weight

            // Downsample proportionally to the blur width. A wide blur on a
            // small image is nearly free and upsamples back indistinguishably.
            let factor = CGFloat(min(max(1.0 / max(scale, 1.0), 0.12), 1.0))
            var layer = highlights
            if factor < 0.99 {
                layer = layer.applyingFilter("CILanczosScaleTransform", parameters: [
                    kCIInputScaleKey: factor, kCIInputAspectRatioKey: 1.0,
                ])
            }
            layer = layer.applyingFilter("CIGaussianBlur", parameters: [
                kCIInputRadiusKey: CGFloat(baseRadius * scale) * factor / 3.0
            ])
            if factor < 0.99 {
                layer = layer.applyingFilter("CILanczosScaleTransform", parameters: [
                    kCIInputScaleKey: 1.0 / factor, kCIInputAspectRatioKey: 1.0,
                ])
            }

            let scaled = layer
                .cropped(to: extent)
                .applyingFilter("CIColorMatrix", parameters: [
                    "inputRVector": CIVector(x: CGFloat(weight), y: 0, z: 0, w: 0),
                    "inputGVector": CIVector(x: 0, y: CGFloat(weight), z: 0, w: 0),
                    "inputBVector": CIVector(x: 0, y: 0, z: CGFloat(weight), w: 0),
                ])

            glow = glow.map {
                $0.applyingFilter("CILinearDodgeBlendMode", parameters: [
                    kCIInputBackgroundImageKey: scaled
                ])
            } ?? scaled
        }

        guard let g = glow, weightSum > 0 else { return image }
        let s = CGFloat(p.strength / weightSum)
        let weighted = g.cropped(to: extent).applyingFilter("CIColorMatrix", parameters: [
            "inputRVector": CIVector(x: s, y: 0, z: 0, w: 0),
            "inputGVector": CIVector(x: 0, y: s, z: 0, w: 0),
            "inputBVector": CIVector(x: 0, y: 0, z: s, w: 0),
        ])

        // Additive in linear light is the physically correct composite.
        return image
            .applyingFilter("CILinearDodgeBlendMode", parameters: [kCIInputBackgroundImageKey: weighted])
            .cropped(to: extent)
    }

    /// Lateral chromatic aberration: a radial per-channel magnification
    /// difference, so fringing grows toward the corners and vanishes at centre.
    /// A uniform RGB offset is the wrong model and reads as a glitch effect.
    private func chromaticAberration(_ image: CIImage, amount: Float) -> CIImage {
        let extent = image.extent
        let centre = CGPoint(x: extent.midX, y: extent.midY)

        /// Isolate one channel and rescale it about the frame centre.
        /// `channel` is an index, not a vector: an earlier version compared
        /// `CIVector` instances with `==` to pick the channel, which relies on
        /// value equality of a reference type and is a trap waiting to spring.
        func isolate(_ channel: Int, magnify: CGFloat) -> CIImage {
            var r = CIVector(x: 0, y: 0, z: 0, w: 0)
            var g = CIVector(x: 0, y: 0, z: 0, w: 0)
            var b = CIVector(x: 0, y: 0, z: 0, w: 0)
            switch channel {
            case 0: r = CIVector(x: 1, y: 0, z: 0, w: 0)
            case 1: g = CIVector(x: 0, y: 1, z: 0, w: 0)
            default: b = CIVector(x: 0, y: 0, z: 1, w: 0)
            }

            let transform = CGAffineTransform(translationX: centre.x, y: centre.y)
                .scaledBy(x: magnify, y: magnify)
                .translatedBy(x: -centre.x, y: -centre.y)

            return image
                .transformed(by: transform)
                .applyingFilter("CIColorMatrix", parameters: [
                    "inputRVector": r,
                    "inputGVector": g,
                    "inputBVector": b,
                    // All three stay opaque: a blend mode does not sum alpha,
                    // and zeroing it here would premultiply the channel away.
                    "inputAVector": CIVector(x: 0, y: 0, z: 0, w: 1),
                ])
                .cropped(to: extent)
        }

        let a = CGFloat(amount)
        return isolate(0, magnify: 1 + a)
            .applyingFilter("CILinearDodgeBlendMode", parameters: [
                kCIInputBackgroundImageKey: isolate(1, magnify: 1)
            ])
            .applyingFilter("CILinearDodgeBlendMode", parameters: [
                kCIInputBackgroundImageKey: isolate(2, magnify: 1 - a)
            ])
            .cropped(to: extent)
    }

    private func vignette(_ image: CIImage, _ p: Vignette) -> CIImage {
        let extent = image.extent
        return image.applyingFilter("CIVignetteEffect", parameters: [
            kCIInputCenterKey: CIVector(x: extent.midX, y: extent.midY),
            // Radius as a fraction of the half-diagonal, never a pixel count.
            kCIInputRadiusKey: hypot(extent.width, extent.height) / 2 * CGFloat(p.radius),
            kCIInputIntensityKey: CGFloat(p.amount),
            "inputFalloff": CGFloat(p.softness),
        ]).cropped(to: extent)
    }
}
