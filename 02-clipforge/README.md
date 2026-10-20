# ClipForge

The first version of my shorts automation idea, and the reason the YouTube channel above looks the way it does.

The original ask was "make me an automated YouTube Shorts channel". Before building anything I ran it through an LLM council (5 advisors who argue and peer review each other). They were unanimous that a generic faceless money channel dies on the platform after YouTube's 2025 crackdown on mass produced content. So the plan changed:

1. The pipeline is the asset, not the channel.
2. A recurring character or point of view instead of faceless quote videos.
3. A human picks about 5 hooks a day (10 minutes), agents do the rest. Automate the grunt work, not the taste.
4. Everything stays copyright clean by construction: original scripts, licensed or AI voice, royalty free visuals.

## What's in `src/`

`prototype-editor/index.html`, a browser prototype of the review and editing surface. Planned stack: Claude API for scripts, ElevenLabs or local TTS, Pexels, Remotion or FFmpeg, Whisper, YouTube Data API.
