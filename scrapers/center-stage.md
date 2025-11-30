# Center Stage Scraper

Covers three venues in the same complex:
- **Center Stage** - Main 1,050-capacity theater
- **The Loft** - Upstairs 400-capacity room
- **Vinyl** - Intimate 250-capacity club

## Data Source

**REST API**: `/wp-json/centerstage/v2/events/`

The venue uses a custom WordPress plugin ("event-fetcher") with a REST API endpoint. This is preferable to HTML scraping because:
- Structured JSON with all event data
- Pagination support (20 events per page)
- Includes all events, not just featured

### Alternative Considered: Ticketmaster Discovery API

All ticket sales go through Ticketmaster, which has a public Discovery API. This would be the **ideal** source because:
- Includes event classifications (segment, genre) for automatic category detection
- System of record for ticket data
- More stable than venue APIs

**Why we don't use it**: Requires API key registration at developer.ticketmaster.com. If you set up a key in the future, consider migrating to Ticketmaster Discovery API.

## API Response Structure

```json
{
  "title": "Artist Name",
  "event_date": "20251210",
  "venue_room": {"value": "center_stage", "label": "Center Stage"},
  "door_time": "7:00 pm",
  "show_time": "8:00 pm",
  "event_url": "https://www.ticketmaster.com/event/...",
  "event_image": "https://...",
  "permalink": "https://www.centerstage-atlanta.com/events/artist-name/",
  "external_venue": ""
}
```

## Venue Filtering

The `venue_room.value` field maps to our venues:
- `center_stage` → "Center Stage"
- `the_loft` → "The Loft"
- `vinyl` → "Vinyl"

Events with non-empty `external_venue` are excluded (shows at other locations promoted by the same company).

## Category Detection

The API doesn't provide category information. We use `detect_category_from_text()` on the event title to infer:
- Comedy keywords → `comedy`
- Default → `concerts` (primary use is music)

## Pagination

API returns 20 events per page. Use `?page=N` parameter to fetch all pages. Stop when:
- Response is empty
- Response has fewer than 20 events

## Edge Cases

1. **Featured carousel trap**: Homepage shows only 3 featured events. The REST API (discovered via "View More Shows" button) has the full list (70+ events).

2. **External venues**: Some events have `external_venue` set (e.g., "Kenny Wayne Shepherd Band" at an external location). These are filtered out.

3. **Time format**: Times are "7:00 pm" format, converted via `normalize_time()`.

## Key Learnings

When building this scraper, we initially tried to parse the homepage HTML and only found 3 events. The correct approach:

1. Check where "Buy Tickets" links go → Ticketmaster (upstream API available)
2. Look for "View More Shows" or similar → Found REST API in Network tab
3. Test the API pagination → Discovered 78 total events vs 3 in HTML
