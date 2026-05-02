from datetime import datetime

import requests

from scraper import config
from scraper.utils.dates import normalize_time
from scraper.utils.descriptions import clean_description

AEG_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64)",
    "Accept": "application/json",
}
AEG_TIMEOUT = (8, 20)


def _parse_aeg_datetime(value):
    if not value or "TBD" in value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _extract_aeg_artists(title_data):
    if not isinstance(title_data, dict):
        return []

    artists = []
    headliner = title_data.get("headlinersText") or title_data.get("eventTitleText")
    support = title_data.get("supportingText")

    if headliner:
        artists.append({"name": headliner})
    if support and support != headliner:
        artists.append({"name": support})

    return artists


def _extract_aeg_image(media):
    if isinstance(media, dict):
        media_items = list(media.values())
    elif isinstance(media, list):
        media_items = media
    else:
        return None

    preferred = next(
        (img for img in media_items if isinstance(img, dict) and img.get("width") == 678 and img.get("file_name")),
        None,
    )
    fallback = next((img for img in media_items if isinstance(img, dict) and img.get("file_name")), None)
    image = preferred or fallback
    return image.get("file_name") if image else None


def _format_aeg_price(event):
    price_low = event.get("ticketPriceLow")
    price_high = event.get("ticketPriceHigh")
    if price_low and price_high:
        return f"{price_low} - {price_high}" if price_low != price_high else price_low
    return price_low or price_high


def transform_aeg_event(event, venue_name):
    event_date = _parse_aeg_datetime(event.get("eventDateTime"))
    if not event_date:
        return None

    artists = _extract_aeg_artists(event.get("title"))
    if not artists:
        return None

    ticket_url = event.get("ticketing", {}).get("url")
    if not ticket_url:
        return None

    doors_time = None
    door_date = _parse_aeg_datetime(event.get("doorDateTime"))
    if door_date:
        doors_time = door_date.strftime("%H:%M")

    transformed = {
        "venue": venue_name,
        "date": event_date.strftime("%Y-%m-%d"),
        "doors_time": normalize_time(doors_time),
        "show_time": normalize_time(event_date.strftime("%H:%M")),
        "artists": artists,
        "ticket_url": ticket_url,
        "image_url": _extract_aeg_image(event.get("media")),
        "price": _format_aeg_price(event),
        "category": config.DEFAULT_CATEGORY,
    }

    description = clean_description(event.get("bio") or event.get("description"), heading=artists[0]["name"])
    if description:
        transformed["description"] = description

    return transformed


def scrape_aeg_venue(url, venue_name):
    """Scrape events from an AEG venue's JSON API."""
    try:
        resp = requests.get(url, headers=AEG_HEADERS, timeout=AEG_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"    {venue_name}: ERROR - {e}")
        return []

    events = []
    for event in data.get("events", []):
        transformed = transform_aeg_event(event, venue_name)
        if transformed:
            events.append(transformed)

    return events


def scrape_terminal_west():
    return scrape_aeg_venue(
        "https://aegwebprod.blob.core.windows.net/json/events/211/events.json",
        "Terminal West",
    )


def scrape_the_eastern():
    return scrape_aeg_venue(
        "https://aegwebprod.blob.core.windows.net/json/events/127/events.json",
        "The Eastern",
    )


def scrape_variety_playhouse():
    return scrape_aeg_venue(
        "https://aegwebprod.blob.core.windows.net/json/events/214/events.json",
        "Variety Playhouse",
    )
