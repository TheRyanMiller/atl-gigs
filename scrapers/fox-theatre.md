# Fox Theatre Scraper

## Overview

- **Venue**: Fox Theatre
- **URL**: https://www.foxtheatre.org
- **Method**: HTML scraping (server-rendered category pages)
- **Added**: 2025-11-30

## Scraping Approach

Fox Theatre uses server-rendered category pages, making HTML scraping straightforward without needing to handle JavaScript or "Load More" XHR endpoints. Each category page (`/events/upcoming-events/{category}`) returns fully rendered HTML.

### Category Pages Scraped

| URL Path | Our Category |
|----------|--------------|
| `/events/upcoming-events/broadway` | broadway |
| `/events/upcoming-events/comedy` | comedy |
| `/events/upcoming-events/holiday` | misc |
| `/events/upcoming-events/family` | misc |
| `/events/upcoming-events/special-engagements` | misc |

### HTML Structure

```html
<div class="eventItem">
  <div class="thumb">
    <img src="..." />
  </div>
  <h3 class="title">
    <a href="/events/event-name">Event Title</a>
  </h3>
  <div class="date">
    <span class="m-date__month">Dec</span>
    <span class="m-date__day">12</span>
    <span class="m-date__year">2025</span>
    <!-- Optional for date ranges: -->
    <span class="m-date__rangeLast">
      <span class="m-date__month">Dec</span>
      <span class="m-date__day">15</span>
    </span>
  </div>
  <a class="tickets" href="https://tickets.foxtheatre.org/...">Tickets</a>
</div>
```

## Category Mapping Decisions

### Direct Mappings
- **broadway** → `broadway` (theater, musicals)
- **comedy** → `comedy` (stand-up, comedy shows)

### Mapped to `misc`
- **holiday** → `misc`
  - Rationale: Mixed content including concerts (Lauren Daigle, Amy Grant), family shows, and seasonal events
  - Notable: Some music concerts appear here, but they're seasonal holiday-themed shows
- **family** → `misc`
  - Rationale: Mix of children's shows, educational events, and family entertainment
- **special-engagements** → `misc`
  - Rationale: Catch-all category for unique events (live podcast recordings, speaker events, etc.)

### No Dedicated Concerts Page
Fox Theatre does not have a `/events/upcoming-events/concerts` page (returns 404). Music events appear in:
- `holiday` category (holiday-themed concerts like Christmas tours)
- Main events page (general concerts)

Decision: Accept that most Fox Theatre events are broadway/comedy/special events. Music concerts from the main page default to `misc` since we can't reliably categorize them as `concerts` without additional parsing.

## Edge Cases

### Date Range Parsing
Fox Theatre displays date ranges for multi-day runs. Three patterns handled:

1. **Single date**: "Dec 12, 2025" → `["2025-12-12"]`
2. **Same-month range**: "Dec 12-15, 2025" → `["2025-12-12", "2025-12-13", "2025-12-14", "2025-12-15"]`
3. **Cross-month range**: "Jan 27-Feb 1, 2026" → Each date in the range

### Event Deduplication
Events can appear on multiple category pages. Deduplication strategy:
- Use `detail_url` as unique key
- When duplicate found, apply category priority: `broadway > comedy > concerts > misc`
- This ensures events are categorized by their primary type

Example: If "Wicked" appears in both `broadway` and `special-engagements`, it keeps the `broadway` category.

### Missing Fields
- **doors_time**: Not provided by venue
- **show_time**: Not consistently available (some events have it in description)
- **price**: Not consistently displayed on listing pages
- **genre**: Not available

## Notes

- All events have images (100% coverage in testing)
- Ticket URLs are direct links to the Fox Theatre ticketing system
- Some events have external ticket links (Ticketmaster) via the tickets button
- The main events page was also scraped but yielded 0 additional events after deduplication
