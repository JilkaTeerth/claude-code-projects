# Agent 07, Analytics & Optimization

## Mission
Read performance, extract what worked, and feed it back to Content Strategy (closing the loop).

## Inputs
- **API (automated):** run `tools/.venv/bin/python tools/yt_analytics.py report <VIDEO_ID>`, returns AVD, view %, retention curve, traffic sources, subs/likes/comments as markdown. (`videos` subcommand lists video IDs; `auth` re-runs login if the token expires.)
- **Manual (API doesn't expose these):** impressions + CTR, read from YouTube Studio → Content → video → Reach, paste into the review.
- Cadence: 48h and 7d after publish. Analytics data itself lags ~48h.

## Review at 48h
- **CTR** low (<4%)? → thumbnail/title problem. Note in learnings; consider A/B swap.
- **Retention dip in first 30s?** → hook problem. Log the exact drop timestamp.
- **Mid-video cliff?** → a curiosity loop failed to pay off. Map the drop to the script line.

## Review at 7d
- Compare AVD to the 8-min target (aim >50% = 4:00+).
- Identify the single best-retaining segment and the single worst.
- Note winning title pattern and hook style.

## Write back (mandatory each cycle)
Append to "Learnings log" below AND, if a pattern repeats across ≥3 videos, update `niche/NICHE.md` + `templates/SCRIPT_TEMPLATE.md` with a dated changelog entry.

Every cycle produce exactly:
1. **Keep**, one thing to repeat.
2. **Cut**, one thing to stop.
3. **Next angle nudge**, a steer for Agent 01's next 5 angles.

## Learnings log

### 2026-07-16, First full cycle (ep001-ep005; ep006 too new)
Reports saved to each episode's `05_ANALYTICS_2026-07-16.md`. CTR/impressions still pending manual paste from Studio.

| Ep | Subject | Live | Length | AVD | AVD % | Views (analytics/public) | Retention @6% elapsed |
|----|---------|------|--------|-----|-------|--------------------------|----------------------|
| 001 | Octopus | 07-10 | 5:15 | 0:28 | 9.1% | 79 / 119 | 36.7% |
| 002 | Mayfly | 07-11 | 4:42 | 0:34 | 12.1% | 30 / 48 | 51.7% |
| 003 | Penguin | 07-11 | 6:56 | 0:41 | 10.1% | 38 / 71 | 46.0% |
| 004 | Anglerfish | 07-11 | 6:29 | 1:04 | 16.5% | 28 / 40 | 53.6% |
| 005 | Tardigrade | 07-13 | 5:38 | 1:17 | 23.0% | 74 / **630** | 60.3% |

**Findings**
- AVD% has climbed almost monotonically ep001→ep005 (9.1 → 23.0). The scripts are getting better at holding people; the octopus is the outlier-bad, the tardigrade outlier-good.
- **Hook style is the differentiator.** Octopus opens atmospheric/mysterious ("you wake in darkness… a clock is counting down") → 69.6% gone in ~30s. Tardigrade opens with an impossible concrete claim + rapid-fire extremes ("Boil the water. Freeze it solid. Blast you with radiation. You do not die.") → best hook retention of the run (97% at 2% elapsed vs octopus's 71%). Anglerfish (body-horror stakes in line 3) is second best. Concrete extreme stakes in the first 15s beat mood-setting.
- **RELATED_VIDEO is the channel's distribution engine** across all 5 episodes (51/79, 19/30, 29/38, 14/61, 61/74 views) and those viewers watch multiples of what channel-page/search viewers do. Optimize for suggested feed: strong first 30s + topics adjacent to big animal/science channels.
- Tardigrade is breaking out: 630 public views vs 40 to 119 for the rest, +1 sub, the "unkillable extremophile" angle got picked up by suggested. (Analytics rows lag ~48h, hence 74 processed.)
- Search traffic bounces (13 search views on octopus = 1 min total watch). Don't chase search; the format is a suggested-feed format.

**Keep:** the ep005 hook formula, one impossible claim, then a rapid-fire list of concrete extremes, all inside 0:00 to 0:15. Stakes before atmosphere.
**Cut:** atmospheric slow-burn openings (ep001 style), scene-setting before stakes loses ~70% of viewers in 30s.
**Next angle nudge (Agent 01):** bias the next 5 angles toward "extreme survival / shouldn't-be-alive / body-horror" subjects with a one-line impossible claim (naked mole rat, immortal jellyfish, giant isopod, vampire squid fit). Tardigrade proved the suggested feed rewards superlatives.

**Follow-ups:** re-pull ep005 after 07-20 (7-day window) to confirm the breakout; first ep006 read after 07-17; paste CTRs from Studio when Teerth is next in there.
