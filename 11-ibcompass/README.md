# IBCompass

An AI guidance platform for IB Diploma students. You enter career goals, target countries, grades and preferences, and it returns subject combinations, university pathways, a workload analysis and a Grade 10 to career timeline.

## Stack

Next.js 15, TypeScript, Tailwind, shadcn/ui, Supabase for auth and storage, an LLM through Groq for generation, Zod schemas so the model's output is validated before it's shown.

## How it's built

- A curated knowledge base (18 career paths, subjects, universities) grounds the model, so it isn't inventing requirements.
- The model returns structured JSON checked against `lib/schemas/roadmap.ts`. If it fails validation it never reaches the page.
- Multi step onboarding form, roadmap pages with timeline, workload and pathway components.

## What's in `src/`

The full app source. Keys come from env vars that are not in the repo.
