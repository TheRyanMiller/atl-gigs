import pytest

responses = pytest.importorskip("responses")

from scraper.venues.live_nation import LIVE_NATION_GRAPHQL_URL, scrape_live_nation_venue


def test_scrape_live_nation_maps_event_time_to_show_time(monkeypatch):
    monkeypatch.setattr("scraper.venues.live_nation.time.sleep", lambda *_: None)

    with responses.RequestsMock() as rsps:
        rsps.add(
            rsps.POST,
            LIVE_NATION_GRAPHQL_URL,
            json={
                "data": {
                    "getEvents": [
                        {
                            "artists": [{"name": "Headliner", "genre": "Rock"}],
                            "event_date": "2026-05-05",
                            "event_time": "19:30:00",
                            "event_end_time": None,
                            "name": "Headliner Tour",
                            "url": "https://tickets.example.com/headliner",
                            "images": [{"image_url": "https://images.example.com/headliner.jpg"}],
                        }
                    ]
                }
            },
            status=200,
        )

        events = scrape_live_nation_venue("venue-id", "Test Live Nation Venue")

    assert events == [
        {
            "venue": "Test Live Nation Venue",
            "date": "2026-05-05",
            "doors_time": None,
            "show_time": "19:30",
            "artists": [{"name": "Headliner", "genre": "Rock"}],
            "ticket_url": "https://tickets.example.com/headliner",
            "image_url": "https://images.example.com/headliner.jpg",
            "category": "concerts",
        }
    ]


def test_scrape_live_nation_raises_graphql_errors(monkeypatch):
    monkeypatch.setattr("scraper.venues.live_nation.time.sleep", lambda *_: None)

    with responses.RequestsMock() as rsps:
        rsps.add(
            rsps.POST,
            LIVE_NATION_GRAPHQL_URL,
            json={"errors": [{"message": "bad venue"}]},
            status=200,
        )

        with pytest.raises(RuntimeError, match="Live Nation GraphQL errors"):
            scrape_live_nation_venue("bad-id", "Bad Venue")


def test_scrape_live_nation_filters_events_missing_required_fields(monkeypatch):
    monkeypatch.setattr("scraper.venues.live_nation.time.sleep", lambda *_: None)

    with responses.RequestsMock() as rsps:
        rsps.add(
            rsps.POST,
            LIVE_NATION_GRAPHQL_URL,
            json={
                "data": {
                    "getEvents": [
                        {
                            "artists": [{"name": "No Ticket", "genre": "Rock"}],
                            "event_date": "2026-05-05",
                            "event_time": "19:30:00",
                            "event_end_time": None,
                            "name": "No Ticket",
                            "url": None,
                            "images": [],
                        },
                        {
                            "artists": [],
                            "event_date": "2026-05-06",
                            "event_time": "20:00:00",
                            "event_end_time": None,
                            "name": "Fallback Artist",
                            "url": "https://tickets.example.com/fallback",
                            "images": [],
                        },
                    ]
                }
            },
            status=200,
        )

        events = scrape_live_nation_venue("venue-id", "Test Live Nation Venue")

    assert len(events) == 1
    assert events[0]["artists"] == [{"name": "Fallback Artist"}]
