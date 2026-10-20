# homesound, API contract

Backend: FastAPI on `http://127.0.0.1:8777`. Frontend: static SPA served from `/`.
This file is the contract between `app/server.py` and `app/static/`. Both sides must match it exactly.

---

## Core concepts

- **Output device**, a CoreAudio output (a BT speaker, built-in speakers, an AirPlay target). Identified by `id` (stable string).
- **Group**, the set of devices currently playing in sync. Each member has its own `trim_ms`, `gain`, `muted`.
- **trim_ms**, per-speaker manual latency trim, −500…+500 ms. Positive = delay this speaker further. This is the knob that makes mismatched speakers line up.
- **auto_ms**, latency the engine computed automatically from CoreAudio's reported device latency. Read-only.
- **total_delay_ms**, `auto_ms + trim_ms`, what the engine actually applies. Read-only.

---

## REST

### `GET /api/state`
Full snapshot. Frontend calls once on load, then relies on the WebSocket.
```json
{
  "transport": {
    "state": "playing",          // "stopped" | "playing" | "paused"
    "position_sec": 42.7,
    "duration_sec": 213.4,
    "source": { "kind": "file", "name": "track.wav", "path": "/abs/path" }
  },
  "group": [
    {
      "id": "coreaudio:3",
      "name": "JBL Go 3",
      "kind": "bluetooth",        // "bluetooth" | "builtin" | "airplay" | "virtual" | "other"
      "channels": 2,
      "auto_ms": 180.0,
      "trim_ms": -20.0,
      "total_delay_ms": 160.0,
      "gain": 1.0,
      "muted": false,
      "active": true,
      "peak": 0.34,               // 0..1, for the level meter
      "error": null
    }
  ],
  "available": [ /* same shape, devices NOT in the group */ ],
  "bluetooth": [
    { "address": "28-fa-19-6d-0a-fc", "name": "JBL Go 3", "connected": false, "is_audio": true }
  ],
  "master": { "gain": 1.0, "muted": false },
  "engine": { "samplerate": 48000, "blocksize": 512, "running": true }
}
```

### `GET /api/devices`, re-scan and return `{ group, available, bluetooth }`

### Group management
- `POST /api/group/add` → `{ "id": "coreaudio:3" }`
- `POST /api/group/remove` → `{ "id": "coreaudio:3" }`
- `POST /api/group/set` → `{ "id": "...", "trim_ms": -20, "gain": 0.8, "muted": false }` (any subset of fields)

### Master
- `POST /api/master` → `{ "gain": 0.9, "muted": false }` (any subset)

### Transport
- `POST /api/transport/play`
- `POST /api/transport/pause`
- `POST /api/transport/stop`
- `POST /api/transport/seek` → `{ "position_sec": 30.0 }`

### Source
- `POST /api/source/file` → `{ "path": "/abs/path.wav" }`
- `POST /api/source/system` → `{}`, capture system audio via BlackHole (requires BlackHole installed)
- `GET  /api/library` → `{ "files": [ { "name": "...", "path": "...", "duration_sec": 0 } ] }`

### Bluetooth
- `POST /api/bluetooth/connect` → `{ "address": "28-fa-..." }` (slow, ~2 to 8s)
- `POST /api/bluetooth/disconnect` → `{ "address": "..." }`

### Calibration
- `POST /api/calibrate/start` → `{ "id": "coreaudio:3" }`, loops a click on that device only
- `POST /api/calibrate/stop`
- `POST /api/calibrate/tap` → `{ "id": "..." }`, user tapped in time with what they hear; server derives trim

All mutating endpoints return `{ "ok": true }` or `{ "ok": false, "error": "..." }` with HTTP 200.

---

## WebSocket `/ws`

Server pushes a message every ~100ms while playing, and immediately on any state change.

```json
{ "type": "state", "data": { /* identical shape to GET /api/state */ } }
```

Other message types:
```json
{ "type": "toast", "level": "info|warn|error", "message": "JBL Go 3 connected" }
{ "type": "calibrating", "id": "coreaudio:3", "active": true }
```

Client sends nothing except an optional `{"type":"ping"}`.

---

## Design tokens (from ui-ux-pro-max, style: Dark Mode OLED)

| Role | Hex |
|---|---|
| Background | `#0F0F23` |
| Surface | `#1E1B4B` |
| Surface raised | `#312E81` |
| Accent / CTA | `#F97316` |
| Text | `#F8FAFC` |

- **Heading font:** Fira Code · **Body font:** Fira Sans
- Effects: minimal glow (`text-shadow: 0 0 10px`), high contrast, low white emission
- Icons: inline SVG only (Lucide-style), never emoji
- Transitions 150 to 300ms; respect `prefers-reduced-motion`
- All clickable elements get `cursor: pointer` and a visible focus ring
