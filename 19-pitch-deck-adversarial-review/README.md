# B2B pitch deck rebuild (client work, anonymised)

A sales deck for an Indian outsourcing firm pitching US community bank CFOs on offshoring finance back office work. The audience fact checks live, so every number had to hold up.

## Four versions

- **v1 to v2, LLM council with 5 lenses** (data, design, flow, CFO buyer, exec polish). Found two blocking cost bugs: a roughly 2x mismatch in per person cost between two slides, and a chart showing a senior accountant as cheaper than a junior one because two sources were mixed.
- **v2 to v3, client feedback.** One source was an outsourcing provider's own blog and it was holding up the entire cost argument. Replaced it everywhere with independent sources a CFO trusts: salary guides, the US Bureau of Labor Statistics and Deloitte.
- **v3 to v4, The Council agent** (in `13-skills-and-agents`). Caught a real bug: overhead was added on top of a rate that already included it, so the implied cost per role was above the deck's own band.

The decks were generated with python-pptx, and each version shipped with a data validation file listing a source for every figure.

No files here: they're client material.
