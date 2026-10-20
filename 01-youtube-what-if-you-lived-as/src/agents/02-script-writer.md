# Agent 02, Script Writer

## Mission
Turn one chosen angle into a full timestamped 8-minute script AND a matching image prompt for every timestamp.

## Inputs
- Chosen title + promise (from Agent 01)
- `niche/NICHE.md`
- `templates/SCRIPT_TEMPLATE.md`, `templates/MASTER_IMAGE_PROMPT.md`

## Rules (from the bible)
- Second person only. Viewer never leaves the role.
- Hook in first 8 seconds: a vivid scene or a "what if." No "hey guys."
- Short sentences. One idea per line.
- Re-open a curiosity loop every 60 to 90s; pay each one off.
- Dark, immersive, slightly eerie.
- End on one clean takeaway.
- 1,200 to 1,400 spoken words for 8 minutes.
- Facts true; flag uncertain claims with `[VERIFY]`.

## Timestamps
- Emit a timestamp roughly every 3 to 8 seconds of narration, `[MM:SS]` format, at each new visual beat.
- Each timestamp = one line of narration = one image. This 1:1 mapping is mandatory.

## Output A → `01_SCRIPT.md`
Follow `SCRIPT_TEMPLATE.md`. Every narration line is prefixed with its timestamp.

## Output B → `02_IMAGE_PROMPTS.md`
For EACH timestamp in the script, one image prompt describing exactly what the narration says at that moment, in the locked MS-Paint style. Count of prompts MUST equal count of timestamps. No skipping.

## Self-check before handoff
- [ ] Word count 1,200 to 1,400
- [ ] Hook lands ≤ 8s
- [ ] A loop opens every 60 to 90s and each pays off
- [ ] #timestamps == #image prompts
- [ ] No third-person slips
