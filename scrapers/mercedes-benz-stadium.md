# Mercedes-Benz Stadium Scraper

## Overview

- **Venue**: Mercedes-Benz Stadium
- **URL**: https://www.mercedesbenzstadium.com
- **Method**: HTML scraping with BeautifulSoup
- **Added**: 2025-11-30

## Scraping Approach

Mercedes-Benz Stadium uses Webflow CMS with Finsweet CMS Filter. All events are rendered server-side as static HTML with client-side filtering via JavaScript.

### Why Not JSON API?

- No public JSON API endpoint discovered
- JSON-LD structured data not present on the events page
- XHR/Fetch requests only load non-event data (analytics, chat widget)

### HTML Structure

Events are displayed in a filtered grid with the following structure:

```html
<div class="events--item w-dyn-item">
  <div class="events_img events_img--16-9">
    <img class="event_image" src="..." />
  </div>
  <div class="events_feature_content alt">
    <h3>Event Title</h3>
    <div class="events_tags--list w-dyn-items">
      <div class="events_tags--item w-dyn-item">Sports</div>
    </div>
    <div class="events_feature_details">
      <div class="events_feature_details--item">
        <div class="events_feature_details_label">Date</div>
        <div class="events_feature_details_dt">December 6, 2025</div>
      </div>
      <div class="events_feature_details--item">
        <div class="events_feature_details_label">Time</div>
        <div class="events_feature_details_dt">4:00 PM</div>
      </div>
    </div>
    <div class="btn--wrapper">
      <a class="btn--1" href="https://ticketmaster.com/...">Tickets</a>
      <a class="btn--3" href="/events/event-slug">Event Details</a>
    </div>
  </div>
</div>
```

### CSS Selectors Used

| Element | Selector |
|---------|----------|
| Event container | `div.events--item.w-dyn-item` |
| Title | `h3` |
| Category | `div.events_tags--item.w-dyn-item` |
| Date/Time | `div.events_feature_details_dt` (first=date, second=time) |
| Ticket URL | `a.btn--1` |
| Detail URL | `a.btn--3[href*='/events/']` |
| Image | `img.event_image` |

## Category Mapping

| Website Category | Our Category | Notes |
|-----------------|--------------|-------|
| Sports | `sports` | Football, soccer, bowl games |
| Concert | `concerts` | Music performances |
| Other | `misc` | Catch-all events |
| Conference | `misc` | Business events (rare) |
| Home Depot Backyard | `misc` | Free community events |

## Edge Cases

### Date Parsing

The site uses two date formats:
- Full date: "December 6, 2025" → parsed with `%B %d, %Y`
- Month-year only: "June 2026" → parsed with `%B %Y` (defaults to 1st of month)

Events with unparseable dates (e.g., "2026", "TBA") are skipped.

### Time Handling

- Times appear as "4:00 PM", "7:30 PM", etc.
- "TBD" and "TBA" times are normalized to `None`
- No doors_time available - only show_time

### No Pagination

All events appear on a single page with client-side filtering. No pagination handling required.

### Game Items

The site also has separate game items for Atlanta Falcons and Atlanta United with class `events_game--item`. These use different HTML structure and link to team-specific pages. Currently not scraped as they have incomplete data in the listing view.

## Notes

- Site uses Webflow and loads relatively quickly
- All events have images (CDN URLs from `cdn.prod.website-files.com`)
- Ticket URLs typically link to Ticketmaster
- Some events (Super Bowl, FIFA World Cup) may not have ticket URLs yet
- Deduplication by detail URL handles any edge cases
