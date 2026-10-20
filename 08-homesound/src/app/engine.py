"""homesound audio engine.

The core trick: instead of using macOS's Multi-Output Device (which has no
per-device delay control), we open one INDEPENDENT CoreAudio OutputStream per
speaker and feed each a differently time-shifted read of the same source.

That gives us a per-speaker millisecond delay knob on ordinary Bluetooth
speakers -- which is the one thing that makes mismatched cheap speakers
actually play in sync.

Clock model
-----------
There is one master timeline in frames since playback started. Every device
slot keeps its own read cursor. Each callback we compute where the cursor
*should* be (master_now - total_delay) and gently pull the real cursor toward
it. Small errors are corrected by a slow leaky integrator so nothing clicks;
large errors (device stall, resume from pause) hard-resync.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

import numpy as np
import sounddevice as sd

SR = 48000
BLOCKSIZE = 512
CHANNELS = 2

# how far off a cursor may drift before we snap instead of easing (frames)
HARD_RESYNC_FRAMES = int(SR * 0.060)
# fraction of the remaining error corrected per callback
EASE = 0.02
# seconds of history kept for live (system-audio) capture
LIVE_BUFFER_SEC = 6.0


# --------------------------------------------------------------------------
# Sources
# --------------------------------------------------------------------------
class Source:
    """Something the engine can read time-aligned audio out of."""

    duration_sec: float = 0.0
    name: str = ""
    kind: str = "none"

    def read(self, start: int, frames: int) -> np.ndarray:
        raise NotImplementedError

    def close(self) -> None:
        pass


class FileSource(Source):
    kind = "file"

    def __init__(self, path: str, name: str, data: np.ndarray):
        self.path = path
        self.name = name
        self._data = data
        self.duration_sec = len(data) / SR

    def read(self, start: int, frames: int) -> np.ndarray:
        out = np.zeros((frames, CHANNELS), dtype=np.float32)
        if start >= len(self._data):
            return out
        if start < 0:
            # cursor is still in the pre-roll silence ahead of the timeline
            skip = min(-start, frames)
            avail = self._data[0: frames - skip]
            out[skip: skip + len(avail)] = avail
            return out
        chunk = self._data[start: start + frames]
        out[: len(chunk)] = chunk
        return out

    @property
    def total_frames(self) -> int:
        return len(self._data)


class LiveSource(Source):
    """System audio captured from a loopback device (BlackHole).

    Writes into a ring buffer indexed by absolute frame number, so delayed
    readers can look backwards in time.
    """

    kind = "system"

    def __init__(self, device_index: int, name: str):
        self.name = name
        self.device_index = device_index
        self.duration_sec = 0.0
        self._n = int(SR * LIVE_BUFFER_SEC)
        self._ring = np.zeros((self._n, CHANNELS), dtype=np.float32)
        self._written = 0
        self._lock = threading.Lock()
        self._stream = sd.InputStream(
            device=device_index,
            samplerate=SR,
            channels=CHANNELS,
            dtype="float32",
            blocksize=BLOCKSIZE,
            callback=self._cb,
        )
        self._stream.start()

    def _cb(self, indata, frames, time_info, status):  # noqa: ANN001
        with self._lock:
            start = self._written % self._n
            end = start + frames
            if end <= self._n:
                self._ring[start:end] = indata
            else:
                split = self._n - start
                self._ring[start:] = indata[:split]
                self._ring[: end - self._n] = indata[split:]
            self._written += frames

    def read(self, start: int, frames: int) -> np.ndarray:
        out = np.zeros((frames, CHANNELS), dtype=np.float32)
        with self._lock:
            written = self._written
            if start < 0 or start + frames > written:
                return out
            if written - start > self._n:
                return out  # fell out of the history window
            s = start % self._n
            e = s + frames
            if e <= self._n:
                out[:] = self._ring[s:e]
            else:
                split = self._n - s
                out[:split] = self._ring[s:]
                out[split:] = self._ring[: e - self._n]
        return out

    def close(self) -> None:
        try:
            self._stream.stop()
            self._stream.close()
        except Exception:
            pass


# --------------------------------------------------------------------------
# Device slots
# --------------------------------------------------------------------------
@dataclass
class Slot:
    """One speaker in the group."""

    id: str
    index: int
    name: str
    kind: str
    channels: int
    auto_ms: float = 0.0
    trim_ms: float = 0.0
    gain: float = 1.0
    muted: bool = False
    peak: float = 0.0
    error: Optional[str] = None
    solo_click: bool = False  # calibration: only this slot emits the click

    stream: Optional[sd.OutputStream] = field(default=None, repr=False)
    cursor: int = 0
    _primed: bool = False

    @property
    def total_delay_ms(self) -> float:
        return self.auto_ms + self.trim_ms

    @property
    def delay_frames(self) -> int:
        return int(self.total_delay_ms * SR / 1000.0)


class Engine:
    def __init__(self, on_event: Optional[Callable[[str, dict], None]] = None):
        self.slots: dict[str, Slot] = {}
        self.source: Optional[Source] = None
        self.master_gain = 1.0
        self.master_muted = False
        self.state = "stopped"  # stopped | playing | paused

        self._t0 = 0.0            # perf_counter at (virtual) timeline zero
        self._paused_frame = 0
        self._lock = threading.RLock()
        self._on_event = on_event or (lambda *_: None)

        # calibration
        self.calibrating: Optional[str] = None
        self._click = self._make_click()
        self._cal_taps: list[float] = []
        self._cal_t0 = 0.0

    # -- timeline ---------------------------------------------------------
    def _master_frame(self) -> int:
        if self.state == "playing":
            return int((time.perf_counter() - self._t0) * SR)
        return self._paused_frame

    @property
    def position_sec(self) -> float:
        return max(0.0, self._master_frame() / SR)

    @property
    def duration_sec(self) -> float:
        return self.source.duration_sec if self.source else 0.0

    # -- click track for calibration --------------------------------------
    @staticmethod
    def _make_click() -> np.ndarray:
        """1-second buffer: a short bright click at frame 0, then silence."""
        buf = np.zeros((SR, CHANNELS), dtype=np.float32)
        n = int(SR * 0.006)
        t = np.arange(n) / SR
        env = np.exp(-t * 900.0)
        tone = (np.sin(2 * np.pi * 2200 * t) * env * 0.5).astype(np.float32)
        buf[:n, 0] = tone
        buf[:n, 1] = tone
        return buf

    # -- device slots -----------------------------------------------------
    def add(self, dev: dict) -> None:
        with self._lock:
            if dev["id"] in self.slots:
                return
            slot = Slot(
                id=dev["id"],
                index=dev["index"],
                name=dev["name"],
                kind=dev["kind"],
                channels=min(2, dev["channels"]),
                auto_ms=dev.get("auto_ms", 0.0),
            )
            self.slots[slot.id] = slot
            self._rebalance()
            if self.state == "playing":
                self._open(slot)

    def remove(self, dev_id: str) -> None:
        with self._lock:
            slot = self.slots.pop(dev_id, None)
            if slot:
                self._close(slot)
                self._rebalance()

    def _rebalance(self) -> None:
        """Normalise auto delays so the SLOWEST speaker gets 0 extra delay.

        We can only ever delay a speaker, never rush it, so everything is
        aligned to whichever device is intrinsically latest.
        """
        if not self.slots:
            return
        raw = {s.id: s.__dict__.get("_raw_latency_ms", s.auto_ms) for s in self.slots.values()}
        worst = max(raw.values()) if raw else 0.0
        for s in self.slots.values():
            s.__dict__.setdefault("_raw_latency_ms", s.auto_ms)
            s.auto_ms = round(worst - s.__dict__["_raw_latency_ms"], 2)

    # -- stream lifecycle -------------------------------------------------
    def _open(self, slot: Slot) -> None:
        if slot.stream is not None:
            return
        try:
            slot._primed = False
            slot.error = None
            stream = sd.OutputStream(
                device=slot.index,
                samplerate=SR,
                channels=slot.channels,
                dtype="float32",
                blocksize=BLOCKSIZE,
                callback=self._make_cb(slot),
            )
            stream.start()
            slot.stream = stream
        except Exception as e:  # device vanished, busy, unsupported rate...
            slot.error = f"{type(e).__name__}: {e}"
            slot.stream = None
            self._on_event("toast", {"level": "error",
                                     "message": f"{slot.name}: {slot.error}"})

    def _close(self, slot: Slot) -> None:
        st, slot.stream = slot.stream, None
        if st is not None:
            try:
                st.stop()
                st.close()
            except Exception:
                pass
        slot.peak = 0.0

    def _make_cb(self, slot: Slot):
        def cb(outdata, frames, time_info, status):  # noqa: ANN001
            try:
                target = self._master_frame() - slot.delay_frames

                if not slot._primed:
                    slot.cursor = target
                    slot._primed = True
                else:
                    err = target - slot.cursor
                    if abs(err) > HARD_RESYNC_FRAMES:
                        slot.cursor = target
                    else:
                        slot.cursor += int(err * EASE)

                if self.calibrating is not None:
                    if slot.id == self.calibrating:
                        idx = slot.cursor % SR
                        take = self._click[idx: idx + frames]
                        block = np.zeros((frames, CHANNELS), dtype=np.float32)
                        block[: len(take)] = take
                        if len(take) < frames:
                            block[len(take):] = self._click[: frames - len(take)]
                    else:
                        block = np.zeros((frames, CHANNELS), dtype=np.float32)
                elif self.source is not None and self.state == "playing":
                    block = self.source.read(slot.cursor, frames)
                else:
                    block = np.zeros((frames, CHANNELS), dtype=np.float32)

                g = 0.0 if (slot.muted or self.master_muted) else slot.gain * self.master_gain
                block = block * g

                slot.peak = float(np.abs(block).max()) if block.size else 0.0

                if slot.channels == 1:
                    outdata[:, 0] = block.mean(axis=1)
                else:
                    outdata[:] = block[:, : slot.channels]

                slot.cursor += frames
            except Exception as e:
                slot.error = f"{type(e).__name__}: {e}"
                outdata.fill(0)

        return cb

    # -- transport --------------------------------------------------------
    def play(self) -> None:
        with self._lock:
            if self.source is None:
                raise RuntimeError("no source loaded")
            if not self.slots:
                raise RuntimeError("no speakers in the group")
            self._t0 = time.perf_counter() - (self._paused_frame / SR)
            self.state = "playing"
            for s in self.slots.values():
                s._primed = False
                self._open(s)

    def pause(self) -> None:
        with self._lock:
            if self.state != "playing":
                return
            self._paused_frame = self._master_frame()
            self.state = "paused"
            for s in self.slots.values():
                self._close(s)

    def stop(self) -> None:
        with self._lock:
            self._paused_frame = 0
            self.state = "stopped"
            for s in self.slots.values():
                self._close(s)

    def seek(self, position_sec: float) -> None:
        with self._lock:
            frame = max(0, int(position_sec * SR))
            self._paused_frame = frame
            if self.state == "playing":
                self._t0 = time.perf_counter() - (frame / SR)
                for s in self.slots.values():
                    s._primed = False

    def set_source(self, src: Source) -> None:
        with self._lock:
            was = self.state
            self.stop()
            if self.source:
                self.source.close()
            self.source = src
            self._paused_frame = 0
            if was == "playing":
                self.play()

    # -- calibration ------------------------------------------------------
    def start_calibration(self, dev_id: str) -> None:
        with self._lock:
            if dev_id not in self.slots:
                raise RuntimeError("device not in group")
            self.calibrating = dev_id
            self._cal_taps = []
            self._paused_frame = 0
            self._t0 = time.perf_counter()
            self.state = "playing"
            self._cal_t0 = self._t0
            for s in self.slots.values():
                s._primed = False
                self._open(s)

    def tap(self) -> dict:
        """User tapped in time with the click they heard.

        The click fires once per second on the engine timeline. The phase
        offset of the taps tells us how late the speaker actually is.
        """
        with self._lock:
            if self.calibrating is None:
                raise RuntimeError("not calibrating")
            elapsed = time.perf_counter() - self._cal_t0
            phase_ms = (elapsed % 1.0) * 1000.0
            # fold into -500..+500 so taps just after the click read small
            if phase_ms > 500.0:
                phase_ms -= 1000.0
            self._cal_taps.append(phase_ms)

            taps = self._cal_taps[-8:]
            med = float(np.median(taps)) if taps else 0.0
            return {"taps": len(self._cal_taps), "offset_ms": round(med, 1)}

    def stop_calibration(self) -> None:
        with self._lock:
            self.calibrating = None
            self._cal_taps = []
            self.stop()

    # -- state ------------------------------------------------------------
    def slot_dict(self, s: Slot) -> dict:
        return {
            "id": s.id,
            "name": s.name,
            "kind": s.kind,
            "channels": s.channels,
            "auto_ms": round(s.auto_ms, 2),
            "trim_ms": round(s.trim_ms, 1),
            "total_delay_ms": round(s.total_delay_ms, 2),
            "gain": round(s.gain, 3),
            "muted": s.muted,
            "active": s.stream is not None,
            "peak": round(s.peak, 4),
            "error": s.error,
        }

    def transport_dict(self) -> dict:
        src = self.source
        return {
            "state": self.state,
            "position_sec": round(self.position_sec, 3),
            "duration_sec": round(self.duration_sec, 3),
            "source": ({"kind": src.kind, "name": src.name,
                        "path": getattr(src, "path", "")} if src else None),
        }

    def shutdown(self) -> None:
        with self._lock:
            self.stop()
            if self.source:
                self.source.close()
                self.source = None
