# Polaroid 600, source registry

Scope: Polaroid 600-series integral instant film, both the historical (pre-2008 Polaroid Corporation, "T-600 film family") chemistry and the current (2017-onward, Polaroid B.V. / "Polaroid Originals" lineage) chemistry. CLAUDE.md section 6 explicitly requires distinguishing these two, so every claim below is tagged historical or current.

## Film speed, historical (T-600 datasheet)
SOURCE: Polaroid Corporation, "T-600 Integral Color Print Film" Film Data Sheet (T-600 Film Family), hosted mirror
URL: https://125px.com/docs/film/polaroid/600plfds.pdf
DATE ACCESSED: 2026-09-21
CLAIM: "Film Speed: ISO 640/DIN 29." Also: "Recommended speed: ISO/DIN 640/290" restated on the H&D curve page. Format: "3½ x 4¼ in. (8.9 x 10.8 cm)." Image Area: "3⅛ x 3⅛ in. (7.9 x 7.9 cm)." Finish: Glossy. "Exposures per Unit: 10 exposures per pack." "Development Time: 3 minutes approximately," with the curve page giving "Recommended processing time and temperature: Approximately 3 minutes at 70°F/21°C." Balance: "Daylight and electronic flash (5500°K)." Contrast: "Medium." Resolution (1000:1): "7-10 line pairs/mm."
SUPPORTS: film.speed (ISO 640), frame.format (physical + image-area dimensions), instantFilm.developmentTime (historical, 3 min at 70°F/21°C), color.balance (5500K), tone.contrast (medium)
CONFIDENCE: manufacturerDocumented
PERIOD: Historical, this datasheet is issued by "Polaroid Corporation, Waltham, MA 02451 USA," describing hardware ("Impulse," "Cool Cam," "OneStep," "600 Business Edition," "JobPro") from the pre-2001-bankruptcy era of the original Polaroid Corporation. It also states "Compared to previous T-600 film chemistry, 600 film has superior color performance, sharper images and better overall exposure performance", i.e. even this sheet describes a chemistry revision within the historical company's own lifetime, not the current company's product.

## Development time, temperature-dependent characteristic curves (historical)
SOURCE: Polaroid Corporation, T-600 Film Data Sheet (same document as above)
URL: https://125px.com/docs/film/polaroid/600plfds.pdf
DATE ACCESSED: 2026-09-21
CLAIM: The datasheet publishes three separate H&D (density vs. relative log exposure) curve sets for blue/red/green channels: "Characteristic H&D curve for normal development" at 70°F/21°C, "Characteristic H&D curve for cold development" at 55°F/18°C, and "Characteristic H&D curve for hot development" at 95°F/35°C. It also includes a Reciprocity Law Failure chart ("A wide range of shutter speeds can be used without loss of film speed... For longer exposure times, some exposure compensation and filtration is suggested") and a Spectral Sensitivity chart for blue/green/red layers across 350-700nm, and a Modulation Transfer Function chart.
SUPPORTS: instantFilm.developmentTemperatureCurve, film.reciprocityFailure, color.spectralSensitivity (curve exists; exact digitized values not extracted, see gap below)
CONFIDENCE: manufacturerDocumented
NOTE: The datasheet publishes the *shapes* of these curves graphically. This registry entry documents that the curves exist and their axis definitions; it does not claim specific numeric density values read off the charts, since the source we could machine-extract is text, not the chart pixels. See "What we still need."

## Warm vs cold temperature colour shift, current chemistry, Polaroid's own support site
SOURCE: Polaroid (current company), "How to get the most out of Polaroid film," Polaroid Support
URL: https://support.polaroid.com/hc/en-us/articles/115012519828-How-to-get-the-most-out-of-Polaroid-film
DATE ACCESSED: 2026-09-21
CLAIM: "Optimal performance occurs between 13-28°C (55-82°F)." Below 13°C: photos "tend to emerge over-exposed, lacking color contrast and with a cyan (blue) tint." Above 28°C: images develop "with a yellow/red tint." Recommends keeping film close to the body in cold weather and pre-chilling packs before hot-weather shooting. Also: store unopened film packs "in a cool and dry environment" between 4-18°C (41-65°F) refrigerated, never frozen, and let film return to ambient temperature for at least 1 hour before shooting after cold storage. Use within 12 months of production date for best results. Photos remain light-sensitive after ejection, shield them face-down or in a pocket during development "for deeper saturation, sharper details."
SUPPORTS: instantFilm.temperatureColorShift (cold -> cyan/blue, hot -> yellow/red), instantFilm.storageGuidance, instantFilm.lightShieldingDuringDevelopment
CONFIDENCE: manufacturerDocumented
PERIOD: Current (support.polaroid.com is the present-day Polaroid company's live support site).
ACCESS NOTE: This URL returns HTTP 403 to a direct fetch (Cloudflare bot protection); content above was retrieved via a text-extraction proxy pointed at the same URL and is a close paraphrase/quote of the live page content as of the access date.

## Historical vs. current chemistry, explicit manufacturer statement
SOURCE: Polaroid (current company), "How is current Polaroid film different from Polaroid film of the past?", Polaroid Support
URL: https://support.polaroid.com/hc/en-us/articles/115012533928-How-is-current-Polaroid-film-different-from-Polaroid-film-of-the-past
DATE ACCESSED: 2026-09-21
CLAIM: States that when the original Polaroid wound down analog instant photography in 2008, chemical suppliers that existed solely to serve Polaroid's film production went out of business, and "some of the chemistry used in film production became unavailable for commercial use." The Impossible Project (which became today's Polaroid) had to "reinvent" the chemistry with what was available, improving it over roughly nine years. Explicitly states the modern colour film's development time is "down to 15 minutes," contrasted with the "5 minute development time that you may remember from back in the day" for original 1980s-era film, i.e. the manufacturer itself states current chemistry is measurably slower to develop than the historical product, not equivalent.
SUPPORTS: Direct justification for CLAUDE.md's mandatory distinction between historical and current chemistry; instantFilm.developmentTime (current, ~15 min) vs historical figure below
CONFIDENCE: manufacturerDocumented
ACCESS NOTE: Same 403/proxy caveat as above.

## CONTRADICTION, development time, historical datasheet vs. current manufacturer statement
The historical T-600 datasheet (Polaroid Corporation) states development completes in "approximately 3 minutes" at 70°F/21°C. The current company's own support article says even *today's* improved chemistry only gets development time "down to 15 minutes," and separately describes "the 5 minute development time that you may remember from back in the day" as the historical benchmark being chased. So there is a three-way figure in the record: 3 minutes (original manufacturer datasheet, technical/formal), ~5 minutes (current manufacturer's own recollection of "back in the day," informal), and ~15 minutes (current chemistry, per the same current-manufacturer article). A separate community source (see below) independently reports 10-15 minutes for current color 600 film, which brackets the manufacturer's own 15-minute figure. Do not average these, the profile's `film` sub-profile should carry two explicit values (historicalDevelopmentTime ≈ 3-5 min, currentDevelopmentTime ≈ 10-15 min) rather than one, and the "warm chemistry" default in a Polaroid 600 profile targeting *today's* film stock should use the 10-15 minute figure, since that's what a user shooting current-production film actually experiences.

## Development time, community corroboration (anecdotal)
SOURCE: Community film-photography site, Analog.Cafe, "Polaroid Color 600 Film Review & Shooting Guide", ANECDOTAL, community/enthusiast review, not a manufacturer measurement
URL: https://www.analog.cafe/r/polaroid-600-colour-film-review-kxll
DATE ACCESSED: 2026-09-21
CLAIM: Reports current Polaroid Color 600 film "takes about 15 minutes to fully develop, though it typically takes around 10 to 15 minutes." Separately reports (also anecdotal, not a cited measurement) that Polaroid 600 has "a narrow dynamic range of 3.5 stops," is "a high-contrast film" where "shadows and over-exposed highlights quickly become ineligible [illegible]," and that the film "tends to shift its colours towards pink highlights and green shadows."
SUPPORTS: instantFilm.developmentTime (corroborates current ~10-15 min), tone.dynamicRange (anecdotal figure only), color.highlightCast/shadowCast (anecdotal)
CONFIDENCE: artisticApproximation
NOTE: The 3.5-stop dynamic range figure and the pink-highlight/green-shadow cast description appear nowhere in Polaroid's own manufacturer documentation found during this research. They are commonly-repeated enthusiast observations. Use only as a starting point for a `referenceCalibrated` value once real reference photographs are shot and measured, never cite "3.5 stops" in a profile as if it were manufacturer data.

## Dynamic range / contrast, manufacturer numeric data
UNKNOWN - requires reference calibration. Neither the historical T-600 datasheet nor the current support.polaroid.com pages found during this research publish a dynamic-range figure in stops or EV. The historical datasheet does give the H&D (density/log-exposure) curve shape and states contrast is "Medium" on Kodak/Polaroid's own low/medium/high slope classification (medium = H&D slope 1.10-1.70 per the shared industry convention used on this and comparable datasheets), which is a proxy for contrast but not a stops-of-latitude number.
WHAT WOULD BE NEEDED: A step-wedge or high-contrast test-chart exposure shot on current-stock 600 film, scanned, and measured for the exposure range between shadow clipping and highlight clipping, per CLAUDE.md section 7's "at least 10 reference photographs" workflow, ideally paired with a modern-phone shot of the same chart for a direct side-by-side.

## Format and image-area dimensions
SOURCE: Polaroid (current company), "What are Polaroid photo dimensions?", Polaroid Support
URL: https://support.polaroid.com/hc/en-us/articles/115012363647-What-are-Polaroid-photo-dimensions
DATE ACCESSED: 2026-09-21
CLAIM: For standard formats (SX-70, 600, i-Type): total print area "3.108 x 3.024 inches (photo area) and 4.233 x 3.483 inches (total area)", i.e. roughly 7.894 x 7.680 cm image area within a 10.752 x 8.847 cm total print. States original and current Polaroid integral film "maintain identical sizing, though contemporary versions are slightly thicker."
SUPPORTS: frame.imageArea, frame.totalPrintArea, frame.borderGeometry (bottom border being the difference between total and image height)
CONFIDENCE: manufacturerDocumented
ACCESS NOTE: 403/proxy caveat as above.
CONTRADICTION - MINOR: The historical T-600 datasheet gives image area as 3⅛ x 3⅛ in. (7.9 x 7.9 cm, i.e. a square), while the current support page gives 3.108 x 3.024 in. (7.894 x 7.680 cm, a rectangle, not square). This is a real, small discrepancy between the historical spec (rounded to eighths of an inch, described as square) and the current company's more precise figure (not square). Use the current figure for a profile targeting present-day film; note the historical figure if ever modelling truly vintage frames specifically, and do not assume the two eras used identical crop geometry without checking a physical frame.

## Film speed, current chemistry
SOURCE: Aggregated retailer/enthusiast citations of current Polaroid Color 600 packaging (B&H, Adorama, Retrospekt product listings), ANECDOTAL/retailer, not fetched from a first-party Polaroid spec page in this session
URL: https://www.bhphotovideo.com/c/product/1555708-REG/polaroid_6002_600_color_film.html
DATE ACCESSED: 2026-09-21
CLAIM: Current Polaroid Color 600 film is labelled ISO 640, matching the historical T-600 speed rating.
SUPPORTS: film.speed (current, ISO 640), corroborates the historical manufacturerDocumented figure above
CONFIDENCE: literatureBased
NOTE: This is retailer product-page data reflecting the box label, not a fetched Polaroid engineering document, but ISO 640 is consistent across every source checked (historical datasheet, current retail packaging, community reviews) with no contradiction found, so it is treated as reliable despite the lower-tier sourcing route.

## Exposure compensation across the 600-family lineup
SOURCE: Polaroid Support, "Exposure compensation on Polaroid SX-70" (found via site search; SX-70 film comparison to 600 film noted directly on this page)
URL: https://support.polaroid.com/hc/en-us/articles/115012563968-Exposure-compensation-on-Polaroid-SX-70
DATE ACCESSED: 2026-09-21
CLAIM: Search-result summary indicates this page states SX-70 film sensitivity is "±160 ASA" while cameras were calibrated for 100 ASA film, and separately that "SX-70 film is roughly ¼ the sensitivity of 600 film", consistent with 640 ISO for 600-series film (160 x 4 = 640).
SUPPORTS: Cross-check / consistency confirmation for film.speed = ISO 640
CONFIDENCE: manufacturerDocumented
NOTE: This entry is based on a search-engine summary of the page rather than a direct fetch of the full article text in this session (direct fetch was not attempted for this specific URL); treat the exact wording as approximate pending a direct read, though the ¼-sensitivity relationship is internally consistent with the other manufacturerDocumented figures above.

## What we still need

1. A physical current-stock Polaroid 600 pack shot as a step-wedge / grey-scale target, in controlled daylight, to measure actual dynamic range in stops and replace the anecdotal "3.5 stops" figure with a `referenceCalibrated` value.
2. The same scene shot on current 600 film at three temperatures (cold ~10°C, room ~20°C, hot ~32°C) to quantify the cyan-shift and yellow/red-shift colour casts numerically (hue angle and saturation delta vs. the room-temperature baseline), rather than only qualitatively as "cyan tint" / "yellow/red tint."
3. A physical current-stock print measured with calipers to confirm or refute the historical-vs-current square/rectangle image-area discrepancy noted above.
4. A digitized reading of the historical T-600 datasheet's H&D curves (density vs. log exposure for R/G/B at 55°F/70°F/95°F), the PDF's chart images were not OCR'd for numeric values in this pass; the axis definitions were transcribed but not the curve data points themselves. This would let temperature-dependent tone-curve shifts be modelled directly from a real Polaroid engineering document rather than approximated.
5. A macro photograph of the physical frame material (paper texture, edge shadow depth, border colour under different lighting) to source `frame.paperTexture` and `frame.edgeShadow`, which no source in this registry addresses, currently a full UNKNOWN, no manufacturer or literature source found describing the physical/optical properties of the frame material itself.
