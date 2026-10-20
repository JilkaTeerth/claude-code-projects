"""homesound HTTP + WebSocket server."""
from __future__ import annotations

import asyncio
import contextlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Optional

import numpy as np
import soundfile as sf
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import calibrate
from . import devices as dev
from .engine import CHANNELS, SR, Engine, FileSource, LiveSource

HERE = Path(__file__).parent
STATIC = HERE / "static"
MEDIA_DIRS = [
    Path.home() / "Projects" / "homesound" / "media",
    Path.home() / "Music",
    Path.home() / "Downloads",
]
AUDIO_EXT = {".wav", ".mp3", ".m4a", ".flac", ".aiff", ".aif", ".ogg", ".opus", ".aac"}

# Max per-speaker manual trim. Was ±500ms, which is too tight once the group
# mixes transports: built-in output sits near 19ms while a slow Bluetooth
# speaker can land past 600ms, and the trim has to cover the whole spread.
# Live capture keeps LIVE_BUFFER_SEC (6s) of history, so 2s is safe.
TRIM_LIMIT_MS = 2000.0

app = FastAPI(title="homesound")

_events: list[asyncio.Queue] = []
_loop: Optional[asyncio.AbstractEventLoop] = None


def _emit(kind: str, data: dict) -> None:
    """Engine callbacks fire on audio threads -- hop back to the event loop."""
    if _loop is None:
        return
    for q in list(_events):
        with contextlib.suppress(Exception):
            _loop.call_soon_threadsafe(q.put_nowait, {"type": kind, **data})


engine = Engine(on_event=_emit)


# --------------------------------------------------------------------------
# audio loading
# --------------------------------------------------------------------------
def _resample(data: np.ndarray, src_sr: int) -> np.ndarray:
    if src_sr == SR:
        return data
    n_out = int(len(data) * SR / src_sr)
    x_old = np.linspace(0.0, 1.0, len(data), endpoint=False)
    x_new = np.linspace(0.0, 1.0, n_out, endpoint=False)
    return np.stack(
        [np.interp(x_new, x_old, data[:, c]) for c in range(data.shape[1])], axis=1
    ).astype(np.float32)


def _decode_ffmpeg(path: str) -> np.ndarray:
    """Fallback decoder for formats libsndfile won't open (mp3, m4a, aac)."""
    cmd = [
        "ffmpeg", "-v", "quiet", "-i", path,
        "-f", "f32le", "-acodec", "pcm_f32le",
        "-ac", str(CHANNELS), "-ar", str(SR), "-",
    ]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).reshape(-1, CHANNELS).copy()


def load_audio(path: str) -> np.ndarray:
    try:
        data, src_sr = sf.read(path, dtype="float32", always_2d=True)
        if data.shape[1] == 1:
            data = np.repeat(data, 2, axis=1)
        elif data.shape[1] > 2:
            data = data[:, :2]
        return _resample(np.ascontiguousarray(data), src_sr)
    except Exception:
        return _decode_ffmpeg(path)


# --------------------------------------------------------------------------
# state
# --------------------------------------------------------------------------
def build_state() -> dict[str, Any]:
    bt = dev.list_bluetooth()
    outs = dev.list_outputs()
    in_group = set(engine.slots.keys())
    return {
        "transport": engine.transport_dict(),
        "group": [engine.slot_dict(s) for s in engine.slots.values()],
        "available": [d for d in outs if d["id"] not in in_group],
        "bluetooth": bt,
        "master": {"gain": round(engine.master_gain, 3), "muted": engine.master_muted},
        "engine": {
            "samplerate": SR,
            "blocksize": 512,
            "running": engine.state == "playing",
            "calibrating": engine.calibrating,
        },
    }


def ok(**extra: Any) -> JSONResponse:
    return JSONResponse({"ok": True, **extra})


def fail(msg: str) -> JSONResponse:
    return JSONResponse({"ok": False, "error": msg})


# --------------------------------------------------------------------------
# routes
# --------------------------------------------------------------------------
@app.get("/api/state")
async def get_state():
    return build_state()


@app.get("/api/devices")
async def get_devices():
    dev.refresh_portaudio()
    s = build_state()
    return {"group": s["group"], "available": s["available"], "bluetooth": s["bluetooth"]}


@app.post("/api/group/add")
async def group_add(body: dict):
    target = body.get("id")
    match = next((d for d in dev.list_outputs(include_virtual=True) if d["id"] == target), None)
    if not match:
        return fail(f"device not found: {target}")
    engine.add(match)
    _emit("toast", {"level": "info", "message": f"Added {match['name']}"})
    return ok()


@app.post("/api/group/remove")
async def group_remove(body: dict):
    engine.remove(body.get("id", ""))
    return ok()


@app.post("/api/group/set")
async def group_set(body: dict):
    slot = engine.slots.get(body.get("id", ""))
    if not slot:
        return fail("device not in group")
    if "trim_ms" in body:
        slot.trim_ms = max(-TRIM_LIMIT_MS, min(TRIM_LIMIT_MS, float(body["trim_ms"])))
    if "gain" in body:
        slot.gain = max(0.0, min(2.0, float(body["gain"])))
    if "muted" in body:
        slot.muted = bool(body["muted"])
    return ok()


@app.post("/api/master")
async def set_master(body: dict):
    if "gain" in body:
        engine.master_gain = max(0.0, min(2.0, float(body["gain"])))
    if "muted" in body:
        engine.master_muted = bool(body["muted"])
    return ok()


@app.post("/api/transport/play")
async def t_play():
    try:
        engine.play()
        return ok()
    except Exception as e:
        return fail(str(e))


@app.post("/api/transport/pause")
async def t_pause():
    engine.pause()
    return ok()


@app.post("/api/transport/stop")
async def t_stop():
    engine.stop()
    return ok()


@app.post("/api/transport/seek")
async def t_seek(body: dict):
    engine.seek(float(body.get("position_sec", 0.0)))
    return ok()


@app.post("/api/source/file")
async def src_file(body: dict):
    path = body.get("path", "")
    if not os.path.isfile(path):
        return fail(f"no such file: {path}")
    try:
        data = await asyncio.to_thread(load_audio, path)
    except Exception as e:
        return fail(f"could not decode: {e}")
    engine.set_source(FileSource(path, Path(path).name, data))
    _emit("toast", {"level": "info", "message": f"Loaded {Path(path).name}"})
    return ok()


@app.post("/api/source/system")
async def src_system():
    bh = dev.blackhole_device()
    if not bh:
        return fail(
            "BlackHole not found. Install with: brew install --cask blackhole-2ch, "
            "then set it as the Mac's output device."
        )
    try:
        engine.set_source(LiveSource(bh["index"], "System audio (BlackHole)"))
    except Exception as e:
        return fail(str(e))
    _emit("toast", {"level": "info", "message": "Capturing system audio"})
    return ok()


@app.get("/api/library")
async def library():
    files = []
    seen: set[str] = set()
    for d in MEDIA_DIRS:
        if not d.is_dir():
            continue
        for p in sorted(d.rglob("*")):
            if p.suffix.lower() in AUDIO_EXT and p.name not in seen:
                seen.add(p.name)
                files.append({"name": p.name, "path": str(p), "duration_sec": 0})
            if len(files) >= 300:
                break
    return {"files": files}


@app.post("/api/bluetooth/connect")
async def bt_connect(body: dict):
    addr = body.get("address", "")
    okk, msg = await asyncio.to_thread(dev.bt_connect, addr)
    _emit("toast", {"level": "info" if okk else "error",
                    "message": msg or ("Connected" if okk else "Connect failed")})
    return ok() if okk else fail(msg)


@app.post("/api/bluetooth/disconnect")
async def bt_disconnect(body: dict):
    addr = body.get("address", "")
    okk, msg = await asyncio.to_thread(dev.bt_disconnect, addr)
    _emit("toast", {"level": "info" if okk else "error",
                    "message": msg or ("Disconnected" if okk else "Disconnect failed")})
    return ok() if okk else fail(msg)


@app.post("/api/calibrate/start")
async def cal_start(body: dict):
    try:
        engine.start_calibration(body.get("id", ""))
    except Exception as e:
        return fail(str(e))
    _emit("calibrating", {"id": body.get("id"), "active": True})
    return ok()


@app.post("/api/calibrate/tap")
async def cal_tap(body: dict):
    try:
        return ok(**engine.tap())
    except Exception as e:
        return fail(str(e))


@app.post("/api/calibrate/stop")
async def cal_stop():
    cal = engine.calibrating
    engine.stop_calibration()
    _emit("calibrating", {"id": cal, "active": False})
    return ok()


# -- acoustic auto-calibration (the good one) -------------------------------
@app.post("/api/calibrate/auto")
async def cal_auto(body: dict):
    """Measure one speaker's true acoustic latency with the Mac's microphone."""
    slot = engine.slots.get(body.get("id", ""))
    if not slot:
        return fail("device not in group")

    was_playing = engine.state == "playing"
    engine.pause()
    _emit("toast", {"level": "info", "message": f"Measuring {slot.name} — stay quiet"})
    try:
        res = await asyncio.to_thread(
            calibrate.measure_latency, slot.index, calibrate.default_input()
        )
    except Exception as e:
        return fail(str(e))
    finally:
        if was_playing:
            with contextlib.suppress(Exception):
                engine.play()

    if not res.get("ok"):
        _emit("toast", {"level": "error", "message": res.get("error", "measurement failed")})
        return fail(res.get("error", "measurement failed"))

    slot.__dict__["_measured_ms"] = res["latency_ms"]
    _emit("toast", {
        "level": "info",
        "message": f"{slot.name}: {res['latency_ms']:.1f}ms measured "
                   f"(confidence {res['confidence']:.0%})",
    })
    return ok(**res, id=slot.id)


@app.post("/api/calibrate/auto-all")
async def cal_auto_all():
    """Measure every speaker in the group, then solve the trims so they align.

    One button, whole house calibrated. This is the feature.
    """
    slots = list(engine.slots.values())
    if len(slots) < 1:
        return fail("no speakers in the group")

    was_playing = engine.state == "playing"
    engine.pause()
    measured: dict[str, float] = {}
    failures: list[str] = []

    try:
        inp = calibrate.default_input()
        for s in slots:
            _emit("toast", {"level": "info", "message": f"Measuring {s.name}…"})
            res = await asyncio.to_thread(calibrate.measure_latency, s.index, inp)
            if res.get("ok"):
                measured[s.id] = res["latency_ms"]
            else:
                failures.append(s.name)
    finally:
        if was_playing:
            with contextlib.suppress(Exception):
                engine.play()

    if not measured:
        _emit("toast", {"level": "error", "message": "Could not hear any speaker"})
        return fail("no speaker could be measured")

    # align everything to the latest speaker; we can delay but never rush
    worst = max(measured.values())
    clamped: list[str] = []
    for sid, ms in measured.items():
        slot = engine.slots[sid]
        wanted = round(worst - ms - slot.auto_ms, 1)
        slot.trim_ms = max(-TRIM_LIMIT_MS, min(TRIM_LIMIT_MS, wanted))
        if slot.trim_ms != wanted:
            clamped.append(f"{slot.name} wanted {wanted:+.0f}ms")

    msg = f"Calibrated {len(measured)} speaker(s)"
    if failures:
        msg += f" — could not hear: {', '.join(failures)}"
    if clamped:
        # Never apply a clamped trim silently: the speakers are NOT aligned,
        # and on Bluetooth a huge `wanted` almost always means the measurement
        # itself is bad rather than the speakers being genuinely that far apart.
        # See logs/decisions.md 2026-08-02, and use scripts/measure_sync.py.
        msg += (f" — TRIM CLAMPED at ±{TRIM_LIMIT_MS:.0f}ms ({'; '.join(clamped)}); "
                f"NOT in sync, measurement is probably wrong")
    _emit("toast", {"level": "warn" if (failures or clamped) else "info",
                    "message": msg})
    return ok(measured=measured, failures=failures,
              applied={s.id: s.trim_ms for s in slots})


# -- scenes -----------------------------------------------------------------
SCENES = Path.home() / "Projects" / "homesound" / "configs" / "scenes.json"


def _load_scenes() -> dict:
    if SCENES.exists():
        with contextlib.suppress(Exception):
            return json.loads(SCENES.read_text())
    return {}


@app.get("/api/scenes")
async def scenes_list():
    return {"scenes": sorted(_load_scenes().keys())}


@app.post("/api/scenes/save")
async def scenes_save(body: dict):
    name = (body.get("name") or "").strip()
    if not name:
        return fail("scene needs a name")
    data = _load_scenes()
    data[name] = {
        "devices": [
            {"id": s.id, "name": s.name, "trim_ms": s.trim_ms,
             "gain": s.gain, "muted": s.muted}
            for s in engine.slots.values()
        ],
        "master": {"gain": engine.master_gain, "muted": engine.master_muted},
    }
    SCENES.parent.mkdir(parents=True, exist_ok=True)
    SCENES.write_text(json.dumps(data, indent=2))
    _emit("toast", {"level": "info", "message": f"Saved scene “{name}”"})
    return ok()


@app.post("/api/scenes/load")
async def scenes_load(body: dict):
    scene = _load_scenes().get((body.get("name") or "").strip())
    if not scene:
        return fail("scene not found")

    outs = {d["id"]: d for d in dev.list_outputs(include_virtual=True)}
    for sid in list(engine.slots.keys()):
        engine.remove(sid)
    missing = []
    for entry in scene["devices"]:
        match = outs.get(entry["id"])
        if not match:
            missing.append(entry["name"])
            continue
        engine.add(match)
        slot = engine.slots[entry["id"]]
        slot.trim_ms = entry.get("trim_ms", 0.0)
        slot.gain = entry.get("gain", 1.0)
        slot.muted = entry.get("muted", False)

    engine.master_gain = scene.get("master", {}).get("gain", 1.0)
    engine.master_muted = scene.get("master", {}).get("muted", False)
    if missing:
        _emit("toast", {"level": "warn",
                        "message": f"Offline, skipped: {', '.join(missing)}"})
    return ok(missing=missing)


@app.post("/api/scenes/delete")
async def scenes_delete(body: dict):
    data = _load_scenes()
    data.pop((body.get("name") or "").strip(), None)
    SCENES.parent.mkdir(parents=True, exist_ok=True)
    SCENES.write_text(json.dumps(data, indent=2))
    return ok()


# --------------------------------------------------------------------------
# websocket
# --------------------------------------------------------------------------
@app.websocket("/ws")
async def ws(sock: WebSocket):
    await sock.accept()
    q: asyncio.Queue = asyncio.Queue()
    _events.append(q)
    try:
        await sock.send_json({"type": "state", "data": build_state()})
        while True:
            try:
                msg = await asyncio.wait_for(q.get(), timeout=0.1)
                await sock.send_json(msg)
            except asyncio.TimeoutError:
                await sock.send_json({"type": "state", "data": build_state()})
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        if q in _events:
            _events.remove(q)


# --------------------------------------------------------------------------
# static
# --------------------------------------------------------------------------
@app.get("/")
async def index():
    f = STATIC / "index.html"
    if not f.exists():
        return JSONResponse({"error": "UI not built yet"}, status_code=503)
    return FileResponse(f)


if STATIC.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")


@app.on_event("startup")
async def _startup():
    global _loop
    _loop = asyncio.get_running_loop()
    dev.list_bluetooth()  # warm the BT name cache so _classify works


@app.on_event("shutdown")
async def _shutdown():
    engine.shutdown()
