# Transition playbook

What the engine (and Claude, when planning) follows. Built from research on 17 Oct 2026 after Teerth judged set01 "horrible" and set02 "better, but study it".

## Rules (non negotiable)
1. **One lead vocal at a time.** Never two singers. But for pop, **keep a vocal going through the transition**: the crowd follows the words while the beat changes underneath. Dead instrumental gaps longer than ~4 bars kill pop energy.
2. **One low end at a time.** Everything under 150 Hz (kick + sub + bass) is one fader. The incoming low end lands in one hit, at the midpoint of the blend, on a bar line.
3. **Phrase lines only.** Every move starts on a phrase line (8 or 16 bars in pop). Real mixes' transition lengths peak at multiples of 32 beats (8 bars).
4. **Pop = short.** Blends are 8 bars by default (4 for vocal heavy radio edits), never 16+ unless both sides are instrumental.
5. **Enter on something recognisable**: the hook, chorus or drop of the next song, cued 4 or 8 bars ahead.
6. **Keys:** blends that overlap harmony need Camelot neighbours (or a 1 semitone shift, which is what 94% of real DJ transpositions are). Clashing keys get a move with no harmonic overlap (strip drop, loop roll, cut).
7. **Tempo:** blend only within ~5% (86% of real tempo changes are under 5%). Bigger jumps get a move with no beat overlap.
8. **Order within a long blend:** percussion first, then melody, then bass.

## Moves (engine techniques)
| technique | what happens | use when |
|---|---|---|
| `vocal_carry` | B's beat (no low end) slides under A's last vocal line, bass swaps halfway, A's beat leaves, A's vocal finishes its line on B's beat and echoes, B's own vocal starts on the phrase | default pop blend; keys within 1 step |
| `acapella_over` | A's vocal ends, B's vocal (acapella) comes in over A's beat, filter build, beats swap on the one | B has a vocal intro or hook to tease; keys within 1 step |
| `strip_drop` | A strips down: drums out, then bass out, filter rises, riser builds; B drops in full on its hook/drop | energy reset, key or tempo clash, going into a big drop |
| `loop_roll` | A's last word loops 1 beat, then 1/2, then 1/4 with a rising filter; B slams in on the one | high energy handover, any key/tempo; sparingly |
| `stem_swap` | long blend, vocal free: B percussion, then B melody, bass swap, A out, B vocal on phrase | both sides instrumental (drops, intros) |
| `cut` (+`vocal_echo`) | hard cut on the one, A's last word echoes | dramatic moment, B opens with something big |
| `echo_out` | A echoes away, B drops clean | rescue move only |

## Sources
- DJ.Studio transitions playbook (8 bar EQ swap drill, stem swap drill, long blend order): https://dj.studio/blog/the-dj-transitions-playbook
- We Are Crossfader, 12 high energy transitions (wordplay, loop cutting, loop tightening, brake, wide sync tempo ramp): https://wearecrossfader.co.uk/blog/12-high-energy-dj-transitions/
- StemSplit DJ stem guide (acapella drop 8 to 16 bars, strip down buildup, frequency crossfade): https://stemsplit.io/blog/dj-stem-separation-guide
- Digital DJ Tips five transitions (8 bar bass swap, swap at bar 4): https://www.digitaldjtips.com/?p=2799229
- DJ Gym, mixing pop (avoid vocal clashes, mix quickly, acapella bridges): https://www.djgym.co.uk/post/how-to-mix-pop-music
- Kim et al., ISMIR 2020, 20,765 real transitions (32 beat peaks, tempo and key stats): https://ar5iv.arxiv.org/html/2008.10267
- DJ forums on top 40 mixing (quick mixes, cue 4/8 bars before the drop, cut on a keyword): https://forum.djtechtools.com/t/chart-music-transitions/48912
