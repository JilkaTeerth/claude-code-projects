import CoreImage
import MetalKit
import SwiftUI
import os

/// The filtered preview surface.
///
/// An `MTKView` driven manually, not `AVCaptureVideoPreviewLayer`, because the
/// preview layer can only show the unfiltered sensor stream.
///
/// `isPaused` and `enableSetNeedsDisplay` are both false: we draw exactly when
/// a camera frame arrives, never on a display-link tick. Drawing on a timer
/// would either render the same frame twice or skip frames, and would burn GPU
/// while the scene is static.
final class MetalPreviewView: MTKView {
    private var commandQueue: (any MTLCommandQueue)?
    private var ciContext: CIContext?
    private var pending: CIImage?
    private let log = Logger(subsystem: "app.filmcam", category: "Preview")

    /// Wall-clock duration of the last GPU render, surfaced in the HUD.
    private(set) var lastRenderMs: Double = 0
    private(set) var renderedFrames: Int = 0

    init() {
        let device = MTLCreateSystemDefaultDevice()
        super.init(frame: .zero, device: device)

        // framebufferOnly must be false or Core Image cannot write to the
        // drawable's texture.
        framebufferOnly = false
        colorPixelFormat = .bgra8Unorm
        isPaused = true
        enableSetNeedsDisplay = false
        autoResizeDrawable = true

        guard let device else {
            log.error("no Metal device")
            return
        }
        commandQueue = device.makeCommandQueue()
        ciContext = RenderEngine.makeContext(commandQueue: commandQueue)
    }

    @available(*, unavailable)
    required init(coder: NSCoder) { fatalError() }

    /// Hand the view an already-filtered image.
    ///
    /// Called from the capture queue, but the actual draw is hopped to the main
    /// thread. `currentDrawable` acquires from `CAMetalLayer`'s pool, which is
    /// not safe to touch off the main thread; doing so appears to work and then
    /// glitches or deadlocks under load, which is the worst possible failure
    /// mode to debug.
    ///
    /// `inFlight` gives the backpressure that dropping the synchronous draw
    /// removed. Without it, a slow GPU would let presentation requests pile up
    /// on the main queue and the preview would drift seconds behind reality.
    func present(_ image: CIImage) {
        lock.lock()
        pending = image
        let busy = inFlight
        inFlight = true
        lock.unlock()

        guard !busy else { return }  // a draw is already queued; it will pick up
        DispatchQueue.main.async { [weak self] in
            self?.draw()
        }
    }

    private let lock = NSLock()
    private var inFlight = false

    override func draw(_ rect: CGRect) {
        lock.lock()
        let image = pending
        pending = nil
        lock.unlock()

        guard
            let drawable = currentDrawable,
            let image,
            let ciContext,
            let commandBuffer = commandQueue?.makeCommandBuffer()
        else {
            lock.lock(); inFlight = false; lock.unlock()
            return
        }

        let start = CACurrentMediaTime()

        // Aspect-fill the drawable, then centre.
        let dw = CGFloat(drawable.texture.width)
        let dh = CGFloat(drawable.texture.height)
        let scale = max(dw / image.extent.width, dh / image.extent.height)
        let scaled = image.transformed(by: CGAffineTransform(scaleX: scale, y: scale))
        let dx = (dw - scaled.extent.width) / 2
        let dy = (dh - scaled.extent.height) / 2
        let centred = scaled.transformed(by: CGAffineTransform(translationX: dx, y: dy))

        ciContext.render(
            centred,
            to: drawable.texture,
            commandBuffer: commandBuffer,
            bounds: CGRect(x: 0, y: 0, width: dw, height: dh),
            colorSpace: CGColorSpace(name: CGColorSpace.sRGB)!
        )

        // Timing is taken in the completion handler, so it measures real GPU
        // work rather than encode time, which would flatter us badly. Doing it
        // this way instead of `waitUntilCompleted` keeps the main thread free;
        // blocking here would stall UI and touch handling for the whole render.
        commandBuffer.addCompletedHandler { [weak self] _ in
            guard let self else { return }
            self.lastRenderMs = (CACurrentMediaTime() - start) * 1000
            self.renderedFrames += 1

            self.lock.lock()
            let hasMore = self.pending != nil
            self.inFlight = hasMore
            self.lock.unlock()

            // A frame arrived while this one was on the GPU; draw it now.
            if hasMore {
                DispatchQueue.main.async { [weak self] in self?.draw() }
            }
        }

        commandBuffer.present(drawable)
        commandBuffer.commit()
    }
}

/// SwiftUI bridge. This is the only UIKit in the app.
struct MetalPreview: UIViewRepresentable {
    let view: MetalPreviewView

    func makeUIView(context: Context) -> MetalPreviewView { view }
    func updateUIView(_ uiView: MetalPreviewView, context: Context) {}
}
