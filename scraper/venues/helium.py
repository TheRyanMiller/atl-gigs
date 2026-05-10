import json
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

from scraper.utils.descriptions import clean_description

HELIUM_EVENTS_URL = "https://atlanta.heliumcomedy.com/events"
HELIUM_BASE_URL = "https://atlanta.heliumcomedy.com"
HELIUM_TIMEOUT = (8, 20)
HELIUM_TIMEZONE = ZoneInfo("America/New_York")
HELIUM_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
HELIUM_TITLE_PREFIXES = (
    "Special Event:",
    "Helium Presents:",
    "In The Other Room:",
)
HELIUM_SKIP_TITLE_MARKERS = ("POSTPONED", "CANCELED", "CANCELLED")
HELIUM_DESCRIPTION_STOP_MARKERS = (
    "Couple's Package includes",
    "Package includes",
    "There is a two-item",
    "There is a 2-item",
    "PLEASE NOTE:",
    "Management reserves",
)


def scrape_helium_comedy():
    """Scrape per-show comedy events from Helium's SeatEngine page JSON-LD."""
    resp = requests.get(HELIUM_EVENTS_URL, headers=HELIUM_HEADERS, timeout=HELIUM_TIMEOUT)
    resp.raise_for_status()

    events = []
    seen_urls = set()
    for raw_event in _extract_jsonld_events(resp.text):
        event = _transform_helium_event(raw_event)
        if not event or event["ticket_url"] in seen_urls:
            continue
        seen_urls.add(event["ticket_url"])
        events.append(event)

    return events


def _extract_jsonld_events(html):
    soup = BeautifulSoup(html, "html.parser")
    events = []

    for script in soup.select('script[type="application/ld+json"]'):
        raw = script.string or script.get_text()
        if not raw:
            continue

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue

        for item in _as_list(data):
            if not isinstance(item, dict):
                continue
            events.extend(_as_list(item.get("Events") or item.get("events")))

    return events


def _transform_helium_event(raw_event):
    raw_title = (raw_event.get("name") or "").strip()
    if not raw_title or any(marker in raw_title.upper() for marker in HELIUM_SKIP_TITLE_MARKERS):
        return None

    start = _parse_helium_start(raw_event.get("startDate"))
    raw_url = raw_event.get("url")
    artist_name = _clean_helium_title(raw_title)

    if not start or not raw_url or not artist_name:
        return None

    ticket_url = urljoin(HELIUM_BASE_URL, raw_url)
    event = {
        "venue": "Helium Comedy Club",
        "date": start.strftime("%Y-%m-%d"),
        "doors_time": None,
        "show_time": start.strftime("%H:%M"),
        "artists": [{"name": artist_name}],
        "ticket_url": ticket_url,
        "info_url": ticket_url,
        "image_url": raw_event.get("image"),
        "price": _extract_offer_price(raw_event.get("offers")),
        "category": "comedy",
    }

    description = _clean_helium_description(raw_event.get("description"))
    if description:
        event["description"] = description

    return event


def _parse_helium_start(value):
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

    return parsed.astimezone(HELIUM_TIMEZONE)


def _clean_helium_title(title):
    title = " ".join((title or "").split())
    for prefix in HELIUM_TITLE_PREFIXES:
        if title.lower().startswith(prefix.lower()):
            return title[len(prefix):].strip()
    return title


def _clean_helium_description(value):
    description = clean_description(value)
    if not description:
        return None

    lowered = description.lower()
    end = len(description)
    for marker in HELIUM_DESCRIPTION_STOP_MARKERS:
        index = lowered.find(marker.lower())
        if index != -1:
            end = min(end, index)

    description = description[:end].strip()
    description = re.sub(
        r"^([^\n]+)\n\n(?=(?:is|are|was|were|has|have|will|can)\b)",
        r"\1 ",
        description,
        flags=re.IGNORECASE,
    )
    return description or None


def _extract_offer_price(offers):
    if not offers:
        return None

    offers = _as_list(offers)
    offer = offers[0] if offers else None
    if not isinstance(offer, dict):
        return None

    price = offer.get("price") or offer.get("lowPrice")
    if not price:
        return None

    try:
        amount = Decimal(str(price).replace("$", "").replace(",", ""))
    except (InvalidOperation, AttributeError):
        return str(price).strip()

    if amount == amount.to_integral():
        return f"${amount:.0f}"
    return f"${amount:.2f}"


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]
