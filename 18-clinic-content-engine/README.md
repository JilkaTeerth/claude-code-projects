# Clinic content engine (client work, anonymised)

An automation pipeline for a health clinic's Instagram: content topics go in, branded posts come out inside the clinic's existing Figma design system, pass a safety guard, and land in a human review queue.

## Constraints that shaped it

- The Instagram Graph API has **no drafts endpoint**, and live publishing needs weeks of Meta App Review. So the review queue *is* the draft. Nothing auto posts.
- The Figma REST API can't write text. All writes go through the Figma plugin API, driven from Claude through an MCP bridge.

## What was built

- Three n8n workflows (27, 20 and 19 nodes).
- A 35 template registry mapping content slots to Figma components, with unfilled slots hidden automatically so placeholder copy never ships.
- A **deterministic, model free guard** with 13 rules: unsourced statistics, diagnostic language, and consent holds the pipeline can't clear by itself. For health content I didn't want an LLM deciding what's safe.
- A 10 post launch grid and a 9 slide carousel built programmatically in Figma.

## Numbers and findings

- The local pipeline processed 28 assets through 13 nodes in 396 ms with no credentials.
- Found that Figma instance child IDs are deterministic, which removed a whole planned layer renaming phase.
- Found a regex bug where a trailing word boundary after an alternation let every percentage claim skip the sourcing check.

No code here: it's full of the client's brand and Figma IDs.
