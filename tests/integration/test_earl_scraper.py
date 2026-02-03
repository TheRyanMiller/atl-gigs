from pathlib import Path

import pytest

responses = pytest.importorskip("responses")

from scraper.venues.earl import scrape_earl


def test_scrape_earl_parses_fixture(monkeypatch):
    monkeypatch.setattr("scraper.venues.earl.time.sleep", lambda *_: None)

    base = "https://badearl.com/show-calendar/"
    fixture = Path("tests/fixtures/earl_page.html").read_text()
    empty_fixture = Path("tests/fixtures/earl_empty.html").read_text()

    with responses.RequestsMock() as rsps:
        rsps.add(rsps.GET, base, body=fixture, status=200)
        rsps.add(rsps.GET, base + "?sf_paged=2", body=empty_fixture, status=200)

        events = scrape_earl()

    assert len(events) == 1
    event = events[0]
    assert event["venue"] == "The Earl"
    assert event["date"] == "2026-02-10"
    assert event["doors_time"] == "19:00"
    assert event["show_time"] == "20:00"
    assert event["ticket_url"] == "https://tickets.example.com"
    assert event["info_url"] == "https://info.example.com"
    assert [a["name"] for a in event["artists"]] == [
        "Headliner",
        "Support One",
        "Support Two",
    ]
