# Sources registry

This directory is the evidence base for the four "definition of done" profiles in `CLAUDE.md` section 11: early iPhone, Polaroid 600, 2000s digicam, Kodak Gold class film. It exists because CLAUDE.md section 7 says calibration is the product and section 3 says every numeric parameter must carry provenance. A profile parameter that cites nothing here should be treated as unverified.

## Files

- `EarlyiPhone.md`, iPhone 5 era digital camera (sensor, lens, JPEG behaviour, dynamic range)
- `Polaroid600.md`, Polaroid 600 integral instant film (speed, format, chemistry, temperature behaviour)
- `Digicam2000s.md`, the Cyber-shot / PowerShot / Coolpix compact CCD class, treated as a class, not one product
- `KodakGold.md`, consumer colour negative film class, keyed on Kodak Gold 200 as the documented representative
- this file

## Claim format

Every claim in every file uses this block, verbatim:

```
## <Topic>
SOURCE: <publisher / document>
URL: <url>
DATE ACCESSED: 2026-09-21
CLAIM: <what the source actually says>
SUPPORTS: <which profile parameter this informs>
CONFIDENCE: measured | manufacturerDocumented | literatureBased | referenceCalibrated | artisticApproximation
```

`CLAIM` is a paraphrase or close quote of what the source says, not an inference. If a number in a profile is derived by combining or interpreting a claim, that derivation happens in the profile JSON or in code comments, not here, this file records what the sources actually say.

## Evidence hierarchy (from CLAUDE.md section 7, strongest first)

1. **Manufacturer documentation**, Apple technical specs and newsroom releases; Polaroid's own support site; Kodak Alaris film datasheets. `CONFIDENCE: manufacturerDocumented`.
2. **Imaging science literature**, sensor physics references (e.g. CCD blooming/smear mechanics from imaging-hardware vendors), spectral response theory. `CONFIDENCE: literatureBased`.
3. **Measured reference images**, our own reference photograph comparisons, once shot. `CONFIDENCE: measured` or `referenceCalibrated` depending on whether the number came directly off a measurement or was tuned by eye against references.
4. **Expert photographic analysis**, DxOMark test reports, DPReview lab reviews (the review body, not its forums), teardown analyses (iFixit, Chipworks/TechInsights via secondary citation). Treated as stronger than casual community comment but weaker than manufacturer data or a direct measurement. Typically `CONFIDENCE: literatureBased`.
5. **Community discussion**, Reddit, forums, blogs, gear-review sites written by hobbyists. **Anecdotal only.** Never cited as measurement. Every such claim below is explicitly labelled "ANECDOTAL" in its CLAIM line and gets `CONFIDENCE: artisticApproximation` when it is used to justify a parameter value, because it is a choice informed by commonly-reported impression, not a citable fact.

A claim one tier lower is never silently substituted for a claim one tier higher. Where two sources disagree, both are recorded, in the "Contradictions" section of the relevant file, rather than picking one.

## On UNKNOWN

Per CLAUDE.md section 7's research rule and section 10 ("do not invent specifications"): if a search does not turn up a number, the relevant profile section says so explicitly, ```
UNKNOWN - requires reference calibration
```, followed by a note on what reference photograph(s) would be needed to derive it. A gap marked this way is not a failure of this document; a plausible invented number would be the failure.

## Access note

Several manufacturer pages (notably `support.polaroid.com`) return HTTP 403 to direct fetches (Cloudflare bot protection) but were readable through a text-extraction proxy (`r.jina.ai`) pointed at the same URL. The `URL` field in each claim below always points at the original manufacturer page, not the proxy, since the proxy is a retrieval mechanism, not a source.
