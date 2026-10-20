# STATE, the resume point

> **Last updated:** 2026-08-02, first real two-speaker sync achieved.
> **Read `CLAUDE.md` § RESUME PROTOCOL before acting on this file.**

---

## WHERE THIS ACTUALLY IS

**It works.** Two Bluetooth speakers, EDIFIER D32 and JBL Go 3, play one source
in sync from the Mac, with a measured residual error of **+7.4 / +7.7 ms** and
under 1.2 ms of jitter. That is well below the ~20 ms audible echo threshold.
Zero rupees spent, zero spare devices used.

Start it with `./run.sh`, open `http://127.0.0.1:8777`, load the scene
**"Edifier + JBL"**, press play.

### The architecture changed, Snapcast was dropped

The old plan (P1-P6 below) assumed a per-speaker delay knob required Snapcast,
a server, and one spare device per room. That was wrong. `app/engine.py` opens
one independent CoreAudio `OutputStream` per speaker and feeds each a
differently time-shifted read of a single master timeline. Same knob, no
server, no spare devices, no browser tabs. **Phases P4 and P5 are obsolete.**

### The finding the project rests on

Bluetooth latency is *stable* during continuous playback (0.5 to 3.3 ms jitter
measured) and only shifts across stream restarts (~10 ms). So a **static**
per-speaker trim is sufficient, no drift correction, no shared clock.
`RESEARCH.md` § "Why Bluetooth is a dead end" is overstated: BT can't
*self*-synchronise, but two BT speakers driven from one Mac sync fine.

---

## CURRENT TASK

**`S4-T6`, Write `app/static/app.js`. The web UI does not exist.**

**The finding:** `app/static/index.html:388` loads `/static/app.js`, and **that
file was never written**. The markup, all five `<template>` blocks, and 854
lines of CSS are complete, but there is zero JavaScript, so nothing renders,
no button works, and the UI is a dead shell. Everything achieved so far was
driven by `curl` against the API directly.

**Exact next action:** Write `app/static/app.js` against the existing markup
hooks, element `id`s in `index.html`, `data-ref` attributes inside the
templates. It needs to cover:
- `GET /api/state` on load, then the `/ws` WebSocket for live updates
- Speaker rack rendered from `tpl-speaker`; trim slider (±2000ms), gain, mute,
  remove, peak meters
- Transport: play / pause / stop / seek
- Available outputs (`tpl-avail`) and Bluetooth connect/disconnect (`tpl-bt`)
- Library modal (`tpl-lib`), calibration wizard, toasts, offline overlay
- Scenes, **not in the markup yet**, needs UI added for `/api/scenes/*`

**Definition of done:** Loading `http://127.0.0.1:8777` shows both speakers
with live meters, and changing a trim slider moves the audio.

**Do not re-run audio tests to verify.** Teerth has confirmed by ear that the
two speakers are perfectly matched; the calibration below is settled.

---

## CALIBRATED VALUES, the working configuration

| Speaker | BT address | auto_ms | trim_ms | total delay | notes |
|---|---|---|---|---|---|
| EDIFIER D32 | `08-f0-b6-a8-d2-ea` | 0.0 | 0.0 | **0.0 ms** | reference, the intrinsically latest speaker |
| JBL Go 3 | `28-fa-19-6d-0a-fc` | 100.66 | **126.4** | **227.1 ms** | quieter into the mic by ~5x; balance by ear |

Saved as scene **"Edifier + JBL"** in `configs/scenes.json`.
Re-derive with `scripts/measure_sync.py`, **not** with `/api/calibrate/auto-all`.

---

## PHASE PROGRESS

| Phase | Status | Notes |
|---|---|---|
| **P0, Research & plan** | ✅ DONE | Architecture since superseded, see above |
| **P1, Inventory & feasibility gate** | ✅ MOOT | Custom engine removed the spare-device dependency |
| **P2, Track A: native AirPlay 2** | ⬜ NOT STARTED | Still a free win for any AirPlay speaker |
| **P3, Track B: Mac Multi-Output** | ✅ SUPERSEDED | The custom engine is strictly better, it has per-device delay |
| **P4, Track C: Snapcast hub** | ❌ DROPPED | Not needed. See `logs/decisions.md` 2026-08-02 |
| **P5, iPhone-as-source chain** | ⬜ OPEN | Still the real unknown, needs BlackHole. See R1 |
| **P6, Daily-driver hardening** | ⬜ PARTIAL | `run.sh` exists; no auto-start, no teardown script |
| **P7, Opportunity evaluation** | ⬜ OPTIONAL | Unblocked, independent |

---

## TASK LEDGER

### S1, Two-speaker sync (the current system)
- [x] `S1-T0` Both BT speakers connected simultaneously as independent CoreAudio outputs
- [x] `S1-T1` Both producing audio at once from the engine
- [x] `S1-T2` Measure true residual sync error without restarting streams
- [x] `S1-T3` Trim solved (+126.4 ms) and verified repeatable
- [x] `S1-T4` Saved as a scene
- [x] `S1-T5` **Confirmed by ear, Teerth: "they are perfectly matched"** (2026-08-02)
- [ ] `S1-T6` Balance gains, the JBL is much quieter than the Edifier

### S2, Make it a daily driver
- [ ] `S2-T1` Auto-connect both speakers on scene load (currently manual `blueutil`)
- [ ] `S2-T2` Auto-start on login (LaunchAgent)
- [ ] `S2-T3` Teardown/revert script
- [ ] `S2-T4` Handle a speaker dropping out mid-playback without killing the group

### S3, Source beyond local files
- [ ] `S3-T1` Install BlackHole 2ch, verify `/api/source/system` captures system audio
- [ ] `S3-T2` Enable AirPlay Receiver on Mac; confirm iPhone can target it
- [ ] `S3-T3` Verify AirPlay-to-Mac audio is capturable via BlackHole *(KEY ASSUMPTION, may fail, R1)*

### S4, Fix what this session exposed
- [x] `S4-T1` Warn instead of silently applying a clamped trim
- [x] `S4-T2` Make `confidence` reflect repeatability, not just peak sharpness
- [x] `S4-T5a` Raise trim limit from ±500ms to ±2000ms (`TRIM_LIMIT_MS`, server + slider)
- [ ] `S4-T3` Rewrite `measure_latency` to reuse the engine's open streams
- [ ] `S4-T4` Wire `scripts/measure_sync.py` into the UI as the real calibrate button
- [ ] `S4-T5` Update `API.md`, it omits `/api/calibrate/auto`, `auto-all`, and all `/api/scenes/*`
- [ ] `S4-T6` **Write `app/static/app.js`**, the UI has no JavaScript at all

### S5, Scale to N speakers (the actual goal)
- [ ] `S5-T1` Find the simultaneous-BT ceiling, how many A2DP streams the Mac's radio sustains
- [ ] `S5-T2` Generalise `scripts/measure_sync.py` beyond exactly 2 speakers
- [ ] `S5-T3` Test a mixed group (BT + built-in + wired), this is what needed the ±2000ms trim

---

## OPEN RISKS

| # | Risk | Impact if true | Where it gets resolved |
|---|---|---|---|
| R1 | AirPlay-to-Mac audio may not be capturable by BlackHole | iPhone can't be the source; Mac-only playback, controlled from phone via the web UI | `S3-T3` |
| R2 | A third simultaneous A2DP speaker may exceed Bluetooth bandwidth | Caps the system at 2 BT speakers; more rooms need AirPlay or wired | untested |
| R3 | Trim may need re-deriving after every reconnect (~10 ms shift per restart) | Mild recalibration chore; 10 ms is under threshold so probably ignorable | observed, tolerable |
| R4 | A speaker dropping out mid-playback may stall or desync the group | Playback breaks in real use | `S2-T4` |
| R5 | `/api/calibrate/auto-all` gives wrong answers on Bluetooth | Users trust a broken number | mitigated by S4-T1/T2; fully fixed at `S4-T3` |

---

## BLOCKERS

None. `S1-T5` is a human listening task.
