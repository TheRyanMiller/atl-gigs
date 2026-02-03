import json
import time
import requests
from pathlib import Path

from scraper import config
from scraper.utils.categories import map_tm_classification
from scraper.utils.dates import normalize_time
from scraper import spotify_enrichment

TM_VENUES = {
    "Center Stage": "KovZpa2gA5",
    "The Loft": "KovZpa2gA6",
    "Vinyl": "KovZpa2gA7",
    "State Farm Arena": "KovZpa2Pae",
    "The Masquerade - Heaven": "KovZpa2WHe",
    "The Masquerade - Hell": "KovZ917AOz0",
    "The Masquerade - Purgatory": "KovZ917AOzm",
    "The Masquerade - Altar": "KovZ917AmQG",
}

TM_CATEGORY_MAP = {
    "Music": "concerts",
    "Sports": "sports",
    "Arts & Theatre": "broadway",
    "Film": "misc",
    "Miscellaneous": "misc",
    "Comedy": "comedy",
    "Stand-Up": "comedy",
    "Theatre": "broadway",
    "Musical": "broadway",
    "Miscellaneous Theatre": "misc",
    "Basketball": "sports",
    "Wrestling": "sports",
    "Hockey": "sports",
    "Football": "sports",
}

_artist_classification_cache = {}


def load_artist_cache():
    """Load artist classification cache (download from R2 first if available)."""
    global _artist_classification_cache
    from scraper.pipeline.r2 import download_from_r2

    download_from_r2("artist-cache.json", config.ARTIST_CACHE_PATH)

    try:
        if config.ARTIST_CACHE_PATH.exists():
            with open(config.ARTIST_CACHE_PATH, "r") as f:
                _artist_classification_cache = json.load(f)
                print(f"  Loaded {len(_artist_classification_cache)} cached artist classifications")
    except Exception as e:
        print(f"  Warning: Could not load artist cache: {e}")
        _artist_classification_cache = {}


def save_artist_cache():
    """Save artist classification cache to disk."""
    try:
        config.ARTIST_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(config.ARTIST_CACHE_PATH, "w") as f:
            json.dump(_artist_classification_cache, f, indent=2)
    except Exception as e:
        print(f"  Warning: Could not save artist cache: {e}")


def get_artist_classification(artist_name):
    """
    Look up artist classification from Ticketmaster Attractions API.
    Results are cached to avoid repeated API calls.
    Returns category string or None if not found.
    """
    if not config.TM_API_KEY:
        return None

    cache_key = artist_name.lower().strip()
    if cache_key in _artist_classification_cache:
        return _artist_classification_cache[cache_key]

    try:
        params = {
            "keyword": artist_name,
            "countryCode": "US",
            "size": 1,
            "apikey": config.TM_API_KEY,
        }
        resp = requests.get(f"{config.TM_BASE_URL}/attractions.json", params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        attractions = data.get("_embedded", {}).get("attractions", [])
        if attractions:
            attraction = attractions[0]
            classifications = attraction.get("classifications", [])
            category = map_tm_classification(classifications, TM_CATEGORY_MAP)
            _artist_classification_cache[cache_key] = category

            external_links = attraction.get("externalLinks", {})
            spotify_links = external_links.get("spotify") if isinstance(external_links, dict) else None
            spotify_url = None
            if isinstance(spotify_links, list) and spotify_links:
                spotify_url = spotify_links[0].get("url")
            elif isinstance(spotify_links, dict):
                spotify_url = spotify_links.get("url")
            elif isinstance(spotify_links, str):
                spotify_url = spotify_links
            if spotify_url:
                spotify_enrichment.cache_spotify_result(artist_name, spotify_url, source="tm-attraction")

            time.sleep(0.2)
            return category

    except Exception as e:
        print(f"      TM artist lookup failed for '{artist_name}': {e}")

    _artist_classification_cache[cache_key] = None
    return None


def scrape_tm_venue(venue_id, venue_name, stage=None):
    """Scrape events from a Ticketmaster venue using Discovery API."""
    if not config.TM_API_KEY:
        print(f"    {venue_name}: Skipped (no TM_API_KEY)")
        return []

    params = {
        "venueId": venue_id,
        "countryCode": "US",
        "sort": "date,asc",
        "size": 200,
        "apikey": config.TM_API_KEY,
    }

    try:
        resp = requests.get(f"{config.TM_BASE_URL}/events.json", params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"    {venue_name}: ERROR - {e}")
        return []

    events = []
    for tm_event in data.get("_embedded", {}).get("events", []):
        start = tm_event.get("dates", {}).get("start", {})
        event_date = start.get("localDate")
        event_time = start.get("localTime")

        if not event_date:
            continue

        attractions = tm_event.get("_embedded", {}).get("attractions", [])
        artists = []
        for attr in attractions:
            artist = {"name": attr.get("name", "")}
            if attr.get("classifications"):
                genre = attr["classifications"][0].get("genre", {}).get("name")
                if genre:
                    artist["genre"] = genre

            external_links = attr.get("externalLinks", {})
            spotify_links = external_links.get("spotify") if isinstance(external_links, dict) else None
            spotify_url = None
            if isinstance(spotify_links, list) and spotify_links:
                spotify_url = spotify_links[0].get("url")
            elif isinstance(spotify_links, dict):
                spotify_url = spotify_links.get("url")
            elif isinstance(spotify_links, str):
                spotify_url = spotify_links
            spotify_url = spotify_enrichment.normalize_spotify_url(spotify_url) if spotify_url else None
            if spotify_url:
                artist["spotify_url"] = spotify_url
                spotify_enrichment.cache_spotify_result(artist.get("name", ""), spotify_url, source="tm-event")

            artists.append(artist)

        if not artists:
            artists = [{"name": tm_event.get("name", "Unknown")}]

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

        category = map_tm_classification(tm_event.get("classifications", []), TM_CATEGORY_MAP)

        image_url = None
        for img in tm_event.get("images", []):
            if img.get("ratio") == "16_9" and img.get("width", 0) >= 600:
                image_url = img.get("url")
                break
        if not image_url and tm_event.get("images"):
            image_url = tm_event["images"][0].get("url")

        event = {
            "venue": venue_name,
            "date": event_date,
            "doors_time": None,
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
    events = scrape_tm_venue(TM_VENUES["State Farm Arena"], "State Farm Arena")
    print(f"    State Farm Arena (TM): {len(events)} events")
    return events


def scrape_masquerade_tm():
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
    if not config.TM_API_KEY:
        return events

    tm_venue_names = {
        "Center Stage", "The Loft", "Vinyl",
        "State Farm Arena",
        "The Masquerade",
    }

    enriched_count = 0
    api_calls = 0
    cache_hits = 0

    def should_enrich(event):
        if event.get("venue") in tm_venue_names:
            return False
        artists = event.get("artists", [])
        if not artists or artists[0].get("genre"):
            return False
        if event.get("category") not in [None, "concerts", config.DEFAULT_CATEGORY]:
            return False
        return True

    artists_to_lookup = set()
    for event in events:
        if not should_enrich(event):
            continue
        headliner = event.get("artists", [{}])[0].get("name", "").lower().strip()
        if headliner and headliner not in _artist_classification_cache:
            artists_to_lookup.add(headliner)

    for artist_name in artists_to_lookup:
        get_artist_classification(artist_name)
        api_calls += 1

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
