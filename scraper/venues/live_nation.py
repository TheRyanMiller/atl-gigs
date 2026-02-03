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
    def pages():
        offset = 0
        while True:
            payload = {
                "query": LIVE_NATION_QUERY,
                "variables": {"offset": offset, "venue_id": venue_id},
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
            "artists": [{"name": a["name"], "genre": a.get("genre")} for a in event["artists"]],
            "ticket_url": event["url"],
            "image_url": event["images"][0]["image_url"] if event["images"] else None,
            "category": get_category_from_genres(event.get("artists", [])),
        }

    return [transform_event(e) for e in itertools.chain.from_iterable(pages())]


def scrape_tabernacle():
    """Scrape events from Tabernacle's GraphQL API."""
    return scrape_live_nation_venue("KovZpaFEZe", "Tabernacle")


def scrape_coca_cola_roxy():
    """Scrape events from Coca-Cola Roxy's GraphQL API."""
    return scrape_live_nation_venue("KovZ917ACc7", "Coca-Cola Roxy")
