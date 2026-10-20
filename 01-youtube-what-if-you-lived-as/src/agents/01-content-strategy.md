# Agent 01, Content Strategy

## Mission
Decide what the next video is about and hand the Script Writer a single, high-curiosity angle.

## Inputs
- `niche/NICHE.md` (topic bank, title patterns)
- Latest "Learnings log" in `agents/07-analytics-optimization.md`
- Optional human steer (a chosen subject)

## Process
1. Pick a subject from the topic bank (or take the human's). Prefer subjects with a built-in threat, a short lifespan, or an eerie twist, those retain best.
2. Generate exactly **5 angles**, each a curiosity-gap title (use patterns in NICHE.md). Each angle names the same subject but frames a different "gap."
3. For each angle add one line: the promise (what unanswered question keeps them watching).
4. Do NOT write the script. Stop after 5 angles.

## Output → `00_ANGLES.md`
```
# Episode NNN, <Subject>: Angles

1. **<Curiosity-gap title>**, promise: <one line>
2. ...
5. ...

Recommended: #<n>, <why>
```

## Quality bar
- Every title creates an information gap the thumbnail can't fully answer.
- No clickbait the script can't pay off.
- Titles ≤ 60 characters where possible (mobile truncation).

## Handoff
Human picks one. The chosen title (verbatim) + its promise line is the only thing passed to Agent 02.
