import xml.etree.ElementTree as ET

from scraper.venues.helium import _extract_jsonld_events, _transform_helium_event
from scraper.venues.punchline import _transform_punchline_show


def test_transform_punchline_show_expands_showtime():
    event_el = ET.fromstring(
        """
        <event>
          <eventid>6843</eventid>
          <comicname>Nick Griffin</comicname>
          <photopath>https://reserve.punchline.com/photos/637.JPG</photopath>
          <comicdescription>Nick Griffin has appeared on late-night TV.</comicdescription>
        </event>
        """
    )
    show_el = ET.fromstring(
        """
        <show>
          <showtimeid>13173</showtimeid>
          <showdate>2026-05-10</showdate>
          <showtimedesc>07:00 PM</showtimedesc>
          <price>28</price>
        </show>
        """
    )

    event = _transform_punchline_show(event_el, show_el)

    assert event["venue"] == "The Punchline"
    assert event["date"] == "2026-05-10"
    assert event["show_time"] == "19:00"
    assert event["artists"] == [{"name": "Nick Griffin"}]
    assert event["ticket_url"].endswith("/f1-sections/?type=new&eventid=6843&showid=13173")
    assert event["info_url"].endswith("/comic/?id=6843&comic=Nick%20Griffin")
    assert event["price"] == "$28"
    assert event["category"] == "comedy"


def test_transform_helium_event_converts_utc_to_eastern_and_cleans_title():
    raw_event = {
        "name": "Special Event: Austin Nasso",
        "startDate": "2026-05-10T23:00:00Z",
        "description": "<p><strong>Austin Nasso</strong> is a comedian.</p><hr><h2>Package includes</h2>",
        "image": "https://files.seatengine.com/talent/headshots/photos/83737/full/data",
        "url": "https://atlanta.heliumcomedy.com/shows/341388",
        "offers": {"price": "35.00"},
    }

    event = _transform_helium_event(raw_event)

    assert event["venue"] == "Helium Comedy Club"
    assert event["date"] == "2026-05-10"
    assert event["show_time"] == "19:00"
    assert event["artists"] == [{"name": "Austin Nasso"}]
    assert event["ticket_url"] == "https://atlanta.heliumcomedy.com/shows/341388"
    assert event["description"] == "Austin Nasso is a comedian."
    assert event["price"] == "$35"
    assert event["category"] == "comedy"


def test_transform_helium_event_skips_postponed_events():
    assert _transform_helium_event({
        "name": "Helium Presents: Someone - POSTPONED",
        "startDate": "2026-05-10T23:00:00Z",
        "url": "https://atlanta.heliumcomedy.com/shows/1",
    }) is None


def test_extract_helium_jsonld_events():
    html = """
    <html>
      <script type="application/ld+json">
        {
          "@context": "http://schema.org",
          "@type": "Place",
          "Events": [
            {"@type": "Event", "name": "One"},
            {"@type": "Event", "name": "Two"}
          ]
        }
      </script>
    </html>
    """

    events = _extract_jsonld_events(html)

    assert [event["name"] for event in events] == ["One", "Two"]
