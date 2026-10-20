#include <metal_stdlib>
#include <CoreImage/CoreImage.h>

using namespace metal;

// Density-weighted film grain.
//
// This is the only stage stock CIFilters genuinely cannot express, which is why
// it is the one custom kernel in the app.
//
// The noise is NOT generated here. It is sampled from a pre-built 512x512 tile
// that `tools/filmlab` generates with a pink (1/f) power spectrum and
// deliberate cross-channel correlation. Both matter and both are wrong in the
// obvious implementation:
//
//   * A per-pixel hash like fract(sin(dot(...))) gives white noise. Measured
//     film grain has a pink spectrum; white noise has too little low-frequency
//     energy and reads as fine electronic hash rather than clumped silver.
//   * Independent per-channel noise seems right, since colour film has three
//     separately developing dye layers. It is not: measured grain has strong
//     cross-channel correlation, because a clump occupies overlapping volume
//     across the layers and scanning integrates through all of them. Fully
//     decorrelated noise reads as digital chroma speckle.
//
// Sampling the tile at a *normalised* frequency also means the apparent grain
// size is identical at 1080p preview and 48MP capture, which satisfies the
// preview/capture parity invariant for free.

// Must match SPAN in the tile generator. The tile stores +/-5 sigma mapped into
// 0..1; anything narrower clips the rare large grains that carry the character.
#define K_NOISE_SPAN 5.0f

// NOTE: this is a general CIKernel, not a CIColorKernel. A colour kernel is
// strictly per-pixel: it receives one already-sampled `sample_t` and cannot
// take a sampler or read any other texture at a computed coordinate. Because
// this kernel samples a noise tile at its own coordinates it must be general,
// which also means the source arrives as a sampler and the Swift side has to
// supply an ROI callback. Declaring it as a colour kernel compiles perfectly
// and then fails to load at runtime, which is how it hid for two builds.
extern "C" float4 filmGrain(
    coreimage::sampler src,
    coreimage::sampler noiseTile,
    float amount,        // std dev of added noise in 0..1 space; 0.015-0.06
    float cell,          // grain cell size in PIXELS, already scaled by caller
    float mu,            // luminance at which grain peaks
    float sigma,         // width of the luminance response
    float shadowFloor,   // grain never fully vanishes in black
    float chroma,        // 0 = pure luminance grain, 1 = full per-channel
    float octaves,       // 1 or 2; real emulsion is a distribution of sizes
    coreimage::destination dest)
{
    float2 d = dest.coord();
    float4 c = src.sample(src.transform(d));

    // Accumulate octaves. A single sampling scale reads as a regular texture
    // because every grain is the same size; two scales an octave apart break
    // that up for very little cost.
    float3 n = float3(0.0);
    float wsum = 0.0;
    int oct = int(clamp(octaves, 1.0, 3.0));

    for (int k = 0; k < oct; ++k) {
        float sc = max(cell * pow(2.0, float(k)), 1.0);
        float ow = (k == 0) ? 1.0 : (k == 1 ? 0.55 : 0.30);
        // The offsets decorrelate the octaves so they do not superimpose into
        // a visible beat pattern.
        float2 uv = (d + float2(float(k) * 137.0, float(k) * 71.0)) / sc;
        float3 s = noiseTile.sample(noiseTile.transform(uv)).rgb;
        // Undo the tile's 0..1 storage encoding back to signed sigma units.
        n += ((s - 0.5) * 2.0 * K_NOISE_SPAN) * ow;
        wsum += ow;
    }
    n /= wsum;

    // Density weighting. Grain peaks in the midtones and falls off toward both
    // the toe and the shoulder; uniform-amplitude noise is the single clearest
    // tell of a fake film filter. The floor keeps blacks from going
    // suspiciously clean, which is the opposite tell.
    float L = dot(c.rgb, float3(0.2126, 0.7152, 0.0722));
    float w = exp(-((L - mu) * (L - mu)) / (2.0 * sigma * sigma));
    w = max(w, shadowFloor);

    // Mostly shared luminance grain with a little per-channel colour speckle.
    float mono = (n.r + n.g + n.b) / 3.0;
    float3 mixed = mono * (1.0 - chroma) + n * chroma;

    c.rgb += mixed * w * amount;
    return c;
}


// Diagnostic probe. Smallest possible general CIKernel. Used once at launch to
// distinguish "the build flags are wrong" from "my kernel body is wrong".
extern "C" float4 probeKernel(coreimage::sampler src, coreimage::destination dest)
{
    return src.sample(src.transform(dest.coord()));
}
