"""Device discovery: CoreAudio outputs + paired Bluetooth speakers."""
from __future__ import annotations

import re
import subprocess
from typing import Optional

import sounddevice as sd

BLUEUTIL = "/opt/homebrew/bin/blueutil"

# Outputs that are never speakers we'd want in a group.
_EXCLUDE = re.compile(
    r"(zoomaudio|microsoft teams|blackhole|soundflower|loopback|aggregate|multi-output)",
    re.I,
)

# Paired BT devices that are input peripherals, not audio sinks.
_NOT_AUDIO = re.compile(
    r"(mouse|mousey|trackpad|keyboard|magickey|magic key|k480|mx keys|mx master|"
    r"joy-con|iphone|ipad|find my)",
    re.I,
)


def refresh_portaudio() -> None:
    """Force PortAudio to re-enumerate.

    Required after a Bluetooth speaker connects or disconnects, otherwise
    sounddevice keeps serving a stale device list.
    """
    try:
        sd._terminate()
        sd._initialize()
    except Exception:
        pass


def _classify(name: str) -> str:
    n = name.lower()
    if "macbook" in n or "built-in" in n or "internal" in n:
        return "builtin"
    if "blackhole" in n or "aggregate" in n or "multi-output" in n:
        return "virtual"
    if "airplay" in n or "apple tv" in n or "homepod" in n or "google tv" in n:
        return "airplay"
    if _bt_names_cache and any(b.lower() in n for b in _bt_names_cache):
        return "bluetooth"
    return "other"


_bt_names_cache: list[str] = []


def list_outputs(include_virtual: bool = False) -> list[dict]:
    """Every usable CoreAudio output device."""
    out = []
    for idx, d in enumerate(sd.query_devices()):
        if d["max_output_channels"] < 1:
            continue
        name = d["name"]
        if not include_virtual and _EXCLUDE.search(name):
            continue
        # CoreAudio's own reported output latency is our starting estimate
        auto_ms = float(d.get("default_low_output_latency", 0.0)) * 1000.0
        out.append(
            {
                "id": f"coreaudio:{name}",
                "index": idx,
                "name": name,
                "kind": _classify(name),
                "channels": int(d["max_output_channels"]),
                "auto_ms": round(auto_ms, 2),
                "samplerate": float(d["default_samplerate"]),
            }
        )
    return out


def find_output(name_fragment: str) -> Optional[dict]:
    for d in list_outputs(include_virtual=True):
        if name_fragment.lower() in d["name"].lower():
            return d
    return None


def blackhole_device() -> Optional[dict]:
    return find_output("blackhole")


# --------------------------------------------------------------------------
# Bluetooth
# --------------------------------------------------------------------------
def _blueutil(*args: str, timeout: int = 20) -> tuple[bool, str]:
    try:
        r = subprocess.run(
            [BLUEUTIL, *args], capture_output=True, text=True, timeout=timeout
        )
        return r.returncode == 0, (r.stdout or r.stderr).strip()
    except FileNotFoundError:
        return False, "blueutil not installed (brew install blueutil)"
    except subprocess.TimeoutExpired:
        return False, "bluetooth operation timed out"
    except Exception as e:
        return False, str(e)


_PAIRED_RE = re.compile(
    r"address: ([0-9a-f\-]+), (not connected|connected[^,]*),.*?name: \"(.*?)\"", re.I
)


def list_bluetooth() -> list[dict]:
    """Paired Bluetooth devices, filtered down to plausible audio sinks."""
    global _bt_names_cache
    ok, out = _blueutil("--paired")
    if not ok:
        return []
    seen: set[str] = set()
    devices = []
    for addr, conn, name in _PAIRED_RE.findall(out):
        if addr in seen:
            continue
        seen.add(addr)
        is_audio = not _NOT_AUDIO.search(name)
        devices.append(
            {
                "address": addr,
                "name": name,
                "connected": conn.lower().startswith("connected"),
                "is_audio": is_audio,
            }
        )
    _bt_names_cache = [d["name"] for d in devices if d["is_audio"]]
    devices.sort(key=lambda d: (not d["is_audio"], not d["connected"], d["name"].lower()))
    return devices


def bt_connect(address: str) -> tuple[bool, str]:
    ok, msg = _blueutil("--connect", address, timeout=25)
    if ok:
        refresh_portaudio()
    return ok, msg


def bt_disconnect(address: str) -> tuple[bool, str]:
    ok, msg = _blueutil("--disconnect", address, timeout=25)
    if ok:
        refresh_portaudio()
    return ok, msg
