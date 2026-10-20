#!/usr/bin/env python3
"""P4-PoC: enumerate CoreAudio output devices and report per-device latency hints.

This is the feasibility probe for the whole project. If sounddevice cannot see
each Bluetooth speaker as an independent output device, the architecture is dead.
"""
import sounddevice as sd

print(f"PortAudio: {sd.get_portaudio_version()[1]}")
print(f"Host APIs: {[a['name'] for a in sd.query_hostapis()]}")
print()

outs = []
for i, d in enumerate(sd.query_devices()):
    if d["max_output_channels"] > 0:
        outs.append((i, d))

print(f"{'idx':<4} {'ch':<3} {'default_sr':<11} {'lo_lat':<9} {'hi_lat':<9} name")
print("-" * 78)
for i, d in outs:
    print(
        f"{i:<4} {d['max_output_channels']:<3} "
        f"{d['default_samplerate']:<11.0f} "
        f"{d['default_low_output_latency']*1000:<9.2f} "
        f"{d['default_high_output_latency']*1000:<9.2f} "
        f"{d['name']}"
    )

print()
print(f"TOTAL OUTPUT DEVICES: {len(outs)}")
try:
    print(f"CURRENT DEFAULT OUT : {sd.query_devices(kind='output')['name']}")
except Exception as e:
    print(f"CURRENT DEFAULT OUT : <error: {e}>")
