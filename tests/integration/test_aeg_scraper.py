import pytest

responses = pytest.importorskip("responses")

from scraper.venues.aeg import scrape_aeg_venue, transform_aeg_event


def test_transform_aeg_event_parses_valid_event():
    event = {
        "eventDateTime": "2026-05-02T20:00:00",
        "doorDateTime": "2026-05-02T19:00:00",
        "title": {
            "headlinersText": "Headliner",
            "supportingText": "Support",
        },
        "ticketing": {"url": "https://tickets.example.com/headliner"},
        "ticketPriceLow": "$20.00",
        "ticketPriceHigh": "$25.00",
        "media": {
            "small": {"width": 300, "file_name": "https://images.example.com/small.jpg"},
            "preferred": {"width": 678, "file_name": "https://images.example.com/preferred.jpg"},
        },
    }

    assert transform_aeg_event(event, "AEG Venue") == {
        "venue": "AEG Venue",
        "date": "2026-05-02",
        "doors_time": "19:00",
        "show_time": "20:00",
        "artists": [{"name": "Headliner"}, {"name": "Support"}],
        "ticket_url": "https://tickets.example.com/headliner",
        "image_url": "https://images.example.com/preferred.jpg",
        "price": "$20.00 - $25.00",
        "category": "concerts",
    }


def test_transform_aeg_event_skips_invalid_required_fields():
    valid_base = {
        "eventDateTime": "2026-05-02T20:00:00",
        "title": {"headlinersText": "Headliner"},
        "ticketing": {"url": "https://tickets.example.com/headliner"},
    }

    assert transform_aeg_event({**valid_base, "eventDateTime": "TBD"}, "AEG Venue") is None
    assert transform_aeg_event({**valid_base, "eventDateTime": "not-a-date"}, "AEG Venue") is None
    assert transform_aeg_event({**valid_base, "title": {}}, "AEG Venue") is None
    assert transform_aeg_event({**valid_base, "ticketing": {}}, "AEG Venue") is None


def test_scrape_aeg_venue_skips_bad_events_without_aborting():
    url = "https://example.com/aeg/events.json"

    with responses.RequestsMock() as rsps:
        rsps.add(
            rsps.GET,
            url,
            json={
                "events": [
                    {
                        "eventDateTime": "not-a-date",
                        "title": {"headlinersText": "Bad Date"},
                        "ticketing": {"url": "https://tickets.example.com/bad-date"},
                    },
                    {
                        "eventDateTime": "2026-05-02T20:00:00",
                        "title": {"headlinersText": "Good Event"},
                        "ticketing": {"url": "https://tickets.example.com/good"},
                    },
                ]
            },
            status=200,
        )

        events = scrape_aeg_venue(url, "AEG Venue")

    assert len(events) == 1
    assert events[0]["artists"] == [{"name": "Good Event"}]
