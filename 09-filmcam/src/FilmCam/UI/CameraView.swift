import CoreImage
import SwiftUI

/// The product camera screen.
///
/// Structural lessons taken from the teardown, surface entirely our own:
///
/// - **The preview is inset and rounded, not edge to edge.** This is the single
///   most effective trick in the reference app. A full-bleed preview reads as
///   "your phone camera with a filter"; an inset one reads as looking *into*
///   something. It costs screen area and buys the whole illusion.
/// - **The selected camera sits next to the shutter as an object.** You are
///   holding a camera, not choosing a preset from a list.
/// - **A focal readout and a zoom frame.** Both say "this is a lens".
/// - **The picker is a sheet of bodies with names**, not a strip of colour
///   swatches.
struct CameraView: View {
    @State private var model: CameraModel
    // Launch argument so screenshot automation can capture the rack open.
    // Debug-only: a release build must never take UI state from argv.
    @State private var showPicker = {
        #if DEBUG
        ProcessInfo.processInfo.arguments.contains("-showRack")
        #else
        false
        #endif
    }()
    @State private var showDebug = false

    init(model: CameraModel = CameraModel()) {
        _model = State(initialValue: model)
    }

    var body: some View {
        ZStack {
            Theme.bg.ignoresSafeArea()

            VStack(spacing: 0) {
                topBar
                Spacer(minLength: 8)
                viewfinder
                Spacer(minLength: 8)
                lensRow
                shutterRow
            }
            .padding(.horizontal, 18)
            .padding(.bottom, 10)

            if showPicker {
                pickerSheet
                    .transition(.move(edge: .bottom).combined(with: .opacity))
            }
        }
        .task { await model.start() }
        .onDisappear { model.stop() }
        .sheet(isPresented: $showDebug) { SpikeView() }
    }

    // MARK: - Top

    private var topBar: some View {
        HStack {
            // Frame counter, the way a film back shows remaining exposures.
            Text(String(format: "%03d", model.shotCount))
                .font(Theme.mono(13, .semibold))
                .foregroundStyle(Theme.accent)
                .padding(.horizontal, 9).padding(.vertical, 5)
                .background(Theme.surface, in: Capsule())

            Spacer()

            Text(model.current?.name.uppercased() ?? "NO CAMERA")
                .font(Theme.mono(13, .bold))
                .foregroundStyle(Theme.text)
                .kerning(1.6)

            Spacer()

            Button { showDebug = true } label: {
                Image(systemName: model.healthy ? "waveform.path.ecg" : "exclamationmark.triangle.fill")
                    .font(.system(size: 14, weight: .semibold))
                    .foregroundStyle(model.healthy ? Theme.textDim : .red)
                    .frame(width: 30, height: 30)
                    .background(Theme.surface, in: Circle())
            }
        }
        .padding(.top, 6)
    }

    // MARK: - Viewfinder

    private var viewfinder: some View {
        GeometryReader { geo in
            let side = min(geo.size.width, geo.size.height)
            ZStack {
                RoundedRectangle(cornerRadius: Theme.previewCorner)
                    .fill(Color.black)

                MetalPreview(view: model.preview)
                    .clipShape(RoundedRectangle(cornerRadius: Theme.previewCorner))

                // Zoom frame: shows the crop the selected focal length takes.
                if model.showZoomFrame, let cam = model.current, cam.focal > 26 {
                    let inset = 1.0 - (26.0 / Double(cam.focal))
                    RoundedRectangle(cornerRadius: 6)
                        .stroke(Theme.text.opacity(0.55), lineWidth: 1)
                        .padding(side * inset * 0.42)
                }

                // Corner ticks. Cheap, and they do a lot of work making the
                // rectangle read as an optical frame rather than a video player.
                cornerTicks
            }
            .frame(width: geo.size.width, height: geo.size.height)
        }
        .aspectRatio(3.0 / 4.0, contentMode: .fit)
    }

    private var cornerTicks: some View {
        GeometryReader { g in
            let len: CGFloat = 14
            let pad: CGFloat = 9
            Path { p in
                let w = g.size.width, h = g.size.height
                for (x, y, dx, dy) in [
                    (pad, pad, 1.0, 1.0), (w - pad, pad, -1.0, 1.0),
                    (pad, h - pad, 1.0, -1.0), (w - pad, h - pad, -1.0, -1.0),
                ] {
                    p.move(to: CGPoint(x: x + len * dx, y: y))
                    p.addLine(to: CGPoint(x: x, y: y))
                    p.addLine(to: CGPoint(x: x, y: y + len * dy))
                }
            }
            .stroke(Theme.text.opacity(0.7), lineWidth: 1.5)
        }
    }

    // MARK: - Controls

    private var lensRow: some View {
        HStack(spacing: 22) {
            iconButton("arrow.triangle.2.circlepath.camera") { model.flipCamera() }

            Button { model.showZoomFrame.toggle() } label: {
                Text("\(model.current?.focal ?? 26)mm")
                    .font(Theme.mono(14, .bold))
                    .foregroundStyle(model.showZoomFrame ? Theme.accent : Theme.text)
                    .frame(minWidth: 62)
                    .padding(.vertical, 7)
                    .background(Theme.surface, in: Capsule())
            }

            iconButton(model.grainOn ? "circle.grid.3x3.fill" : "circle.grid.3x3") {
                model.grainOn.toggle()
            }
        }
        .padding(.vertical, 14)
    }

    private var shutterRow: some View {
        HStack {
            // Camera body thumbnail. Tapping opens the rack.
            Button {
                withAnimation(.spring(response: 0.34, dampingFraction: 0.82)) { showPicker = true }
            } label: {
                bodyChip(model.current)
            }

            Spacer()

            Button { model.capture() } label: {
                ZStack {
                    Circle().stroke(Theme.text, lineWidth: 3.5).frame(width: 74, height: 74)
                    Circle().fill(model.isCapturing ? Theme.accent : Theme.text).frame(width: 60, height: 60)
                }
            }
            .disabled(model.isCapturing)

            Spacer()

            // Balances the shutter optically; shows the last frame taken.
            RoundedRectangle(cornerRadius: 7)
                .fill(Theme.surface)
                .frame(width: 46, height: 46)
                .overlay(
                    Image(systemName: "photo.stack")
                        .font(.system(size: 15))
                        .foregroundStyle(Theme.textDim)
                )
        }
        .padding(.top, 4)
    }

    private func bodyChip(_ cam: Camera?) -> some View {
        VStack(spacing: 3) {
            Image(systemName: "camera.fill")
                .font(.system(size: 17))
                .foregroundStyle(Theme.accent)
            Text(cam.map { "\($0.focal)" } ?? "--")
                .font(Theme.mono(9, .semibold))
                .foregroundStyle(Theme.textDim)
        }
        .frame(width: 46, height: 46)
        .background(Theme.surface, in: RoundedRectangle(cornerRadius: 7))
    }

    private func iconButton(_ symbol: String, _ action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Image(systemName: symbol)
                .font(.system(size: 16, weight: .medium))
                .foregroundStyle(Theme.text)
                .frame(width: 38, height: 38)
                .background(Theme.surface, in: Circle())
        }
    }

    // MARK: - The rack

    private var pickerSheet: some View {
        VStack {
            Spacer()
            VStack(spacing: 14) {
                HStack {
                    Text("THE RACK")
                        .font(Theme.mono(12, .bold))
                        .kerning(2.2)
                        .foregroundStyle(Theme.textDim)
                    Spacer()
                    Button {
                        withAnimation(.spring(response: 0.3, dampingFraction: 0.85)) { showPicker = false }
                    } label: {
                        Image(systemName: "xmark")
                            .font(.system(size: 12, weight: .bold))
                            .foregroundStyle(Theme.textDim)
                            .frame(width: 26, height: 26)
                            .background(Theme.surfaceHigh, in: Circle())
                    }
                }

                ScrollView(showsIndicators: false) {
                  VStack(alignment: .leading, spacing: 14) {
                   ForEach(model.families, id: \.self) { family in
                    VStack(alignment: .leading, spacing: 7) {
                        Text(family.uppercased())
                            .font(Theme.mono(9, .semibold))
                            .kerning(1.4)
                            .foregroundStyle(Theme.accentDim)

                        ScrollView(.horizontal, showsIndicators: false) {
                            HStack(spacing: 9) {
                                ForEach(model.cameras(in: family)) { cam in
                                    bodyCard(cam)
                                }
                            }
                        }
                    }
                   }
                  }
                }
                .frame(maxHeight: 340)
            }
            .padding(18)
            .background(Theme.surface, in: RoundedRectangle(cornerRadius: Theme.sheetCorner))
            .padding(10)
        }
        .ignoresSafeArea(edges: .bottom)
    }

    /// A camera's identity is the image it makes.
    ///
    /// The reference app uses photorealistic 3D renders of real camera bodies,
    /// which needs a design team and borrows other manufacturers' industrial
    /// design. The honest equivalent for us is to show what the camera actually
    /// does: a reference frame graded through that exact camera, generated by
    /// `filmlab` from the same parameters the render graph uses. It is entirely
    /// our own, it updates automatically whenever a camera is retuned, and it
    /// tells you more than a picture of a body ever could.
    private func bodyCard(_ cam: Camera) -> some View {
        let selected = model.current?.id == cam.id
        return Button {
            model.select(cam)
        } label: {
            VStack(spacing: 5) {
                ZStack(alignment: .bottomTrailing) {
                    Group {
                        if let ui = SwatchStore.image(for: cam.id) {
                            Image(uiImage: ui).resizable().aspectRatio(contentMode: .fill)
                        } else {
                            Theme.surfaceHigh
                        }
                    }
                    .frame(width: 66, height: 50)
                    .clipShape(RoundedRectangle(cornerRadius: 8))

                    if cam.frame != .none {
                        Image(systemName: "film")
                            .font(.system(size: 8, weight: .bold))
                            .foregroundStyle(Theme.text)
                            .padding(3)
                            .background(.black.opacity(0.6), in: Circle())
                            .padding(3)
                    }
                }
                .overlay(
                    RoundedRectangle(cornerRadius: 8)
                        .stroke(selected ? Theme.accent : Color.white.opacity(0.10),
                                lineWidth: selected ? 2 : 1)
                )
                .shadow(color: selected ? Theme.accent.opacity(0.45) : .clear, radius: 6)

                Text(cam.name)
                    .font(Theme.mono(9, selected ? .bold : .medium))
                    .foregroundStyle(selected ? Theme.text : Theme.textDim)
                    .lineLimit(1)
            }
            .frame(width: 70)
        }
    }
}
