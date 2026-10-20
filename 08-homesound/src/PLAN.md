# PLAN, strict, phased, resumable

Every task has: an **ID**, a **definition of done**, and a **verification command**. Do not mark a task done in `STATE.md` until its verification passes. Phases are strictly ordered except P7.

---

## The architecture in one paragraph

Bluetooth cannot synchronize multiple speakers, that's physics, not a missing feature. So we don't use it as a transport. Instead: **make every speaker in the house look like a network audio receiver, and drive them all from the Mac over Wi-Fi.** Three transports, in increasing order of effort and capability, AirPlay 2 (free, native, zero-config, but only reaches AirPlay speakers), macOS Multi-Output Device (free, reaches anything the Mac can output to, but no per-device latency control), and Snapcast (free, reaches anything with a browser nearby, and is the only one with a per-room millisecond offset knob). We build all three, measure, and keep whichever covers the most rooms with no audible echo.

**The target end-state chain:**

```
iPhone ──AirPlay──▶ Mac (AirPlay Receiver)
                     │
                     ▼
              BlackHole 2ch  (free virtual audio cable)
                     │
                     ▼
               snapserver (Mac, brew)
                     │
        ┌────────────┼────────────┬──────────────┐
        ▼            ▼            ▼              ▼
   snapclient    snapclient   browser tab    AirPlay 2
   (old laptop)  (old phone)  (any device)   (native)
        │            │            │              │
        ▼            ▼            ▼              ▼
    wired hi-fi   BT speaker   BT speaker    HomePod/etc
   ← each with its own tunable latency offset in ms →
```

---

# P0, Research & plan ✅ DONE

Complete. See `RESEARCH.md`.

---

# P1, Inventory & feasibility gate

**Purpose:** With ₹0, spare devices are the only currency. Count them before designing anything.

### `P1-T1` Fill the inventory
- **Do:** Walk the house. Fill both tables in `INVENTORY.md` completely.
- **Done when:** No `?` remains in `INVENTORY.md`.
- **Verify:** `grep -c '?' ~/Projects/homesound/INVENTORY.md` returns `0`
- **Human task.** Claude cannot do this.

### `P1-T2` Classify each speaker
- **Do:** For each speaker row, assign a track:
  - **Track A**, already an AirPlay 2 receiver → free, zero work
  - **Track B**, Mac can reach it directly (BT pair, or AUX cable to Mac) → Multi-Output candidate
  - **Track C**, a spare device sits near it → Snapcast client node
  - **Dead**, Alexa/Nest/no path, no spare device → excluded, document why
- **Done when:** Every speaker has exactly one track assigned in `INVENTORY.md`.
- **Verify:** Read `INVENTORY.md`; count of classified speakers == count of speakers.

### `P1-T3` Feasibility gate
- **Do:** Confirm ≥2 speakers land in Tracks A/B/C. If fewer, the whole project is not achievable at ₹0, **STOP**, write the finding in `logs/decisions.md`, and present Teerth the cheapest unblock (see § Deferred).
- **Done when:** Explicit go/no-go recorded in `logs/decisions.md`.
- **Verify:** `grep -i 'P1-T3' ~/Projects/homesound/logs/decisions.md` returns a line.

---

# P2, Track A: native AirPlay 2 (the free win)

**Purpose:** Grab the zero-effort result first. If Teerth owns 2+ AirPlay 2 speakers, iOS already does perfect clock-synced multi-room and no software needs writing.

### `P2-T1` Enumerate AirPlay targets
- **Do:** On iPhone: Control Center → hold the audio card → AirPlay icon. List every device that appears. Same on Mac: Control Center → Sound.
- **Done when:** The list is written into `INVENTORY.md` under "Confirmed AirPlay targets".
- **Verify:** That section is non-empty.

### `P2-T2` Multi-select test
- **Do:** Select 2+ AirPlay targets simultaneously. Play a track with a sharp transient (hi-hat, clap, not pads). Stand between the two rooms.
- **Done when:** You can state clearly: sync is perfect / slight echo / unusable.
- **Verify:** Result recorded in `logs/decisions.md`.

### `P2-T3` Record coverage
- **Do:** Note exactly which rooms Track A covers, and which are left.
- **Done when:** `logs/decisions.md` has a "Track A covers: …" line.
- **Note:** If Track A already covers every room you care about, **you are done.** Stop here. Skip to P7. Don't build Snapcast for its own sake.

---

# P3, Track B: Mac Multi-Output Device

**Purpose:** Cover speakers the Mac can talk to directly. Free, ~30 minutes, but has a known weakness (no per-device latency control) that P3-T3 exists to measure.

### `P3-T1` Snapshot baseline, DO THIS FIRST
- **Do:**
  ```bash
  system_profiler SPAudioDataType > ~/Projects/homesound/configs/audio-baseline.txt
  system_profiler SPBluetoothDataType > ~/Projects/homesound/configs/bluetooth-baseline.txt
  ```
- **Done when:** Both files exist and are non-empty.
- **Verify:** `test -s ~/Projects/homesound/configs/audio-baseline.txt && echo OK`
- **Why:** This Mac does real work. Everything must be revertible.

### `P3-T2` Build the Multi-Output Device
- **Do:** Open **Audio MIDI Setup** → `+` → *Create Multi-Output Device*. Add every Track B speaker.
  - **Built-in Output must be first / the clock source**, macOS misbehaves otherwise.
  - **Enable Drift Correction on every member EXCEPT the clock source.**
- **Done when:** The device exists and appears in the Sound output menu.
- **Verify:** `system_profiler SPAudioDataType | grep -i "multi-output"` returns a match.

### `P3-T3` Measure the drift, the honest test
- **Do:** Play a transient-heavy track through the Multi-Output Device. For each pair of member speakers, stand between them and judge. Record ms estimates if you can hear a distinct slap-back.
- **Done when:** A drift table exists in `logs/decisions.md`, one row per pair.
- **Expected result:** All-wired or all-AirPlay members will be fine. **Mixing Bluetooth with AirPlay members will almost certainly echo**, BT buffers ~150-200ms, AirPlay ~2s. Multi-Output has no knob to fix this. That is the expected finding, and it is *why* P4 exists.

### `P3-T4` Verdict
- **Do:** Decide which subset of speakers Track B can serve without audible echo. It may be a smaller set than you added.
- **Done when:** "Track B final set: …" recorded in `logs/decisions.md`.

---

# P4, Track C: Snapcast hub (the real system)

**Purpose:** The only free path with a **per-client latency offset in milliseconds**. This is the knob that makes heterogeneous cheap speakers actually sync. Everything before this was warm-up.

### `P4-T1` Install
- **Do:**
  ```bash
  brew install snapcast          # v0.35.0, confirmed available
  brew install --cask blackhole-2ch
  ```
  BlackHole is a free open-source virtual audio driver, it lets us capture Mac output and feed it into snapserver. Reboot may be required for the driver to load.
- **Done when:** Both installed.
- **Verify:** `which snapserver && system_profiler SPAudioDataType | grep -i blackhole`

### `P4-T2` Configure and start snapserver
- **Do:** Write `configs/snapserver.conf` with a pipe or BlackHole-capture source. Start snapserver. Open Snapweb.
- **Done when:** `http://localhost:1780` loads the Snapweb UI in a browser.
- **Verify:** `curl -s -o /dev/null -w '%{http_code}' http://localhost:1780` returns `200`
- **Save:** the working conf into `configs/`.

### `P4-T3` First client, the proof
- **Do:** On any spare device (old phone, old laptop, iPad, second browser window), open `http://<mac-lan-ip>:1780` and let it play. Connect that device to a speaker (BT pair or AUX cable).
- **Done when:** Audio from the Mac comes out of that speaker, via the network, in sync with the Mac.
- **Verify:** Client appears in Snapweb's client list.
- **Risk R5:** Mobile browsers throttle background tabs. Keep the screen awake; note if it drops.

### `P4-T4` Remaining clients
- **Do:** Repeat P4-T3 for every Track C speaker. Native `snapclient` (via brew/apt) is more reliable than a browser tab wherever the spare device can run it.
- **Done when:** Every Track C speaker has a client in Snapweb.
- **Verify:** Snapweb client count == Track C speaker count.

### `P4-T5` Tune latency, the payoff
- **Do:** In Snapweb, set each client's latency offset. Method: play a click track, walk the house, increase the offset on whichever room arrives *early* until the slap-back disappears. Iterate.
- **Done when:** You can walk the whole house with no audible echo.
- **Verify:** Final per-client offsets recorded in `configs/latency-offsets.md`.
- **This is the deliverable.** This is the thing you couldn't buy for ₹0 anywhere else.

---

# P5, iPhone as the source

**Purpose:** Until now the Mac is the source. This phase makes the iPhone the source, so music, YouTube, anything on the phone feeds the whole house.

### `P5-T1` Enable AirPlay Receiver on the Mac
- **Do:** System Settings → General → AirDrop & Handoff → **AirPlay Receiver: On**. Set "Allow AirPlay for: Anyone on the same network" or your Apple account.
- **Done when:** The Mac appears in the iPhone's AirPlay list and audio from the phone plays out of the Mac.
- **Verify:** By ear.

### `P5-T2` ⚠️ KEY ASSUMPTION, verify capturability
- **Do:** With the iPhone AirPlaying to the Mac, set the Mac's output device to **BlackHole 2ch**. Check whether snapserver receives the stream.
- **Done when:** Either confirmed working, or confirmed impossible.
- **Verify:** Audio reaches the Snapcast clients.
- **If this fails (Risk R1):** macOS may route AirPlay-receiver audio outside the normal output chain. **Fallback, and it's a fine one:** keep the Mac as the source (Apple Music / Spotify / YouTube on the Mac) and control everything from the phone via the Snapweb UI in Safari. You lose "play from phone", you keep the whole synced house. Record the fallback decision and move on, do not sink a session into fighting this.

### `P5-T3` Wire the full chain
- **Do:** iPhone → Mac → BlackHole → snapserver → all rooms. End to end.
- **Done when:** Playing a song on the iPhone fills the house in sync.
- **Verify:** By ear, walking the house.

---

# P6, Daily-driver hardening

**Purpose:** A demo that works once is not a system. This makes it survive reboots and daily use.

### `P6-T1` Start/stop scripts
- **Do:** `scripts/homesound-up.sh` and `scripts/homesound-down.sh`, start/stop snapserver, switch audio devices, restore output.
- **Verify:** Both run clean from a fresh terminal.

### `P6-T2` Auto-start
- **Do:** LaunchAgent plist in `configs/`, loaded so snapserver starts at login.
- **Verify:** `launchctl list | grep -i snap` after a reboot.

### `P6-T3` Revert script, required, not optional
- **Do:** `scripts/homesound-revert.sh`, unload LaunchAgent, delete Multi-Output Device, restore default output, optionally `brew uninstall`.
- **Verify:** Run it; confirm `system_profiler SPAudioDataType` matches `configs/audio-baseline.txt` in the ways that matter.
- **Why:** This Mac is Teerth's work machine. An escape hatch is mandatory.

### `P6-T4` Live with it
- **Do:** Use it for a week. Log every failure in `logs/decisions.md`.
- **Done when:** A week has passed and the failure list is written.

---

# P7, Opportunity evaluation *(independent, runnable any time)*

### `P7-T1` Read `OPPORTUNITY.md`
### `P7-T2` Pressure-test it
- **Do:** Run `/llm-council` on: *"Is a zero-config multi-room audio app for people who own cheap mismatched Bluetooth speakers worth building as a product in 2026, given Auracast is shipping in phones?"*
- **Note:** This burns real credits. It's a genuine tradeoff decision, so it qualifies, but do it deliberately, not casually.
### `P7-T3` Decide
- Personal system only / portfolio piece / pursue as product. Record in `logs/decisions.md`. Then graduate to the vault via `/obsidian-graduate`.

---

# Deferred, costs money (DO NOT EXECUTE under current constraints)

Listed so the ₹0 ceiling is visible, not so it gets crossed. Revisit only if Teerth explicitly lifts the budget.

| Item | Approx cost | What it unblocks |
|---|---|---|
| Raspberry Pi Zero 2 W ×N | ~₹1,500 each | A dedicated, always-on, reliable Snapcast/AirPlay node per room. Removes all "spare device" and browser-throttling problems. This is the single highest-leverage purchase. |
| USB DAC / 3.5mm adapters | ~₹500 each | Better audio quality off Pi nodes |
| WiiM Mini | ~₹6,000 each | Commercial, works instantly, AirPlay 2 + Chromecast built in |
| Sonos | ₹20,000+ each | The thing this project exists to avoid buying |

---

# Stop conditions

Stop and report to Teerth, rather than pushing on, if:
- P1-T3 fails the feasibility gate (fewer than 2 reachable speakers)
- P5-T2 fails **and** the fallback is also unacceptable to him
- Any step would require spending money
- Any step would leave the Mac's audio in a broken state with no revert path
