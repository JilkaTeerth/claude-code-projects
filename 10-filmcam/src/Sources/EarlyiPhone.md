# Early iPhone (iPhone 5 era), source registry

Scope: iPhone 5 specifically (announced 12 Sep 2012, shipped 21 Sep 2012), as named in CLAUDE.md section 6 ("Early iPhone (4/5/5S/6/6S)"). Where a spec is genuinely shared across that whole generation it is noted, but this file does not attempt to separately source the 4/5S/6/6S.

## Sensor, resolution and type
SOURCE: Apple, "Apple Introduces iPhone 5" (newsroom press release, 12 Sep 2012)
URL: https://www.apple.com/au/newsroom/2012/09/12Apple-Introduces-iPhone-5/
DATE ACCESSED: 2026-09-21
CLAIM: "The 8 megapixel iSight camera is the most popular camera in the world and with iPhone 5, it's even better... The new camera is completely redesigned with incredible optical performance, yet amazingly it's 25 per cent smaller than the camera in iPhone 4S." The release also states the new panorama feature captures images "of up to 28 megapixels."
SUPPORTS: sensor.resolution (8MP stills), general redesign context
CONFIDENCE: manufacturerDocumented

## Sensor and lens, current Apple support page
SOURCE: Apple, "iPhone 5 - Technical Specifications"
URL: https://support.apple.com/en-us/112016
DATE ACCESSED: 2026-09-21
CLAIM: Apple's currently-published tech-specs page for iPhone 5 lists: "8-megapixel iSight camera," autofocus, tap to focus, face detection, LED flash, "improved video stabilization," panorama, HD video recording at 1080p up to 30 fps, and a 1.2MP FaceTime camera (720p HD video). This current page does **not** list aperture, sensor size, pixel pitch, sensor generation, or backside-illumination, those details are absent from Apple's own currently-live spec sheet.
SUPPORTS: sensor.resolution, flash.type (LED), video specs, absence noted for other params
CONFIDENCE: manufacturerDocumented

## Aperture, lens element count, sensor format, secondary aggregation
SOURCE: GSMArena, "Apple iPhone 5 - Full phone specifications"
URL: https://www.gsmarena.com/apple_iphone_5-4910.php
DATE ACCESSED: 2026-09-21
CLAIM: Lists the iPhone 5 rear camera as 8 MP, f/2.4 aperture, 1/3.2" sensor size, backside-illuminated, five-element lens, hybrid IR filter.
SUPPORTS: lens.aperture (f/2.4), sensor.opticalFormat (1/3.2"), lens.elementCount (5)
CONFIDENCE: literatureBased
NOTE: This is a widely-used industry spec aggregator, not Apple's own current documentation, Apple's live pages (checked above) do not publish aperture or sensor-format numbers for this model. Multiple independent secondary sources (Wikipedia, DxOMark test notes, contemporary tech press from Sep 2012) repeat the same f/2.4 and 1/3.2" figures, which is why this is rated literatureBased rather than left as pure anecdote, but it falls short of manufacturerDocumented because no live first-party Apple page states it.

## Sensor identity, teardown analysis
SOURCE: Wikipedia, "IPhone 5," citing iFixit teardown and Chipworks/TechInsights die analysis
URL: https://en.wikipedia.org/wiki/IPhone_5
DATE ACCESSED: 2026-09-21
CLAIM: Article states the rear sensor is a "Sony Exmor R IMX145," 8 MP, backside-illuminated, citing iFixit and Chipworks analysis (references 11-12 in that revision). Wikipedia does not itself state pixel pitch or physical sensor size in this section.
SUPPORTS: sensor.model/manufacturer identity
CONFIDENCE: literatureBased
NOTE: Direct iFixit teardown page (https://www.ifixit.com/Teardown/iPhone+5+Teardown/10525, accessed 2026-09-21) confirms Sony as the module manufacturer and describes "improved low light performance and 40% faster image capture" versus the prior generation and a sapphire crystal lens cover, but its published teardown text does not itself state the IMX145 part number, pixel pitch, or sensor die size, that attribution comes from the Chipworks-sourced citation, one hop further removed. Treat the exact part number as probable, not confirmed by a source we could read directly.

## Sensor part number, separate iPhone 4S/5 generation datasheet search
SOURCE: Search across manufacturer/datasheet aggregators (TechInsights, Datasheet Archive) for "Sony IMX145"
URL: https://www.techinsights.com/products/car-1208-902
DATE ACCESSED: 2026-09-21
CLAIM: TechInsights lists a commercial circuit-analysis report for "Sony IMX145 CMOS Image Sensor" without publishing the underlying pixel-level specs (pixel pitch, full well capacity, read noise, quantum efficiency) for free; those numbers sit behind a paid report. No public Sony datasheet for IMX145 was found, Sony does not publish full electrical datasheets for phone-camera sensors to the general public.
SUPPORTS: UNKNOWN gap acknowledgment for sensor.noise model inputs
CONFIDENCE: literatureBased

## Dynamic range and low-light behaviour
SOURCE: DxOMark, "Apple iPhone 5" camera test
URL: https://www.dxomark.com/apple-iphone-5/
DATE ACCESSED: 2026-09-21
CLAIM: Overall DxOMark score 72 (Photo 74, Video 70), tested December 2012 under DxOMark's then-current (pre-2013) test protocol. Reported strengths: "good performance in bright conditions (above 20 lux)," "accurate autofocus and broad dynamic range," "strong detail retention in bright lighting." Reported weaknesses: "noisy images in low light with poor retention of detail," "purple flare in some circumstances," yellow-tinted white balance under tungsten lighting, and poor low-light video stabilization. DxOMark's published summary text does not give a numeric dynamic-range value in stops or EV for this test.
SUPPORTS: tone.dynamicRange (qualitative only), noise (low-light degradation), color.whiteBalance (tungsten yellow cast), lens (purple flare / veiling flare in backlight)
CONFIDENCE: literatureBased
GAP: No numeric dynamic-range figure (stops/EV) was found in DxOMark's public summary for this specific 2012-era test. DxOMark's older protocol reports were less numerically granular in public write-ups than their current one.

## Purple/pink flare artefact
SOURCE: Wikipedia, "IPhone 5" (camera section)
URL: https://en.wikipedia.org/wiki/IPhone_5
DATE ACCESSED: 2026-09-21
CLAIM: Article notes the camera "exhibited an unintended purple hue when a strong source of light is present," which Apple characterized as normal behaviour for the sapphire-lens/IR-filter combination rather than a defect.
SUPPORTS: lens.chromaticAberration / flare behaviour under bright point sources
CONFIDENCE: literatureBased

## JPEG processing behaviour
UNKNOWN - requires reference calibration. No manufacturer or teardown source found describing Apple's specific in-camera JPEG encoder settings for iPhone 5 (chroma subsampling scheme, quality factor, in-ISP sharpening kernel or strength, noise-reduction aggressiveness curve vs. ISO). Apple has never published ISP pipeline details for this generation.
WHAT WOULD BE NEEDED: A set of iPhone 5 JPEGs (ideally straight off the original hardware, not re-exported) at multiple ISOs and lighting levels, examined for (a) chroma subsampling pattern via a hex/JPEG structure dump, (b) edge haloing characteristic of USM-style ISP sharpening, (c) luminance noise floor and chroma noise floor separated by patch analysis on a grey card, across at least three light levels (bright daylight, indoor tungsten, low light near ISO ceiling).

## Sensor noise model parameters (photon/read/PRNU/chroma split)
UNKNOWN - requires reference calibration. CLAUDE.md section 4 requires modelling photon noise (sqrt(signal)), read noise (roughly constant), chroma noise and pixel-response non-uniformity as separate terms. No source found gives these as separated, quantified values for the IMX145 in this camera module (full well capacity, read noise in electrons, PRNU percentage).
WHAT WOULD BE NEEDED: A minimum of 10 reference photographs of a flat, evenly-lit grey/step-chart target shot on real or borrowed iPhone 5 hardware at a spread of ISOs (from base to max), with dark-frame captures at matching ISO/exposure to isolate read noise from photon noise, per CLAUDE.md section 7's calibration workflow.

## What we still need

Reference photographs required to close the gaps above, in priority order:
1. A flat grey-card / step-wedge exposure series across the iPhone 5's native ISO range, in bright and low light, to separate photon noise from read noise and derive dynamic range in stops directly (closes the DxOMark numeric gap and the sensor noise model gap).
2. A same-scene comparison set (skin tone, sky, foliage, deep shadow, bright highlight) shot on real iPhone 5 hardware next to a modern iPhone, per the section 7 workflow, to derive tone-curve and colour-matrix parameters empirically rather than from any spec sheet (none of the sources above give a 3x3 colour matrix or tone curve, none exist publicly).
3. A raw JPEG file from the camera (not re-compressed) examined for subsampling mode and quantization tables, to source compression.quality and compression.chromaSubsampling honestly rather than guessing "high quality, likely 4:2:0" from general knowledge of the era.
4. A bright tungsten/fluorescent indoor shot to confirm and quantify the "yellow tint" white-balance behaviour DxOMark mentions only qualitatively.
5. A backlit/point-light-source shot to characterise the purple flare artefact geometrically (is it centred, radial, sensor-stack reflection-shaped?) before attempting to model it as anything beyond an artisticApproximation.
