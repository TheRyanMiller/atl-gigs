# Fox Theatre Scraper

## Scraping Approach
- Source: Fox Theatre AJAX endpoint under `https://www.foxtheatre.org/events/events_ajax/{offset}`.
- The scraper first initializes a browser-like session against `/events`, then requests AJAX pages with `per_page=60`.
- AJAX responses may be JSON-encoded HTML or raw HTML; both forms are handled.
- Event cards are selected with `div.eventItem`.
- Detail URL, ticket URL, image, date block, title, and category classes are parsed from each card.
- Optional descriptions are fetched from detail pages using non-empty meta description tags.

## Category Mapping
- Card class `broadway` -> `broadway`
- Card class `comedy` -> `comedy`
- Card class `concerts` -> `concerts`
- Anything else -> `misc`

## Edge Cases
- Cloudflare/406 responses can happen; the scraper refreshes the session and retries the AJAX request.
- Date ranges are preserved as `date` plus optional `end_date`; the pipeline currently publishes the start date.
- The parser handles single dates, same-month ranges, cross-month ranges, and Fox markup with spaced commas such as `May 2 - 3 , 2026`.
- Duplicate detail URLs are skipped while walking AJAX pages.
- Fox does not expose consistent doors, show time, price, or genre fields on listing cards.
- Detail-page description failures are non-fatal; affected events are still published without `description`.

## Fallback
- If the Fox AJAX scrape fails, the venue scraper tries to preserve previously saved Fox Theatre events from `events.json`.
- Cached fallback is used only when previous Fox events exist; otherwise the original scrape error is raised so venue status reports the failure.

## Opinionated Decisions
- The AJAX endpoint is used instead of category pages because it returns the current unified event list and avoids maintaining multiple category URLs.
- Date ranges are not expanded into multiple rows because the existing app schema and merge logic treat each listing as one event.
