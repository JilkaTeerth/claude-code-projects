# What If You Lived As... (YouTube automation)

A faceless long form YouTube channel run by a team of AI agents. Each video drops you inside an animal's whole life in about 8 minutes, told in second person ("you hatch alone..."), with a David Attenborough style voiceover over crude MS Paint drawings.

## How Claude Code runs it

- **7 agents, each one an md spec**: content strategy, script writer, thumbnail designer, SEO, production, publishing, analytics. The analytics agent writes what it learns back into the format bible, so the loop closes.
- **Palmier Pro MCP** drives the video editor directly: import, timeline, export. No manual editing.
- **ElevenLabs MCP** generates the voiceover and the ambient music bed. VO recipe tuned to "95% calm, 5% life" (stability 0.5, style 0.30, speed 0.96).
- **fal.ai image bridge** (`pipeline/genimg.py`). When Palmier's built in image generator ran out of credits mid episode, I had Claude write a bridge that generates stills on fal.ai and imports them into Palmier. About $0.08 an image.

## Numbers

- Episode 6 (Cordyceps): 66 transcript synced stills, full VO, music bed, 8:31 at 1080p, thumbnail, all generated end to end.
- The flat drawing style is held by a locked prompt prefix, so the image model can be swapped without the look drifting.

## What's in `src/`

Agent specs, handoff contracts (`pipeline/PIPELINE.md`), the format bible (`niche/NICHE.md`), templates, and the Python assembly and analytics tools. OAuth tokens, client secrets and generated media are left out.
