import AVFoundation
import CoreImage
import Foundation
import os

/// The capture session feeding the filtered preview.
///
/// Deliberate choices, each of which has a reason that is easy to forget:
///
/// - **`AVCaptureVideoDataOutput`, not `AVCaptureVideoPreviewLayer`.** The
///   preview layer shows the raw sensor stream and cannot be filtered. The
///   whole product is a filtered preview, so frames have to come to us.
/// - **BGRA, not biplanar YUV.** BGRA costs some bandwidth but removes the YUV
///   conversion matrix and the video-range/full-range distinction, which is a
///   whole class of "why is the still slightly different from the preview"
///   bugs. Revisit only if profiling says we need the bandwidth back.
/// - **1080p at 30fps, not 60.** Film looks read fine at 30 and it halves the
///   GPU budget and thermal load. This is a correct default, not a compromise.
/// - **`.balanced` photo quality.** `.quality` triggers Deep Fusion and
///   computational tone mapping that the video stream never gets, so the still
///   would simply not match the preview.
final class CameraSession: NSObject {
    let session = AVCaptureSession()
    private let videoOutput = AVCaptureVideoDataOutput()
    private let photoOutput = AVCapturePhotoOutput()
    private let queue = DispatchQueue(label: "app.filmcam.capture", qos: .userInitiated)
    private let log = Logger(subsystem: "app.filmcam", category: "CameraSession")

    /// Called on the capture queue for every frame. Keep the work here small.
    var onFrame: ((CIImage) -> Void)?

    private(set) var isConfigured = false

    func configure() async -> Bool {
        #if targetEnvironment(simulator)
        // The simulator has no camera hardware, so asking for permission only
        // puts a modal over the UI we are trying to look at. Fail straight to
        // the still fallback.
        return false
        #else
        guard await Self.requestAccess() else {
            log.error("camera access denied")
            return false
        }

        session.beginConfiguration()
        session.sessionPreset = .hd1920x1080

        guard
            let device = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .back),
            let input = try? AVCaptureDeviceInput(device: device),
            session.canAddInput(input)
        else {
            session.commitConfiguration()
            log.error("no usable back camera")
            return false
        }
        session.addInput(input)

        videoOutput.videoSettings = [
            kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA
        ]
        // Dropping late frames keeps latency bounded; a backed-up queue would
        // make the preview lag behind reality, which feels broken in a camera.
        videoOutput.alwaysDiscardsLateVideoFrames = true
        videoOutput.setSampleBufferDelegate(self, queue: queue)
        if session.canAddOutput(videoOutput) { session.addOutput(videoOutput) }

        if session.canAddOutput(photoOutput) {
            session.addOutput(photoOutput)
            photoOutput.maxPhotoQualityPrioritization = .balanced
        }

        // Pin to 30fps so the thermal budget is predictable.
        if let format = device.formats.last(where: {
            let d = CMVideoFormatDescriptionGetDimensions($0.formatDescription)
            return d.width == 1920 && d.height == 1080
                && $0.videoSupportedFrameRateRanges.contains { $0.maxFrameRate >= 30 }
        }) {
            try? device.lockForConfiguration()
            device.activeFormat = format
            device.activeVideoMinFrameDuration = CMTime(value: 1, timescale: 30)
            device.activeVideoMaxFrameDuration = CMTime(value: 1, timescale: 30)
            device.unlockForConfiguration()
        }

        session.commitConfiguration()
        isConfigured = true
        log.info("session configured: 1080p BGRA @30")
        return true
        #endif
    }

    func start() {
        guard isConfigured, !session.isRunning else { return }
        queue.async { [session] in session.startRunning() }
    }

    /// Always stop when leaving the camera screen. A running session is the
    /// single largest sustained power draw in the app.
    func stop() {
        guard session.isRunning else { return }
        queue.async { [session] in session.stopRunning() }
    }

    private static func requestAccess() async -> Bool {
        switch AVCaptureDevice.authorizationStatus(for: .video) {
        case .authorized: return true
        case .notDetermined: return await AVCaptureDevice.requestAccess(for: .video)
        default: return false
        }
    }
}

extension CameraSession: AVCaptureVideoDataOutputSampleBufferDelegate {
    func captureOutput(
        _ output: AVCaptureOutput,
        didOutput sampleBuffer: CMSampleBuffer,
        from connection: AVCaptureConnection
    ) {
        guard let buffer = CMSampleBufferGetImageBuffer(sampleBuffer) else { return }
        onFrame?(CIImage(cvPixelBuffer: buffer))
    }
}
