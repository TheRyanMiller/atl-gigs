# Helium Comedy Club Scraper

## Scraping Approach
- Scrapes `https://atlanta.heliumcomedy.com/events`, which is powered by SeatEngine.
- The page is server-rendered and embeds schema.org JSON-LD containing per-show `Event` records.
- The scraper uses JSON-LD because it includes individual show URLs and start times; the visible cards were checked to confirm the JSON-LD covers the listed events.

## Category Mapping
- All Helium Atlanta events map to `comedy`.

## Edge Cases
- JSON-LD `startDate` values are UTC; the scraper converts them to `America/New_York` before writing `date` and `show_time`.
- Titles with `POSTPONED`, `CANCELED`, or `CANCELLED` are skipped.
- Display prefixes such as `Special Event:`, `Helium Presents:`, and `In The Other Room:` are removed from artist names.
- Descriptions are trimmed before package, two-item-minimum, and venue policy boilerplate.

## Opinionated Decisions
- `ticket_url` and `info_url` both use the SeatEngine show URL because it is the detail and purchase entry point.
- `doors_time` is left empty because the source does not provide per-show doors data.
