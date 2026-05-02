import pytest

responses = pytest.importorskip("responses")

from scraper import config
from scraper.tm import scrape_tm_venue


def test_scrape_tm_venue_parses_events_and_filters_invalid(monkeypatch):
    monkeypatch.setattr(config, "TM_API_KEY", "test-key")
    monkeypatch.setattr("scraper.tm.spotify_enrichment.cache_spotify_result", lambda *_, **__: None)

    with responses.RequestsMock() as rsps:
        rsps.add(
            rsps.GET,
            f"{config.TM_BASE_URL}/events.json",
            json={
                "_embedded": {
                    "events": [
                        {
                            "url": "https://ticketmaster.example.com/good",
                            "name": "Good Event",
                            "dates": {"start": {"localDate": "2026-05-02", "localTime": "20:00:00"}},
                            "_embedded": {
                                "attractions": [
                                    {
                                        "name": "Headliner",
                                        "classifications": [{"genre": {"name": "Rock"}}],
                                        "externalLinks": {
                                            "spotify": [{"url": "spotify:artist:ABC123"}],
                                        },
                                    }
                                ]
                            },
                            "priceRanges": [{"min": 0, "max": 0}],
                            "classifications": [{"segment": {"name": "Music"}, "genre": {"name": "Rock"}}],
                            "images": [
                                {"url": "https://images.example.com/small.jpg", "ratio": "16_9", "width": 200},
                                {"url": "https://images.example.com/large.jpg", "ratio": "16_9", "width": 1024},
                            ],
                        },
                        {
                            "url": None,
                            "name": "Missing Ticket",
                            "dates": {"start": {"localDate": "2026-05-03", "localTime": "20:00:00"}},
                        },
                    ]
                }
            },
            status=200,
        )

        events = scrape_tm_venue("venue-id", "TM Venue", stage="Main")

    assert events == [
        {
            "venue": "TM Venue",
            "date": "2026-05-02",
            "doors_time": None,
            "show_time": "20:00",
            "artists": [
                {
                    "name": "Headliner",
                    "genre": "Rock",
                    "spotify_url": "https://open.spotify.com/artist/ABC123",
                }
            ],
            "ticket_url": "https://ticketmaster.example.com/good",
            "image_url": "https://images.example.com/large.jpg",
            "price": "$0",
            "category": "concerts",
            "stage": "Main",
        }
    ]
