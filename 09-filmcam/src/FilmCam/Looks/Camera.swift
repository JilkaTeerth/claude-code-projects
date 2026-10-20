import Foundation

/// A camera, not a filter.
///
/// The teardown's central finding: this category sells cameras. A camera
/// bundles a colour grade (carried as a 3D LUT), a lens, a frame, a focal
/// length and its own artifacts. Decoded straight from the `looks.json` that
/// `tools/filmlab` emits, so the Python side is the single source of truth and
/// adding or retuning a camera never requires touching Swift.
struct Camera: Codable, Identifiable, Hashable {
    let id: String
    let name: String
    let family: String
    let version: Int
    let focal: Int
    let frame: FrameStyle

    let lut: LUTRef
    let halation: Halation
    let grain: Grain
    let vignette: Vignette
    let optics: Optics
    let leak: Leak
    let stamp: Stamp
}

enum FrameStyle: String, Codable, Hashable {
    case none, sprocket, instant
}

struct LUTRef: Codable, Hashable {
    /// Path relative to the looks bundle, e.g. `luts/<sha256>.cubedata`.
    let data: String
    let size: Int
    let amount: Float
    let sha256: String
}

struct Halation: Codable, Hashable {
    let strength: Float
    let threshold: Float
    let softness: Float
    let tint: [Float]
    /// Blur radius as a fraction of image width. Never a pixel count: that is
    /// what makes a 1080p preview and a 48MP still agree.
    let radiusPct: Float
    let scales: [Float]
    let weights: [Float]

    enum CodingKeys: String, CodingKey {
        case strength, threshold, softness, tint
        case radiusPct = "radius_pct"
        case scales, weights
    }
}

struct Grain: Codable, Hashable {
    /// Standard deviation of the added noise in 0...1 space. The usable band is
    /// roughly 0.015 to 0.06; 0.12 is about +/-30/255 and reads as sensor noise.
    let amount: Float
    /// Grain cell size at a 1000px reference width, scaled at render time.
    let sizePx1000: Float
    let mu: Float
    let sigma: Float
    let shadowFloor: Float
    let chroma: Float
    let octaves: Int

    enum CodingKeys: String, CodingKey {
        case amount
        case sizePx1000 = "size_px1000"
        case mu, sigma
        case shadowFloor = "shadow_floor"
        case chroma, octaves
    }
}

struct Vignette: Codable, Hashable {
    let amount: Float
    let radius: Float
    let softness: Float
    let roundness: Float
}

struct Optics: Codable, Hashable {
    /// Lateral chromatic aberration: a radial per-channel magnification
    /// difference, so fringing grows toward the corners and is absent at centre.
    let aberration: Float
    let softness: Float
}

struct Leak: Codable, Hashable {
    let strength: Float
    /// A seed, never a baked texture, so re-rendering a shot months later
    /// reproduces the identical leak.
    let seed: Int
    let tint: [Float]
}

struct Stamp: Codable, Hashable {
    let enabled: Bool
    let sizePct: Float
    let corner: String
    let tint: [Float]
    let glow: Float

    enum CodingKeys: String, CodingKey {
        case enabled
        case sizePct = "size_pct"
        case corner, tint, glow
    }
}

struct CameraLibraryFile: Codable {
    let version: Int
    let looks: [Camera]
}
