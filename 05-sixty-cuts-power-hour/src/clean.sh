#!/usr/bin/env bash
# Clean pre-pass for the power hour rebuild.
#
# build.sh used to burn the leader, movie name card, and drink badge straight
# into each round with ffmpeg overlays. We are moving assembly into an NLE
# instead, so every round now needs to exist as a plain, overlay free clip
# that an editor can drop on a timeline and trust:
#
#   - exactly 60.000 seconds long
#   - 1280x720, 30fps, setsar=1, letterboxed with pad (never cropped)
#   - loudnorm audio, continuous for the full 60s, same targets as build.sh
#   - encoded with the same VOPTS as build.sh, so clean/NN.mp4 concats fine
#     alongside anything else already cut with that pipeline
#   - no text, no leader, no cards, no badges, nothing overlaid at all
#
# This reuses three pieces of logic straight out of build.sh's cmd_cut so the
# two pipelines agree on what a "round" is:
#   - lead_in()          measures and skips leading silence when a row has
#                         no explicit offset in the tsv
#   - the three way pick between -ss <start>, -ss 0, and -stream_loop -1
#     depending on how long the source runs versus the round length
#   - the anullsrc fallback for a source clip that has no audio stream
#
#   ./clean.sh          cut clean/NN.mp4 for every row in clips.tsv
#
# Same env override style as build.sh:
#   ROUND=60 ./clean.sh

set -uo pipefail
cd "$(dirname "$0")"

TSV="${TSV:-clips.tsv}"
ROUND="${ROUND:-60}"      # length of one round, seconds

RAW="raw"; CLEAN="clean"
VOPTS=(-c:v libx264 -preset veryfast -crf 21 -pix_fmt yuv420p -g 60 -r 30
       -c:a aac -b:a 160k -ar 48000 -ac 2 -movflags +faststart)
mkdir -p "$CLEAN"

rows() { tail -n +2 "$TSV" | grep -v '^[[:space:]]*$'; }
dur() { ffprobe -v error -show_entries format=duration -of csv=p=0 "$1" 2>/dev/null; }

# how much dead air a clip opens on. scene rips often start on black and
# silence, so burning that into the round would waste the sound only window.
# lifted verbatim from build.sh cmd_cut.
lead_in() {
  local s
  s=$(ffmpeg -nostdin -v info -t 20 -i "$1" -af "silencedetect=n=-45dB:d=0.7" \
        -f null - 2>&1 \
      | awk '/silence_start: 0(\.0*)?$/ {f=1} f && /silence_end/ {print $5; exit}')
  awk -v s="${s:-0}" 'BEGIN{ if (s+0 > 0.4 && s+0 < 9) printf "%.2f", s-0.15; else print 0 }'
}

cmd_cut() {
  echo "clean rounds of ${ROUND}s, no overlays"

  rows | while IFS=$'\t' read -r min act side movie year scene search url off; do
    n=$(printf '%02d' "$min")
    [ -s "$RAW/$n.mp4" ] || { echo "skip  $n (no raw)"; continue; }
    [ -s "$CLEAN/$n.mp4" ] && { echo "have  $n"; continue; }

    d=$(dur "$RAW/$n.mp4"); d=${d:-0}
    if [ -n "${off:-}" ]; then start="$off"; else start=$(lead_in "$RAW/$n.mp4"); fi
    # a source too short to fill the round just runs round again rather than
    # freezing on a still frame for the rest of the minute
    if awk -v d="$d" -v s="$start" -v p="$ROUND" 'BEGIN{exit !(d >= s + p)}'; then
      SRC=(-ss "$start" -i "$RAW/$n.mp4")
    elif awk -v d="$d" -v p="$ROUND" 'BEGIN{exit !(d >= p)}'; then
      SRC=(-ss 0 -i "$RAW/$n.mp4"); start=0
    else
      SRC=(-stream_loop -1 -i "$RAW/$n.mp4"); start="0, looped, source is only ${d%%.*}"
    fi

    if ffprobe -v error -select_streams a -show_entries stream=index -of csv=p=0 \
         "$RAW/$n.mp4" | grep -q .; then AIN="[0:a]"; else AIN="[1:a]"; fi

    echo "round $n  $movie  (from ${start}s)"
    ffmpeg -nostdin -y -v error \
      "${SRC[@]}" \
      -f lavfi -t "$ROUND" -i anullsrc=r=48000:cl=stereo \
      -filter_complex "\
[0:v]scale=1280:720:force_original_aspect_ratio=decrease,\
pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30,\
tpad=stop_mode=clone:stop_duration=${ROUND}[v];\
${AIN}aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,\
loudnorm=I=-16:TP=-1.5:LRA=11,apad[a]" \
      -map "[v]" -map "[a]" -t "$ROUND" "${VOPTS[@]}" "$CLEAN/$n.mp4" \
      || echo "  !! round $n failed"
  done
}

cmd_cut
