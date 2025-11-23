#!/usr/bin/env python3
"""
Scrape concert events from multiple venues and save to JSON.
Currently supports:
- The Earl (badearl.com)
- Tabernacle (tabernacleatl.com)
- Terminal West (AEG)
- The Eastern (AEG)
- Coca-Cola Roxy (Live Nation)
"""

import requests, datetime as dt, re, itertools, json, time, os, traceback
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent
OUTPUT_PATH = SCRIPT_DIR / "atl-gigs" / "public" / "events.json"
STATUS_PATH = SCRIPT_DIR / "atl-gigs" / "public" / "scrape-status.json"
BACKUP_PATH = SCRIPT_DIR / "events.json"  # Also save to root for reference

REQUIRED_FIELDS = ["venue", "date", "artists", "ticket_url"]

# ----------------------------------------------------------------------
# Utility Functions
# ----------------------------------------------------------------------

def generate_slug(event):
    """
    Generate a unique slug for an event based on date, venue, and artist.
    Format: YYYY-MM-DD-venue-name-artist-name
    """
    date = event.get("date", "")
    venue = event.get("venue", "")
    artist = event.get("artists", [{}])[0].get("name", "unknown")
    
    # Slugify: lowercase, replace spaces with hyphens, remove special chars
    def slugify(text):
        text = text.lower().strip()
        text = re.sub(r'[^\w\s-]', '', text)  # Remove special chars except hyphens
        text = re.sub(r'[\s_]+', '-', text)   # Replace spaces/underscores with hyphens
        text = re.sub(r'-+', '-', text)       # Remove duplicate hyphens
        return text.strip('-')
    
    slug_parts = [date, slugify(venue), slugify(artist)]
    return "-".join(filter(None, slug_parts))


def normalize_time(time_str):
    """
    Normalize time strings to consistent HH:MM 24-hour format.
    Handles: "8:00", "8:30pm", "20:00:00", "19:00", "8:00pm"
    """
    if not time_str:
        return None
    
    time_str = time_str.strip().lower()
    
    # Remove seconds if present (20:00:00 -> 20:00)
    if time_str.count(":") == 2:
        time_str = ":".join(time_str.split(":")[:2])
    
    # Handle 12-hour format with am/pm
    is_pm = "pm" in time_str
    is_am = "am" in time_str
    time_str = time_str.replace("pm", "").replace("am", "").strip()
    
    # Parse hours and minutes
    parts = time_str.split(":")
    if len(parts) != 2:
        return None
    
    try:
        hours = int(parts[0])
        minutes = int(parts[1])
    except ValueError:
        return None
    
    # Convert to 24-hour if needed
    if is_pm and hours < 12:
        hours += 12
    elif is_am and hours == 12:
        hours = 0
    
    return f"{hours:02d}:{minutes:02d}"


def is_zero_price(price_str):
    """Check if a price string represents $0 or free."""
    if not price_str:
        return True
    # Match variations of $0.00, $0, $0.0, etc.
    zero_patterns = [r'^\$0(\.0+)?$', r'^\$0(\.0+)?\s*-\s*\$0(\.0+)?$']
    price_clean = price_str.strip()
    for pattern in zero_patterns:
        if re.match(pattern, price_clean):
            return True
    return False


def normalize_price(event):
    """
    Consolidate price fields into a single 'price' field.
    Combines adv_price/dos_price from The Earl into standard format.
    Filters out $0 prices (often means price not available in API).
    """
    if "price" in event and event["price"]:
        price = event["price"]
    elif "adv_price" in event or "dos_price" in event:
        adv = event.get("adv_price", "")
        dos = event.get("dos_price", "")
        if adv and dos:
            # Extract just the dollar amounts
            adv_match = re.search(r'\$[\d.]+', adv)
            dos_match = re.search(r'\$[\d.]+', dos)
            if adv_match and dos_match:
                price = f"{adv_match.group()} ADV / {dos_match.group()} DOS"
            else:
                price = f"{adv} / {dos}"
        else:
            price = adv or dos
    else:
        price = None
    
    # Replace $0 prices with "See website" - these usually mean price not available in API
    if is_zero_price(price):
        price = "See website"
    
    # Remove the old fields and set normalized price
    event.pop("adv_price", None)
    event.pop("dos_price", None)
    event["price"] = price
    return event


def validate_event(event):
    """Check that event has all required fields with valid data."""
    for field in REQUIRED_FIELDS:
        if not event.get(field):
            return False
    # Must have at least one artist
    if not event.get("artists") or len(event["artists"]) == 0:
        return False
    return True


def load_existing_status():
    """Load existing status file to preserve historical data."""
    try:
        if STATUS_PATH.exists():
            with open(STATUS_PATH, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {"venues": {}}


# ----------------------------------------------------------------------
# The Earl scraper
# ----------------------------------------------------------------------

EARL_BASE   = "https://badearl.com/show-calendar/"
EARL_PAGE_Q = "?sf_paged={}"
EARL_HEADERS = {
    "User-Agent":      "Mozilla/5.0 (X11; Linux x86_64)",
    "Accept-Language": "en-US,en;q=0.8",
}

def scrape_earl():
    """Scrape events from The Earl's website."""
    def pages():
        n = 1
        while True:
            url = EARL_BASE if n == 1 else EARL_BASE + EARL_PAGE_Q.format(n)
            r = requests.get(url, headers=EARL_HEADERS, timeout=15)
            if r.status_code != 200 or "No results found." in r.text:
                break
            yield r.text
            n += 1

    def parse_page(html):
        soup = BeautifulSoup(html, "html.parser")
        for card in soup.select("div.cl-layout__item"):
            # --- image -------------------------------------------------
            img = card.select_one("div.cl-element-featured_media img")
            image_url = img["src"] if img else None

            # --- date --------------------------------------------------
            date_tag = card.select_one("p.show-listing-date")
            if not date_tag:
                continue
            date = dt.datetime.strptime(date_tag.text.strip(),
                                      "%A, %b. %d, %Y").date()

            # --- times -------------------------------------------------
            times = [t.text.strip() for t in card.select("p.show-listing-time")]
            doors = times[0].split()[0] if times else None
            show = times[1].split()[0] if len(times) > 1 else None

            # --- prices ------------------------------------------------
            prices = [p.text.strip() for p in card.select("p.show-listing-price")]
            adv = next((p for p in prices if "ADV" in p), None)
            dos = next((p for p in prices if "DOS" in p), None)

            # --- artists ----------------------------------------------
            headliners = [h.text.strip()
                         for h in card.select("div.show-listing-headliner")]
            supports = [s.text.strip()
                       for s in card.select("div.show-listing-support")]
            artists = headliners + supports

            # --- links -------------------------------------------------
            tix = card.find("a", string="TIX", href=True)
            info = card.find("a", string="More Info", href=True)

            yield {
                "venue": "The Earl",
                "date": str(date),
                "doors_time": normalize_time(doors),
                "show_time": normalize_time(show),
                "artists": [{"name": a} for a in artists],
                "adv_price": adv,
                "dos_price": dos,
                "ticket_url": tix["href"] if tix else None,
                "info_url": info["href"] if info else None,
                "image_url": image_url
            }

    return list(itertools.chain.from_iterable(parse_page(p) for p in pages()))

# ----------------------------------------------------------------------
# AEG Venues scraper (Terminal West and The Eastern)
# ----------------------------------------------------------------------

AEG_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64)",
    "Accept": "application/json",
}

def scrape_aeg_venue(url, venue_name):
    """Scrape events from an AEG venue's JSON API."""
    resp = requests.get(url, headers=AEG_HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    events = []
    for event in data.get("events", []):
        # Skip events with TBD or missing dates
        event_dt_str = event.get("eventDateTime", "")
        if not event_dt_str or "TBD" in event_dt_str:
            continue
        
        # Parse the event date
        event_date = datetime.fromisoformat(event_dt_str.replace("Z", "+00:00"))
        
        # Get artists
        artists = []
        if event.get("title", {}).get("headlinersText"):
            artists.append({"name": event["title"]["headlinersText"]})
        if event.get("title", {}).get("supportingText"):
            artists.append({"name": event["title"]["supportingText"]})

        # Get ticket price range
        price_low = event.get("ticketPriceLow", "$0.00")
        price_high = event.get("ticketPriceHigh", "$0.00")
        price = f"{price_low} - {price_high}" if price_low != price_high else price_low

        # Parse times
        doors_time = None
        if event.get("doorDateTime"):
            doors_time = event["doorDateTime"].split("T")[1][:5]
        show_time = event["eventDateTime"].split("T")[1][:5]

        # Get image URL - media can be dict or empty list
        image_url = None
        media = event.get("media")
        if isinstance(media, dict) and media:
            image_url = next((img["file_name"] for img in media.values() 
                             if img.get("width") == 678), None)

        events.append({
            "venue": venue_name,
            "date": event_date.strftime("%Y-%m-%d"),
            "doors_time": normalize_time(doors_time),
            "show_time": normalize_time(show_time),
            "artists": artists,
            "ticket_url": event.get("ticketing", {}).get("url"),
            "image_url": image_url,
            "price": price
        })

    return events

def scrape_terminal_west():
    """Scrape events from Terminal West's JSON API."""
    return scrape_aeg_venue(
        "https://aegwebprod.blob.core.windows.net/json/events/211/events.json",
        "Terminal West"
    )

def scrape_the_eastern():
    """Scrape events from The Eastern's JSON API."""
    return scrape_aeg_venue(
        "https://aegwebprod.blob.core.windows.net/json/events/127/events.json",
        "The Eastern"
    )

# ----------------------------------------------------------------------
# Live Nation Venues scraper (Tabernacle and Coca-Cola Roxy)
# ----------------------------------------------------------------------

LIVE_NATION_GRAPHQL_URL = "https://api.livenation.com/graphql"
LIVE_NATION_HEADERS = {
    "content-type": "application/json; charset=UTF-8",
    "origin": "https://www.cocacolaroxy.com",
    "referer": "https://www.cocacolaroxy.com/",
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64)",
    "x-api-key": "da2-jmvb5y2gjfcrrep3wzeumqwgaq",
    "x-amz-user-agent": "aws-amplify/6.13.5 api/1 framework/2",
}

LIVE_NATION_QUERY = """
query EVENTS_PAGE($offset: Int!, $venue_id: String!) {
  getEvents(
    filter: {
      exclude_status_codes: ["cancelled", "postponed"]
      image_identifier: "RETINA_PORTRAIT_16_9"
      venue_id: $venue_id
    }
    limit: 36
    offset: $offset
    order: "ascending"
    sort_by: "start_date"
  ) {
    artists { name genre }
    event_date
    event_time
    event_end_time
    name
    url
    images { image_url }
  }
}
"""

def scrape_live_nation_venue(venue_id, venue_name):
    """Scrape events from a Live Nation venue's GraphQL API."""
    def pages():
        offset = 0
        while True:
            payload = {
                "query": LIVE_NATION_QUERY,
                "variables": {
                    "offset": offset,
                    "venue_id": venue_id,
                },
            }
            resp = requests.post(LIVE_NATION_GRAPHQL_URL, json=payload, headers=LIVE_NATION_HEADERS, timeout=20)
            resp.raise_for_status()
            data = resp.json()

            events = data.get("data", {}).get("getEvents", [])
            if not events:
                break

            yield events
            offset += 36
            time.sleep(0.4)

    def transform_event(event):
        return {
            "venue": venue_name,
            "date": event["event_date"],
            "doors_time": normalize_time(event["event_time"]),
            "show_time": normalize_time(event["event_end_time"]),
            "artists": [{"name": a["name"], "genre": a.get("genre")} 
                       for a in event["artists"]],
            "ticket_url": event["url"],
            "image_url": event["images"][0]["image_url"] if event["images"] else None
        }

    return [transform_event(e) for e in itertools.chain.from_iterable(pages())]

def scrape_tabernacle():
    """Scrape events from Tabernacle's GraphQL API."""
    return scrape_live_nation_venue("KovZpaFEZe", "Tabernacle")

def scrape_coca_cola_roxy():
    """Scrape events from Coca-Cola Roxy's GraphQL API."""
    return scrape_live_nation_venue("KovZ917ACc7", "Coca-Cola Roxy")

# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------

# Registry of all scrapers for easy iteration
SCRAPERS = {
    "The Earl": scrape_earl,
    "Tabernacle": scrape_tabernacle,
    "Terminal West": scrape_terminal_west,
    "The Eastern": scrape_the_eastern,
    "Coca-Cola Roxy": scrape_coca_cola_roxy,
}

def main():
    all_events = []
    run_timestamp = datetime.utcnow().isoformat() + "Z"
    
    # Load existing status to preserve last_success data
    existing_status = load_existing_status()
    venue_statuses = {}
    
    for venue_name, scraper in SCRAPERS.items():
        print(f"Scraping {venue_name}...")
        venue_status = {
            "last_run": run_timestamp,
            "success": False,
            "event_count": 0,
            "error": None,
        }
        
        # Preserve last successful scrape info from existing status
        existing_venue = existing_status.get("venues", {}).get(venue_name, {})
        if existing_venue.get("last_success"):
            venue_status["last_success"] = existing_venue["last_success"]
            venue_status["last_success_count"] = existing_venue.get("last_success_count", 0)
        
        try:
            events = scraper()
            event_count = len(events)
            print(f"  Found {event_count} events")
            all_events.extend(events)
            
            venue_status["success"] = True
            venue_status["event_count"] = event_count
            venue_status["last_success"] = run_timestamp
            venue_status["last_success_count"] = event_count
            
        except Exception as e:
            error_msg = str(e)
            error_trace = traceback.format_exc()
            print(f"  ERROR: Failed to scrape {venue_name}: {error_msg}")
            
            venue_status["success"] = False
            venue_status["error"] = error_msg
            venue_status["error_trace"] = error_trace
        
        venue_statuses[venue_name] = venue_status
    
    # Normalize prices, generate slugs, and validate events
    print("\nProcessing events...")
    all_events = [normalize_price(e) for e in all_events]
    
    # Generate slugs for each event, ensuring uniqueness
    slug_counts = {}
    for event in all_events:
        base_slug = generate_slug(event)
        
        # Handle duplicate slugs by appending a counter
        if base_slug in slug_counts:
            slug_counts[base_slug] += 1
            event["slug"] = f"{base_slug}-{slug_counts[base_slug]}"
        else:
            slug_counts[base_slug] = 0
            event["slug"] = base_slug
    
    valid_events = [e for e in all_events if validate_event(e)]
    invalid_count = len(all_events) - len(valid_events)
    
    if invalid_count > 0:
        print(f"  Filtered out {invalid_count} invalid events")
    
    # Sort by date
    valid_events.sort(key=lambda x: x["date"])
    
    # Determine overall status
    all_success = all(v["success"] for v in venue_statuses.values())
    any_success = any(v["success"] for v in venue_statuses.values())
    
    print(f"\nTotal valid events: {len(valid_events)}")
    
    failed_venues = [name for name, status in venue_statuses.items() if not status["success"]]
    if failed_venues:
        print(f"Warning: Failed to scrape: {', '.join(failed_venues)}")

    # Save to frontend public directory
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(valid_events, f, indent=2)
    print(f"Events saved to {OUTPUT_PATH}")
    
    # Also save backup to root
    with open(BACKUP_PATH, "w") as f:
        json.dump(valid_events, f, indent=2)
    print(f"Backup saved to {BACKUP_PATH}")
    
    # Save scrape status
    status_data = {
        "last_run": run_timestamp,
        "all_success": all_success,
        "any_success": any_success,
        "total_events": len(valid_events),
        "venues": venue_statuses,
    }
    
    with open(STATUS_PATH, "w") as f:
        json.dump(status_data, f, indent=2)
    print(f"Status saved to {STATUS_PATH}")

if __name__ == "__main__":
    main()
