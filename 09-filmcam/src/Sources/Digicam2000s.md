# 2000s digicam (Cyber-shot / PowerShot / Coolpix class), source registry

Scope: treated as a class per the task brief, not one product, because per-model manufacturer datasheets for consumer CCD compacts from this era are not published with the technical depth film datasheets or modern phone spec sheets are. Where a specific model's review is used as the class exemplar, it is named explicitly and the generalisation is flagged.

## Class-representative model review, image quality, noise, tone curve
SOURCE: DPReview, "Canon PowerShot A70 Review" (published 13 August 2003), this is DPReview's own lab review body, not its user forums; treated as expert photographic analysis, one tier below manufacturer/measured
URL: https://www.dpreview.com/reviews/2961382645/canona70/
DATE ACCESSED: 2026-09-21
CLAIM: For "a three megapixel 'entry level' digital camera," the A70 delivered "very good image quality with images well exposed with relatively good dynamic range, a normal Canon tone curve (lower contrast, more shadow detail) and natural but not under-saturated color response." "Noise levels were low, especially at the ISO 50 setting and even at higher sensitivities noise is acceptable and increases predictably." The camera provided no direct user control over contrast, saturation, or sharpening; Canon's resizing/interpolation for lower-resolution output modes was judged high quality ("probably bilinear... detailed clean images with no hard edges or alias effects").
SUPPORTS: tone.curve (manufacturer-house tone-curve behaviour differs by brand, flagged, not a single universal digicam curve), noise.isoScaling (qualitative: predictable, low at base ISO), sharpening (no user-facing controls typical of the class; fixed in-camera pipeline)
CONFIDENCE: literatureBased
NOTE: This is one specific model (3MP Canon, 2003) used as a class exemplar. CLAUDE.md explicitly says "a digicam is not an iPhone 5 with more grain" but also to treat this as a class; the honest caveat is that Canon's, Sony's, and Nikon's in-camera tone curves and sharpening defaults were not identical to each other across this era, and no single number here should be read as universal.

## CCD sensor physics, blooming and vertical smear
SOURCE: Hamamatsu Photonics, "CCD Saturation and Blooming" (Hamamatsu Learning Center / educational technical resource) and Oxford Instruments (Andor), "What is CCD Blooming and Anti-Blooming"
URL: https://hamamatsu.magnet.fsu.edu/articles/ccdsatandblooming.html ; https://andor.oxinst.com/learning/view/article/ccd-blooming-and-anti-blooming
DATE ACCESSED: 2026-09-21
CLAIM: "Blooming occurs when the charge in a pixel exceeds the saturation level and the charge starts to fill adjacent pixels. Full well capacity defines the amount of charge an individual pixel can hold before saturating... Full well capacity is dependent on the physical area of the pixel and is therefore higher with larger pixels." Vertical smear in interline-transfer CCDs occurs "when the sensor is illuminated during readout and electrons leak into the [vertical shift register]," producing "a bright column of pixels extending above and below the offending pixel", i.e. vertical streaks from bright highlights, distinct from blooming's local spreading. Anti-blooming structures (vertical or lateral overflow drains) reduce but do not eliminate this in consumer sensors.
SUPPORTS: sensor.highlightClipping behaviour (should be modelled with localized bloom/smear artefacts near bright highlights, not simple hard clipping), tone.highlightCompression (physical basis for why small-sensor CCDs clip abruptly and sometimes streak)
CONFIDENCE: literatureBased
NOTE: This is imaging-hardware-vendor technical literature describing CCD physics generally, not measurements specific to any particular Cyber-shot/PowerShot/Coolpix model's sensor. Whether a specific 2000s consumer compact's CCD had adequate anti-blooming to suppress visible streaking in typical use is model-dependent and not confirmed here.

## CCD vs. CMOS spectral response and colour rendering
SOURCE: Multiple imaging-sensor technical sources (Adimec technical articles; general CCD/CMOS quantum-efficiency literature), aggregated technical claim, not one canonical document
URL: https://www.adimec.com/ccd-vs-cmos-sensitivity-in-low-light-improvements-with-industrial-cmos-image-sensors-and-cameras/
DATE ACCESSED: 2026-09-21
CLAIM: CCDs of this era offered "high quantum efficiency, broad spectral response, low readout noise" relative to contemporaneous CMOS. Spectral response in silicon-based photoelements "typically peak[s] at the red, yellow or green spectrum," with quantum efficiency poorer at short (blue) wavelengths because "most of these electrons do not reach the CCD photoelement collecting well" when absorbed near the surface. Contemporary CMOS designs of the same era suffered worse blue-channel response than CCDs because "over 70 percent of the photodiode area may be shielded by transistors and stacked or interleaved metallic bus lines."
SUPPORTS: color.spectralResponse (basis for a mild blue-channel deficiency being physically real for silicon sensors generally, more so for period CMOS than period CCD, supports CCDs of this era having comparatively cleaner blue response, not the inverse)
CONFIDENCE: literatureBased
CONTRADICTION - FLAG: This literature-based, technical explanation does not support the commonly-repeated internet claim (see anecdotal entry below) that CCDs produce categorically "warmer, more saturated, more cinematic" colour than CMOS as some inherent, easily-modelled property. The technical sources describe a real but narrow blue-channel-QE difference; the popular "CCD look" narrative is broader and less physically specific than that. Do not conflate the two.

## "CCD look", popular characterisation (anecdotal)
SOURCE: General digicam buying-guide/marketing content, ANECDOTAL, not a measurement or manufacturer claim
URL: https://electronics.alibaba.com/buyingguides/ccd-camera-guide-when-to-choose-vintage-digital-over-modern-sensors
DATE ACCESSED: 2026-09-21
CLAIM: "Older CCD sensors render color with a rich, cinematic, organic quality that feels closer to analog film, unlike modern CMOS sensors that tend to prioritize accuracy and efficiency," and "bright areas would glow and bleed, creating a dreamy effect."
SUPPORTS: color.characterMotivation (as a design intent reference only, never as a physical spec)
CONFIDENCE: artisticApproximation
NOTE: This is marketing-adjacent commentary reflecting a widely-repeated online narrative about "the CCD look." It is not physically specific enough to derive a colour matrix or tone curve from, and should never be cited as if it were a measured characteristic. The "bright areas glow and bleed" observation is plausibly describing real CCD blooming/smear (see the Hamamatsu/Andor entry above), which does have a documented physical mechanism, but the broader "cinematic, organic" framing is an aesthetic judgement, not a spec.

## In-camera JPEG sharpening, general behaviour
SOURCE: DPReview user forums, ANECDOTAL, community discussion, cited only as commonly-reported observation, never as measurement
URL: https://www.dpreview.com/forums/thread/1451088 (and related threads on in-camera sharpening vs. unsharp mask)
DATE ACCESSED: 2026-09-21
CLAIM: Commonly repeated observation across multiple forum threads that "point-and-shoot cameras do quite a bit of in-camera sharpening to come up with nice looking photos that print well," and that most JPEGs from this era "have already been sharpened in the camera" before any further post-processing, with unsharp-mask-style edge haloing being a recognized, frequently-discussed artefact of that in-camera processing.
SUPPORTS: sharpening.strength (qualitative: aggressive by default, class-wide), sharpening.haloArtefact (qualitative existence, not quantified)
CONFIDENCE: artisticApproximation
NOTE: Explicitly anecdotal per the evidence hierarchy in README.md. No forum thread found gives a quantified sharpening radius/amount/threshold for a specific period digicam model.

## Flash behaviour and colour temperature
UNKNOWN - requires reference calibration. No manufacturer datasheet or expert review found during this research that quantifies built-in flash guide number, colour temperature, or falloff behaviour for a representative 2000s compact digicam specifically. General flash guide-number concepts were found (an unrelated modern compact camera's flash guide number, and disposable-film-camera flash figures, see KodakGold.md cross-reference is not applicable; those numbers belong to a different device class and are not reused here) but nothing tying a documented guide number, colour temperature, or falloff curve to a Cyber-shot/PowerShot/Coolpix-era built-in flash specifically.
WHAT WOULD BE NEEDED: A flash-lit reference photograph series at multiple subject distances (0.5m, 1m, 2m, 3m) with a period-representative digicam (or a well-documented emulation target), measuring both intensity falloff (to check against the 1/distance² falloff CLAUDE.md section 4 specifies) and the flash's colour temperature against a grey card, compared to the same shots under ambient light only.

## JPEG compression / chroma subsampling specifics
UNKNOWN - requires reference calibration. No source found gives the specific JPEG quality factor or chroma subsampling scheme (4:2:0 vs 4:2:2) used by any specific period digicam model's firmware.
WHAT WOULD BE NEEDED: A raw JPEG file directly off period digicam hardware (or a well-documented archival scan clearly stating it is unaltered from camera output), inspected for quantization tables and subsampling mode, the same approach flagged as needed for the iPhone 5 profile.

## Dynamic range of the class
SOURCE: DPReview forum discussion, "Dynamic range of CCD's compared to film/slides" and related threads, ANECDOTAL, forum discussion citing informal test comparisons, not a controlled measurement published by DPReview's review body
URL: https://www.dpreview.com/forums/threads/dynamic-range-of-ccds-compared-to-film-slides.329419/
DATE ACCESSED: 2026-09-21
CLAIM: Forum discussion reports, for example, that an early digital compact (Olympus C2500L cited as one example) was informally estimated at "more like 5 or 6 stops" of dynamic range, and a separate informal RAW-mode test on a different (higher-end, non-compact) camera suggested "6 or 7 stops." No formal, citable, class-wide number was found.
SUPPORTS: tone.dynamicRange (rough class order-of-magnitude only: notably narrower than a modern sensor, plausibly in the 5-7 stop range for compact CCDs of this era)
CONFIDENCE: artisticApproximation
NOTE: This is forum-level anecdote about specific, mostly non-representative cameras (a bridge camera and a DSLR), not a controlled study of Cyber-shot/PowerShot/Coolpix compacts. Treat 5-7 stops as a starting hypothesis for reference calibration, not a citable number for the profile.

## What we still need

1. At least 10 reference photographs from an actual period digicam (per CLAUDE.md section 7's workflow) covering exposure, white balance, skin tones, sky, foliage, deep shadow and bright highlight, matched against a modern-phone shot of the same scenes, since no manufacturer source publishes a colour matrix, tone curve, or dynamic-range figure for this class.
2. A step-wedge exposure on real period hardware to derive an actual dynamic-range figure in stops, replacing the anecdotal 5-7 stop range above.
3. A raw in-camera JPEG (unaltered) to determine actual chroma subsampling and quantization, and to measure sharpening halo width/strength directly by edge-profile analysis rather than citing forum impressions.
4. A flash-lit distance series to source flash.intensity falloff and flash.colorTemperature, both currently full UNKNOWNs.
5. A bright-highlight scene (specular reflection, window, or direct light source in frame) shot on real period CCD hardware to determine whether vertical smear (as distinct from blooming) is visually significant enough to model, given that the Hamamatsu/Andor sources describe smear as an interline-CCD-specific phenomenon whose visibility is highly implementation-dependent.
