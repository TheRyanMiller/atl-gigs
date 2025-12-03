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
- Center Stage / The Loft / Vinyl
"""

import requests, datetime as dt, re, itertools, json, time, os, traceback, random
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
from dataclasses import dataclass, field

# Load environment variables from .env file
load_dotenv()

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent
EVENTS_DIR = SCRIPT_DIR / "atl-gigs" / "public" / "events"
OUTPUT_PATH = EVENTS_DIR / "events.json"
ARCHIVE_PATH = EVENTS_DIR / "archive.json"
STATUS_PATH = EVENTS_DIR / "scrape-status.json"
LOG_PATH = EVENTS_DIR / "scrape-log.txt"
SEEN_CACHE_PATH = EVENTS_DIR / "seen-cache.json"
ARCHIVE_DIR = EVENTS_DIR / "archive"
ARCHIVE_INDEX_PATH = ARCHIVE_DIR / "index.json"

# first_seen configuration
NEW_EVENT_DAYS = 5  # Events are considered "new" for this many days

# Event categories
CATEGORIES = ["concerts", "comedy", "broadway", "sports", "misc"]
DEFAULT_CATEGORY = "concerts"

REQUIRED_FIELDS = ["venue", "date", "artists", "ticket_url"]

# ----------------------------------------------------------------------
# Logging and Metrics
# ----------------------------------------------------------------------

@dataclass
class VenueMetrics:
    """Track scraping metrics for each venue."""
    name: str
    event_count: int = 0
    new_events: int = 0
    errors: int = 0
    error_messages: list = field(default_factory=list)
    duration_ms: float = 0.0


def trim_log_by_time(log_path, retention_days=14):
    """
    Remove log entries older than retention_days.
    Returns list of lines to keep.
    """
    if not log_path.exists():
        return []

    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")

    kept_lines = []
    current_entry_recent = False

    with open(log_path, "r") as f:
        for line in f:
            # Check if this is a timestamped log entry
            match = re.match(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', line)
            if match:
                current_entry_recent = match.group(1) >= cutoff_str

            # Keep line if current entry is recent
            if current_entry_recent:
                kept_lines.append(line)

    return kept_lines


def load_seen_cache():
    """Load the seen events cache."""
    try:
        if SEEN_CACHE_PATH.exists():
            with open(SEEN_CACHE_PATH, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {"events": {}, "last_updated": None}


def save_seen_cache(cache):
    """Save the seen events cache."""
    cache["last_updated"] = datetime.utcnow().isoformat() + "Z"
    with open(SEEN_CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=2)


def update_first_seen(events, seen_cache):
    """
    Update events with first_seen field and update the seen cache.
    Returns (updated_events, new_event_count).
    """
    now = datetime.utcnow().isoformat() + "Z"
    new_count = 0

    for event in events:
        slug = event.get("slug")
        if not slug:
            continue

        if slug in seen_cache["events"]:
            event["first_seen"] = seen_cache["events"][slug]["first_seen"]
        else:
            event["first_seen"] = now
            seen_cache["events"][slug] = {"first_seen": now}
            new_count += 1

    return events, new_count


def prune_seen_cache(seen_cache, current_slugs, archive_slugs):
    """Remove cache entries for events no longer tracked."""
    all_known = current_slugs | archive_slugs
    seen_cache["events"] = {
        slug: data
        for slug, data in seen_cache["events"].items()
        if slug in all_known
    }
    return seen_cache


def get_archive_slugs():
    """Get all slugs from monthly archive files."""
    slugs = set()

    # Check new monthly archive directory
    if ARCHIVE_DIR.exists():
        for path in ARCHIVE_DIR.glob("archive-*.json"):
            try:
                with open(path, "r") as f:
                    for event in json.load(f):
                        if event.get("slug"):
                            slugs.add(event["slug"])
            except Exception:
                pass

    # Also check old archive.json for backwards compatibility during migration
    if ARCHIVE_PATH.exists():
        try:
            with open(ARCHIVE_PATH, "r") as f:
                for event in json.load(f):
                    if event.get("slug"):
                        slugs.add(event["slug"])
        except Exception:
            pass

    return slugs

# ----------------------------------------------------------------------
# Ticketmaster Discovery API Configuration
# ----------------------------------------------------------------------

TM_API_KEY = os.environ.get("TM_API_KEY")
TM_BASE_URL = "https://app.ticketmaster.com/discovery/v2"

# Live Nation GraphQL API key (used for Tabernacle, Coca-Cola Roxy)
# Can be overridden via environment variable
LIVE_NATION_API_KEY = os.environ.get("LIVE_NATION_API_KEY", "da2-jmvb5y2gjfcrrep3wzeumqwgaq")

# Venue IDs discovered from TM API
TM_VENUES = {
    # Center Stage Complex
    "Center Stage": "KovZpZAFF1tA",
    "The Loft": "KovZpa2qJe",
    "Vinyl": "KovZpZA1lJ7A",
    # State Farm Arena
    "State Farm Arena": "KovZpa2Xke",
    # The Masquerade (separate IDs per room)
    "The Masquerade - Heaven": "KovZpa2WHe",
    "The Masquerade - Hell": "KovZ917AOz0",
    "The Masquerade - Purgatory": "KovZ917AOzm",
    "The Masquerade - Altar": "KovZ917AmQG",
}

# Classification mapping: TM segment/genre -> our category
TM_CATEGORY_MAP = {
    # Segment-level (less specific)
    "Music": "concerts",
    "Sports": "sports",
    "Arts & Theatre": "broadway",
    "Film": "misc",
    "Miscellaneous": "misc",
    # Genre-level overrides (more specific - takes precedence)
    "Comedy": "comedy",
    "Stand-Up": "comedy",
    "Theatre": "broadway",
    "Musical": "broadway",
    "Miscellaneous Theatre": "misc",  # Catch-all for non-theatrical "Arts & Theatre"
    "Basketball": "sports",
    "Wrestling": "sports",
    "Hockey": "sports",
    "Football": "sports",
}

# Cache for artist classifications (avoid repeated API calls)
# This cache is persisted to disk to avoid redundant API calls between runs
_artist_classification_cache = {}
ARTIST_CACHE_PATH = Path(__file__).parent / "atl-gigs" / "public" / "events" / "artist-cache.json"

def load_artist_cache():
    """Load artist classification cache from disk."""
    global _artist_classification_cache
    try:
        if ARTIST_CACHE_PATH.exists():
            with open(ARTIST_CACHE_PATH, "r") as f:
                _artist_classification_cache = json.load(f)
                print(f"  Loaded {len(_artist_classification_cache)} cached artist classifications")
    except Exception as e:
        print(f"  Warning: Could not load artist cache: {e}")
        _artist_classification_cache = {}

def save_artist_cache():
    """Save artist classification cache to disk."""
    try:
        ARTIST_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(ARTIST_CACHE_PATH, "w") as f:
            json.dump(_artist_classification_cache, f, indent=2)
    except Exception as e:
        print(f"  Warning: Could not save artist cache: {e}")

# Feature flag to use TM API (can disable for fallback to HTML scrapers)
USE_TM_API = os.environ.get("USE_TM_API", "true").lower() == "true"

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
        "jessica kirson", "modi",  # Center Stage regulars
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


def load_monthly_archive(month):
    """Load events from a specific monthly archive file."""
    path = ARCHIVE_DIR / f"archive-{month}.json"
    if path.exists():
        with open(path, "r") as f:
            return json.load(f)
    return []


def save_monthly_archive(month, events):
    """Save events to a specific monthly archive file."""
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    path = ARCHIVE_DIR / f"archive-{month}.json"
    with open(path, "w") as f:
        json.dump(events, f, indent=2)


def save_archive_index(months_data):
    """
    Save the archive index with month counts.
    months_data: dict of month -> event count
    """
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    months = sorted(months_data.keys(), reverse=True)
    index = {
        "months": [{"month": m, "count": months_data[m]} for m in months],
        "total_events": sum(months_data.values()),
        "last_updated": datetime.utcnow().isoformat() + "Z"
    }

    with open(ARCHIVE_INDEX_PATH, "w") as f:
        json.dump(index, f, indent=2)


def migrate_archive_to_monthly():
    """
    One-time migration: convert existing archive.json to monthly files.
    Renames old file to archive.json.bak after migration.
    Returns True if migration was performed.
    """
    if not ARCHIVE_PATH.exists():
        return False

    # Check if already migrated (backup exists or archive dir has files)
    backup_path = EVENTS_DIR / "archive.json.bak"
    if backup_path.exists():
        return False

    try:
        with open(ARCHIVE_PATH, "r") as f:
            old_archive = json.load(f)
    except Exception:
        return False

    if not old_archive:
        return False

    # Organize events by month
    by_month = {}
    for event in old_archive:
        date = event.get("date", "")
        if len(date) >= 7:
            month = date[:7]  # YYYY-MM
            if month not in by_month:
                by_month[month] = []
            by_month[month].append(event)

    # Save monthly files
    for month, events in by_month.items():
        events.sort(key=lambda x: x.get("date", ""), reverse=True)
        save_monthly_archive(month, events)

    # Save index
    save_archive_index({m: len(e) for m, e in by_month.items()})

    # Rename old archive to backup
    ARCHIVE_PATH.rename(backup_path)

    return True


def archive_past_events(events):
    """
    Separate events into upcoming and past.
    Past events are saved to monthly archive files.
    Returns (upcoming_events, archive_summary, newly_archived_count)

    archive_summary: dict with months and counts for logging
    """
    today = datetime.now().strftime("%Y-%m-%d")

    upcoming = []
    newly_archived = []

    for event in events:
        if event.get("date", "") < today:
            newly_archived.append(event)
        else:
            upcoming.append(event)

    # Group newly archived by month
    by_month = {}
    for event in newly_archived:
        date = event.get("date", "")
        if len(date) >= 7:
            month = date[:7]
            if month not in by_month:
                by_month[month] = []
            by_month[month].append(event)

    # Update each monthly archive file
    months_updated = {}
    for month, new_events in by_month.items():
        existing = load_monthly_archive(month)
        existing_slugs = {e.get("slug") for e in existing}

        added = 0
        for event in new_events:
            if event.get("slug") not in existing_slugs:
                existing.append(event)
                added += 1

        if added > 0:
            existing.sort(key=lambda x: x.get("date", ""), reverse=True)
            save_monthly_archive(month, existing)

        months_updated[month] = len(existing)

    # Update index with all months (include existing ones not modified)
    if ARCHIVE_INDEX_PATH.exists():
        try:
            with open(ARCHIVE_INDEX_PATH, "r") as f:
                old_index = json.load(f)
                for item in old_index.get("months", []):
                    if item["month"] not in months_updated:
                        months_updated[item["month"]] = item["count"]
        except Exception:
            pass

    if months_updated:
        save_archive_index(months_updated)

    return upcoming, months_updated, len(newly_archived)


# ----------------------------------------------------------------------
# Ticketmaster API Functions
# ----------------------------------------------------------------------

def map_tm_classification(classifications):
    """
    Map Ticketmaster classification hierarchy to our category.
    Priority: genre > segment (more specific wins)
    """
    if not classifications:
        return "concerts"

    primary = classifications[0] if classifications else {}
    segment = primary.get("segment", {}).get("name", "")
    genre = primary.get("genre", {}).get("name", "")

    # Check genre first (most specific)
    if genre in TM_CATEGORY_MAP:
        return TM_CATEGORY_MAP[genre]

    # Check segment
    if segment in TM_CATEGORY_MAP:
        return TM_CATEGORY_MAP[segment]

    return "concerts"


def get_artist_classification(artist_name):
    """
    Look up artist classification from Ticketmaster Attractions API.
    Results are cached to avoid repeated API calls.
    Returns category string or None if not found.
    """
    if not TM_API_KEY:
        return None

    # Check cache first
    cache_key = artist_name.lower().strip()
    if cache_key in _artist_classification_cache:
        return _artist_classification_cache[cache_key]

    try:
        params = {
            "keyword": artist_name,
            "countryCode": "US",
            "size": 1,
            "apikey": TM_API_KEY,
        }
        resp = requests.get(f"{TM_BASE_URL}/attractions.json", params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        attractions = data.get("_embedded", {}).get("attractions", [])
        if attractions:
            classifications = attractions[0].get("classifications", [])
            category = map_tm_classification(classifications)
            _artist_classification_cache[cache_key] = category
            # Rate limiting - avoid hitting TM API too fast
            time.sleep(0.2)
            return category

    except Exception as e:
        print(f"      TM artist lookup failed for '{artist_name}': {e}")

    # Cache negative result to avoid retrying
    _artist_classification_cache[cache_key] = None
    return None


def scrape_tm_venue(venue_id, venue_name, stage=None):
    """
    Scrape events from a Ticketmaster venue using Discovery API.
    Returns list of events in our standard format.
    """
    if not TM_API_KEY:
        print(f"    {venue_name}: Skipped (no TM_API_KEY)")
        return []

    params = {
        "venueId": venue_id,
        "countryCode": "US",
        "sort": "date,asc",
        "size": 200,
        "apikey": TM_API_KEY,
    }

    try:
        resp = requests.get(f"{TM_BASE_URL}/events.json", params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"    {venue_name}: ERROR - {e}")
        return []

    events = []
    for tm_event in data.get("_embedded", {}).get("events", []):
        # Parse dates
        start = tm_event.get("dates", {}).get("start", {})
        event_date = start.get("localDate")
        event_time = start.get("localTime")

        if not event_date:
            continue

        # Get artists from attractions
        attractions = tm_event.get("_embedded", {}).get("attractions", [])
        artists = []
        for attr in attractions:
            artist = {"name": attr.get("name", "")}
            # Get genre from attraction classifications
            if attr.get("classifications"):
                genre = attr["classifications"][0].get("genre", {}).get("name")
                if genre:
                    artist["genre"] = genre
            artists.append(artist)

        # Fallback to event name if no attractions
        if not artists:
            artists = [{"name": tm_event.get("name", "Unknown")}]

        # Get price range
        price = None
        price_ranges = tm_event.get("priceRanges", [])
        if price_ranges:
            pr = price_ranges[0]
            min_p, max_p = pr.get("min"), pr.get("max")
            if min_p and max_p:
                if min_p == max_p:
                    price = f"${min_p:.0f}"
                else:
                    price = f"${min_p:.0f} - ${max_p:.0f}"

        # Get category from event classifications
        category = map_tm_classification(tm_event.get("classifications", []))

        # Get image (prefer 16:9 ratio)
        image_url = None
        for img in tm_event.get("images", []):
            if img.get("ratio") == "16_9" and img.get("width", 0) >= 600:
                image_url = img.get("url")
                break
        # Fallback to any image
        if not image_url and tm_event.get("images"):
            image_url = tm_event["images"][0].get("url")

        event = {
            "venue": venue_name,
            "date": event_date,
            "doors_time": None,  # TM doesn't provide
            "show_time": normalize_time(event_time) if event_time else None,
            "artists": artists,
            "ticket_url": tm_event.get("url"),
            "image_url": image_url,
            "price": price,
            "category": category,
        }

        if stage:
            event["stage"] = stage

        events.append(event)

    return events


def scrape_center_stage_tm():
    """Scrape Center Stage, The Loft, and Vinyl via Ticketmaster API."""
    all_events = []

    # Each stage maps to a TM venue ID
    stages = [
        ("Main", TM_VENUES["Center Stage"]),
        ("The Loft", TM_VENUES["The Loft"]),
        ("Vinyl", TM_VENUES["Vinyl"]),
    ]

    for stage_name, venue_id in stages:
        events = scrape_tm_venue(venue_id, "Center Stage", stage=stage_name)
        all_events.extend(events)

    print(f"    Center Stage complex (TM): {len(all_events)} events")
    return all_events


def scrape_state_farm_arena_tm():
    """Scrape State Farm Arena via Ticketmaster API."""
    events = scrape_tm_venue(TM_VENUES["State Farm Arena"], "State Farm Arena")
    print(f"    State Farm Arena (TM): {len(events)} events")
    return events


def scrape_masquerade_tm():
    """Scrape The Masquerade via Ticketmaster API (all stages)."""
    all_events = []

    stages = [
        ("Heaven", TM_VENUES["The Masquerade - Heaven"]),
        ("Hell", TM_VENUES["The Masquerade - Hell"]),
        ("Purgatory", TM_VENUES["The Masquerade - Purgatory"]),
        ("Altar", TM_VENUES["The Masquerade - Altar"]),
    ]

    for stage_name, venue_id in stages:
        events = scrape_tm_venue(venue_id, "The Masquerade", stage=stage_name)
        all_events.extend(events)

    print(f"    The Masquerade (TM): {len(all_events)} events")
    return all_events


def enrich_events_with_tm(events):
    """
    Enrich events from non-TM venues with artist classifications.
    Only processes events that don't already have genre data.
    Skips events from TM venues (they already have classification from TM Events API).
    Uses persistent cache to minimize API calls.
    """
    if not TM_API_KEY:
        return events

    # Venues that use TM API - don't enrich these, they already have accurate data
    tm_venue_names = {
        "Center Stage", "The Loft", "Vinyl",  # Center Stage complex
        "State Farm Arena",
        "The Masquerade",
    }

    enriched_count = 0
    api_calls = 0
    cache_hits = 0

    def should_enrich(event):
        """Check if event should be enriched with TM artist data."""
        # Skip TM venues - they already have classification from Events API
        if event.get("venue") in tm_venue_names:
            return False
        # Skip if already has genre data
        artists = event.get("artists", [])
        if not artists or artists[0].get("genre"):
            return False
        # Skip if category was already set to something other than default
        if event.get("category") not in [None, "concerts", DEFAULT_CATEGORY]:
            return False
        return True

    # Collect unique artists that need lookup
    artists_to_lookup = set()
    for event in events:
        if not should_enrich(event):
            continue
        headliner = event.get("artists", [{}])[0].get("name", "").lower().strip()
        if headliner and headliner not in _artist_classification_cache:
            artists_to_lookup.add(headliner)

    # Look up new artists (not in cache)
    for artist_name in artists_to_lookup:
        get_artist_classification(artist_name)
        api_calls += 1

    # Now apply classifications to events
    for event in events:
        if not should_enrich(event):
            continue

        headliner = event.get("artists", [{}])[0].get("name", "").lower().strip()
        if headliner in _artist_classification_cache:
            category = _artist_classification_cache[headliner]
            if headliner not in artists_to_lookup:
                cache_hits += 1
            if category and category != "concerts":
                event["category"] = category
                enriched_count += 1

    print(f"  API calls: {api_calls} | Cache hits: {cache_hits} | Total cached: {len(_artist_classification_cache)}")
    if enriched_count > 0:
        print(f"  Enriched {enriched_count} events with TM artist data")

    return events


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
            time.sleep(0.3)  # Rate limiting between pages

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
    try:
        resp = requests.get(url, headers=AEG_HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"    {venue_name}: ERROR - {e}")
        return []

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
    "x-api-key": LIVE_NATION_API_KEY,
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
    """Determine event category from headliner's genre (not openers)."""
    if not artists:
        return "concerts"

    # Only check headliner (first artist), not openers
    genre = (artists[0].get("genre") or "").lower()

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

# Headers for Fox Theatre AJAX API requests (mimics browser XHR)
# Updated Dec 2025: Chrome 131, Client Hints to avoid 406 bot detection
FOX_THEATRE_AJAX_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.foxtheatre.org/events",
    "Origin": "https://www.foxtheatre.org",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Sec-CH-UA": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    "Sec-CH-UA-Mobile": "?0",
    "Sec-CH-UA-Platform": '"Windows"',
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}

def parse_fox_date_range(date_text):
    """
    Parse Fox Theatre date formats into start and end dates.
    Handles: "Dec 12-13, 2025", "Jan 27-Feb 1, 2026", "Nov 30, 2025"
    Also handles variations with spaces: "Jan  6 - 11, 2026", "Feb 28 - Mar 15, 2026"
    Returns: (start_date_str, end_date_str) in YYYY-MM-DD format
    """
    # Normalize whitespace: collapse multiple spaces and handle " - " separator
    date_text = ' '.join(date_text.split())  # Collapse multiple spaces
    date_text = date_text.replace(' - ', '-').replace('- ', '-').replace(' -', '-')  # Normalize separator

    # Map full month names to abbreviations for strptime
    month_map = {
        'january': 'Jan', 'february': 'Feb', 'march': 'Mar', 'april': 'Apr',
        'may': 'May', 'june': 'Jun', 'july': 'Jul', 'august': 'Aug',
        'september': 'Sep', 'october': 'Oct', 'november': 'Nov', 'december': 'Dec'
    }
    for full, abbrev in month_map.items():
        date_text = re.sub(rf'\b{full}\b', abbrev, date_text, flags=re.IGNORECASE)

    # Single date: "Nov 30, 2025"
    single_match = re.match(r'^([A-Za-z]+)\s+(\d+),\s*(\d{4})$', date_text)
    if single_match:
        month_str, day, year = single_match.groups()
        try:
            date = datetime.strptime(f"{month_str} {day}, {year}", "%b %d, %Y")
            date_str = date.strftime("%Y-%m-%d")
            return date_str, date_str
        except ValueError:
            pass

    # Range within same month: "Dec 12-13, 2025"
    same_month = re.match(r'^([A-Za-z]+)\s+(\d+)-(\d+),\s*(\d{4})$', date_text)
    if same_month:
        month_str, start_day, end_day, year = same_month.groups()
        try:
            start = datetime.strptime(f"{month_str} {start_day}, {year}", "%b %d, %Y")
            end = datetime.strptime(f"{month_str} {end_day}, {year}", "%b %d, %Y")
            return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")
        except ValueError:
            pass

    # Range across months: "Jan 27-Feb 1, 2026"
    cross_month = re.match(r'^([A-Za-z]+)\s+(\d+)-([A-Za-z]+)\s+(\d+),\s*(\d{4})$', date_text)
    if cross_month:
        start_month, start_day, end_month, end_day, year = cross_month.groups()
        try:
            start = datetime.strptime(f"{start_month} {start_day}, {year}", "%b %d, %Y")
            end = datetime.strptime(f"{end_month} {end_day}, {year}", "%b %d, %Y")
            return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")
        except ValueError:
            pass

    return None, None


def init_fox_session(max_retries=3):
    """
    Initialize a session with Fox Theatre cookies.
    Retries cookie acquisition to handle transient failures.
    """
    session = requests.Session()
    session.headers.update(FOX_THEATRE_AJAX_HEADERS)

    for attempt in range(max_retries):
        try:
            resp = session.get(f"{FOX_THEATRE_BASE}/events", timeout=20)
            if resp.status_code == 200:
                # Successfully got the page, session should have cookies
                # Small delay after cookie acquisition to appear more human
                time.sleep(random.uniform(0.5, 1.5))
                return session
        except Exception:
            pass

        if attempt < max_retries - 1:
            time.sleep(random.uniform(2, 4))

    # Return session anyway - might work without cookies
    return session


def scrape_fox_ajax_all_events():
    """
    Scrape ALL Fox Theatre events using their AJAX pagination API.
    This endpoint returns HTML with the same structure as the main page,
    allowing us to get all events including those behind "Load More" pagination.
    Returns a list of events with fox_category set based on CSS classes.

    Includes retry logic with session refresh to handle ephemeral 406 errors.
    """
    events = []
    seen_urls = set()
    offset = 0
    per_page = 100  # Request many at once to minimize requests
    max_retries = 3  # Max retries per request

    # Initialize session with cookies
    session = init_fox_session()

    while True:
        ajax_url = f"{FOX_THEATRE_BASE}/events/events_ajax/{offset}?category=0&venue=0&team=0&exclude=&per_page={per_page}&came_from_page=event-list-page"

        # Retry loop with 406-specific recovery
        resp = None
        last_error = None
        for attempt in range(max_retries):
            try:
                resp = session.get(ajax_url, timeout=20)

                # Handle 406 specifically - refresh session and retry with longer delays
                if resp.status_code == 406:
                    if attempt < max_retries - 1:
                        # Longer, more human-like delays to avoid bot detection
                        wait = (3 ** attempt) * 2 + random.uniform(2, 5)
                        print(f"    Fox Theatre: 406 error, refreshing session (attempt {attempt + 1}/{max_retries})...")
                        time.sleep(wait)
                        session = init_fox_session()
                        continue
                    else:
                        raise requests.exceptions.HTTPError(f"406 Client Error after {max_retries} retries")

                resp.raise_for_status()
                break  # Success

            except requests.exceptions.RequestException as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait = (3 ** attempt) * 2 + random.uniform(2, 5)
                    time.sleep(wait)
                    # Refresh session on any error
                    session = init_fox_session()
                else:
                    raise

        if resp is None:
            raise last_error or Exception("Failed to fetch Fox Theatre events")

        # Response is JSON-encoded HTML string
        try:
            html = json.loads(resp.text)
        except json.JSONDecodeError:
            html = resp.text  # Fallback to raw text

        if not html.strip() or '<div class="eventItem' not in html:
            break  # No more events

        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("div.eventItem")

        if not cards:
            break

        for card in cards:
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

            if detail_url in seen_urls:
                continue
            seen_urls.add(detail_url)

            # Extract date
            date_div = card.select_one("div.date")
            if date_div:
                month = date_div.select_one(".m-date__month")
                day = date_div.select_one(".m-date__day")
                year = date_div.select_one(".m-date__year")

                if month and day and year:
                    range_end = date_div.select_one(".m-date__rangeLast")
                    if range_end:
                        end_month = range_end.select_one(".m-date__month")
                        end_day = range_end.select_one(".m-date__day")
                        date_text = f"{month.get_text(strip=True)} {day.get_text(strip=True)}-{end_month.get_text(strip=True) + ' ' if end_month else ''}{end_day.get_text(strip=True)}{year.get_text(strip=True)}"
                    else:
                        date_text = f"{month.get_text(strip=True)} {day.get_text(strip=True)}{year.get_text(strip=True)}"
                else:
                    date_text = date_div.get_text(strip=True)
            else:
                card_text = card.get_text()
                date_match = re.search(r'([A-Z][a-z]{2,}\s+\d+(?:-(?:[A-Z][a-z]{2,}\s+)?\d+)?,\s*\d{4})', card_text)
                date_text = date_match.group(1) if date_match else None

            if not date_text:
                continue

            start_date, end_date = parse_fox_date_range(date_text)
            if not start_date:
                continue

            # Extract image
            img = card.select_one("div.thumb img, .thumb img, img")
            image_url = None
            if img:
                image_url = img.get("src") or img.get("data-src")
                if image_url and not image_url.startswith("http"):
                    image_url = FOX_THEATRE_BASE + image_url

            # Extract ticket URL
            ticket_link = card.select_one("a.tickets, a[href*='evenue.net']")
            ticket_url = ticket_link.get("href").strip() if ticket_link else detail_url

            # Determine category from CSS classes on eventItem
            card_classes = card.get("class", [])
            if "broadway" in card_classes:
                fox_category = "broadway"
            elif "comedy" in card_classes:
                fox_category = "comedy"
            elif "concerts" in card_classes:
                fox_category = "concerts"
            else:
                fox_category = "misc"

            events.append({
                "title": title,
                "date": start_date,
                "end_date": end_date if end_date != start_date else None,
                "info_url": detail_url,
                "ticket_url": ticket_url,
                "image_url": image_url,
                "fox_category": fox_category,
            })

        # Check if we got fewer than requested - means we're done
        if len(cards) < per_page:
            break

        offset += len(cards)
        # Longer random delay to avoid rate limiting / bot detection
        time.sleep(random.uniform(2.0, 4.0))

    return events

def scrape_fox_theatre():
    """
    Scrape events from Fox Theatre using the AJAX API endpoint.
    This gets ALL events including those behind "Load More" pagination.
    Category is determined from CSS classes on event items (broadway, comedy, concerts).
    """
    # Use the AJAX endpoint to get ALL events
    ajax_events = scrape_fox_ajax_all_events()
    print(f"    Fox Theatre AJAX API: {len(ajax_events)} events")

    # Convert to our event format
    events = []
    for event in ajax_events:
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
    try:
        resp = requests.get(url, headers=MERCEDES_BENZ_STADIUM_HEADERS, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        print(f"    Mercedes-Benz Stadium: ERROR - {e}")
        return []

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

    # Parse team sections (Falcons and United "next home game")
    # Each config: (css_class, title_prefix, logo_pattern)
    team_configs = [
        ("falcons", "Atlanta Falcons vs. ", "falcons"),
        ("united", "Atlanta United vs. ", "AU_Primary"),
    ]

    for team_class, title_prefix, logo_pattern in team_configs:
        team_item = soup.select_one(f"div.events_game--item.{team_class}")
        if not team_item:
            continue

        # Extract team logo image
        team_logo = None
        for img in team_item.select("img"):
            src = img.get("src", "")
            if logo_pattern in src:
                team_logo = src
                break

        # Extract text content to parse (normalize non-breaking spaces)
        text_content = team_item.get_text(separator=" | ", strip=True).replace('\xa0', ' ')

        # Parse opponent from text (e.g., "Seattle Seahawks" or "vs. Real Salt Lake")
        # Format: "NEXT HOME GAME: | Seattle Seahawks | Sunday | Dec 7, 2025 | 1:00 pm"
        # or: "NEXT HOME MATCH: | Atlanta United vs. Real Salt Lake | Saturday | March 7, 2026 | 7:30 pm"
        parts = [p.strip().replace('\xa0', ' ') for p in text_content.split("|") if p.strip()]

        # Find opponent name (first part after NEXT HOME GAME/MATCH header)
        opponent = None
        for i, part in enumerate(parts):
            normalized = part.replace('\xa0', ' ').upper()
            if "NEXT" in normalized and "HOME" in normalized:
                if i + 1 < len(parts):
                    opponent = parts[i + 1]
                    # Clean up "Atlanta United vs. Real Salt Lake" to just "Real Salt Lake"
                    if "vs." in opponent:
                        opponent = opponent.split("vs.")[-1].strip()
                break

        if not opponent:
            continue

        # Find date (look for pattern like "Dec 7, 2025" or "March 7, 2026")
        team_date = None
        team_time = None
        for part in parts:
            # Try to parse as date
            for fmt in ["%B %d, %Y", "%b %d, %Y"]:
                try:
                    dt = datetime.strptime(part, fmt)
                    team_date = dt.strftime("%Y-%m-%d")
                    break
                except ValueError:
                    pass
            # Parse time (e.g., "1:00 pm")
            time_match = re.match(r'(\d{1,2}:\d{2})\s*(am|pm)', part, re.IGNORECASE)
            if time_match:
                team_time = normalize_time(f"{time_match.group(1)}{time_match.group(2)}")

        if not team_date:
            continue

        # Skip if already in events list (by date + title)
        title = f"{title_prefix}{opponent}"
        event_key = f"{team_date}-{title}"
        if any(e["date"] == team_date and title in e["artists"][0]["name"] for e in events):
            continue

        # Get ticket URL
        ticket_link = team_item.select_one("a[href*='ticketmaster'], a[href*='tickets']")
        team_ticket_url = ticket_link.get("href") if ticket_link else None

        events.append({
            "venue": "Mercedes-Benz Stadium",
            "date": team_date,
            "doors_time": None,
            "show_time": team_time,
            "artists": [{"name": title}],
            "ticket_url": team_ticket_url,
            "info_url": None,
            "image_url": team_logo,
            "category": "sports",
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

# Masquerade stages (events at other venues should be filtered out)
MASQUERADE_STAGES = ["Heaven", "Hell", "Purgatory", "Altar"]

def scrape_masquerade():
    """
    Scrape events from The Masquerade using HTML parsing.
    Only includes events at Masquerade stages (Heaven, Hell, Purgatory, Altar).
    """
    url = MASQUERADE_BASE + "/events/"
    try:
        resp = requests.get(url, headers=MASQUERADE_HEADERS, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        print(f"    The Masquerade: ERROR - {e}")
        return []

    events = []

    for article in soup.select("article.event"):
        # Check if this is at The Masquerade (not an external venue)
        venue_span = article.select_one(".js-listVenue")
        if not venue_span:
            continue

        venue_text = venue_span.get_text(strip=True)
        stage = None
        for s in MASQUERADE_STAGES:
            if s in venue_text:
                stage = s
                break

        # Skip events not at Masquerade
        if not stage:
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
            "stage": stage,  # Heaven, Hell, Purgatory, or Altar
        })

    print(f"    The Masquerade: {len(events)} events")
    return events

# ----------------------------------------------------------------------
# Center Stage scraper (includes The Loft and Vinyl)
# ----------------------------------------------------------------------

CENTER_STAGE_API = "https://www.centerstage-atlanta.com/wp-json/centerstage/v2/events/"
CENTER_STAGE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
}

# Map venue_room.value to stage names
CENTER_STAGE_STAGES = {
    "center_stage": "Main",
    "the_loft": "The Loft",
    "vinyl": "Vinyl",
}

def scrape_center_stage():
    """
    Scrape events from Center Stage, The Loft, and Vinyl.
    Uses their REST API at /wp-json/centerstage/v2/events/ which returns
    paginated JSON with 20 events per page.

    Note: Ticketmaster Discovery API would be preferable (has classifications
    for categories) but requires an API key. This REST API is a good fallback.
    """
    events = []
    page = 1
    max_pages = 20  # Safety limit

    while page <= max_pages:
        url = f"{CENTER_STAGE_API}?page={page}"
        try:
            resp = requests.get(url, headers=CENTER_STAGE_HEADERS, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"    Center Stage page {page}: ERROR - {e}")
            break

        # Empty response or error message means no more pages
        if not data or not isinstance(data, list):
            break

        # Check for "No Additional Shows" message (API returns this as string)
        if len(data) == 0:
            break

        for event in data:
            # Skip external venues
            external_venue = event.get("external_venue", "")
            if external_venue:
                continue

            # Get stage from venue_room
            venue_room = event.get("venue_room", {})
            venue_key = venue_room.get("value", "").lower()

            if venue_key not in CENTER_STAGE_STAGES:
                continue

            stage_name = CENTER_STAGE_STAGES[venue_key]

            # Parse date (format: YYYYMMDD)
            date_raw = event.get("event_date", "")
            if not date_raw or len(date_raw) != 8:
                continue

            try:
                event_date = datetime.strptime(date_raw, "%Y%m%d").strftime("%Y-%m-%d")
            except ValueError:
                continue

            # Get artist name
            title = event.get("title", "").strip()
            if not title:
                continue

            # Get ticket URL
            ticket_url = event.get("event_url", "")
            if not ticket_url:
                continue

            # Parse times (format: "7:00 pm")
            doors_time = normalize_time(event.get("door_time"))
            show_time = normalize_time(event.get("show_time"))

            # Get image URL
            image_url = event.get("event_image")

            # Get info URL (event detail page)
            info_url = event.get("permalink")

            # Detect category from title (venue hosts music and comedy)
            category = detect_category_from_text(title) or "concerts"

            events.append({
                "venue": "Center Stage",
                "date": event_date,
                "doors_time": doors_time,
                "show_time": show_time,
                "artists": [{"name": title}],
                "ticket_url": ticket_url,
                "info_url": info_url,
                "image_url": image_url,
                "category": category,
                "stage": stage_name,
            })

        # If we got fewer than 20 events, we've hit the last page
        if len(data) < 20:
            break

        page += 1
        time.sleep(0.3)  # Rate limiting

    print(f"    Center Stage venues: {len(events)} events")
    return events

# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------

# Registry of all scrapers for easy iteration
# When TM API is available, use it for venues that use Ticketmaster ticketing
# This provides better categorization via TM classifications
def get_scrapers():
    """Build scraper registry, using TM API when available."""
    scrapers = {
        "The Earl": scrape_earl,
        "Tabernacle": scrape_tabernacle,
        "Terminal West": scrape_terminal_west,
        "The Eastern": scrape_the_eastern,
        "Variety Playhouse": scrape_variety_playhouse,
        "Coca-Cola Roxy": scrape_coca_cola_roxy,
        "Fox Theatre": scrape_fox_theatre,
        "Mercedes-Benz Stadium": scrape_mercedes_benz_stadium,
    }

    # Use TM API for venues that use Ticketmaster, if API key is available
    if USE_TM_API and TM_API_KEY:
        scrapers["State Farm Arena"] = scrape_state_farm_arena_tm
        scrapers["The Masquerade"] = scrape_masquerade_tm
        scrapers["Center Stage"] = scrape_center_stage_tm
    else:
        scrapers["State Farm Arena"] = scrape_state_farm_arena
        scrapers["The Masquerade"] = scrape_masquerade
        scrapers["Center Stage"] = scrape_center_stage

    return scrapers

SCRAPERS = get_scrapers()

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
    venue_metrics = {}  # Track metrics for summary table

    for venue_name, scraper in SCRAPERS.items():
        log(f"Scraping {venue_name}...")
        metrics = VenueMetrics(name=venue_name)
        start_time = time.time()

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
            metrics.event_count = event_count
            metrics.duration_ms = (time.time() - start_time) * 1000
            log(f"  Found {event_count} events")
            all_events.extend(events)

            venue_status["success"] = True
            venue_status["event_count"] = event_count
            venue_status["last_success"] = run_timestamp
            venue_status["last_success_count"] = event_count

        except Exception as e:
            error_msg = str(e)
            error_trace = traceback.format_exc()
            metrics.errors = 1
            metrics.error_messages.append(error_msg)
            metrics.duration_ms = (time.time() - start_time) * 1000
            log(f"  ERROR: Failed to scrape {venue_name}: {error_msg}", "ERROR")
            log(f"  Traceback:\n{error_trace}", "ERROR")

            venue_status["success"] = False
            venue_status["error"] = error_msg
            venue_status["error_trace"] = error_trace

        venue_statuses[venue_name] = venue_status
        venue_metrics[venue_name] = metrics

    # Enrich events with TM artist classifications (for non-TM venues)
    if TM_API_KEY:
        log("\nEnriching events with Ticketmaster artist data...")
        load_artist_cache()
        all_events = enrich_events_with_tm(all_events)
        save_artist_cache()

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

    # Update first_seen field for tracking new events
    seen_cache = load_seen_cache()
    valid_events, new_event_count = update_first_seen(valid_events, seen_cache)
    log(f"  {new_event_count} newly discovered events")

    # Sort by date
    valid_events.sort(key=lambda x: x["date"])

    # Migrate old archive.json to monthly files if needed
    log("\nArchiving past events...")
    if migrate_archive_to_monthly():
        log("  Migrated archive.json to monthly files")

    # Separate past events into monthly archive files
    valid_events, archive_summary, archived_count = archive_past_events(valid_events)
    if archived_count > 0:
        log(f"  Archived {archived_count} past events")
    if archive_summary:
        total_archived = sum(archive_summary.values())
        log(f"  Archive total: {total_archived} events across {len(archive_summary)} months")

    # Determine overall status
    all_success = all(v["success"] for v in venue_statuses.values())
    any_success = any(v["success"] for v in venue_statuses.values())

    # Log summary table
    log("")
    log("=" * 60)
    log("VENUE SUMMARY")
    log("=" * 60)
    log(f"{'Venue':<24} {'Events':>7} {'Errors':>7} {'Time':>10}")
    log("-" * 60)
    for name in sorted(venue_metrics.keys()):
        m = venue_metrics[name]
        time_str = f"{m.duration_ms:.0f}ms"
        log(f"{name:<24} {m.event_count:>7} {m.errors:>7} {time_str:>10}")
    log("-" * 60)
    total_events = sum(m.event_count for m in venue_metrics.values())
    total_errors = sum(m.errors for m in venue_metrics.values())
    total_time = sum(m.duration_ms for m in venue_metrics.values())
    log(f"{'TOTAL':<24} {total_events:>7} {total_errors:>7} {total_time:.0f}ms")
    log("=" * 60)

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

    # Archive is now saved to monthly files by archive_past_events()
    # No need to save single archive.json

    # Prune and save seen cache
    current_slugs = {e.get("slug") for e in valid_events if e.get("slug")}
    archive_slugs = get_archive_slugs()
    seen_cache = prune_seen_cache(seen_cache, current_slugs, archive_slugs)
    save_seen_cache(seen_cache)
    log(f"Seen cache saved ({len(seen_cache['events'])} events tracked)")

    # Save scrape status
    total_archived = sum(archive_summary.values()) if archive_summary else 0
    status_data = {
        "last_run": run_timestamp,
        "all_success": all_success,
        "any_success": any_success,
        "total_events": len(valid_events),
        "archived_events": total_archived,
        "venues": venue_statuses,
    }

    with open(STATUS_PATH, "w") as f:
        json.dump(status_data, f, indent=2)
    log(f"Status saved to {STATUS_PATH}")

    # Save log file (time-based retention: 14 days)
    existing_log = trim_log_by_time(LOG_PATH, retention_days=14)

    # Add separator and new log entries
    log_content = existing_log + ["\n--- New Run ---\n"] + [line + "\n" for line in log_lines]

    with open(LOG_PATH, "w") as f:
        f.writelines(log_content)
    log(f"Log saved to {LOG_PATH}")

if __name__ == "__main__":
    main()
