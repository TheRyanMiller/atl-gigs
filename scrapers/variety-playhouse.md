# Variety Playhouse Scraper

## Overview

- **Venue**: Variety Playhouse
- **URL**: https://www.variety-playhouse.com
- **Method**: AEG JSON API
- **Venue ID**: 214
- **Added**: 2025-11-30

## Scraping Approach

### Why Not Variety Playhouse Website?

The venue's own website (variety-playhouse.com/calendar) loads events via JavaScript using an AXS widget. The events are not present in the static HTML, making direct scraping impractical.

### Why Not AXS Directly?

The original plan was to scrape https://www.axs.com/venues/102442/variety-playhouse-atlanta-tickets, but AXS has aggressive Cloudflare bot protection that blocks programmatic requests (403 errors).

### Solution: AEG JSON API

Variety Playhouse is an **AEG-managed venue** that uses the same JSON API infrastructure as Terminal West and The Eastern. The API endpoint was discovered by examining the venue's calendar page JavaScript:

```
https://aegwebprod.blob.core.windows.net/json/events/214/events.json
```

This JSON API:
- Has no authentication required
- Returns complete event data
- Is the same format used by other AEG venues

## Data Structure

The API returns the standard AEG event format:

```json
{
  "events": [
    {
      "eventId": "909214",
      "title": {
        "headlinersText": "Bonnie 'Prince' Billy",
        "supportingText": "Matt Kivel"
      },
      "eventDateTime": "2025-12-04T20:00:00",
      "doorDateTime": "2025-12-04T19:00:00",
      "ticketing": {
        "url": "https://www.axs.com/events/909214/bonnie-prince-billy-tickets"
      },
      "ticketPriceLow": "$25.00",
      "ticketPriceHigh": "$30.00",
      "media": { ... }
    }
  ]
}
```

## Implementation

Reuses the existing `scrape_aeg_venue()` function:

```python
def scrape_variety_playhouse():
    """Scrape events from Variety Playhouse's JSON API."""
    return scrape_aeg_venue(
        "https://aegwebprod.blob.core.windows.net/json/events/214/events.json",
        "Variety Playhouse"
    )
```

## Category

All events default to `concerts` (music venue). This is appropriate since Variety Playhouse is primarily a music venue.

## Notes

- Ticket URLs link to AXS (not Ticketmaster)
- All events have images available
- Doors time and show time both available
- Price range available for all events
- Venue capacity: ~1,000 (intimate music venue)

## Discovery Process

1. Checked variety-playhouse.com - events loaded via JS widget
2. Tried AXS direct scraping - blocked by Cloudflare (403)
3. Examined calendar page JavaScript for API hints
4. Found references to `aegwebprod.blob.core.windows.net` (same as Terminal West/Eastern)
5. Discovered venue ID 214 in page source
6. Confirmed API endpoint returns valid event data
