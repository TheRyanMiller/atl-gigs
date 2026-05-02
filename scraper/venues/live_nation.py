import itertools
import os
import time

import requests

from scraper.utils.dates import normalize_time

LIVE_NATION_API_KEY = os.environ.get("LIVE_NATION_API_KEY", "da2-jmvb5y2gjfcrrep3wzeumqwgaq")
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
LIVE_NATION_PAGE_SIZE = 36
LIVE_NATION_TIMEOUT = (8, 20)


def get_category_from_genres(artists):
    """Determine event category from headliner's genre (not openers)."""
    if not artists:
        return "concerts"

    genre = (artists[0].get("genre") or "").lower()

    if any(kw in genre for kw in ["comedy", "stand-up", "standup", "comedian"]):
        return "comedy"
    if any(kw in genre for kw in ["theatre", "theater", "broadway", "musical"]):
        return "broadway"

    return "concerts"


def scrape_live_nation_venue(venue_id, venue_name):
    """Scrape events from a Live Nation venue's GraphQL API."""
    session = requests.Session()
    session.headers.update(LIVE_NATION_HEADERS)

    def pages():
        offset = 0
        while True:
            payload = {
                "query": LIVE_NATION_QUERY,
                "variables": {"offset": offset, "venue_id": venue_id},
            }
            resp = session.post(LIVE_NATION_GRAPHQL_URL, json=payload, timeout=LIVE_NATION_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            if data.get("errors"):
                raise RuntimeError(f"Live Nation GraphQL errors for {venue_name}: {data['errors']}")

            events = data.get("data", {}).get("getEvents", [])
            if not events:
                break

            yield events
            if len(events) < LIVE_NATION_PAGE_SIZE:
                break

            offset += LIVE_NATION_PAGE_SIZE
            time.sleep(0.4)

    def transform_event(event):
        event_date = event.get("event_date")
        ticket_url = event.get("url")
        artists = [
            {"name": a.get("name"), "genre": a.get("genre")}
            for a in event.get("artists", [])
            if a.get("name")
        ]
        if not artists and event.get("name"):
            artists = [{"name": event["name"]}]

        return {
            "venue": venue_name,
            "date": event_date,
            "doors_time": None,
            "show_time": normalize_time(event.get("event_time")),
            "artists": artists,
            "ticket_url": ticket_url,
            "image_url": next(
                (img.get("image_url") for img in event.get("images", []) if img.get("image_url")),
                None,
            ),
            "category": get_category_from_genres(event.get("artists", [])),
        }

    return [
        event
        for event in (transform_event(e) for e in itertools.chain.from_iterable(pages()))
        if event["date"] and event["ticket_url"] and event["artists"]
    ]


def scrape_tabernacle():
    """Scrape events from Tabernacle's GraphQL API."""
    return scrape_live_nation_venue("KovZpaFEZe", "Tabernacle")


def scrape_coca_cola_roxy():
    """Scrape events from Coca-Cola Roxy's GraphQL API."""
    return scrape_live_nation_venue("KovZ917ACc7", "Coca-Cola Roxy")
