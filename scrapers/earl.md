# The Earl Scraper

## Scraping Approach
- Source: The Earl WordPress calendar HTML at `https://badearl.com/`.
- Pagination uses the Search & Filter query parameter `?sf_paged=N`.
- Event cards are selected with `div.cl-layout__item`.
- Date, time, price, artists, ticket URL, detail URL, and image URL come from the `show-listing-*` classes inside each card.
- Optional artist descriptions are fetched from each detail page and parsed from `.band-details .band-info`.
- Freshtix is the upstream ticketing provider, but it currently redirects generic event listing requests through Queue-it, so the venue calendar remains the practical source.

## Category Mapping
- The Earl is a music venue, so all scraped events use `concerts`.
- Ticketmaster artist enrichment may refine artist metadata later in the pipeline, but the venue scraper itself does not assign non-concert categories.

## Edge Cases
- `https://badearl.com/show-calendar/` redirects to the home page, so the scraper uses the canonical home URL directly.
- Door times can appear as `8:00 pm doors`; the parser preserves the meridiem before calling `normalize_time()`.
- The scraper retries transient timeouts and connection failures, then raises a venue-specific error so the pipeline records The Earl as failed while preserving existing events during merge.
- Pagination stops when a page contains `No results found.`.
- Detail-page description failures are non-fatal; affected events are still published without `description`.

## Opinionated Decisions
- A split connect/read timeout keeps dead connections from hanging the run for a full 30 seconds per attempt while still allowing slow page responses.
- HTML scraping is retained because the WordPress `show` REST endpoint exposes show records but not the custom event fields needed for dates, prices, and ticket links.
