import time
from datetime import datetime

import requests

from scraper.utils.dates import normalize_time
from scraper.utils.categories import detect_category_from_text

CENTER_STAGE_API = "https://www.centerstage-atlanta.com/wp-json/centerstage/v2/events/"
CENTER_STAGE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
}
CENTER_STAGE_TIMEOUT = (8, 20)

# Map venue_room.value to stage names
CENTER_STAGE_STAGES = {
    "center_stage": "Main",
    "the_loft": "The Loft",
    "vinyl": "Vinyl",
}


def transform_center_stage_event(event):
    """Transform one Center Stage API event, or return None if required data is missing."""
    if event.get("external_venue"):
        return None

    venue_room = event.get("venue_room") or {}
    venue_key = (venue_room.get("value") or "").lower()
    if venue_key not in CENTER_STAGE_STAGES:
        return None

    date_raw = event.get("event_date", "")
    if not date_raw or len(date_raw) != 8:
        return None

    try:
        event_date = datetime.strptime(date_raw, "%Y%m%d").strftime("%Y-%m-%d")
    except ValueError:
        return None

    title = (event.get("title") or "").strip()
    ticket_url = event.get("event_url")
    if not title or not ticket_url:
        return None

    return {
        "venue": "Center Stage",
        "date": event_date,
        "doors_time": normalize_time(event.get("door_time")),
        "show_time": normalize_time(event.get("show_time")),
        "artists": [{"name": title}],
        "ticket_url": ticket_url,
        "info_url": event.get("permalink"),
        "image_url": event.get("event_image"),
        "category": detect_category_from_text(title) or "concerts",
        "stage": CENTER_STAGE_STAGES[venue_key],
    }


def scrape_center_stage():
    """
    Scrape events from Center Stage, The Loft, and Vinyl.
    Uses their REST API at /wp-json/centerstage/v2/events/ which returns
    paginated JSON with 20 events per page.

    Note: Ticketmaster Discovery API is preferable when available.
    """
    events = []
    page = 1
    max_pages = 20  # Safety limit

    while page <= max_pages:
        url = f"{CENTER_STAGE_API}?page={page}"
        try:
            resp = requests.get(url, headers=CENTER_STAGE_HEADERS, timeout=CENTER_STAGE_TIMEOUT)
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
            transformed = transform_center_stage_event(event)
            if transformed:
                events.append(transformed)

        # If we got fewer than 20 events, we've hit the last page
        if len(data) < 20:
            break

        page += 1
        time.sleep(0.3)  # Rate limiting

    return events
