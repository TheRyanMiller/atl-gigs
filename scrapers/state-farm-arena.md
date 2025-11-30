# State Farm Arena Scraper

## Overview

- **Venue**: State Farm Arena
- **URL**: https://www.statefarmarena.com
- **Method**: HTML scraping with BeautifulSoup
- **Added**: 2025-11-30

## Scraping Approach

State Farm Arena uses server-rendered HTML with category pages. Each category page (`/events/category/{category}`) contains event cards with structured date elements.

### Category Pages Scraped

| URL Path | Our Category | Notes |
|----------|--------------|-------|
| `/events/category/concerts` | concerts | Music performances |
| `/events/category/family-shows` | misc | Family entertainment |
| `/events/category/hawks` | sports | Atlanta Hawks basketball |
| `/events/category/other` | misc | Catch-all category |

### HTML Structure

```html
<div class="eventItem">
  <div class="thumb">
    <img src="..." />
  </div>
  <div class="info">
    <div class="title">
      <a href="/events/detail/...">Event Title</a>
    </div>
    <div class="date">
      <div class="m-date__singleDate">
        <span class="m-date__month">Dec</span>
        <span class="m-date__day">1</span>
        <span class="m-date__year">2025</span>
      </div>
      <!-- OR for date ranges: -->
      <div class="m-date__rangeFirst">...</div>
      <div class="m-date__rangeLast">...</div>
    </div>
    <div class="meta">
      <div class="time">Event Starts 7:00 PM</div>
    </div>
  </div>
  <a class="more" href="/events/detail/...">More Info</a>
  <a class="tickets" href="https://ticketmaster.com/...">Buy Tickets</a>
</div>
```

## Category Mapping Decisions

### Concerts → `concerts`
Direct mapping for music performances.

### Hawks → `sports`
Atlanta Hawks basketball games. Mapped to `sports` category.

### Family Shows → `misc`
Family entertainment like Monster Truck shows. Mapped to `misc`.

### Other → `misc` (with intelligent detection)
Catch-all page containing mixed event types. For events on this page, the scraper uses `detect_category_from_text()` to infer the correct category from:
1. **Title keywords** - "sports", "hoops", "comedy", "tour", "jam", etc.
2. **Ticketmaster URL paths** - When URLs contain descriptive names like `/cbs-sports-classic-2025/`
3. **Known entity fallback** - Popular comedy acts like "Katt Williams", "85 South"

This allows events like "Holiday Hoopsgiving" (sports) and "Winter Jam" (concerts) to be properly categorized even though they appear on the catch-all "other" page.

## Edge Cases

### Date Range Parsing
Multi-day events (e.g., concerts with multiple shows) have date ranges:
- Uses `.m-date__rangeFirst` and `.m-date__rangeLast` elements
- Scraper uses the start date for the event listing

### Time Parsing
Show times appear as "Event Starts 7:00 PM" in the `.time` element.
- Regex extracts the time portion
- Normalized to 24-hour format (e.g., "19:00")

### Pagination
The site has a "Load More Events" link for pagination.
- Pattern: `a[href*='/events/index/']`
- Scraper follows up to 10 pages per category (safety limit)

### Deduplication
Events may appear in multiple categories. Deduplication strategy:
- Use `detail_url` as unique key
- Apply category priority: `concerts > misc`

## Notes

- All events have images (100% coverage in testing)
- Ticket URLs link directly to Ticketmaster
- Site also has JSON-LD structured data, but it only contains a subset of events
- No doors_time available - only show_time
