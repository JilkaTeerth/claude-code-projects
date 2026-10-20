import SwiftUI

/// Design tokens.
///
/// The reference app's identity is acid green on white with heavy italic caps.
/// That is *their* identity and copying it would make this a knockoff, so the
/// structural lessons are taken and the surface is our own.
///
/// Ours is a darkroom: safelight amber on near-black warm greys. It ties to the
/// thing the product actually is (photochemistry, not Y2K nostalgia), it is the
/// same amber as the date-stamp burn so the UI and the output rhyme, and it is
/// legible over a live camera feed, which a light theme is not.
enum Theme {
    /// Safelight amber. The single accent; everything else is greyscale.
    static let accent = Color(red: 1.00, green: 0.45, blue: 0.13)
    static let accentDim = Color(red: 0.62, green: 0.28, blue: 0.09)

    /// Warm blacks, never pure #000. A true black next to a live preview reads
    /// as a dead region; a warm near-black reads as a camera body.
    static let bg = Color(red: 0.055, green: 0.051, blue: 0.047)
    static let surface = Color(red: 0.105, green: 0.098, blue: 0.090)
    static let surfaceHigh = Color(red: 0.160, green: 0.150, blue: 0.140)

    static let text = Color(red: 0.96, green: 0.95, blue: 0.93)
    static let textDim = Color(red: 0.58, green: 0.56, blue: 0.53)

    /// Monospaced throughout. Camera bodies label themselves in stencilled,
    /// mechanical type; a rounded humanist face would fight that.
    static func mono(_ size: CGFloat, _ weight: Font.Weight = .medium) -> Font {
        .system(size: size, weight: weight, design: .monospaced)
    }

    static let previewCorner: CGFloat = 14
    static let sheetCorner: CGFloat = 22
}
