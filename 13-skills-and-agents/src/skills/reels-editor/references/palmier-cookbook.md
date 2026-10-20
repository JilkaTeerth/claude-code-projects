# Palmier Pro MCP cookbook

Mechanics, frame math, and the gotchas that cost real time. Everything here is read off
the live tool schemas, trust this over intuition, and correct it here when the app
updates.

**Prerequisite:** the Palmier Pro desktop app must be **running**. The MCP is a local HTTP
server on `127.0.0.1:19789`. If tools 404 or the server shows as failed, the app isn't
open, that is always the first thing to check.

---

## The units problem (read this first)

Three different units are in play and mixing them is the #1 source of wrong edits:

| Unit | Where it's used |
|---|---|
| **Project frames** | `startFrame`, `endFrame`, `durationFrames`, `trimStartFrame`, `trimEndFrame`, keyframe rows |
| **Source seconds** | `source: [start, end]`, `detect_beats` results, `inspect_media` segments, `search_media` hits |
| **Normalized 0 to 1** | `transform`, keyframe `position`/`scale`/`crop`, text `transform` |

The tools convert between frames and seconds themselves. **Never multiply by fps
yourself** except when converting a `detect_beats` result, which is the one documented
case.

**Beat → timeline frame:**
```
timelineFrame = startFrame + (beatSeconds × fps − trimStartFrame) / speed
```
For a music bed placed at frame 0, untrimmed, speed 1, this is just `beatSeconds × 30`.

**Critical:** `trimStartFrame` and `trimEndFrame` are measured in **project frames**, never
the source's own fps, even though they are offsets into the source media.

---

## Fill vs fit, silent letterboxing

**Palmier auto-fits, it does not auto-fill.** A still whose aspect ratio doesn't match the
canvas gets pillar/letterboxed, and the only sign is a `transform` in the `add_clips`
response like `"transform": {"height": 0.75}`. On a reel this reads as black bars.

To **fill** the canvas, scale up by the fitted axis's shortfall. For a 1080×1920 (0.5625)
canvas:

| Source | Aspect | Fitted | Fill scale | Fill w × h |
|---|---|---|---|---|
| 1200×1600 phone portrait | 0.75 | `height: 0.75` | ÷0.75 = **1.333** | 1.333 × 1.000 |
| 1280×1280 square | 1.0 | `height: 0.5625` | ÷0.5625 = **1.778** | 1.778 × 1.000 |
| 1920×1080 landscape | 1.778 | `height: 0.3164` | ÷0.3164 = **3.16** | 3.160 × 1.000 |

Landscape into 9:16 crops away 68% of the width, usually reframe or letterbox
deliberately instead. Feed the fill values in as the *starting* scale of the Ken Burns
keyframes below, and remember position must compensate (`topLeft = (1 − scale) / 2`).

## Resolution hijack, check after your first add_clips

`add_clips` **silently rewrites the project resolution to match the first clip** and only
mentions it in `notes`:
```
"notes": ["Matched timeline resolution to clip: 720×1280."]
```
A project created at 1080p 9:16 will quietly become 720×1280 the moment you drop a 720p
phone clip on it. **Read `notes` on every mutation**, and re-assert after import:
```
set_project_settings  width:1080  height:1920  fps:30
```
Existing clips are re-fitted automatically, so doing this after the first `add_clips` is
safe and costs one call.

## Ken Burns, the one that will bite you

`set_keyframes` `scale` is **NOT a scale factor.** It is the clip's normalized width and
height in canvas coords, where `1.0` fills that axis. And `position` is the clip's
**TOP-LEFT corner**, not its centre.

So a naive push-in to 1.08 anchors to the top-left and drifts the subject down-right.
To push in **centred**, position must compensate: `topLeft = (1 − scale) / 2`.

**Centred push-in, 1.00 → 1.08 over a 60-frame clip:**
```jsonc
// property: "scale"
[[0, 1.00, 1.00, "smooth"], [60, 1.08, 1.08, "smooth"]]
// property: "position"   ← both are required
[[0, 0.00, 0.00, "smooth"], [60, -0.04, -0.04, "smooth"]]
```
`(1 − 1.08) / 2 = −0.04`. Negative top-left is correct and expected, the clip is larger
than the canvas and hangs off both edges equally.

**Off-centre drift** (push in *and* toward a subject on the left): keep the scale rows,
then bias the end position, e.g. `-0.055` in x instead of `-0.04`. Keep the bias under 3%
of frame width.

Other keyframe facts:
- Frames are **clip-relative** (0 = the clip's first frame), so keyframes survive moves.
- `smooth` is the default interp and is what you want. `linear` is the amateur look.
- Setting `volume` or `opacity` via `set_clip_properties` **clears** that property's
  keyframe track. Set statics first, keyframe second, never the reverse.
- Passing an empty array clears a track.

---

## Build order

This order minimises re-reads and avoids the overwrite traps:

```
1  manage_project  action:create   aspectRatio:"9:16" quality:"1080p" fps:30
2  get_timeline                    ← ONCE. Check canGenerate. Note track ids.
3  import_media    source:{path:"/abs/dir"}    ← whole folder, recursive
4  get_media                       ← map every asset id to what it actually is
5  add_clips       video spine, in order, ONE track
6  add_clips       stills into the gaps
7  set_keyframes   Ken Burns per still
8  add_clips       music (audio track) → detect_beats → move_clips to snap
9  add_texts       hook, lower-thirds, end card
10 apply_color     grade one clip, then paste its `color` object to the rest
11 export_project
```

**Do not re-read `get_timeline` between your own edits.** Every mutation returns a delta
in `get_timeline` vocabulary, `clips` (resulting state), `shifted` (`{track, fromFrame,
by, count}`), `removedClipIds`, `createdTracks`, `notes`. Patch your model from that.
Re-read only after a failure that suggests staleness.

---

## Gotchas

**Import**
- `source.path` files are **referenced in place, not copied** into the project. If the
  source folder moves or is cleaned, the project breaks. For anything you care about,
  move the footage out of `~/Downloads` into a project folder *before* importing.
- Directory imports land in a **subfolder mirroring the source directory name**, not
  directly in the target folder. Account for it when filtering `get_media` by folder.
- Directory import is recursive and replicates subfolder structure as media folders.

**Tracks and clips**
- Track **index 0 renders on top.** Indexes shift as tracks are created; `manage_tracks`
  takes the stable `trackId` instead, use that.
- Clips on the **same track overwrite** on overlap: an overlapping `add_clips` trims,
  splits, or removes what was there. Layering requires a different track.
- `add_clips`: set `trackIndex` on **every** entry or **none**. Mixing is rejected.
- `source` and `endFrame` are **mutually exclusive** on an entry. For stills, `endFrame`
  is the frame-exact choice; `source` is a display length in seconds.
- Removing **every** clip on a track deletes the track itself and shifts indices. Re-read
  before any further index-based call.
- A clip occupies `[start, end)`, end exclusive, `duration = end − start`.
- IDs are short prefixes. Pass them back **exactly** as given, never pad or complete them.
- Folders have no ids; they're paths (`'B-roll/Sunset'`), created on demand.

**Video with audio**
- Placing a video with audio on a video track auto-creates a **linked** audio clip. It's
  folded into the video clip as `audio: {id, track, …}`, address the audio side by that
  nested id, not by hunting the audio track.
- Timing changes (`speed`, trims, `durationFrames`) propagate to the linked partner.
  Per-clip fields (`volume`, `opacity`, `transform`) do **not**.

**Speed**
- `speed` < 1 slows down and **lengthens** the clip on the timeline; > 1 shortens it.
  Downstream clips shift. Do speed ramps before you fine-tune positions, or pass
  `durationFrames` alongside to pin the length.

**Text**
- `fontSize` is capped at **300**. `tracking` runs −20…100. `cornerRadius` max 300.
- `transform` is the normalized text-box **centre** (`centerX`/`centerY`). Centre-only
  auto-fits the box; supply all four fields to override it.
- Safe area in normalized y: **0.115 → 0.8125**. Keep `centerX` ≤ 0.83.
- Animations that suit this brand: `popIn` (hooks), `wordPop` / `highlightPop`
  (energy formats), `slideUp` (lower-thirds). Avoid `typewriter`, it dates the edit.
- `add_texts` with `trackIndex` omitted on all entries creates **one new top track**, and text obeys the same-track overwrite rule. **Two text clips that overlap in time
  cannot share a track**: the later one silently truncates the earlier one. A title at
  478 to 538 plus a wordmark at 492 to 538 in the same call leaves the title as `[478, 492]`.
  Overlapping text = one clip per track. Add them in separate calls, each omitting
  `trackIndex`, so each gets its own new top track.
- **`transform` with only `centerX`/`centerY` auto-fits the box and can override your
  `fontSize`.** Supply `width` and `height` too whenever the size matters, otherwise a
  96px title renders at whatever the auto-fit decides, and stacked text collides.
- Use `add_captions` for spoken audio, not `add_texts`.

**Fonts**
- Verify a font exists before specifying it, an unavailable name falls back silently:
  `system_profiler SPFontsDataType | grep -i "Full Name:" | sort -u`
- Archivo / Anton / Bebas / Inter are **not** installed on this machine. The working
  house pairing is **`Avenir Next Condensed`** (bold, uppercase) for display and
  **`Avenir Next`** for body, both are macOS system fonts, both look the part.

**Colour**
- `apply_color` **merges** by default, pass `reset:true` to start neutral.
- `temperature`: **higher = warmer** (6500 neutral). `tint`: **positive = green**, so
  fighting fluorescent green needs a **negative** tint.
- To copy a grade: read a graded clip's `color` object and pass it as the `color`
  parameter on the others. It **replaces** the whole grade and is mutually exclusive with
  `reset` and the individual knobs.
- `apply_color` is the colorist path; `apply_effect` is looks/FX. Don't confuse them.

**Layout**
- Split screen, PIP, and grids belong to `apply_layout`, it sets transform and crop
  together. Do **not** hand-build them with `transform` or keyframed position/scale. This
  matters for the Grid Drop format.

**Generation**
- Call `list_models` before any `generate_*` or `upscale_media`. If `get_timeline` reports
  `canGenerate: false`, generation will fail, the user needs to sign in and subscribe.
- Palmier's image-generation credits were exhausted on 2026-07-15 on this machine;
  generation is not part of the reel workflow. Don't build a plan that depends on it.
- `compose_music` caps around 160s regardless of the requested length. Loop for longer.

**Captions / speech**
- `get_transcript` gives spoken words; `inspect_media` on a voice clip yields ASR sentence
  segments in project frames, that's what transcript-sync alignment is built on.
- `remove_silence` and `denoise_audio` are the Silent Coach format's whole toolkit.
- `get_timeline` returns caption clips as `captionGroup` summaries. Restyle a whole group
  with `update_text` + `captionGroupId` from that summary alone. Only pass
  `captionDetail:true` (windowed) when you must touch an individual caption clip.

---

## Export

```
export_project  mode:"video"  codec:"H.264"  resolution:"Match Timeline"
                outputPath:"/abs/path/NAME.mp4"
```
Returns `status` + `jobId`; poll `manage_exports` for progress. Omitting `outputPath`
writes to `~/Downloads`. Existing files are overwritten by default, pass
`overwrite:false` to refuse.

Other modes: `xml` (Premiere), `fcpxml` (Resolve/FCP, also carries text, transforms,
crop, opacity, and keyframes that `xml` cannot), `palmier` (self-contained package,
exports every timeline).

**Then verify.** An export that returned `started` is not a finished reel:
```bash
ffprobe -v error -select_streams v:0 \
  -show_entries stream=width,height,r_frame_rate \
  -show_entries format=duration -of default=nw=1 FINAL.mp4
```
Expect `1080×1920`, `30/1`. Then pull frames at the hook, a middle cut, and the end, and
look at them.

---

## Recovery

- `undo` reverses the last action.
- If indices look wrong after a removal, re-read `get_timeline`, don't guess.
- Projects live at `~/Documents/Palmier Pro/*.palmier`. These are media bundles, are
  large, and are **not** in the source archive, Time Machine only.
- `send_feedback` exists. Palmier is new; when a tool behaves unexpectedly, using it is
  genuinely worth the 20 seconds.
