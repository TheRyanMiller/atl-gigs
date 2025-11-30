# OG Image Generation - Technical Summary

## Goal
Generate dynamic OpenGraph images for event pages with:
- Event poster image as background
- Date badge overlay (top-left)
- ATL Gigs logo badge (bottom-right)
- Default homepage image with stylized logo when no event params

## Tech Stack
- **Frontend**: Vite + React + TypeScript
- **Hosting**: Vercel (via GitHub Actions deployment)
- **Attempted Solution**: `@vercel/og` (v0.8.5) - Vercel's official OG image library

## Current Blockers

### Root Cause (Confirmed)
```
WebAssembly.instantiate(): Wasm code generation disallowed by embedder
```

`@vercel/og` uses Satori (WASM-based SVG renderer) internally. Vercel's edge runtime is blocking WebAssembly execution in our deployment configuration.

## Approaches Tried

| Approach | Result |
|----------|--------|
| Basic `@vercel/og` edge function | Empty 0-byte response |
| JSX import source pragma | No change |
| Explicit font loading | No change |
| Node.js runtime (instead of edge) | FUNCTION_INVOCATION_FAILED |
| `vercel.json` with `@vercel/edge` runtime | Still WASM blocked |
| `"framework": "vite"` in vercel.json | Still WASM blocked |
| Various CSS simplifications | No change |
| Remove emojis/special characters | No change |

## Key Observations
1. The edge function **does execute** (returns HTTP 200)
2. Content-type is correctly set to `image/png`
3. Response body is 0 bytes (before debug changes)
4. With try/catch, we now see the WASM error
5. The og.ts serverless function (Node.js, no WASM) works fine

## Files Involved
- `/api/og-image.tsx` - Main OG image endpoint (edge)
- `/api/og-test.tsx` - Minimal test endpoint (edge)
- `/api/og.ts` - HTML/meta tag endpoint for crawlers (works)
- `/vercel.json` - Vercel configuration

## Potential Solutions to Evaluate

### Option 1: Debug Vercel Edge Config
- Check Vercel project settings for edge function restrictions
- Verify WASM is enabled for the project
- Contact Vercel support about WASM in Vite projects

### Option 2: Migrate to Next.js
- Next.js has first-class @vercel/og support
- Would require significant refactoring
- Guaranteed to work with OG images

### Option 3: Alternative Image Generation
- Use `sharp` or `canvas` in Node.js serverless function
- More manual but avoids edge/WASM issues
- Can render images server-side

### Option 4: External Service
- Use Cloudinary or imgix transformations
- Offload image generation entirely
- Additional service dependency

### Option 5: Static Pre-generation
- Generate OG images at scrape time (GitHub Actions)
- Store as static files
- No runtime generation needed

## Recommended Next Steps
1. **Verify** WASM config in Vercel dashboard (Project Settings > Functions)
2. **Test** a fresh Vite + @vercel/og project to isolate if issue is project-specific
3. **Consider** Option 3 or 5 as pragmatic workarounds if edge WASM remains blocked

## Resources
- [@vercel/og documentation](https://vercel.com/docs/functions/og-image-generation)
- [Satori (underlying renderer)](https://github.com/vercel/satori)
- [Vercel Edge Functions WASM support](https://vercel.com/docs/functions/edge-functions/wasm)
