# Kodak Gold class (consumer colour negative film), source registry

Scope: consumer, general-purpose, daylight-balanced colour negative film, keyed on Kodak Gold 200 as the documented representative (per CLAUDE.md section 11's phrasing "Kodak Gold class film profile"). Kodak Alaris publishes a real technical datasheet for this exact product, which is the strongest source in this entire registry, most claims below are manufacturerDocumented.

## Primary manufacturer datasheet, identity, use case, exposure latitude
SOURCE: Kodak Alaris Inc., "KODAK GOLD 200 Film" Technical Data sheet, Publication No. E-7022, revised February 2016
URL: https://business.kodakmoments.com/sites/default/files/files/resources/E7022_Gold_200.pdf
DATE ACCESSED: 2026-09-21
CLAIM: "KODAK GOLD 200 Film is a low-speed color negative film that offers an outstanding combination of color saturation, fine grain, and high sharpness. It is designed for general picture-taking situations in daylight or with electronic flash. You can also expose this film under photolamps (3400 K) or tungsten illumination (3200 K) with filters. It also features wide exposure latitude, from two stops underexposure to three stops overexposure."
SUPPORTS: film.speed context, film.exposureLatitude (-2 stops / +3 stops from box speed), color.balance (daylight, 5500K-class, with filter guidance for tungsten/photolamp)
CONFIDENCE: manufacturerDocumented

## Film speed and light-source exposure table
SOURCE: Same datasheet, E-7022
URL: https://business.kodakmoments.com/sites/default/files/files/resources/E7022_Gold_200.pdf
DATE ACCESSED: 2026-09-21
CLAIM: ISO Speed table: "Daylight or Electronic Flash: None [filter], 200 [ISO]. Photolamp (3400K): No. 80B filter, 64 [effective ISO]. Tungsten (3200K): No. 80A filter, 50 [effective ISO]." Daylight exposure table gives standard Sunny-16-style settings, e.g. "Bright or Hazy Sun (Distinct Shadows): 1/250 sec, f/11." Electronic flash guide numbers given from 350 to 8000 BCPS output, e.g. "1000 BCPS: guide number 100 ft / 30 m."
SUPPORTS: film.speed = ISO 200 (box speed, daylight), color.filterFactors for tungsten/photolamp use, flash.guideNumberReference (generic flash-exposure calculation method, not camera-specific)
CONFIDENCE: manufacturerDocumented

## Grain, Print Grain Index
SOURCE: Same datasheet, E-7022, "Image Structure" section
URL: https://business.kodakmoments.com/sites/default/files/files/resources/E7022_Gold_200.pdf
DATE ACCESSED: 2026-09-21
CLAIM: "The Print Grain Index number refers to a method of defining graininess in a print made with diffuse-printing illumination. It replaces rms granularity and has a different scale which cannot be compared to rms granularity." "A Print Grain Index rating of 25 on the scale represents the approximate visual threshold for graininess. A higher number indicates an increase in the amount of graininess observed." Standard viewing/measurement conditions: "Negative size: 24 x 36mm (135-size standard format). Print Size: 4 x 6 in / 10.2 x 15.2 cm. Magnification: 4.4X." Kodak Gold 200's rating under these conditions: "Print Grain Index: 44."
SUPPORTS: film.grain (relative graininess quantified on Kodak's own perceptual scale, 44 vs. their stated 25 visual-threshold baseline means Gold 200's grain is clearly above the threshold of visibility at 4x6 print size, i.e. genuinely visible grain, not "fine grain" in absolute terms despite the film being marketed with "fine grain" language)
CONFIDENCE: manufacturerDocumented
NOTE: Kodak does **not** publish an RMS granularity number for this film in this datasheet, only Print Grain Index, which explicitly "cannot be compared to rms granularity." Any RMS-style grain-amount parameter in the profile that claims to derive from "Kodak's granularity spec" would be fabricating a conversion Kodak itself says isn't valid. If the renderer's noise/grain model wants an RMS-style input, it must be reference-calibrated from a scan, not converted from Print Grain Index.

## Processing
SOURCE: Same datasheet, E-7022, "Processing" section
URL: https://business.kodakmoments.com/sites/default/files/files/resources/E7022_Gold_200.pdf
DATE ACCESSED: 2026-09-21
CLAIM: "Use KODAK FLEXICOLOR Chemicals for Process C-41." References Kodak Publication No. Z-131 for further detail (not itself fetched in this research pass).
SUPPORTS: film.processStandard (C-41), relevant mainly as a boundary condition: this profile assumes standard, correctly-timed C-41 processing, not cross-processing or push/pull, unless a separate development-variation parameter is explicitly added
CONFIDENCE: manufacturerDocumented

## Spectral sensitivity and dye-density curves, existence and axes
SOURCE: Same datasheet, E-7022, "Curves" section
URL: https://business.kodakmoments.com/sites/default/files/files/resources/E7022_Gold_200.pdf
DATE ACCESSED: 2026-09-21
CLAIM: The datasheet publishes: (1) a characteristic (H&D-style) curve of Density vs. Log Exposure for the three colour-forming layers (yellow-forming, magenta-forming, cyan-forming), measured with Status M densitometry, daylight exposure, 1/50 sec, density threshold 0.2 above D-min; (2) a Spectral-Sensitivity curve (Log Sensitivity vs. Wavelength 250-750nm) for the three emulsion layers; (3) a Spectral-Dye-Density curve (Diffuse Spectral Density vs. Wavelength 400-700nm) for minimum density and a typical midscale neutral subject.
SUPPORTS: color.spectralResponse curve shapes (existence and axis definitions confirmed from a genuine manufacturer document), color.crossTalk basis
CONFIDENCE: manufacturerDocumented
GAP: As with the Polaroid H&D curves, this text extraction captured the chart's axis labels and captions but not digitized numeric curve values, the PDF's chart content is rendered as vector/image graphics, not extractable as a data table. Deriving an actual 3x3 colour matrix or per-channel tone curve from these charts requires reading pixel positions off the graphs, which was not done in this pass.

## Densitometry reference values (exposure judgment table)
SOURCE: Same datasheet, E-7022, "Judging Negative Exposures" section
URL: https://business.kodakmoments.com/sites/default/files/files/resources/E7022_Gold_200.pdf
DATE ACCESSED: 2026-09-21
CLAIM: For a normally exposed and correctly processed negative, measured through a red (Status M or Wratten 92) filter: "KODAK Gray Card (gray side): 0.85 to 1.05" density. "Lightest step... of a KODAK Paper Gray Scale: 1.25 to 1.45." "Highest diffuse density on normally lighted forehead, light complexion: 1.15 to 1.45; dark complexion: 0.90 to 1.30."
SUPPORTS: tone.referenceExposureDensities (a genuinely rare, directly quotable manufacturer number set, useful as a calibration target if we ever scan a real negative densitometrically, though our pipeline works from scanned/digital images, not raw negative density, so this maps indirectly)
CONFIDENCE: manufacturerDocumented

## Dynamic range in stops, community estimate (anecdotal, contradicts manufacturer framing)
SOURCE: Community film-review site, Analog.Cafe, "Kodak Gold 200 Film Review", ANECDOTAL, enthusiast review, not a manufacturer or lab measurement
URL: https://www.analog.cafe/r/kodak-gold-film-review-chsw
DATE ACCESSED: 2026-09-21
CLAIM: Characterizes Kodak Gold 200 as capable of "roughly 8 stops of dynamic range with additional latitude in highlights and minimal give in shadows."
SUPPORTS: tone.dynamicRange (anecdotal figure only)
CONFIDENCE: artisticApproximation
CONTRADICTION - FLAG: This "8 stops of dynamic range" framing is not the same measurement as Kodak's own "two stops under, three stops over" exposure latitude figure in the primary datasheet above. Exposure latitude (how far off box-speed metering you can be and still get a usable negative) and dynamic range (the tonal range the film itself can record in a single exposure) are related but distinct properties, and Kodak's datasheet only speaks to the former. Do not treat "8 stops" as if Kodak said it, it did not. Use the anecdotal figure only as a starting hypothesis pending direct measurement.

## Colour character, community/review description (anecdotal)
SOURCE: Community review site, CulturedKiwi, "Kodak Gold 200 Review", ANECDOTAL
URL: https://www.culturedkiwi.com/kodak-gold-200-review/
DATE ACCESSED: 2026-09-21
CLAIM: Describes the film's signature as "a specific yellow-amber cast that lifts midtones, turning foliage olive, concrete sand-tinted, and late sun syrupy."
SUPPORTS: color.characteristicCast (as a design-intent reference only)
CONFIDENCE: artisticApproximation
NOTE: Evocative but non-quantitative. Cannot be turned into a colour-matrix or hue-rotation value without a reference scan; recorded here so the description is at least sourced and attributed rather than invented fresh during profile authoring.

## Grain structure, pronounced-visibility description (anecdotal, corroborating but not contradicting manufacturer data)
SOURCE: General search-aggregated review commentary (multiple consumer film-review sites), ANECDOTAL
URL: (aggregated across several film-review sites found via search; no single canonical URL, treat as a repeated community observation rather than a single citable source)
DATE ACCESSED: 2026-09-21
CLAIM: Commonly-repeated observation that Gold 200 "has a fairly pronounced grain structure visible across the entire image from highlights to shadows," consistent in direction (though not in exact magnitude) with the manufacturer's own Print Grain Index of 44 being above their stated 25-point visibility threshold.
SUPPORTS: film.grain (directional corroboration of the manufacturerDocumented Print Grain Index entry above)
CONFIDENCE: artisticApproximation
NOTE: Recorded mainly to show the anecdotal record agrees in direction with the one hard number Kodak publishes (PGI 44 > threshold 25), this is a case where community sourcing and manufacturer data align, which is worth noting explicitly rather than silently relying on either alone.

## What we still need

1. A scanned Kodak Gold 200 negative or print, shot on a step-wedge / grey-scale chart in daylight, to convert the manufacturer's Print Grain Index (44, at 4x6 print / 4.4x magnification) into an actual RMS-style noise-amount parameter for the renderer's grain model, the datasheet itself says this conversion is not valid without direct measurement ("cannot be compared to rms granularity").
2. A same-scene reference set (skin, sky, foliage, shadow, highlight) shot on real Kodak Gold 200 stock and cross-processed through a modern-phone comparison shot, per CLAUDE.md section 7, to derive the actual colour matrix and tone curve, none of the manufacturer's published curves were digitized into numeric form in this pass, only their existence and axis definitions were confirmed.
3. A deliberately over- and under-exposed bracket series (at least the ±2/+3 stop latitude window the datasheet specifies) to directly measure where highlights and shadows actually clip in scanned output, replacing the contested "8 stops" anecdotal dynamic-range figure with a `referenceCalibrated` number specific to how this project will scan/digitize the film.
4. Digitized numeric extraction of the datasheet's spectral-sensitivity and spectral-dye-density curve charts (reading pixel positions off the published graphs, or sourcing the same data from Kodak's underlying scientific publications if available), to properly source a spectral-response-based colour model rather than an eyeballed 3x3 matrix.
5. If disposable-camera-plus-Kodak-Gold and dedicated-camera-plus-Kodak-Gold profiles are ever both built (per CLAUDE.md's "camera vs stock are orthogonal" principle), a reference set shot on the same film stock through both a sharp lens and a cheap fixed-focus lens, to confirm the film's own grain/colour signature stays visually consistent while only the optical characteristics change.
