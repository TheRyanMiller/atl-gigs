# The Eastern Scraper

## Scraping Approach
- Source: AEG JSON API at `https://aegwebprod.blob.core.windows.net/json/events/127/events.json`.
- Shared implementation: `scrape_aeg_venue()` in `scraper/venues/aeg.py`.
- Event records are transformed by `transform_aeg_event()`, which parses dates, doors/show times, artists, prices, images, AXS ticket URLs, and optional `description`/`bio` copy.

## Category Mapping
- The Eastern is a music venue, so events default to `concerts`.
- Artist/category enrichment later in the pipeline may add genre metadata when available.

## Edge Cases
- Events with `TBD` or malformed dates are skipped.
- Events missing artists or ticket URLs are skipped so invalid records do not reach the pipeline.
- Malformed individual events do not abort the whole venue scrape.
- Image extraction prefers AEG media entries with width `678`, then falls back to the first usable media URL.
- Description copy is optional; empty or logistics-only text is omitted.

## Opinionated Decisions
- AEG is preferred over direct AXS scraping because the JSON endpoint is structured and AXS pages are bot-protected.
