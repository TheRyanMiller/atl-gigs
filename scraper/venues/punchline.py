import re
import xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation
from urllib.parse import quote

import requests

from scraper.utils.dates import normalize_time
from scraper.utils.descriptions import clean_description

PUNCHLINE_API_URL = "https://webservice.punchline.com/"
PUNCHLINE_BASE_URL = "https://www.punchline.com"
PUNCHLINE_TOKEN = "xJ9nDflAoe93x"
PUNCHLINE_TIMEOUT = (8, 20)
PUNCHLINE_PAGE_SIZE = 50
PUNCHLINE_MAX_PAGES = 25
PUNCHLINE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64)",
    "Accept": "application/xml,text/xml,*/*;q=0.8",
}
XML_ILLEGAL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def scrape_punchline():
    """Scrape comedy shows from The Punchline's XML webservice."""
    events = []

    for event_el in _iter_punchline_event_nodes():
        event_id = _text(event_el, "eventid")
        if not event_id:
            continue

        shows_root = _post_punchline("show", variable1=event_id)
        if shows_root is None:
            continue

        for show_el in shows_root.findall(".//show"):
            event = _transform_punchline_show(event_el, show_el)
            if event:
                events.append(event)

    return events


def _iter_punchline_event_nodes():
    seen_ids = set()
    offset = 0

    for _ in range(PUNCHLINE_MAX_PAGES):
        root = _post_punchline(
            "event",
            variable1=0,
            variable2=PUNCHLINE_PAGE_SIZE,
            variable3=offset,
        )
        event_nodes = root.findall(".//event") if root is not None else []
        if not event_nodes:
            break

        last_event_id = _text(event_nodes[0], "lasteventid")
        new_this_page = 0

        for event_el in event_nodes:
            event_id = _text(event_el, "eventid")
            if not event_id or event_id in seen_ids:
                continue
            seen_ids.add(event_id)
            new_this_page += 1
            yield event_el

        if (
            not new_this_page
            or len(event_nodes) < PUNCHLINE_PAGE_SIZE
            or (last_event_id and last_event_id in seen_ids)
        ):
            break

        offset += PUNCHLINE_PAGE_SIZE


def _post_punchline(entity, **variables):
    payload = {"token": PUNCHLINE_TOKEN, "entity": entity}
    payload.update({key: value for key, value in variables.items() if value is not None})

    resp = requests.post(
        PUNCHLINE_API_URL,
        data=payload,
        headers=PUNCHLINE_HEADERS,
        timeout=PUNCHLINE_TIMEOUT,
    )
    resp.raise_for_status()

    if not resp.content.strip():
        return None

    text = resp.content.decode("utf-8", errors="replace")
    text = XML_ILLEGAL_CHAR_RE.sub("", text)
    return ET.fromstring(text)


def _transform_punchline_show(event_el, show_el):
    event_id = _text(event_el, "eventid")
    show_id = _text(show_el, "showtimeid")
    date = _text(show_el, "showdate")
    artist_name = _text(event_el, "comicname")

    if not event_id or not show_id or not date or not artist_name:
        return None

    ticket_url = f"{PUNCHLINE_BASE_URL}/f1-sections/?type=new&eventid={event_id}&showid={show_id}"
    info_url = f"{PUNCHLINE_BASE_URL}/comic/?id={event_id}&comic={quote(artist_name)}"

    event = {
        "venue": "The Punchline",
        "date": date,
        "doors_time": None,
        "show_time": normalize_time(_text(show_el, "showtimedesc") or _text(show_el, "showtime")),
        "artists": [{"name": artist_name}],
        "ticket_url": ticket_url,
        "info_url": info_url,
        "image_url": _text(event_el, "photopath") or None,
        "price": _format_price(_text(show_el, "price")),
        "category": "comedy",
    }

    description = _clean_punchline_description(_text(event_el, "comicdescription"))
    if description:
        event["description"] = description

    return event


def _text(node, tag):
    found = node.find(tag)
    if found is None or found.text is None:
        return None
    return " ".join(found.text.replace("\ufffd", "").split()).strip() or None


def _clean_punchline_description(value):
    if not value:
        return None

    value = value.replace("^^^", " ").replace("^^", " ").replace("^", " ")
    return clean_description(value)


def _format_price(value):
    if not value:
        return None

    try:
        amount = Decimal(value.strip().replace("$", "").replace(",", ""))
    except (InvalidOperation, AttributeError):
        return value.strip()

    if amount == amount.to_integral():
        return f"${amount:.0f}"
    return f"${amount:.2f}"
