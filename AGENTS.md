# Agent Instructions for ATL Gigs

This document provides instructions for AI coding agents working on this codebase.

## Project Overview

ATL Gigs is an Atlanta event aggregator. The system has two main parts:

1. **Python scraper** (`scrape.py`): Fetches events from venue websites/APIs
2. **React frontend** (`atl-gigs/`): Displays events with filtering

Events flow: `Venue APIs/Websites → scrape.py → events.json → React app → Vercel`

## Event Schema

Every scraper must return events matching this structure:

```python
{
    "venue": str,              # Venue name (e.g., "The Earl")
    "date": str,               # "YYYY-MM-DD" format
    "doors_time": str | None,  # "HH:MM" 24-hour format
    "show_time": str | None,   # "HH:MM" 24-hour format
    "artists": [               # List of performers
        {"name": str, "genre": str | None}
    ],
    "ticket_url": str,         # Link to buy tickets
    "info_url": str | None,    # Optional detail page
    "image_url": str | None,   # Event/artist image
    "price": str | None,       # e.g., "$25" or "$20 ADV / $25 DOS"
    "category": str,           # One of: "concerts", "comedy", "broadway", "misc"
}
```

### Required Fields
- `venue`, `date`, `artists` (with at least one), `ticket_url`, `category`

### Category Selection
- `"concerts"` - Music performances (default for music venues)
- `"comedy"` - Stand-up, improv, comedy shows
- `"broadway"` - Theater, musicals, plays
- `"sports"` - Sporting events (basketball, hockey, etc.)
- `"misc"` - Everything else

---

## Adding a New Scraper

> **Before you begin**: Check `scrapers/` for existing documentation on similar venues. When done, you MUST create documentation in `scrapers/{venue-slug}.md` (see Step 5).

### Step 1: Identify the Data Source

Before writing code, inspect the venue's website to determine the best scraping approach.

**IMPORTANT: Check for upstream ticketing APIs first!**

#### Option A: Upstream Ticketing API (BEST)

Before scraping the venue's website, check if tickets are sold through a major ticketing platform:

1. **Click "Buy Tickets"** on any event and check where it goes
2. Common platforms with public APIs:
   - **Ticketmaster** → Discovery API (requires free API key from developer.ticketmaster.com)
   - **AXS** → Has API endpoints
   - **Eventbrite** → Public API available
   - **Live Nation** → GraphQL API (see existing scrapers)

**Why upstream APIs are better:**
- **Structured data**: Categories/classifications, venues, dates already parsed
- **System of record**: More complete and up-to-date than venue websites
- **Stable**: Public APIs have versioning; venue HTML can change anytime
- **Rich metadata**: Price ranges, seating, accessibility info

**Example - Ticketmaster Discovery API:**
```python
# Get venue ID once, then query events
# GET /discovery/v2/venues.json?keyword=Center Stage&city=Atlanta
# GET /discovery/v2/events.json?venueId=<id>&countryCode=US&sort=date,asc

# Events include classifications for category mapping:
# segment=Music → concerts
# segment=Arts & Theatre, genre=Comedy → comedy
```

**Current TM API Integration:**
This project already uses TM Discovery API for State Farm Arena, The Masquerade, and Center Stage complex. See `TM_VENUES` dict in `scrape.py` for venue IDs. Set `TM_API_KEY` env var to enable.

**When to skip upstream APIs:**
- Venue uses in-house ticketing (no external platform)
- API requires paid access or complex auth
- Venue has their own API that's more complete

#### Option B: Venue's JSON API (Preferred)
1. Open browser DevTools → Network tab
2. Load the venue's events page
3. Filter by "XHR" or "Fetch"
4. Look for JSON responses containing event data

**Signs of a JSON API:**
- Response content-type is `application/json`
- Clean structured data with event arrays
- Often endpoints like `/api/events`, `/events.json`, `/wp-json/*/events`, or GraphQL

**Common WordPress patterns:**
- `/wp-json/wp/v2/posts?categories=events`
- `/wp-json/{plugin}/v2/events/` (custom plugin endpoints)
- Check Network tab for XHR requests when page loads or "Load More" is clicked

#### Option C: GraphQL API
1. Look for requests to `/graphql` endpoints
2. Check request payload for `query` field
3. Copy the query and variables structure

**Example from Live Nation venues:**
```python
GRAPHQL_QUERY = """
query EVENTS($venue_id: String!) {
  getEvents(filter: { venue_id: $venue_id }) {
    name
    event_date
    artists { name }
    url
  }
}
"""
```

#### Option D: HTML Scraping (Last Resort)
Use only when no API is available. More fragile and slower.

1. Inspect the page HTML structure
2. Identify CSS selectors for event containers
3. Map selectors to required fields

#### Warning: JSON-LD Structured Data

Some venues include JSON-LD (`<script type="application/ld+json">`) in their HTML. While tempting, **JSON-LD often contains only a subset of events** (e.g., featured or upcoming). Always verify the event count against what's visible on the page. If JSON-LD is incomplete, fall back to HTML scraping or find another API.

#### Warning: Featured vs Full Event Lists

Many venue homepages show only "featured" events in a carousel or hero section. **Always look for:**
- "View All Events" or "See More Shows" buttons
- Separate `/events` or `/calendar` pages
- Network requests triggered by "Load More" buttons
- Pagination in API responses (check for `page` parameter)

The homepage carousel might show 3 events while the full calendar has 80+.

---

### Step 2: Write the Scraper Function

Add your scraper function to `scrape.py`. Follow these patterns:

#### Pattern: JSON API Scraper

```python
def scrape_example_venue():
    """Scrape events from Example Venue's JSON API."""
    url = "https://example.com/api/events"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64)",
        "Accept": "application/json",
    }

    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    events = []
    for event in data.get("events", []):
        # Skip events with missing dates
        if not event.get("date"):
            continue

        events.append({
            "venue": "Example Venue",
            "date": event["date"],  # Ensure YYYY-MM-DD format
            "doors_time": normalize_time(event.get("doors")),
            "show_time": normalize_time(event.get("showtime")),
            "artists": [{"name": event["artist"]}],
            "ticket_url": event["tickets_url"],
            "image_url": event.get("image"),
            "price": event.get("price"),
            "category": "concerts",  # Or determine from event data
        })

    return events
```

#### Pattern: GraphQL API Scraper

```python
GRAPHQL_URL = "https://api.venue.com/graphql"
GRAPHQL_HEADERS = {
    "content-type": "application/json",
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64)",
    # Copy any required headers from browser DevTools
}

GRAPHQL_QUERY = """
query GetEvents($venueId: String!) {
  events(venueId: $venueId) {
    title
    date
    ticketUrl
    artists { name }
  }
}
"""

def scrape_graphql_venue():
    """Scrape events from GraphQL API."""
    payload = {
        "query": GRAPHQL_QUERY,
        "variables": {"venueId": "abc123"},
    }

    resp = requests.post(GRAPHQL_URL, json=payload, headers=GRAPHQL_HEADERS, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    events = []
    for event in data.get("data", {}).get("events", []):
        events.append({
            "venue": "GraphQL Venue",
            "date": event["date"],
            "doors_time": None,
            "show_time": None,
            "artists": [{"name": a["name"]} for a in event["artists"]],
            "ticket_url": event["ticketUrl"],
            "image_url": None,
            "category": "concerts",
        })

    return events
```

#### Pattern: HTML Scraper

```python
def scrape_html_venue():
    """Scrape events from HTML page."""
    url = "https://example.com/events"
    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}

    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    events = []
    for card in soup.select("div.event-card"):
        # Extract date - adapt selectors to actual HTML
        date_el = card.select_one(".event-date")
        if not date_el:
            continue

        # Parse date from text like "Saturday, Jan 15, 2025"
        date_text = date_el.text.strip()
        try:
            date = datetime.strptime(date_text, "%A, %b %d, %Y").date()
        except ValueError:
            continue

        # Extract other fields
        title = card.select_one(".event-title")
        link = card.select_one("a.tickets")
        image = card.select_one("img")

        events.append({
            "venue": "HTML Venue",
            "date": str(date),
            "doors_time": None,
            "show_time": None,
            "artists": [{"name": title.text.strip() if title else "Unknown"}],
            "ticket_url": link["href"] if link else None,
            "image_url": image["src"] if image else None,
            "category": "concerts",
        })

    return events
```

#### Pattern: Paginated API

```python
def scrape_paginated_venue():
    """Scrape events from paginated API."""
    def fetch_pages():
        offset = 0
        while True:
            resp = requests.get(
                f"https://api.venue.com/events?offset={offset}&limit=50",
                timeout=15
            )
            resp.raise_for_status()
            data = resp.json()

            events = data.get("events", [])
            if not events:
                break

            yield events
            offset += 50
            time.sleep(0.3)  # Rate limiting

    all_events = []
    for page in fetch_pages():
        for event in page:
            all_events.append({
                "venue": "Paginated Venue",
                "date": event["date"],
                # ... map other fields
                "category": "concerts",
            })

    return all_events
```

---

### Step 3: Register the Scraper

Add your scraper to the `SCRAPERS` dictionary in `scrape.py`:

```python
SCRAPERS = {
    "The Earl": scrape_earl,
    "Tabernacle": scrape_tabernacle,
    "Terminal West": scrape_terminal_west,
    "The Eastern": scrape_the_eastern,
    "Coca-Cola Roxy": scrape_coca_cola_roxy,
    "Your New Venue": scrape_your_new_venue,  # Add here
}
```

---

### Step 4: Test Your Scraper

```bash
# Run the full scraper
python scrape.py

# Or test just your function in Python REPL
python -c "from scrape import scrape_your_new_venue; print(scrape_your_new_venue())"
```

Verify:
- Events have all required fields
- Dates are in `YYYY-MM-DD` format
- Times are in `HH:MM` 24-hour format (use `normalize_time()`)
- No duplicate events
- `category` is one of the valid values

---

### Step 5: Document the Scraper

**REQUIRED**: Create `scrapers/{venue-slug}.md` to document the scraper. This documentation must be created for every new scraper and updated when modifying existing scrapers.

See [Documentation Requirements](#documentation-requirements) for the full template and requirements.

Minimum required sections:
1. **Scraping approach** - API type or HTML selectors used
2. **Category mappings** - How venue categories map to ours
3. **Edge cases** - Any special handling needed

Example: See `scrapers/fox-theatre.md` for a complete reference.

---

## Utility Functions

The scraper provides these helpers:

### `normalize_time(time_str)`
Converts various time formats to `HH:MM` 24-hour format:
```python
normalize_time("8:30pm")    # → "20:30"
normalize_time("20:00:00")  # → "20:00"
normalize_time("8:00")      # → "08:00"
```

### `normalize_price(event)`
Consolidates `adv_price`/`dos_price` fields into single `price` field.

### `generate_slug(event)`
Creates URL-safe identifier from date + venue + artist.

### `validate_event(event)`
Checks that required fields are present.

### `get_artist_classification(artist_name)`
Looks up artist in Ticketmaster Attractions API to get genre/category. Results are cached to `artist-cache.json` to minimize API calls between runs.

### `enrich_events_with_tm(events)`
Enriches events from non-TM venues with artist classifications. Only looks up artists not already in cache.

---

## Ticketmaster API Integration

The scraper uses Ticketmaster Discovery API in two ways:

### 1. Primary Source for TM Venues
For venues that use Ticketmaster ticketing (State Farm Arena, The Masquerade, Center Stage), the TM API is used as the primary event source. This provides:
- Structured event data with classifications
- Automatic category mapping (Music → concerts, Comedy → comedy, etc.)
- Price ranges and high-quality images

### 2. Artist Classification Enrichment
For events from non-TM venues (The Earl, AEG venues, etc.), the scraper looks up each artist in TM's Attractions API to get their classification. This improves category accuracy for venues that don't provide genre data.

### Caching Strategy
Artist classifications are cached in `artist-cache.json` to minimize API calls:
- Cache persists between runs (locally and via GitHub Actions cache)
- Both positive results (`"concerts"`) and negative results (`null`) are cached
- Typical daily usage: <20 API calls (only new artists)

### Environment Variables
| Variable | Description |
|----------|-------------|
| `TM_API_KEY` | Ticketmaster Discovery API key (get free at developer.ticketmaster.com) |
| `USE_TM_API` | Set to `false` to disable TM API and use HTML scrapers instead |

---

## Common Issues & Solutions

### Issue: Date parsing fails
Different venues use different date formats. Parse explicitly:
```python
# "January 15, 2025"
datetime.strptime(date_str, "%B %d, %Y")

# "2025-01-15T20:00:00Z"
datetime.fromisoformat(date_str.replace("Z", "+00:00"))

# "01/15/25"
datetime.strptime(date_str, "%m/%d/%y")
```

### Issue: API requires authentication headers
Copy headers from browser DevTools:
1. Network tab → find the API request
2. Right-click → Copy as cURL
3. Extract headers like `x-api-key`, `authorization`, etc.

### Issue: Cloudflare or bot protection
- Add realistic `User-Agent` header
- Add `Accept`, `Accept-Language` headers
- Consider adding delays between requests
- As last resort, may need browser automation (not currently supported)

### Issue: Missing image URLs
Some APIs return relative URLs or CDN identifiers:
```python
# Relative URL
image_url = f"https://venue.com{event['image_path']}"

# CDN with size parameters
image_url = f"https://cdn.venue.com/images/{event['image_id']}?width=600"
```

---

## Frontend Type Updates

If you add a new category, update `atl-gigs/src/types.ts`:

```typescript
export type EventCategory = "concerts" | "comedy" | "broadway" | "misc" | "newcategory";

export const CATEGORY_LABELS: Record<EventCategory, string> = {
  concerts: "Concerts",
  comedy: "Comedy",
  broadway: "Broadway",
  misc: "Other",
  newcategory: "New Category",  // Add label
};

export const ALL_CATEGORIES: EventCategory[] = [
  "concerts", "comedy", "broadway", "misc", "newcategory"
];
```

Also update `api/og.ts` category descriptors for OG tags.

---

## Advanced Patterns

### Pattern: Multi-Category Page Scraping

Some venues organize events into category pages. Scrape all pages and deduplicate:

```python
VENUE_CATEGORY_PAGES = {
    "/events/broadway": "broadway",
    "/events/comedy": "comedy",
    "/events/special": "misc",
}

def scrape_multi_category_venue():
    """Scrape events from multiple category pages."""
    all_events = {}  # Use dict for deduplication by URL

    for path, category in VENUE_CATEGORY_PAGES.items():
        events = scrape_category_page(f"https://venue.com{path}", category)
        for event in events:
            key = event.get("info_url") or event["ticket_url"]
            # Category priority: broadway > comedy > sports > concerts > misc
            if key not in all_events or should_override_category(
                all_events[key]["category"], category
            ):
                all_events[key] = event

    return list(all_events.values())

def should_override_category(existing: str, new: str) -> bool:
    """Return True if new category should override existing."""
    priority = {"broadway": 0, "comedy": 1, "sports": 2, "concerts": 3, "misc": 4}
    return priority.get(new, 99) < priority.get(existing, 99)
```

### Pattern: Date Range Parsing

Some venues show date ranges for multi-day runs. Expand to individual dates:

```python
def parse_date_range(text: str) -> list[str]:
    """Parse 'Dec 12-15, 2025' or 'Jan 27-Feb 1, 2026' to date list."""
    # Single date: "Dec 12, 2025"
    single_match = re.match(r"(\w+)\s+(\d+),\s+(\d{4})", text)
    if single_match and "-" not in text:
        month, day, year = single_match.groups()
        date = datetime.strptime(f"{month} {day}, {year}", "%b %d, %Y")
        return [date.strftime("%Y-%m-%d")]

    # Same month range: "Dec 12-15, 2025"
    same_month = re.match(r"(\w+)\s+(\d+)-(\d+),\s+(\d{4})", text)
    if same_month:
        month, start_day, end_day, year = same_month.groups()
        dates = []
        for day in range(int(start_day), int(end_day) + 1):
            date = datetime.strptime(f"{month} {day}, {year}", "%b %d, %Y")
            dates.append(date.strftime("%Y-%m-%d"))
        return dates

    # Cross-month range: "Jan 27-Feb 1, 2026"
    cross_month = re.match(r"(\w+)\s+(\d+)-(\w+)\s+(\d+),\s+(\d{4})", text)
    if cross_month:
        # Parse start and end, iterate through range
        ...

    return []
```

---

## Category Mapping Guidelines

When a venue uses different category names than ours, map them to our preset list:

### Our Categories
- `concerts` - Music performances
- `comedy` - Stand-up, improv, comedy shows
- `broadway` - Theater, musicals, plays
- `sports` - Sporting events
- `misc` - Everything else

### Common Mappings
| Venue Category | Our Category | Rationale |
|----------------|--------------|-----------|
| music, concert | `concerts` | Direct match |
| stand-up, improv | `comedy` | Direct match |
| theater, musical, plays | `broadway` | Direct match |
| basketball, hockey, sports | `sports` | Direct match |
| hawks, team names | `sports` | Sports teams |
| holiday, seasonal | `misc` | Mixed content |
| family, kids | `misc` | General entertainment |
| special events | `misc` | Catch-all |
| live podcast | `misc` | Not a performance |
| speaker, lecture | `misc` | Not entertainment |

### When in Doubt
- If mostly music → `concerts`
- If has punchlines → `comedy`
- If has a script/story → `broadway`
- If involves teams/competition → `sports`
- Otherwise → `misc`

### Handling Catch-All Category Pages

Some venues have an "other" or "misc" category page that contains mixed event types. When events from these pages would otherwise be categorized as `misc`, use the `detect_category_from_text()` utility function to infer the correct category.

**Detection priority:**
1. **Page-based categorization** - Use the venue's category page mapping first (most reliable)
2. **Keyword detection** - For `misc` events, analyze title/URL for category keywords
3. **Known entity fallback** - Last resort for popular acts without genre keywords

**Keyword patterns (in `detect_category_from_text()`):**
- **Sports**: "sports", "hoops", "basketball", "nba", "wrestling", "wwe", "ufc", "championship", "vs", etc.
- **Comedy**: "comedy", "comedian", "stand-up", "improv", "laugh", etc.
- **Concerts**: "tour", "jam", "fest", "festival", "concert", etc.

**Ticketmaster URL hints:**
Some Ticketmaster URLs contain descriptive paths like `/cbs-sports-classic-2025/event/...`. Use `detect_category_from_ticket_url()` to extract category hints from these URLs.

**Known entity fallback:**
For popular acts whose names don't contain genre keywords (e.g., "Katt Williams", "85 South"), maintain a minimal fallback list in `detect_category_from_text()`. Keep this list small and only add acts that frequently appear at Atlanta venues.

```python
# Example usage in scraper
final_category = page_category  # From venue's category page
if final_category == "misc":
    detected = detect_category_from_text(title) or detect_category_from_ticket_url(ticket_url)
    if detected:
        final_category = detected
```

---

## Documentation Requirements

**MANDATORY**: Every scraper must have accompanying documentation in `scrapers/{venue-slug}.md`. This documentation should be:
- Created when building a new scraper
- Updated when modifying an existing scraper
- Referenced when troubleshooting scraper issues

For each scraper, document:

1. **Scraping approach** - API type, HTML structure, selectors used
2. **Category mappings** - How venue categories map to ours
3. **Edge cases** - Date formats, missing fields, deduplication
4. **Opinionated decisions** - Any non-obvious choices made

Example: `scrapers/fox-theatre.md`

```markdown
# Fox Theatre Scraper

## Category Mapping
- broadway → broadway
- comedy → comedy
- holiday → misc (mixed content including concerts)
- family → misc
- special-engagements → misc

## Edge Cases
- Date ranges parsed to individual dates
- Events deduplicated by detail_url with category priority
- No dedicated concerts page exists
```

---

## Checklist for New Scrapers

- [ ] Checked if venue uses Ticketmaster ticketing (if so, prefer TM API)
- [ ] Identified data source (TM API, JSON API, GraphQL, or HTML)
- [ ] Scraper function returns list of event dicts
- [ ] All required fields present: `venue`, `date`, `artists`, `ticket_url`, `category`
- [ ] Date format is `YYYY-MM-DD`
- [ ] Times use `normalize_time()` helper
- [ ] Category is valid: `concerts`, `comedy`, `broadway`, `sports`, or `misc`
- [ ] Venue categories mapped to our preset list
- [ ] Scraper registered in `SCRAPERS` dict (or `get_scrapers()` for TM venues)
- [ ] Tested with `python scrape.py`
- [ ] Handles errors gracefully (try/except with logging)
- [ ] Created `scrapers/{venue}.md` documentation
