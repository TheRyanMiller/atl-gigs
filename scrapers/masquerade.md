# The Masquerade Scraper

## Overview

- **Venue**: The Masquerade
- **URL**: https://www.masqueradeatlanta.com/events/
- **Method**: HTML scraping with BeautifulSoup
- **Added**: 2025-11-30

## Venue Details

The Masquerade is a multi-stage music venue in Atlanta with 4 stages:
- **Heaven** - Largest room
- **Hell** - Medium room
- **Purgatory** - Smaller room
- **Altar** - Intimate room

## Scraping Approach

### Why HTML Scraping?

The Masquerade website renders events in static HTML with well-structured `article.event` elements. No JavaScript loading or API authentication required.

### Important: Stage Filtering

The Masquerade's events page lists events at both their own venue AND other Atlanta venues (Tabernacle, Eastern, etc.) since they're part of the same promotion network.

The scraper filters to only include events at actual Masquerade stages by checking the venue text for stage names (Heaven, Hell, Purgatory, Altar).

## Data Structure

Events are parsed from `article.event` elements:

```html
<article class="event">
  <span class="eventStartDate" content="2025-01-17T00:00:00">...</span>
  <span class="time-show">Doors 7:00 pm / All Ages</span>
  <h3 class="eventHeader__title">Artist Name</h3>
  <p class="eventHeader__support">Support Act 1, Support Act 2</p>
  <span class="js-listVenue">The Masquerade - Heaven</span>
  <a class="btn-purple" href="...">Tickets</a>
  <a class="wrapperLink" href="...">Details</a>
  <div class="event--featuredImage" style="background-image: url(...)"></div>
</article>
```

Optional descriptions are fetched from each detail page by matching the headliner against `.attractions .attraction-bio`. Support-act bios are not used as event descriptions when the headliner has no usable copy.

## Implementation

```python
def scrape_masquerade():
    """
    Scrape events from The Masquerade using HTML parsing.
    Only includes events at Masquerade stages (Heaven, Hell, Purgatory, Altar).
    """
    url = MASQUERADE_BASE + "/events/"
    resp = requests.get(url, headers=MASQUERADE_HEADERS, timeout=MASQUERADE_TIMEOUT)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    events = []
    for article in soup.select("article.event"):
        # Check venue - skip events not at Masquerade stages
        venue_span = article.select_one(".js-listVenue")
        venue_text = venue_span.get_text(strip=True)
        stage = None
        for s in MASQUERADE_STAGES:
            if s in venue_text:
                stage = s
                break
        if not stage:
            continue  # Skip external venue events

        # Parse event details...
        events.append({
            "venue": "The Masquerade",
            "stage": stage,  # Heaven, Hell, Purgatory, or Altar
            # ... other fields
            "category": "concerts",  # Default for music venue
        })

    return events
```

## Category

All events default to `concerts` since The Masquerade is primarily a music venue hosting rock, metal, electronic, and alternative acts.

## Notes

- Door times available for most events
- Support acts listed separately from headliners
- Support acts are split on common delimiters and leading `&`/`and` fragments are removed
- Images available for all events
- Ticket links go to various providers (AXS, Eventbrite, etc.)
- Events at external venues (Tabernacle, Eastern) are filtered out
- Stage stored in separate `stage` field (displayed in modal as "The Masquerade · Heaven")
- Detail-page description failures are non-fatal; affected events are still published without `description`.

## Discovery Process

1. Inspected events page HTML structure
2. Found `article.event` elements with consistent CSS classes
3. Discovered venue listing includes external venues - added stage filtering
4. Identified 4 stages: Heaven, Hell, Purgatory, Altar
5. Tested date parsing from `content` attribute and door time spans
