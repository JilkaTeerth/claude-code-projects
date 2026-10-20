#!/usr/bin/env bash
# Power hour builder.
#
# Sixty rounds, sixty seconds each, cut the way the format actually plays:
#
#   0:00  black, round number, then the academy leader counts down.
#         The scene's AUDIO IS ALREADY RUNNING under it. Sound is all you get.
#   0:20  the leader dissolves. The picture is revealed, already twenty
#         seconds into the scene, audio unbroken.
#   0:40  the movie name fades into the bottom left and stays.
#   0:55  "Drink!" flashes.
#   1:00  hard cut to the next round.
#
# Plus a how to play card at the front and an end card at the back.
#
#   ./build.sh links   print the URL each row resolves to (eyeball this first)
#   ./build.sh art     rerender the leader and the cards
#   ./build.sh fetch   download the 60 sources into raw/
#   ./build.sh cut     build the 60 second rounds into cut60/
#   ./build.sh join    intro + rounds + outro -> powerhour.mp4
#   ./build.sh all     the lot
#
# Timings (seconds) can be overridden on the command line:
#   LEAD=15 NAME=35 ./build.sh cut
#
# Per row in clips.tsv: fill the `url` column to pin an exact video, or add a
# 9th tab separated column with a start offset in seconds to move the window.
# A row with no offset gets its leading silence trimmed automatically, so a
# clip that opens on two seconds of black does not waste the guessing window.
#
# No browser cookies, no logins, nothing touched outside this folder.

set -uo pipefail
cd "$(dirname "$0")"

TSV="${TSV:-clips.tsv}"
LEAD="${LEAD:-20}"        # sound only, leader on screen
NAME="${NAME:-40}"        # the answer drops in
ROUND="${ROUND:-60}"      # length of one round
DRINK_IN="${DRINK_IN:-55.2}"
DRINK_OUT="${DRINK_OUT:-58.0}"

RAW="raw"; CUT="cut60"; OUT="powerhour.mp4"; LEADER="leader.mp4"
YTC="youtube:player_client=web_embedded,mweb,tv_simply"
VOPTS=(-c:v libx264 -preset veryfast -crf 21 -pix_fmt yuv420p -g 60 -r 30
       -c:a aac -b:a 160k -ar 48000 -ac 2 -movflags +faststart)
PAD=$((ROUND + 1))
mkdir -p "$RAW" "$CUT"

rows() { tail -n +2 "$TSV" | grep -v '^[[:space:]]*$'; }
resolve() { if [ -n "${2:-}" ]; then printf '%s' "$2"; else printf 'ytsearch1:%s' "$1"; fi; }
dur() { ffprobe -v error -show_entries format=duration -of csv=p=0 "$1" 2>/dev/null; }

cmd_art() {
  python3 cards.py "$TSV"
  [ -s "$LEADER" ] || python3 leader.py
}

cmd_links() {
  rows | while IFS=$'\t' read -r min act side movie year scene search url off; do
    printf '%02d  %-30s ' "$min" "$movie"
    yt-dlp --no-warnings --extractor-args "$YTC" \
      --print "%(webpage_url)s  %(duration)ss  %(title).55s" "$(resolve "$search" "${url:-}")" \
      2>/dev/null || echo "NO RESULT: $search"
  done
}

cmd_fetch() {
  rows | while IFS=$'\t' read -r min act side movie year scene search url off; do
    n=$(printf '%02d' "$min")
    [ -s "$RAW/$n.mp4" ] && { echo "have  $n  $movie"; continue; }
    echo "fetch $n  $movie"
    yt-dlp -q --no-warnings --extractor-args "$YTC" \
      -f "bv*[height<=720]+ba/b[height<=720]/b" --merge-output-format mp4 \
      -o "$RAW/$n.%(ext)s" "$(resolve "$search" "${url:-}")" \
      || echo "  !! failed $n ($movie) - paste a URL into the url column for this row"
  done
}

# How much dead air a clip opens on. Scene rips often start on black and
# silence; burning that inside the sound only window would be a wasted guess.
lead_in() {
  local s
  s=$(ffmpeg -nostdin -v info -t 20 -i "$1" -af "silencedetect=n=-45dB:d=0.7" \
        -f null - 2>&1 \
      | awk '/silence_start: 0(\.0*)?$/ {f=1} f && /silence_end/ {print $5; exit}')
  awk -v s="${s:-0}" 'BEGIN{ if (s+0 > 0.4 && s+0 < 9) printf "%.2f", s-0.15; else print 0 }'
}

still() { # $1=png $2=seconds $3=out
  ffmpeg -nostdin -y -v error -loop 1 -framerate 30 -t "$2" -i "$1" \
    -f lavfi -t "$2" -i anullsrc=r=48000:cl=stereo \
    -map 0:v -map 1:a -t "$2" "${VOPTS[@]}" "$3"
}

cmd_intro() {
  # the rules land one at a time, then good luck. Hard cuts, same as the format.
  local secs=(2.5 4.5 6.5 6.5 4.5) i=1 parts=()
  : > "$CUT/intro_list.txt"
  for s in "${secs[@]}"; do
    [ -s "$CUT/00_intro_$i.mp4" ] || still "cards/intro_$i.png" "$s" "$CUT/00_intro_$i.mp4"
    echo "file '00_intro_$i.mp4'" >> "$CUT/intro_list.txt"
    i=$((i + 1))
  done
  ffmpeg -nostdin -y -v error -f concat -safe 0 -i "$CUT/intro_list.txt" -c copy "$CUT/00_intro.mp4"
}

cmd_cut() {
  [ -s "$LEADER" ] || { echo "no $LEADER, run ./build.sh art"; exit 1; }
  [ -s "cards/drink.png" ] || { echo "no cards, run ./build.sh art"; exit 1; }
  echo "rounds of ${ROUND}s  (sound only ${LEAD}s, name at ${NAME}s)"
  [ -s "$CUT/00_intro.mp4" ] || cmd_intro
  [ -s "$CUT/99_outro.mp4" ] || still cards/outro.png 9 "$CUT/99_outro.mp4"

  rows | while IFS=$'\t' read -r min act side movie year scene search url off; do
    n=$(printf '%02d' "$min")
    [ -s "$RAW/$n.mp4" ] || { echo "skip  $n (no raw)"; continue; }
    [ -s "$CUT/$n.mp4" ] && { echo "have  $n"; continue; }

    d=$(dur "$RAW/$n.mp4"); d=${d:-0}
    if [ -n "${off:-}" ]; then start="$off"; else start=$(lead_in "$RAW/$n.mp4"); fi
    # a source too short to fill the round just runs round again rather than
    # freezing on a still frame for the rest of the minute
    if awk -v d="$d" -v s="$start" -v p="$PAD" 'BEGIN{exit !(d >= s + p)}'; then
      SRC=(-ss "$start" -i "$RAW/$n.mp4")
    elif awk -v d="$d" -v p="$PAD" 'BEGIN{exit !(d >= p)}'; then
      SRC=(-ss 0 -i "$RAW/$n.mp4"); start=0
    else
      SRC=(-stream_loop -1 -i "$RAW/$n.mp4"); start="0, looped, source is only ${d%%.*}"
    fi

    if ffprobe -v error -select_streams a -show_entries stream=index -of csv=p=0 \
         "$RAW/$n.mp4" | grep -q .; then AIN="[0:a]"; else AIN="[5:a]"; fi

    echo "round $n  $movie  (from ${start}s)"
    ffmpeg -nostdin -y -v error \
      "${SRC[@]}" \
      -i "$LEADER" \
      -loop 1 -framerate 30 -t "$PAD" -i "cards/n_$n.png" \
      -loop 1 -framerate 30 -t "$PAD" -i "cards/t_$n.png" \
      -loop 1 -framerate 30 -t "$PAD" -i "cards/drink.png" \
      -f lavfi -t "$PAD" -i anullsrc=r=48000:cl=stereo \
      -filter_complex "\
[0:v]scale=1280:720:force_original_aspect_ratio=decrease,\
pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30,\
tpad=stop_mode=clone:stop_duration=${PAD}[film];\
[1:v]scale=1280:720,setsar=1,fps=30,format=rgba,\
fade=t=out:st=$(awk -v l=$LEAD 'BEGIN{print l-0.55}'):d=0.55:alpha=1[lead];\
[2:v]format=rgba[num];\
[3:v]format=rgba,fade=t=in:st=${NAME}:d=0.7:alpha=1[ttl];\
[4:v]format=rgba,fade=t=in:st=${DRINK_IN}:d=0.25:alpha=1,\
fade=t=out:st=$(awk -v o=$DRINK_OUT 'BEGIN{print o-0.35}'):d=0.35:alpha=1[drk];\
[film][ttl]overlay=0:0:enable='gte(t,${NAME})'[v1];\
[v1][drk]overlay=0:0:enable='between(t,${DRINK_IN},${DRINK_OUT})'[v2];\
[v2][lead]overlay=0:0:enable='lt(t,${LEAD})'[v3];\
[v3][num]overlay=0:0:enable='lt(t,$(awk -v l=$LEAD 'BEGIN{print l-0.4}'))'[v];\
${AIN}aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,\
loudnorm=I=-16:TP=-1.5:LRA=11,apad[a]" \
      -map "[v]" -map "[a]" -t "$ROUND" "${VOPTS[@]}" "$CUT/$n.mp4" \
      || echo "  !! round $n failed"
  done
}

cmd_join() {
  : > "$CUT/list.txt"
  for f in "$CUT"/00_intro.mp4 "$CUT"/[0-9][0-9].mp4 "$CUT"/99_outro.mp4; do
    [ -s "$f" ] && echo "file '$(basename "$f")'" >> "$CUT/list.txt"
  done
  [ -s "$CUT/list.txt" ] || { echo "nothing in $CUT/"; exit 1; }
  ffmpeg -nostdin -y -v error -f concat -safe 0 -i "$CUT/list.txt" \
    -c copy -movflags +faststart "$OUT"
  s=$(printf '%.0f' "$(dur "$OUT")")
  echo "built $OUT  ($((s / 60))m $((s % 60))s, $(( $(grep -c . "$CUT/list.txt") - 2 )) rounds)"
}

case "${1:-all}" in
  links) cmd_links ;; art) cmd_art ;; fetch) cmd_fetch ;;
  intro) cmd_intro ;; cut) cmd_cut ;; join) cmd_join ;;
  all) cmd_art; cmd_fetch; cmd_cut; cmd_join ;;
  *) sed -n '2,30p' "$0"; exit 1 ;;
esac
