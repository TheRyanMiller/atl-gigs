from datetime import datetime

import requests

from scraper import config
from scraper.utils.dates import normalize_time

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
        event_dt_str = event.get("eventDateTime", "")
        if not event_dt_str or "TBD" in event_dt_str:
            continue

        event_date = datetime.fromisoformat(event_dt_str.replace("Z", "+00:00"))

        artists = []
        if event.get("title", {}).get("headlinersText"):
            artists.append({"name": event["title"]["headlinersText"]})
        if event.get("title", {}).get("supportingText"):
            artists.append({"name": event["title"]["supportingText"]})

        price_low = event.get("ticketPriceLow", "$0.00")
        price_high = event.get("ticketPriceHigh", "$0.00")
        price = f"{price_low} - {price_high}" if price_low != price_high else price_low

        doors_time = None
        if event.get("doorDateTime"):
            doors_time = event["doorDateTime"].split("T")[1][:5]
        show_time = event["eventDateTime"].split("T")[1][:5]

        image_url = None
        media = event.get("media")
        if isinstance(media, dict) and media:
            image_url = next((img["file_name"] for img in media.values() if img.get("width") == 678), None)

        events.append({
            "venue": venue_name,
            "date": event_date.strftime("%Y-%m-%d"),
            "doors_time": normalize_time(doors_time),
            "show_time": normalize_time(show_time),
            "artists": artists,
            "ticket_url": event.get("ticketing", {}).get("url"),
            "image_url": image_url,
            "price": price,
            "category": config.DEFAULT_CATEGORY,
        })

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
