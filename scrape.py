#!/usr/bin/env python3
"""
Scrape concert events from multiple venues and save to JSON.
Currently supports:
- The Earl (badearl.com)
- Tabernacle (Live Nation)
- Terminal West (AEG)
- The Eastern (AEG)
- Variety Playhouse (AEG)
- Coca-Cola Roxy (Live Nation)
- Fox Theatre
- State Farm Arena
- Mercedes-Benz Stadium
- The Masquerade (Heaven, Hell, Purgatory, Altar)
"""

import requests, datetime as dt, re, itertools, json, time, os, traceback
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent
EVENTS_DIR = SCRIPT_DIR / "atl-gigs" / "public" / "events"
OUTPUT_PATH = EVENTS_DIR / "events.json"
ARCHIVE_PATH = EVENTS_DIR / "archive.json"
STATUS_PATH = EVENTS_DIR / "scrape-status.json"
LOG_PATH = EVENTS_DIR / "scrape-log.txt"

# Event categories
CATEGORIES = ["concerts", "comedy", "broadway", "sports", "misc"]
DEFAULT_CATEGORY = "concerts"

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


def detect_category_from_text(text):
    """
    Detect event category from text (title or URL path) using keyword analysis.
    Used to refine categorization for events from catch-all pages.
    Returns detected category or None if uncertain.

    Uses generic patterns rather than specific names for maintainability.
    Priority order: sports > comedy > concerts (most specific first)
    """
    text_lower = text.lower()

    # Sports indicators (most distinctive - check first)
    sports_patterns = [
        # Explicit sports terms
        "sports",
        "basketball", "hoops", "hoopsgiving", "nba",
        "football", "nfl", "gridiron",
        "soccer", "mls", "fifa",
        "hockey", "nhl",
        "baseball", "mlb",
        # Combat sports
        "wrestling", "wwe", "aew", "raw", "smackdown",
        "boxing", "ufc", "mma", "fight night",
        # Competition terms
        "championship", "tournament", "playoffs",
        "bowl",  # College football bowls
        "classic",  # Often used for college sports events
        "game day", "gameday", "matchday",
    ]

    # Check for "vs" pattern (Team A vs Team B) - strong sports indicator
    if " vs " in text_lower or " vs. " in text_lower or " versus " in text_lower:
        return "sports"

    if any(pattern in text_lower for pattern in sports_patterns):
        return "sports"

    # Comedy indicators
    comedy_patterns = [
        "comedy", "comedian", "comedians",
        "stand-up", "standup", "stand up",
        "comic", "comics",
        "laugh", "laughs",  # "night of laughs", etc.
        "funny",
        "improv",
    ]

    if any(pattern in text_lower for pattern in comedy_patterns):
        return "comedy"

    # Fallback: Known comedy acts whose names don't contain genre keywords
    # This is a last resort for popular acts that would otherwise be miscategorized
    # Keep this list minimal and only add acts that frequently appear at Atlanta venues
    known_comedy_acts = [
        "katt williams", "kevin hart", "dave chappelle", "chris rock",
        "steve harvey", "mike epps", "martin lawrence",
        "85 south", "dc young fly", "karlous miller", "chico bean",
        "theo von", "andrew schulz", "tom segura", "bert kreischer",
        "nate bargatze", "sebastian maniscalco", "jim gaffigan",
    ]

    if any(act in text_lower for act in known_comedy_acts):
        return "comedy"

    # Concert/music indicators (check last - most generic)
    concert_patterns = [
        "concert", "concerts",
        "tour",     # Most tours are music
        "jam",      # Winter Jam, Summer Jam (music festivals)
        "fest",     # Festivals
        "festival",
        "live music",
        "in concert",
    ]

    if any(pattern in text_lower for pattern in concert_patterns):
        return "concerts"

    return None  # Uncertain - keep original category


def detect_category_from_ticket_url(ticket_url):
    """
    Extract category hints from Ticketmaster URL paths.
    Some TM URLs contain descriptive event names: /cbs-sports-classic-2025/event/...
    Returns detected category or None if URL doesn't contain useful info.
    """
    if not ticket_url or "ticketmaster.com" not in ticket_url:
        return None

    # Extract path between ticketmaster.com/ and /event/
    # e.g., "cbs-sports-classic-2025-atlanta-georgia-12-20-2025" from
    # "https://www.ticketmaster.com/cbs-sports-classic-2025-atlanta-georgia-12-20-2025/event/..."
    if "/event/" in ticket_url:
        path = ticket_url.split("ticketmaster.com/")[-1].split("/event/")[0]
        if path and path != "event":
            return detect_category_from_text(path.replace("-", " "))

    return None


def load_existing_status():
    """Load existing status file to preserve historical data."""
    try:
        if STATUS_PATH.exists():
            with open(STATUS_PATH, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {"venues": {}}


def load_existing_archive():
    """Load existing archive to preserve historical events."""
    try:
        if ARCHIVE_PATH.exists():
            with open(ARCHIVE_PATH, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return []


def archive_past_events(events, existing_archive):
    """
    Separate events into upcoming and past.
    Past events are merged into archive.
    Returns (upcoming_events, updated_archive, newly_archived_count)
    """
    today = datetime.now().strftime("%Y-%m-%d")

    upcoming = []
    newly_archived = []

    for event in events:
        if event.get("date", "") < today:
            newly_archived.append(event)
        else:
            upcoming.append(event)

    # Merge newly archived events with existing archive (avoid duplicates by slug)
    existing_slugs = {e.get("slug") for e in existing_archive}
    for event in newly_archived:
        if event.get("slug") not in existing_slugs:
            existing_archive.append(event)

    # Sort archive by date (newest first)
    existing_archive.sort(key=lambda x: x.get("date", ""), reverse=True)

    return upcoming, existing_archive, len(newly_archived)


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
                "image_url": image_url,
                "category": DEFAULT_CATEGORY
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
            "price": price,
            "category": DEFAULT_CATEGORY
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

def scrape_variety_playhouse():
    """Scrape events from Variety Playhouse's JSON API."""
    return scrape_aeg_venue(
        "https://aegwebprod.blob.core.windows.net/json/events/214/events.json",
        "Variety Playhouse"
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

def get_category_from_genres(artists):
    """Determine event category from artist genres."""
    for artist in artists:
        genre = (artist.get("genre") or "").lower()
        if any(kw in genre for kw in ["comedy", "stand-up", "standup", "comedian"]):
            return "comedy"
        if any(kw in genre for kw in ["theatre", "theater", "broadway", "musical"]):
            return "broadway"
    return "concerts"  # Default for music venues

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
            "image_url": event["images"][0]["image_url"] if event["images"] else None,
            "category": get_category_from_genres(event.get("artists", []))
        }

    return [transform_event(e) for e in itertools.chain.from_iterable(pages())]

def scrape_tabernacle():
    """Scrape events from Tabernacle's GraphQL API."""
    return scrape_live_nation_venue("KovZpaFEZe", "Tabernacle")

def scrape_coca_cola_roxy():
    """Scrape events from Coca-Cola Roxy's GraphQL API."""
    return scrape_live_nation_venue("KovZ917ACc7", "Coca-Cola Roxy")

# ----------------------------------------------------------------------
# Fox Theatre scraper
# ----------------------------------------------------------------------

FOX_THEATRE_BASE = "https://www.foxtheatre.org"
FOX_THEATRE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Fox Theatre category pages and their mapping to our categories
# See scrapers/fox-theatre.md for detailed mapping decisions
FOX_CATEGORY_PAGES = {
    "/events/upcoming-events/broadway": "broadway",
    "/events/upcoming-events/comedy": "comedy",
    "/events/upcoming-events/holiday": "misc",      # Mixed: concerts + broadway, default to misc
    "/events/upcoming-events/family": "misc",       # Family shows
    "/events/upcoming-events/special-engagements": "misc",  # Dance, speakers, variety
}

def parse_fox_date_range(date_text):
    """
    Parse Fox Theatre date formats into start and end dates.
    Handles: "Dec 12-13, 2025", "Jan 27-Feb 1, 2026", "Nov 30, 2025"
    Returns: (start_date_str, end_date_str) in YYYY-MM-DD format
    """
    date_text = date_text.strip()

    # Single date: "Nov 30, 2025"
    single_match = re.match(r'^([A-Za-z]+)\s+(\d+),\s+(\d{4})$', date_text)
    if single_match:
        month_str, day, year = single_match.groups()
        try:
            date = datetime.strptime(f"{month_str} {day}, {year}", "%b %d, %Y")
            date_str = date.strftime("%Y-%m-%d")
            return date_str, date_str
        except ValueError:
            pass

    # Range within same month: "Dec 12-13, 2025"
    same_month = re.match(r'^([A-Za-z]+)\s+(\d+)-(\d+),\s+(\d{4})$', date_text)
    if same_month:
        month_str, start_day, end_day, year = same_month.groups()
        try:
            start = datetime.strptime(f"{month_str} {start_day}, {year}", "%b %d, %Y")
            end = datetime.strptime(f"{month_str} {end_day}, {year}", "%b %d, %Y")
            return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")
        except ValueError:
            pass

    # Range across months: "Jan 27-Feb 1, 2026"
    cross_month = re.match(r'^([A-Za-z]+)\s+(\d+)-([A-Za-z]+)\s+(\d+),\s+(\d{4})$', date_text)
    if cross_month:
        start_month, start_day, end_month, end_day, year = cross_month.groups()
        try:
            start = datetime.strptime(f"{start_month} {start_day}, {year}", "%b %d, %Y")
            end = datetime.strptime(f"{end_month} {end_day}, {year}", "%b %d, %Y")
            return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")
        except ValueError:
            pass

    return None, None

def scrape_fox_category_page(url, category):
    """Scrape events from a Fox Theatre category page."""
    resp = requests.get(url, headers=FOX_THEATRE_HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    events = []
    seen_urls = set()

    # Fox Theatre uses div.eventItem as the event container
    for card in soup.select("div.eventItem"):
        # Extract title from h3.title or link title attribute
        title_el = card.select_one("h3.title a, h3.title, .title a")
        if title_el:
            title = title_el.get_text(strip=True)
        else:
            # Fallback to link title attribute
            link = card.select_one("a[title*='More Info']")
            title = link.get("title", "").replace("More Info for ", "") if link else None

        if not title:
            continue

        # Get detail URL
        detail_link = card.select_one("h3.title a, a.more, a[href*='/events/detail/']")
        if not detail_link:
            continue
        detail_url = detail_link.get("href", "")
        if not detail_url.startswith("http"):
            detail_url = FOX_THEATRE_BASE + detail_url

        # Skip duplicates
        if detail_url in seen_urls:
            continue
        seen_urls.add(detail_url)

        # Extract date from div.date structure
        date_div = card.select_one("div.date")
        if date_div:
            # Get all date text - handles ranges like "Nov 30, 2025" or "Jan 27-Feb 1, 2026"
            month = date_div.select_one(".m-date__month")
            day = date_div.select_one(".m-date__day")
            year = date_div.select_one(".m-date__year")

            if month and day and year:
                # Check for range (second date)
                range_end = date_div.select_one(".m-date__rangeLast")
                if range_end:
                    end_month = range_end.select_one(".m-date__month")
                    end_day = range_end.select_one(".m-date__day")
                    end_year = range_end.select_one(".m-date__year") or year

                    start_text = f"{month.get_text(strip=True)} {day.get_text(strip=True)}{year.get_text(strip=True)}"
                    end_text = f"{end_month.get_text(strip=True) if end_month else month.get_text(strip=True)} {end_day.get_text(strip=True)}{end_year.get_text(strip=True)}"

                    date_text = f"{month.get_text(strip=True)} {day.get_text(strip=True)}-{end_month.get_text(strip=True) if end_month else ''}{end_day.get_text(strip=True)}{year.get_text(strip=True)}"
                else:
                    date_text = f"{month.get_text(strip=True)} {day.get_text(strip=True)}{year.get_text(strip=True)}"
            else:
                date_text = date_div.get_text(strip=True)
        else:
            # Fallback: search card text for date pattern
            card_text = card.get_text()
            date_match = re.search(r'([A-Z][a-z]{2}\s+\d+(?:-(?:[A-Z][a-z]{2}\s+)?\d+)?,\s*\d{4})', card_text)
            date_text = date_match.group(1) if date_match else None

        if not date_text:
            continue

        start_date, end_date = parse_fox_date_range(date_text)
        if not start_date:
            continue

        # Extract image from div.thumb img
        img = card.select_one("div.thumb img, .thumb img, img")
        image_url = None
        if img:
            image_url = img.get("src") or img.get("data-src")
            if image_url and not image_url.startswith("http"):
                image_url = FOX_THEATRE_BASE + image_url

        # Extract ticket URL (a.tickets)
        ticket_link = card.select_one("a.tickets, a[href*='evenue.net']")
        ticket_url = ticket_link.get("href").strip() if ticket_link else detail_url

        events.append({
            "title": title,
            "date": start_date,
            "end_date": end_date if end_date != start_date else None,
            "info_url": detail_url,
            "ticket_url": ticket_url,
            "image_url": image_url,
            "fox_category": category,
        })

    return events

def scrape_fox_theatre():
    """
    Scrape events from Fox Theatre by combining category pages.
    Events may appear in multiple categories - we dedupe by detail URL
    and prioritize category assignment: broadway > comedy > concerts > misc
    """
    # Category priority for deduplication (lower = higher priority)
    category_priority = {"broadway": 0, "comedy": 1, "concerts": 2, "sports": 3, "misc": 4}

    all_events = {}  # Keyed by detail_url for deduplication

    # Scrape each category page
    for path, category in FOX_CATEGORY_PAGES.items():
        url = FOX_THEATRE_BASE + path
        try:
            page_events = scrape_fox_category_page(url, category)
            print(f"    Fox Theatre {path}: {len(page_events)} events")

            for event in page_events:
                detail_url = event["info_url"]

                if detail_url in all_events:
                    # Event already exists - keep higher priority category
                    existing = all_events[detail_url]
                    existing_priority = category_priority.get(existing["fox_category"], 99)
                    new_priority = category_priority.get(category, 99)
                    if new_priority < existing_priority:
                        existing["fox_category"] = category
                else:
                    all_events[detail_url] = event

        except Exception as e:
            print(f"    Fox Theatre {path}: ERROR - {e}")

    # Also scrape the main events page for any uncategorized events (concerts)
    try:
        main_url = FOX_THEATRE_BASE + "/events"
        resp = requests.get(main_url, headers=FOX_THEATRE_HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        main_page_count = 0
        # Use same parsing logic as category pages
        for card in soup.select("div.eventItem"):
            title_el = card.select_one("h3.title a, h3.title, .title a")
            if title_el:
                title = title_el.get_text(strip=True)
            else:
                link = card.select_one("a[title*='More Info']")
                title = link.get("title", "").replace("More Info for ", "") if link else None

            if not title:
                continue

            detail_link = card.select_one("h3.title a, a.more, a[href*='/events/detail/']")
            if not detail_link:
                continue
            detail_url = detail_link.get("href", "")
            if not detail_url.startswith("http"):
                detail_url = FOX_THEATRE_BASE + detail_url

            # Skip if already have this event from category pages
            if detail_url in all_events:
                continue

            # Extract date
            date_div = card.select_one("div.date")
            if date_div:
                date_text = date_div.get_text(strip=True)
            else:
                card_text = card.get_text()
                date_match = re.search(r'([A-Z][a-z]{2}\s+\d+(?:-(?:[A-Z][a-z]{2}\s+)?\d+)?,\s*\d{4})', card_text)
                date_text = date_match.group(1) if date_match else None

            if not date_text:
                continue

            start_date, end_date = parse_fox_date_range(date_text)
            if not start_date:
                continue

            img = card.select_one("div.thumb img, .thumb img, img")
            image_url = None
            if img:
                image_url = img.get("src") or img.get("data-src")
                if image_url and not image_url.startswith("http"):
                    image_url = FOX_THEATRE_BASE + image_url

            ticket_link = card.select_one("a.tickets, a[href*='evenue.net']")
            ticket_url = ticket_link.get("href").strip() if ticket_link else detail_url

            # Events not in any category page are likely concerts
            all_events[detail_url] = {
                "title": title,
                "date": start_date,
                "end_date": end_date if end_date != start_date else None,
                "info_url": detail_url,
                "ticket_url": ticket_url,
                "image_url": image_url,
                "fox_category": "concerts",  # Default for main page events
            }
            main_page_count += 1

        print(f"    Fox Theatre main page: {main_page_count} additional events")
    except Exception as e:
        print(f"    Fox Theatre main page: ERROR - {e}")

    # Convert to our event format
    events = []
    for detail_url, event in all_events.items():
        events.append({
            "venue": "Fox Theatre",
            "date": event["date"],
            "doors_time": None,  # Fox Theatre doesn't show this on list pages
            "show_time": None,   # Would need to fetch detail page
            "artists": [{"name": event["title"]}],
            "ticket_url": event["ticket_url"],
            "info_url": event["info_url"],
            "image_url": event["image_url"],
            "category": event["fox_category"],
        })

    return events

# ----------------------------------------------------------------------
# State Farm Arena scraper
# ----------------------------------------------------------------------

STATE_FARM_ARENA_BASE = "https://www.statefarmarena.com"
STATE_FARM_ARENA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# State Farm Arena category pages and their mapping to our categories
# See scrapers/state-farm-arena.md for detailed mapping decisions
STATE_FARM_ARENA_CATEGORIES = {
    "/events/category/concerts": "concerts",
    "/events/category/family-shows": "misc",   # Family entertainment
    "/events/category/hawks": "sports",        # Atlanta Hawks basketball
    "/events/category/other": "misc",          # Catch-all
}

def scrape_state_farm_arena():
    """Scrape events from State Farm Arena using HTML parsing."""
    all_events = {}  # Keyed by detail URL for deduplication
    category_priority = {"concerts": 0, "comedy": 1, "broadway": 2, "sports": 3, "misc": 4}

    def parse_date(date_div):
        """Parse date from State Farm Arena date structure."""
        if not date_div:
            return None, None

        # Try single date first
        single = date_div.select_one(".m-date__singleDate")
        if single:
            month = single.select_one(".m-date__month")
            day = single.select_one(".m-date__day")
            year = single.select_one(".m-date__year")
            if month and day and year:
                try:
                    date_str = f"{month.get_text(strip=True)} {day.get_text(strip=True)}, {year.get_text(strip=True)}"
                    dt = datetime.strptime(date_str, "%b %d, %Y")
                    return dt.strftime("%Y-%m-%d"), dt.strftime("%Y-%m-%d")
                except ValueError:
                    pass

        # Try range (first date)
        range_first = date_div.select_one(".m-date__rangeFirst")
        range_last = date_div.select_one(".m-date__rangeLast")
        if range_first:
            month = range_first.select_one(".m-date__month")
            day = range_first.select_one(".m-date__day")
            year = range_first.select_one(".m-date__year") or date_div.select_one(".m-date__year")
            if month and day and year:
                try:
                    date_str = f"{month.get_text(strip=True)} {day.get_text(strip=True)}, {year.get_text(strip=True)}"
                    start_dt = datetime.strptime(date_str, "%b %d, %Y")
                    start_date = start_dt.strftime("%Y-%m-%d")

                    # Parse end date if available
                    end_date = start_date
                    if range_last:
                        end_month = range_last.select_one(".m-date__month") or month
                        end_day = range_last.select_one(".m-date__day")
                        end_year = range_last.select_one(".m-date__year") or year
                        if end_day:
                            try:
                                end_str = f"{end_month.get_text(strip=True)} {end_day.get_text(strip=True)}, {end_year.get_text(strip=True)}"
                                end_dt = datetime.strptime(end_str, "%b %d, %Y")
                                end_date = end_dt.strftime("%Y-%m-%d")
                            except ValueError:
                                pass
                    return start_date, end_date
                except ValueError:
                    pass

        return None, None

    def parse_time(meta_div):
        """Extract show time from meta section."""
        if not meta_div:
            return None
        time_el = meta_div.select_one(".time")
        if time_el:
            time_text = time_el.get_text(strip=True)
            # Extract time like "7:00 PM" from "Event Starts 7:00 PM"
            match = re.search(r'(\d{1,2}:\d{2})\s*(AM|PM)', time_text, re.IGNORECASE)
            if match:
                return normalize_time(f"{match.group(1)}{match.group(2)}")
        return None

    def scrape_page(url, category):
        """Scrape a single page and return events."""
        resp = requests.get(url, headers=STATE_FARM_ARENA_HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        events = []

        for card in soup.select(".eventItem"):
            # Get title
            title_el = card.select_one(".title a, .title")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not title:
                continue

            # Get detail URL
            detail_link = card.select_one("a.more, a[href*='/events/detail/']")
            if detail_link:
                detail_url = detail_link.get("href", "")
                if not detail_url.startswith("http"):
                    detail_url = STATE_FARM_ARENA_BASE + detail_url
            else:
                detail_url = None

            # Get ticket URL
            ticket_link = card.select_one("a.tickets, a[href*='ticketmaster']")
            ticket_url = ticket_link.get("href", "") if ticket_link else detail_url

            if not ticket_url:
                continue

            # Parse date
            date_div = card.select_one(".date")
            start_date, end_date = parse_date(date_div)
            if not start_date:
                continue

            # Parse time
            meta_div = card.select_one(".meta")
            show_time = parse_time(meta_div)

            # Get image
            img = card.select_one(".thumb img, img")
            image_url = None
            if img:
                image_url = img.get("src") or img.get("data-src")
                if image_url and not image_url.startswith("http"):
                    image_url = STATE_FARM_ARENA_BASE + image_url

            # For events from catch-all pages, try to detect category from title and ticket URL
            final_category = category
            if category == "misc":
                # Try title first, then ticket URL
                detected = detect_category_from_text(title) or detect_category_from_ticket_url(ticket_url)
                if detected:
                    final_category = detected

            events.append({
                "name": title,
                "date": start_date,
                "end_date": end_date if end_date != start_date else None,
                "show_time": show_time,
                "detail_url": detail_url,
                "ticket_url": ticket_url,
                "image_url": image_url,
                "category": final_category,
            })

        # Check for "Load More" link
        load_more = soup.select_one("a.loadMore, a[href*='/events/index/']")
        next_url = None
        if load_more:
            next_href = load_more.get("href", "")
            if next_href and not next_href.startswith("http"):
                next_url = STATE_FARM_ARENA_BASE + next_href

        return events, next_url

    # Scrape each category page with pagination
    for path, category in STATE_FARM_ARENA_CATEGORIES.items():
        try:
            url = STATE_FARM_ARENA_BASE + path
            page_count = 0
            pages_scraped = 0
            max_pages = 10  # Safety limit

            while url and pages_scraped < max_pages:
                page_events, next_url = scrape_page(url, category)
                pages_scraped += 1

                for event in page_events:
                    key = event["detail_url"] or event["ticket_url"]

                    # If event exists, keep higher priority category
                    if key in all_events:
                        existing = all_events[key]
                        existing_priority = category_priority.get(existing["category"], 99)
                        new_priority = category_priority.get(category, 99)
                        if new_priority < existing_priority:
                            all_events[key]["category"] = category
                    else:
                        all_events[key] = event
                        page_count += 1

                url = next_url
                if url:
                    time.sleep(0.3)  # Rate limiting

            print(f"    State Farm Arena {path}: {page_count} events ({pages_scraped} pages)")

        except Exception as e:
            print(f"    State Farm Arena {path}: ERROR - {e}")

    # Convert to our event format
    events = []
    for event in all_events.values():
        events.append({
            "venue": "State Farm Arena",
            "date": event["date"],
            "doors_time": None,
            "show_time": event["show_time"],
            "artists": [{"name": event["name"]}],
            "ticket_url": event["ticket_url"],
            "info_url": event["detail_url"],
            "image_url": event["image_url"],
            "category": event["category"],
        })

    print(f"    State Farm Arena total: {len(events)} events")
    return events

# ----------------------------------------------------------------------
# Mercedes-Benz Stadium scraper
# ----------------------------------------------------------------------

MERCEDES_BENZ_STADIUM_BASE = "https://www.mercedesbenzstadium.com"
MERCEDES_BENZ_STADIUM_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Mercedes-Benz Stadium category mapping
# See scrapers/mercedes-benz-stadium.md for detailed mapping decisions
MBS_CATEGORY_MAP = {
    "sports": "sports",      # Football, soccer, etc.
    "concert": "concerts",   # Music events
    "other": "misc",         # Catch-all
    "conference": "misc",    # Business events (skip or misc)
    "home depot backyard": "misc",  # Free backyard events
}

def scrape_mercedes_benz_stadium():
    """
    Scrape events from Mercedes-Benz Stadium using HTML parsing.
    The site uses Webflow CMS with Finsweet CMS Filter.
    """
    url = MERCEDES_BENZ_STADIUM_BASE + "/events"
    resp = requests.get(url, headers=MERCEDES_BENZ_STADIUM_HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    events = []
    seen_urls = set()

    # Main events are in div.events--item.w-dyn-item
    for card in soup.select("div.events--item.w-dyn-item"):
        # Get title from h3
        title_el = card.select_one("h3")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        if not title:
            continue

        # Get category from div.events_tags--item
        category_el = card.select_one("div.events_tags--item.w-dyn-item")
        raw_category = category_el.get_text(strip=True).lower() if category_el else "other"
        category = MBS_CATEGORY_MAP.get(raw_category, "misc")

        # Get date and time from div.events_feature_details_dt elements
        detail_items = card.select("div.events_feature_details_dt")
        date_str = detail_items[0].get_text(strip=True) if len(detail_items) > 0 else None
        time_str = detail_items[1].get_text(strip=True) if len(detail_items) > 1 else None

        # Parse date (format: "December 6, 2025" or "June 2026")
        event_date = None
        if date_str:
            # Try full date format
            for fmt in ["%B %d, %Y", "%B %Y"]:
                try:
                    dt_obj = datetime.strptime(date_str, fmt)
                    event_date = dt_obj.strftime("%Y-%m-%d")
                    break
                except ValueError:
                    continue

        if not event_date:
            # Skip events without parseable dates
            continue

        # Parse time (format: "4:00 PM" or "TBD" or "TBA")
        show_time = None
        if time_str and time_str.upper() not in ["TBD", "TBA"]:
            # Try to extract time like "7:00 PM" or "12:00 PM"
            time_match = re.search(r'(\d{1,2}:\d{2})\s*(AM|PM)', time_str, re.IGNORECASE)
            if time_match:
                show_time = normalize_time(f"{time_match.group(1)}{time_match.group(2)}")

        # Get detail URL from a.btn--3[href*='/events/']
        detail_link = card.select_one("a.btn--3[href*='/events/']")
        detail_url = None
        if detail_link:
            detail_url = detail_link.get("href", "")
            if detail_url and not detail_url.startswith("http"):
                detail_url = MERCEDES_BENZ_STADIUM_BASE + detail_url

        # Get ticket URL from a.btn--1
        ticket_link = card.select_one("a.btn--1")
        ticket_url = ticket_link.get("href", "") if ticket_link else None

        # If no ticket URL, use detail URL
        if not ticket_url:
            ticket_url = detail_url

        if not ticket_url:
            continue

        # Skip duplicates
        key = detail_url or ticket_url
        if key in seen_urls:
            continue
        seen_urls.add(key)

        # Get image URL from img.event_image
        img = card.select_one("img.event_image")
        image_url = None
        if img:
            image_url = img.get("src") or img.get("data-src")
            if image_url and not image_url.startswith("http"):
                image_url = MERCEDES_BENZ_STADIUM_BASE + image_url

        # For events from catch-all categories, try to detect category from title and ticket URL
        final_category = category
        if category == "misc":
            # Try title first, then ticket URL
            detected = detect_category_from_text(title) or detect_category_from_ticket_url(ticket_url)
            if detected:
                final_category = detected

        events.append({
            "venue": "Mercedes-Benz Stadium",
            "date": event_date,
            "doors_time": None,
            "show_time": show_time,
            "artists": [{"name": title}],
            "ticket_url": ticket_url,
            "info_url": detail_url,
            "image_url": image_url,
            "category": final_category,
        })

    print(f"    Mercedes-Benz Stadium: {len(events)} events")
    return events

# ----------------------------------------------------------------------
# The Masquerade scraper
# ----------------------------------------------------------------------

MASQUERADE_BASE = "https://www.masqueradeatlanta.com"
MASQUERADE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Masquerade rooms (events at other venues should be filtered out)
MASQUERADE_ROOMS = ["Heaven", "Hell", "Purgatory", "Altar"]

def scrape_masquerade():
    """
    Scrape events from The Masquerade using HTML parsing.
    Only includes events at Masquerade rooms (Heaven, Hell, Purgatory, Altar).
    """
    url = MASQUERADE_BASE + "/events/"
    resp = requests.get(url, headers=MASQUERADE_HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    events = []

    for article in soup.select("article.event"):
        # Check if this is at The Masquerade (not an external venue)
        venue_span = article.select_one(".js-listVenue")
        if not venue_span:
            continue

        venue_text = venue_span.get_text(strip=True)
        room = None
        for r in MASQUERADE_ROOMS:
            if r in venue_text:
                room = r
                break

        # Skip events not at Masquerade
        if not room:
            continue

        # Parse date from .eventStartDate content attribute or spans
        date_el = article.select_one(".eventStartDate")
        if not date_el:
            continue

        # Try content attribute first (has full datetime)
        date_content = date_el.get("content", "")
        event_date = None
        doors_time = None

        if date_content:
            # Format: "November 30, 2025 6:00 pm"
            try:
                dt_obj = datetime.strptime(date_content, "%B %d, %Y %I:%M %p")
                event_date = dt_obj.strftime("%Y-%m-%d")
                doors_time = dt_obj.strftime("%H:%M")
            except ValueError:
                pass

        # Fallback to spans if content attribute didn't work
        if not event_date:
            month_el = date_el.select_one(".eventStartDate__month")
            day_el = date_el.select_one(".eventStartDate__date")
            year_el = date_el.select_one(".eventStartDate__year")

            if month_el and day_el and year_el:
                try:
                    date_str = f"{month_el.get_text(strip=True)} {day_el.get_text(strip=True)}, {year_el.get_text(strip=True)}"
                    dt_obj = datetime.strptime(date_str, "%b %d, %Y")
                    event_date = dt_obj.strftime("%Y-%m-%d")
                except ValueError:
                    continue
            else:
                continue

        # Parse doors time from .time-show if not already extracted
        if not doors_time:
            time_el = article.select_one(".time-show")
            if time_el:
                time_text = time_el.get_text(strip=True)
                # Extract time from "Doors 7:00 pm / All Ages"
                time_match = re.search(r'(\d{1,2}:\d{2})\s*(am|pm)', time_text, re.IGNORECASE)
                if time_match:
                    doors_time = normalize_time(f"{time_match.group(1)}{time_match.group(2)}")

        # Get title (headliner)
        title_el = article.select_one(".eventHeader__title")
        if not title_el:
            continue
        headliner = title_el.get_text(strip=True)
        if not headliner:
            continue

        # Get supporting acts
        support_el = article.select_one(".eventHeader__support")
        support_text = support_el.get_text(strip=True) if support_el else ""

        # Build artists list
        artists = [{"name": headliner}]
        if support_text:
            # Split by common delimiters: ", ", " & ", " and "
            support_acts = re.split(r',\s*|\s+&\s+|\s+and\s+', support_text)
            for act in support_acts:
                act = act.strip()
                if act and act != headliner:
                    artists.append({"name": act})

        # Get ticket URL
        ticket_link = article.select_one("a.btn-purple, a[itemprop='url']")
        ticket_url = ticket_link.get("href", "") if ticket_link else None

        if not ticket_url:
            # Try detail page link as fallback
            detail_link = article.select_one("a.wrapperLink")
            ticket_url = detail_link.get("href", "") if detail_link else None

        if not ticket_url:
            continue

        # Get detail URL
        detail_link = article.select_one("a.wrapperLink, a[href*='/events/']")
        detail_url = detail_link.get("href", "") if detail_link else None
        if detail_url and not detail_url.startswith("http"):
            detail_url = MASQUERADE_BASE + detail_url

        # Get image URL from background-image style
        image_el = article.select_one(".event--featuredImage")
        image_url = None
        if image_el:
            style = image_el.get("style", "")
            img_match = re.search(r"url\(['\"]?([^'\"]+)['\"]?\)", style)
            if img_match:
                image_url = img_match.group(1)

        events.append({
            "venue": "The Masquerade",
            "date": event_date,
            "doors_time": doors_time,
            "show_time": None,  # Site only shows doors time
            "artists": artists,
            "ticket_url": ticket_url,
            "info_url": detail_url,
            "image_url": image_url,
            "category": "concerts",  # Default category for this venue
            "room": room,  # Heaven, Hell, Purgatory, or Altar
        })

    print(f"    The Masquerade: {len(events)} events")
    return events

# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------

# Registry of all scrapers for easy iteration
SCRAPERS = {
    "The Earl": scrape_earl,
    "Tabernacle": scrape_tabernacle,
    "Terminal West": scrape_terminal_west,
    "The Eastern": scrape_the_eastern,
    "Variety Playhouse": scrape_variety_playhouse,
    "Coca-Cola Roxy": scrape_coca_cola_roxy,
    "Fox Theatre": scrape_fox_theatre,
    "State Farm Arena": scrape_state_farm_arena,
    "Mercedes-Benz Stadium": scrape_mercedes_benz_stadium,
    "The Masquerade": scrape_masquerade,
}

def main():
    all_events = []
    run_timestamp = datetime.utcnow().isoformat() + "Z"
    log_lines = []  # Collect log entries

    def log(message, level="INFO"):
        """Log a message to both console and log buffer."""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        print(message)
        log_lines.append(log_entry)

    log(f"Starting scrape run at {run_timestamp}")

    # Load existing status to preserve last_success data
    existing_status = load_existing_status()
    venue_statuses = {}

    for venue_name, scraper in SCRAPERS.items():
        log(f"Scraping {venue_name}...")
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
            log(f"  Found {event_count} events")
            all_events.extend(events)

            venue_status["success"] = True
            venue_status["event_count"] = event_count
            venue_status["last_success"] = run_timestamp
            venue_status["last_success_count"] = event_count

        except Exception as e:
            error_msg = str(e)
            error_trace = traceback.format_exc()
            log(f"  ERROR: Failed to scrape {venue_name}: {error_msg}", "ERROR")
            log(f"  Traceback:\n{error_trace}", "ERROR")

            venue_status["success"] = False
            venue_status["error"] = error_msg
            venue_status["error_trace"] = error_trace

        venue_statuses[venue_name] = venue_status
    
    # Normalize prices, generate slugs, and validate events
    log("\nProcessing events...")
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
        log(f"  Filtered out {invalid_count} invalid events", "WARNING")

    # Sort by date
    valid_events.sort(key=lambda x: x["date"])

    # Load existing archive and separate past events
    log("\nArchiving past events...")
    existing_archive = load_existing_archive()
    valid_events, updated_archive, archived_count = archive_past_events(valid_events, existing_archive)
    if archived_count > 0:
        log(f"  Archived {archived_count} past events")
    log(f"  Archive total: {len(updated_archive)} events")

    # Determine overall status
    all_success = all(v["success"] for v in venue_statuses.values())
    any_success = any(v["success"] for v in venue_statuses.values())

    log(f"\nTotal valid events: {len(valid_events)}")

    failed_venues = [name for name, status in venue_statuses.items() if not status["success"]]
    if failed_venues:
        log(f"WARNING: Failed to scrape: {', '.join(failed_venues)}", "ERROR")

    # Ensure events directory exists
    EVENTS_DIR.mkdir(parents=True, exist_ok=True)

    # Save upcoming events
    with open(OUTPUT_PATH, "w") as f:
        json.dump(valid_events, f, indent=2)
    log(f"Events saved to {OUTPUT_PATH}")

    # Save archive
    with open(ARCHIVE_PATH, "w") as f:
        json.dump(updated_archive, f, indent=2)
    log(f"Archive saved to {ARCHIVE_PATH}")

    # Save scrape status
    status_data = {
        "last_run": run_timestamp,
        "all_success": all_success,
        "any_success": any_success,
        "total_events": len(valid_events),
        "archived_events": len(updated_archive),
        "venues": venue_statuses,
    }

    with open(STATUS_PATH, "w") as f:
        json.dump(status_data, f, indent=2)
    log(f"Status saved to {STATUS_PATH}")

    # Save log file (append to existing log, keep last 1000 lines)
    existing_log = []
    if LOG_PATH.exists():
        with open(LOG_PATH, "r") as f:
            existing_log = f.readlines()

    # Add separator and new log entries
    log_content = existing_log[-900:] + ["\n--- New Run ---\n"] + [line + "\n" for line in log_lines]

    with open(LOG_PATH, "w") as f:
        f.writelines(log_content)
    log(f"Log saved to {LOG_PATH}")

if __name__ == "__main__":
    main()
