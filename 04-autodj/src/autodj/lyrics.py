"""Transcribe each song's vocal stem with word level timestamps.

The critic uses this to tell whether a vocal is cut mid-word or mid-line, and whether
an incoming singer starts on the beginning of a line. Wordplay transitions use it to
find lyric hand offs.

usage: python -m autodj.lyrics music/*.mp3
writes lyrics/<name>.json: {"words": [{"w", "start", "end"}], "lines": [{"text", "start", "end"}]}
"""
import json
import sys
from pathlib import Path

import librosa
import soundfile as sf
from faster_whisper import WhisperModel

ROOT = Path(__file__).resolve().parent.parent


def clean_words(words):
    """Whisper sometimes stretches a word across a long instrumental gap. No sung word
    lasts more than ~1.2 s, so pull such a word's start in to just before its end."""
    out = []
    for w in words:
        w = dict(w)
        if w["end"] - w["start"] > 1.2:
            w["start"] = round(w["end"] - 0.6, 2)
        out.append(w)
    return out


def main(paths):
    model = WhisperModel("small", device="cpu", compute_type="int8")
    out_dir = ROOT / "lyrics"
    out_dir.mkdir(exist_ok=True)
    for p in paths:
        name = Path(p).stem
        dst = out_dir / f"{name}.json"
        if dst.exists():
            continue
        # decode ourselves (the bundled PyAV version clashes with faster-whisper's decoder)
        audio, sr = sf.read(ROOT / "stems" / name / "vocals.flac", dtype="float32")
        audio = librosa.resample(audio.mean(axis=1), orig_sr=sr, target_sr=16000)
        segs, info = model.transcribe(audio, word_timestamps=True,
                                      vad_filter=False, condition_on_previous_text=False,
                                      no_speech_threshold=0.9, language="en" if "Bunny" not in name else None)
        words, lines = [], []
        for s in segs:
            lines.append({"text": s.text.strip(), "start": round(s.start, 2), "end": round(s.end, 2)})
            for w in s.words or []:
                words.append({"w": w.word.strip(), "start": round(w.start, 2), "end": round(w.end, 2)})
        dst.write_text(json.dumps({"language": info.language, "words": words, "lines": lines}, indent=1))
        print(f"{name}: {len(words)} words, {len(lines)} lines ({info.language})", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
