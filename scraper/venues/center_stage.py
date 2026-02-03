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

    Note: Ticketmaster Discovery API is preferable when available.
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

    return events
