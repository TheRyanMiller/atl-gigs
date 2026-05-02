import pytest

responses = pytest.importorskip("responses")

from scraper.venues.center_stage import CENTER_STAGE_API, scrape_center_stage, transform_center_stage_event


def test_transform_center_stage_event_parses_valid_event():
    event = {
        "external_venue": "",
        "venue_room": {"value": "the_loft"},
        "event_date": "20260502",
        "title": "Stand-up Comedy Night",
        "event_url": "https://tickets.example.com/comedy",
        "door_time": "7:00 pm",
        "show_time": "8:00 pm",
        "event_image": "https://images.example.com/comedy.jpg",
        "permalink": "https://centerstage.example.com/events/comedy",
    }

    assert transform_center_stage_event(event) == {
        "venue": "Center Stage",
        "date": "2026-05-02",
        "doors_time": "19:00",
        "show_time": "20:00",
        "artists": [{"name": "Stand-up Comedy Night"}],
        "ticket_url": "https://tickets.example.com/comedy",
        "info_url": "https://centerstage.example.com/events/comedy",
        "image_url": "https://images.example.com/comedy.jpg",
        "category": "comedy",
        "stage": "The Loft",
    }


def test_transform_center_stage_event_skips_invalid_required_fields():
    valid_base = {
        "external_venue": "",
        "venue_room": {"value": "center_stage"},
        "event_date": "20260502",
        "title": "Headliner",
        "event_url": "https://tickets.example.com/headliner",
    }

    assert transform_center_stage_event({**valid_base, "external_venue": "Other Venue"}) is None
    assert transform_center_stage_event({**valid_base, "venue_room": None}) is None
    assert transform_center_stage_event({**valid_base, "event_date": "bad-date"}) is None
    assert transform_center_stage_event({**valid_base, "title": ""}) is None
    assert transform_center_stage_event({**valid_base, "event_url": ""}) is None


def test_scrape_center_stage_skips_bad_events_without_aborting(monkeypatch):
    monkeypatch.setattr("scraper.venues.center_stage.time.sleep", lambda *_: None)

    with responses.RequestsMock() as rsps:
        rsps.add(
            rsps.GET,
            f"{CENTER_STAGE_API}?page=1",
            json=[
                {
                    "external_venue": "",
                    "venue_room": None,
                    "event_date": "20260502",
                    "title": "Bad Venue Room",
                    "event_url": "https://tickets.example.com/bad",
                },
                {
                    "external_venue": "",
                    "venue_room": {"value": "vinyl"},
                    "event_date": "20260503",
                    "title": "Good Event",
                    "event_url": "https://tickets.example.com/good",
                },
            ],
            status=200,
        )

        events = scrape_center_stage()

    assert len(events) == 1
    assert events[0]["artists"] == [{"name": "Good Event"}]
    assert events[0]["stage"] == "Vinyl"
