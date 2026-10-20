# DECISION LOG

Append-only. Newest at the bottom. Every deviation from `PLAN.md` gets a line here, with the reason.

Format: `YYYY-MM-DD · TASK-ID · what happened · why it matters`

---

**2026-07-31 · P0 · Architecture chosen: AirPlay 2 first, Snapcast as the real system, Bluetooth explicitly rejected as a transport.**
Reason: Bluetooth A2DP is point-to-point with no shared clock and per-device latency variance well past the ~20ms echo threshold. No amount of software fixes it. Snapcast is the only free option with a per-client millisecond latency offset, which is the specific knob a house of mismatched cheap speakers needs. See `RESEARCH.md`.

**2026-07-31 · P0 · Constraints locked from Teerth:** ₹0 budget (software only), iPhone + Mac (M1 Max, macOS 26.6), speakers are a mixed bag of dumb BT + smart WiFi + wired hi-fi, intent is "build it for me, then evaluate as a product".
Reason: The ₹0 constraint is the dominant one, it means spare devices already in the house are the only available receiver nodes, and it's why P1 (inventory) blocks everything.

**2026-07-31 · P0 · Environment verified:** Homebrew present at `/opt/homebrew/bin/brew`; `snapcast 0.35.0` available, not installed; 2 Bluetooth devices paired (1 connected).
Reason: Confirms the Track C toolchain is installable at ₹0 with no surprises.

**2026-08-02 · ARCH · Snapcast is no longer the architecture. A custom CoreAudio engine (`app/`) is.**
Reason: The original plan assumed the only way to get a per-speaker delay knob for free was Snapcast. That turned out to be wrong. `app/engine.py` opens one independent `sd.OutputStream` per speaker and feeds each a differently time-shifted read of one master timeline, which gives the same per-speaker millisecond trim with no server, no client nodes, and no spare devices required. This deletes the dependency on spare hardware that P1 was gating on.

**2026-08-02 · FINDING · macOS holds TWO Bluetooth A2DP speakers connected simultaneously, as independent CoreAudio outputs.**
Verified: EDIFIER D32 (08-f0-b6-a8-d2-ea) and JBL Go 3 (28-fa-19-6d-0a-fc) both `connected (master)` at once, both enumerated by PortAudio, both producing audio simultaneously from the engine. `RESEARCH.md` § "Why Bluetooth is a dead end" is too strong: BT cannot *self*-synchronise, but two BT speakers driven from one Mac with per-stream delay compensation sync fine. Bluetooth is dead as a *sync protocol*, not as a *transport*.

**2026-08-02 · FINDING · Bluetooth latency is STABLE during continuous playback (<2.5ms jitter). It is only unstable across stream restarts.**
Measured by `scripts/measure_sync.py`: within a continuous playback run, per-speaker click arrival jitter was 0.5 to 3.3ms. Across separate runs (each restarting the A2DP streams) the offset moved ~10ms. This is the finding the whole project rests on, a *static* per-speaker trim is sufficient. No drift correction needed.

**2026-08-02 · BUG · `calibrate.measure_latency` is unreliable on Bluetooth and must not be trusted.**
It opens a FRESH `sd.OutputStream` per repeat, so it measures the latency of a just-started A2DP stream, not of continuous playback. On the Edifier it returned 1196.42ms on one call and 645.62ms on the next (spread 406.69ms within a single 3-repeat call). It reported `confidence: 1.0` for both, the confidence metric measures correlation peak sharpness, not repeatability, so it is actively misleading. `approx_distance_m` came back as 221m, which should have been an obvious tell.
Consequence: `/api/calibrate/auto-all` computed a 772ms required trim, hit the ±500ms clamp in `server.py:360`, and silently applied a wrong value with no warning.
Correct measured answer, via `scripts/measure_sync.py`: JBL Go 3 needs **+126.4ms** trim relative to the Edifier at 0. Residual error +7.4/+7.7ms, repeatable.

**2026-08-02 · S1-T5 · Two-speaker sync CONFIRMED BY EAR.** Teerth: "they are perfectly matched".
Closes the loop on the +7.4ms measured result. The calibration (Edifier 0ms reference, JBL Go 3 +126.4ms) is settled, do not re-run audio tests to re-derive it, just load the "Edifier + JBL" scene.

**2026-08-02 · S4-T5a · Trim limit raised ±500ms → ±2000ms (`TRIM_LIMIT_MS` in `server.py`, slider in `index.html`).**
Reason: ±500ms is fine for two Bluetooth speakers but too tight the moment a group mixes transports, built-in output sits near 19ms while a slow BT speaker can exceed 600ms, and the trim has to span the whole spread. This was the first hard blocker to scaling past 2 speakers. Safe because `LIVE_BUFFER_SEC` keeps 6s of history for live capture.

**2026-08-02 · S4-T6 · FOUND: the web UI has no JavaScript. `app/static/app.js` was never written.**
`index.html:388` loads `/static/app.js`; the file does not exist. The markup (388 lines, 5 templates) and CSS (854 lines) are complete, so the page renders as a static shell where nothing is wired and no button works. Every result in this project so far was produced by `curl` against the API, never through the UI. This is now the top task, the engine is finished and the UI is the only thing standing between it and being usable.
