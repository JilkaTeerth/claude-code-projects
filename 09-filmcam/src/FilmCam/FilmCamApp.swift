import SwiftUI

@main
struct FilmCamApp: App {
    var body: some Scene {
        WindowGroup {
            CameraView()
                .preferredColorScheme(.dark)
                .statusBarHidden()
        }
    }
}
