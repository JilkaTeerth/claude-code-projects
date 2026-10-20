# ClutchUp

A driving practice app for people learning manual in Pune who have a car but no driving school. It came from my own experience learning.

The LLM council's main point: **the progression is the product, not the map.** So it's a sequenced curriculum of real roads, ranked easy to hard, each tagged with the skill it trains:

1. Open road: straights and U turns
2. Light society traffic: confidence
3. Hills: clutch control and hill starts
4. Peak traffic: graduation

Each spot has calm traffic timings and a Maps link. Progress is saved on the device.

## Stack

Next.js 15, TypeScript, Tailwind, static with no backend, installable as a PWA. A React Native version was started separately.

## What's in `src/`

The app source (`app/`, `components/`, `lib/spots.ts` holds the curriculum).
