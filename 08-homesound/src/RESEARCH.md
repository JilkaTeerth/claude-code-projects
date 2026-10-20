# RESEARCH, what's true, and why the plan looks like it does

Compiled 2026-07-31. Sources at the bottom.

---

## Why Bluetooth is a dead end

This is the single most important finding, and it kills the naive version of the idea.

Bluetooth A2DP was designed as a **point-to-point** protocol: one source, one sink. Every workaround for "connect to two speakers at once" runs into the same three walls:

1. **No shared clock.** Each speaker plays on its own internal clock. There is no timestamp in the stream telling both speakers *when* to play a given sample. They will drift apart, not might, will.
2. **Per-device latency varies.** Different chipsets, different codecs (SBC vs AAC vs aptX), different buffer sizes. Two speakers from different brands can differ by 100ms+, which is well past the ~20ms threshold where the human ear stops hearing "one sound" and starts hearing slap-back echo.
3. **Bandwidth.** Splitting an A2DP stream N ways degrades the codec for all of them.

"Multipoint," which sounds like it should help, is the opposite feature: it lets **one speaker connect to two phones**, not one phone drive two speakers.

Vendor features like Samsung Dual Audio, JBL PartyBoost, and Bose SimpleSync do work, but only within one brand, using proprietary sync layers, and typically capped at 2 devices. Teerth's speakers are a mixed bag, so none of these apply.

**Conclusion: don't use Bluetooth as the transport. Use it only as the last hop**, network → a device near the speaker → Bluetooth → that one speaker. One BT link per speaker, never one source split across many.

### The exception that's coming: Auracast

Auracast (Bluetooth LE Audio broadcast) genuinely solves this, one transmitter, unlimited synchronized receivers, and it's built into the protocol rather than bolted on. As of 2026 it's in Android 16 at the OS level, Samsung Galaxy S23+, Pixel 8+, and 2026 LG/Samsung TVs. Frankfurt Airport deployed it in January 2026.

**But it's irrelevant to this project**, for two reasons: it requires both transmitter and receiver hardware support (Teerth's existing cheap speakers have none), and iPhone support is not there. It matters strategically, not practically, see `OPPORTUNITY.md`.

---

## Transport comparison

| Transport | Sync quality | Cost | Reaches | Per-room latency knob | Verdict |
|---|---|---|---|---|---|
| **AirPlay 2** | Excellent, real clock sync | ₹0, native on iPhone/Mac | Only AirPlay 2 receivers | ❌ | **Track A.** Free win where it applies |
| **macOS Multi-Output Device** | Good within a class, poor across classes | ₹0, built into macOS | Anything the Mac can output to | ❌ (drift correction only) | **Track B.** Easy, limited |
| **Snapcast** | Excellent, timestamped frames, shared time base | ₹0, open source | Anything running a client, incl. a browser tab | ✅ **milliseconds, per client** | **Track C.** The real system |
| **Chromecast groups** | Good | ₹0 | Cast devices only | ❌ | Not usable, iPhone-hostile, and won't sync with AirPlay devices |
| **Bluetooth direct** | Unusable across brands | ₹0 | 2 speakers, same brand | ❌ | Rejected, see above |
| **AmpMe / SoundSeeder** | ~"95% accurate" per vendor claims | Free tier w/ ads | Phones running the app | Manual, app-level | Rejected, turns phones into speakers, doesn't drive *your* speakers |
| **Sonos** | Excellent | ₹20,000+/room | Sonos only | n/a | Violates ₹0 |

---

## Why Snapcast is the answer

Snapcast has no playback engine, it does exactly one thing, which is the hard thing: **distribution and synchronization.** The server stamps each audio chunk with timing data; each client buffers, then schedules playback against a shared time base. That's the same technique Sonos uses, open-sourced.

Three properties make it the right fit here:

1. **Per-client latency offset, in milliseconds, adjustable live from a web UI.** No other free option has this. It is precisely the knob that fixes a house full of mismatched cheap speakers.
2. **Browser clients.** Since v0.21, Snapweb does synchronized playback in a browser tab over WebSocket. This is the ₹0 unlock, *any* device with a browser and a speaker connection becomes a node, with no install and no purchase. The catch: the tab must stay open and foregrounded (mobile browsers throttle background tabs, logged as Risk R5).
3. **It's on Homebrew.** `snapcast 0.35.0`, confirmed available, not yet installed on this machine.

**Known weakness:** Snapcast sends over TCP, so packet loss and jitter directly hurt it. Wired Ethernet is ideal; Wi-Fi works but a congested 2.4GHz network will cause dropouts. If rooms drop out, suspect the network before suspecting Snapcast.

---

## The ₹0 chain, and its one weak link

```
iPhone ──AirPlay──▶ Mac (AirPlay Receiver, macOS built-in)
                     └─▶ BlackHole 2ch (free virtual audio driver)
                          └─▶ snapserver (brew, free)
                               └─▶ clients (browser tabs / native) ──▶ speakers
```

Every component is free and already available. **The unverified link is Mac AirPlay-Receiver audio → BlackHole.** macOS may route AirPlay-receiver audio through a path that a virtual output driver can't capture. This is Risk R1, tested at `P5-T2`.

If it fails, the fallback costs almost nothing in practice: play from the **Mac** instead (Apple Music, Spotify, YouTube all run there), and control it from the phone via Snapweb in Safari. You lose "source from phone", you keep the synchronized house.

---

## Turning a dumb speaker into a network receiver

Two free options for any spare device sitting near a speaker:

- **`shairport-sync`**, makes the device an AirPlay 2 receiver. Best if the device is a Linux box or a Pi. Combine with the device's Bluetooth to drive a BT speaker, or a cable to drive a hi-fi.
- **`snapclient` / Snapweb tab**, makes it a Snapcast node. Preferred here, because of the latency knob.

`balenaSound` is a prebuilt image that does Bluetooth + AirPlay + Spotify Connect in one shot, worth knowing about if a Raspberry Pi turns up in the inventory.

---

## What this means for the plan

- Build Track A first, it may already be enough, and it's free and instant.
- Expect Track B to disappoint when Bluetooth and AirPlay devices are mixed in one Multi-Output Device (~150ms vs ~2s buffers, no way to compensate). Measure it anyway; the measurement is what justifies Track C.
- Track C is the real system. Budget the most time there.
- Alexa and Google Nest speakers are almost certainly unreachable at ₹0 from an iPhone. Say so plainly rather than burning sessions on it.

---

## Sources

- [snapcast/snapcast, GitHub](https://github.com/snapcast/snapcast)
- [Snapcast has synchronous browser playback since v0.21, Hacker News](https://news.ycombinator.com/item?id=24685269)
- [Snapcast Player Provider, Music Assistant](https://www.music-assistant.io/player-support/snapcast/)
- [Build a multi-room audio system with Raspberry Pi, Raspberry Pi Official Magazine](https://magazine.raspberrypi.com/articles/build-a-multi-room-audio-system-with-raspberry-pi)
- [I run Snapcast on Raspberry Pis instead of paying for Sonos, XDA](https://www.xda-developers.com/run-snapcast-on-raspberry-pis-instead-of-paying-for-sonos/)
- [Multi-Room Synchronization, Music Assistant / DeepWiki](https://deepwiki.com/music-assistant/server/5.5-multi-room-synchronization)
- [Set aggregate device settings in Audio MIDI Setup, Apple Support](https://support.apple.com/guide/audio-midi-setup/set-aggregate-device-settings-ams094c7edb4/mac)
- [Multi Output Device, BlackHole Wiki](https://github.com/ExistentialAudio/BlackHole/wiki/Multi-Output-Device)
- [Auracast FAQ, Bluetooth.com](https://www.bluetooth.com/auracast/faq/)
- [Consumer audio is going all in on Auracast, Bluetooth.com](https://www.bluetooth.com/blog/consumer-audio-is-going-all-in-on-auracast-broadcast-audio-are-you-keeping-up/)
- [Auracast Reality Check 2026, Venucast](https://venucast.com/blogs/news/auracast-reality-check-2026-does-bluetooth-auracast-actually-work-with-real-devices-today)
- [Turn old speakers into Bluetooth/AirPlay receivers, balena](https://blog.balena.io/turn-your-old-speakers-or-hi-fi-into-bluetooth-receivers-using-only-a-raspberry-pi/)
- [Build an AirPlay receiver using a Raspberry Pi, XDA](https://www.xda-developers.com/build-airplay-receiver-using-raspberry-pi/)
- [Multiroom audio: Bluetooth is just not cut out for multiroom, Raspberry Pi Forums](https://forums.raspberrypi.com/viewtopic.php?t=113288)
- [AmpMe, App Store](https://apps.apple.com/us/app/ampme-speaker-music-sync/id986905979)
- [SoundSeeder](https://soundseeder.com/)
