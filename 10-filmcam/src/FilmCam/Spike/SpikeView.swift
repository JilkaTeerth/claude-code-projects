import CoreImage
import SwiftUI
import os

/// M1 — the hot-loop spike.
///
/// This is not product UI. It is the smallest possible test of the four things
/// that could each independently kill the project:
///
///   1. is the multi-pass graph fast enough for a live preview
///   2. does it survive ten minutes without thermal throttling
///   3. does rapid camera switching destabilise it
///   4. is the architecture sound
///
/// Pass criteria, both on a physical device:
///   - **sustained:** 10 min continuous preview, >= 30fps at 1080p,
///     thermal state stays nominal or fair, memory flat
///   - **thrash:** 2 min cycling every camera as fast as possible,
///     no crash, no hitch beyond one frame, memory flat
///
/// If M1 passes, everything downstream is work rather than risk.
struct SpikeView: View {
    @State private var model = SpikeModel()

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()
            MetalPreview(view: model.preview).ignoresSafeArea()

            VStack {
                hud
                Spacer()
                controls
            }
            .padding()
        }
        .task { await model.start() }
        .onDisappear { model.stop() }
    }

    private var hud: some View {
        VStack(alignment: .leading, spacing: 3) {
            Text(String(format: "%.1f fps", model.fps))
                .foregroundStyle(model.fps >= 29 ? .green : (model.fps >= 24 ? .yellow : .red))
            Text(String(format: "render %.1f ms", model.renderMs))
            Text("thermal \(model.thermalLabel)")
                .foregroundStyle(model.thermalColor)
            Text("mem \(model.memoryMB) MB")
            Text("cam \(model.currentName)")
            Text("looks: \(model.librarySource)")
            if let err = model.error {
                Text(err).foregroundStyle(.red)
            }
            Text(model.identityLabel)
                .foregroundStyle(model.identityOK ? .green : .red)
        }
        .font(.system(size: 12, weight: .medium, design: .monospaced))
        .foregroundStyle(.white)
        .padding(10)
        .background(.black.opacity(0.55), in: RoundedRectangle(cornerRadius: 8))
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var controls: some View {
        VStack(spacing: 10) {
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    ForEach(model.cameras) { cam in
                        Button {
                            model.select(cam)
                        } label: {
                            VStack(spacing: 2) {
                                Text(cam.name).font(.system(size: 11, weight: .semibold))
                                Text("\(cam.focal)").font(.system(size: 9)).opacity(0.6)
                            }
                            .padding(.horizontal, 10).padding(.vertical, 7)
                            .background(
                                model.current?.id == cam.id ? Color.white.opacity(0.9) : Color.white.opacity(0.14),
                                in: Capsule()
                            )
                            .foregroundStyle(model.current?.id == cam.id ? .black : .white)
                        }
                    }
                }
            }

            HStack(spacing: 10) {
                Button(model.thrashing ? "STOP THRASH" : "THRASH 2 min") {
                    model.toggleThrash()
                }
                .tint(model.thrashing ? .red : .orange)

                Button(model.grainOn ? "grain on" : "grain off") {
                    model.grainOn.toggle()
                }
                Button("reload looks") { model.reloadLibrary() }
            }
            .buttonStyle(.borderedProminent)
            .font(.system(size: 12, weight: .semibold))
        }
    }
}

@Observable
final class SpikeModel {
    let preview = MetalPreviewView()
    private let session = CameraSession()
    private let library = CameraLibrary()
    private var engine: RenderEngine?

    var cameras: [Camera] { library.cameras }
    private(set) var current: Camera?
    var currentName: String { current?.name ?? "none" }
    var librarySource: String { library.sourceDescription }
    var error: String? { library.loadError }

    var grainOn = true
    private(set) var thrashing = false
    private var thrashIndex = 0
    private var thrashTimer: Timer?

    // Telemetry
    private(set) var fps: Double = 0
    private(set) var renderMs: Double = 0
    private var frameTimes: [CFTimeInterval] = []
    private var lastStatsUpdate: CFTimeInterval = 0

    private(set) var identityLabel = "cube: untested"
    private(set) var identityOK = false

    private let log = Logger(subsystem: "app.filmcam", category: "Spike")

    func start() async {
        engine = RenderEngine(library: library)
        current = library.cameras.first

        // Prove the cube layout before trusting a single rendered pixel. The
        // Python side runs the same test; if these disagree the bug is in the
        // byte layout, not in the shader.
        let err = CameraLibrary.identityCubeError()
        identityOK = err.isFinite && err < 0.02
        identityLabel = String(format: "cube err %.4f %@", err, identityOK ? "OK" : "FAIL")

        session.onFrame = { [weak self] image in
            self?.handle(frame: image)
        }
        guard await session.configure() else { return }
        session.start()
    }

    func stop() {
        session.stop()
        thrashTimer?.invalidate()
        thrashing = false
    }

    func select(_ camera: Camera) { current = camera }

    func reloadLibrary() {
        library.reload()
        current = library.cameras.first
    }

    /// The direct analogue of the VisionCamera filter-switch crash that ruled
    /// out the RN stack. If Core Image has an equivalent failure mode under
    /// rapid cube swapping, this is what surfaces it.
    func toggleThrash() {
        thrashing.toggle()
        thrashTimer?.invalidate()
        guard thrashing, !library.cameras.isEmpty else { return }
        thrashTimer = Timer.scheduledTimer(withTimeInterval: 0.08, repeats: true) { [weak self] _ in
            guard let self, !self.library.cameras.isEmpty else { return }
            self.thrashIndex = (self.thrashIndex + 1) % self.library.cameras.count
            self.current = self.library.cameras[self.thrashIndex]
        }
    }

    private func handle(frame: CIImage) {
        guard let engine, let camera = current else { return }

        let quality: RenderEngine.Quality = switch ProcessInfo.processInfo.thermalState {
        case .nominal, .fair: .full
        case .serious: .reduced
        default: .minimal
        }

        let output = engine.buildGraph(frame, camera: camera, grainEnabled: grainOn, quality: quality)
        preview.present(output)

        let now = CACurrentMediaTime()
        frameTimes.append(now)
        frameTimes.removeAll { now - $0 > 1.0 }
        if now - lastStatsUpdate > 0.25 {
            let count = frameTimes.count
            let ms = preview.lastRenderMs
            Task { @MainActor [weak self] in
                self?.fps = Double(count)
                self?.renderMs = ms
            }
            lastStatsUpdate = now
        }
    }

    var thermalLabel: String {
        switch ProcessInfo.processInfo.thermalState {
        case .nominal: "nominal"
        case .fair: "fair"
        case .serious: "SERIOUS"
        case .critical: "CRITICAL"
        @unknown default: "?"
        }
    }

    var thermalColor: Color {
        switch ProcessInfo.processInfo.thermalState {
        case .nominal: .green
        case .fair: .yellow
        default: .red
        }
    }

    /// Resident footprint. A steadily climbing number here during the sustained
    /// test means a leak in the render loop, which is the most likely way this
    /// architecture fails.
    var memoryMB: Int {
        var info = task_vm_info_data_t()
        var count = mach_msg_type_number_t(MemoryLayout<task_vm_info_data_t>.size / MemoryLayout<natural_t>.size)
        let result = withUnsafeMutablePointer(to: &info) {
            $0.withMemoryRebound(to: integer_t.self, capacity: Int(count)) {
                task_info(mach_task_self_, task_flavor_t(TASK_VM_INFO), $0, &count)
            }
        }
        return result == KERN_SUCCESS ? Int(info.phys_footprint / 1024 / 1024) : -1
    }
}
